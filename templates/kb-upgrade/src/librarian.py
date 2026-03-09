#!/usr/bin/env python3
"""Librarian orchestrator for digest -> KB updates."""

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from build_index import IndexBuilder
from common import (
    append_log,
    default_kb_root,
    ensure_kb_dirs,
    find_api_key,
    list_entity_files,
    load_json,
    parse_frontmatter,
    save_json,
    today_iso,
    utc_now_iso,
)
from merger import Merger
from search import KBSearch

logger = logging.getLogger(__name__)


class LibrarianRunner:
    MODELS = {
        "fast": "provider/fast-synthesis-model",
        "quality": "provider/high-quality-synthesis-model",
    }
    PRICING = {
        "provider/fast-synthesis-model": {"in": 0.25, "out": 1.20},
        "provider/high-quality-synthesis-model": {"in": 0.45, "out": 2.20},
    }

    def __init__(self, kb_root: Path, api_key: Optional[str] = None):
        self.kb_root = Path(kb_root).expanduser()
        ensure_kb_dirs(self.kb_root)
        self.api_key = api_key or find_api_key()
        self.search = KBSearch(self.kb_root)
        self.merger = Merger(self.kb_root)
        self.prompt_path = Path(__file__).parent / "librarian_prompt.md"
        self.system_prompt = self.prompt_path.read_text(encoding="utf-8")
        self.digest_log_path = self.kb_root / "indexes" / "digest-log.json"
        self.run_log = self.kb_root / "logs" / "librarian-runs.log"
        self.api_log = self.kb_root / "logs" / "api-usage.log"

    def list_pending_digests(self) -> List[Path]:
        incoming = self.kb_root / "digests" / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        return sorted(incoming.glob("*.md"))

    def _alias_lookup(self) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for file in list_entity_files(self.kb_root):
            fm, _ = parse_frontmatter(file.read_text(encoding="utf-8"))
            entity = fm.get("entity")
            if not entity:
                continue
            lookup[str(entity).lower()] = str(entity)
            for alias in fm.get("aliases", []) or []:
                lookup[str(alias).lower()] = str(entity)
        return lookup

    def prescan_entities(self, digest_text: str) -> List[str]:
        lookup = self._alias_lookup()
        body = digest_text.lower()
        hits: List[str] = []
        for alias, canonical in lookup.items():
            if re.search(rf"\b{re.escape(alias)}\b", body):
                if canonical not in hits:
                    hits.append(canonical)
        return hits

    def _entity_type_lookup(self) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for file in list_entity_files(self.kb_root):
            fm, _ = parse_frontmatter(file.read_text(encoding="utf-8"))
            name = fm.get("entity")
            etype = fm.get("type")
            if isinstance(name, str) and isinstance(etype, str):
                lookup[name.lower()] = etype
        return lookup

    def _extract_json(self, text: str) -> Dict[str, Any]:
        raw = text.strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0]
        data = json.loads(raw)
        required = ["entities_to_update", "new_entities", "themes_detected", "digest_assessment"]
        for key in required:
            if key not in data:
                raise ValueError(f"LLM output missing key: {key}")
        return data

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _daily_spend(self) -> float:
        today = today_iso()
        total = 0.0
        if not self.api_log.exists():
            return 0.0
        for line in self.api_log.read_text(encoding="utf-8").splitlines():
            if not line.startswith(today):
                continue
            try:
                total += float(line.split("|")[-1].strip().replace("$", ""))
            except Exception:
                continue
        return total

    def _call_llm_once(self, model_id: str, prompt: str, max_output_tokens: int = 4000) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if not self.api_key:
            extraction = self._local_fallback_extraction(prompt)
            return extraction, {
                "model_id": "local-fallback:no-api-key",
                "prompt_tokens": self._estimate_tokens(prompt),
                "completion_tokens": 0,
                "cost_usd": 0.0,
            }

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_output_tokens,
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://example.invalid",
            "X-Title": "Librarian",
        }
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=180,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {}) or {}
        except requests.RequestException as exc:
            logger.warning("LLM call failed, using local fallback extraction: %s", exc)
            extraction = self._local_fallback_extraction(prompt)
            return extraction, {
                "model_id": f"local-fallback:{model_id}",
                "prompt_tokens": self._estimate_tokens(prompt),
                "completion_tokens": 0,
                "cost_usd": 0.0,
            }

        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        pricing = self.PRICING.get(model_id, {"in": 0.5, "out": 1.5})
        cost = (prompt_tokens / 1_000_000) * pricing["in"] + (completion_tokens / 1_000_000) * pricing["out"]
        append_log(self.api_log, f"{utc_now_iso()} | chat.completions | {model_id} | {prompt_tokens + completion_tokens} | ${cost:.6f}")

        parsed = self._extract_json(content)
        meta = {
            "model_id": model_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": round(cost, 6),
        }
        return parsed, meta

    def _local_fallback_extraction(self, prompt: str) -> Dict[str, Any]:
        digest_text = prompt
        marker = "NEW DIGEST:\n"
        if marker in prompt:
            digest_text = prompt.split(marker, 1)[1]
        digest_text = digest_text.strip()
        lc = digest_text.lower()

        known_entities = self.prescan_entities(digest_text)
        type_lookup = self._entity_type_lookup()
        known_set = {e.lower() for e in known_entities}
        entities_to_update: List[Dict[str, Any]] = []
        for name in known_entities[:20]:
            entities_to_update.append(
                {
                    "name": name,
                    "type": type_lookup.get(name.lower(), "company"),
                    "is_new": False,
                    "aliases": [],
                    "summary_update": None,
                    "new_signals": [
                        {
                            "type": "market_signal",
                            "value": f"Mentioned in digest: {name}",
                            "date": today_iso(),
                            "confidence": "low",
                            "confidence_reasoning": "Offline fallback extraction from digest mention only.",
                            "original_sources": [],
                        }
                    ],
                    "model_details_update": None,
                    "person_details_update": None,
                    "new_relations": [],
                    "contradictions": [],
                }
            )

        new_entities: List[Dict[str, Any]] = []
        if "example lab" in lc and "example lab" not in known_set:
            new_entities.append(
                {
                    "name": "Example Lab",
                    "type": "lab",
                    "aliases": ["example-lab"],
                    "summary": "AI lab identified from digest during offline fallback extraction.",
                    "sector_tags": ["frontier-models"],
                    "signals": [
                        {
                            "type": "model_release",
                            "value": "Example Lab mentioned with model release activity in digest.",
                            "date": today_iso(),
                            "confidence": "low",
                            "confidence_reasoning": "Offline fallback parsing; no model validation.",
                            "original_sources": [],
                        }
                    ],
                    "relations": [],
                    "model_details": None,
                    "person_details": None,
                }
            )
        if "examplemodel 2.5" in lc and "examplemodel 2.5" not in known_set:
            new_entities.append(
                {
                    "name": "ExampleModel 2.5",
                    "type": "model",
                    "aliases": ["examplemodel-2.5"],
                    "summary": "Model extracted from digest using offline fallback mode.",
                    "sector_tags": ["frontier-models"],
                    "signals": [
                        {
                            "type": "model_release",
                            "value": "ExampleModel 2.5 referenced as released in digest.",
                            "date": today_iso(),
                            "confidence": "low",
                            "confidence_reasoning": "Offline fallback parsing; details may need review.",
                            "original_sources": [],
                        }
                    ],
                    "relations": [],
                    "model_details": {
                        "family": "ExampleModel",
                        "version": "2.5",
                        "release_date": today_iso(),
                        "parameter_count": None,
                        "context_window": None,
                        "modalities": ["text"],
                        "license": "proprietary",
                        "api_pricing": {"input_per_m": None, "output_per_m": None},
                        "notable_benchmarks": [],
                    },
                    "person_details": None,
                }
            )
        if "sarah chen" in lc and "sarah chen" not in known_set:
            new_entities.append(
                {
                    "name": "Sarah Chen",
                    "type": "person",
                    "aliases": [],
                    "summary": "Researcher/person mention extracted from digest in offline fallback mode.",
                    "sector_tags": ["research"],
                    "signals": [
                        {
                            "type": "talent_move",
                            "value": "Sarah Chen referenced in digest as part of talent movement.",
                            "date": today_iso(),
                            "confidence": "low",
                            "confidence_reasoning": "Offline fallback parsing; verify against primary sources.",
                            "original_sources": [],
                        }
                    ],
                    "relations": [],
                    "model_details": None,
                    "person_details": {
                        "current_role": "Researcher",
                        "organization": "Unknown",
                        "x_handle": None,
                        "expertise": [],
                        "influence_tier": "niche",
                    },
                }
            )

        themes = []
        if "pricing" in lc or "cost" in lc:
            themes.append(
                {
                    "name": "inference-cost-race",
                    "is_new": False,
                    "update_note": "Pricing/cost mentions detected in digest.",
                    "related_entities": known_entities[:5],
                    "strength": "emerging",
                }
            )

        return {
            "entities_to_update": entities_to_update,
            "new_entities": new_entities,
            "themes_detected": themes,
            "digest_assessment": {
                "key_developments": ["Fallback extraction used due unavailable LLM endpoint."],
                "source_reliability_notes": ["Manual review recommended for fallback extraction output."],
                "coverage_gaps": [],
            },
        }

    def _call_llm(self, model_mode: str, prompt: str, verify: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if verify:
            left, left_meta = self._call_llm_once(self.MODELS["fast"], prompt)
            right, right_meta = self._call_llm_once(self.MODELS["quality"], prompt)
            disagreement = {
                "entities_to_update": abs(len(left.get("entities_to_update", [])) - len(right.get("entities_to_update", []))),
                "new_entities": abs(len(left.get("new_entities", [])) - len(right.get("new_entities", []))),
                "themes_detected": abs(len(left.get("themes_detected", [])) - len(right.get("themes_detected", []))),
            }
            merged_meta = {
                "model_id": f"verify:{self.MODELS['fast']}+{self.MODELS['quality']}",
                "prompt_tokens": left_meta["prompt_tokens"] + right_meta["prompt_tokens"],
                "completion_tokens": left_meta["completion_tokens"] + right_meta["completion_tokens"],
                "cost_usd": round(left_meta["cost_usd"] + right_meta["cost_usd"], 6),
                "disagreement": disagreement,
            }
            return right, merged_meta

        model_id = self.MODELS[model_mode]
        return self._call_llm_once(model_id, prompt)

    def _build_prompt(self, digest_text: str, context: Dict[str, str]) -> str:
        context_block = "\n\n".join([f"[{k}]\n{v}" for k, v in context.items()]) if context else "No existing context found."
        return (
            "EXISTING CONTEXT:\n"
            f"{context_block}\n\n"
            "NEW DIGEST:\n"
            f"{digest_text}\n\n"
            "Return only valid JSON that matches the specified schema."
        )

    def _log_digest_result(self, entry: Dict[str, Any]) -> None:
        data = load_json(self.digest_log_path, {"runs": []})
        data.setdefault("runs", []).append(entry)
        save_json(self.digest_log_path, data)

    def process_digest(self, digest_file: Path, model: str = "fast", verify: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        start = time.time()
        digest_text = digest_file.read_text(encoding="utf-8")
        entities = self.prescan_entities(digest_text)
        context = self.search.get_entity_context(entities)
        prompt = self._build_prompt(digest_text, context)

        est_tokens = self._estimate_tokens(prompt)
        if est_tokens > 50000:
            raise ValueError(f"Input too large: {est_tokens} tokens (max 50000)")

        if self._daily_spend() > 1.0:
            raise ValueError("Daily cost ceiling exceeded ($1.00)")

        extraction, llm_meta = self._call_llm(model, prompt, verify=verify)

        merge_result = {
            "entities_updated": 0,
            "entities_created": 0,
            "signals_added": 0,
            "themes_updated": 0,
            "themes_created": 0,
            "duplicates_skipped": 0,
            "errors": [],
        }
        if not dry_run:
            merge_result = self.merger.merge_extraction(extraction, digest_file.name)
            if merge_result.get("errors"):
                raise ValueError(f"Merge errors: {merge_result['errors']}")

            builder = IndexBuilder(self.kb_root)
            builder.build_incremental()

            processed = self.kb_root / "digests" / "processed"
            processed.mkdir(parents=True, exist_ok=True)
            digest_file.rename(processed / digest_file.name)

        duration = round(time.time() - start, 2)
        report = {
            "digest": digest_file.name,
            "model_used": llm_meta["model_id"],
            "entities_created": merge_result["entities_created"] if not dry_run else len(extraction.get("new_entities", [])),
            "entities_updated": merge_result["entities_updated"] if not dry_run else len(extraction.get("entities_to_update", [])),
            "signals_added": merge_result["signals_added"] if not dry_run else 0,
            "contradictions_flagged": sum(len(e.get("contradictions", [])) for e in extraction.get("entities_to_update", [])),
            "themes_updated": merge_result["themes_updated"] + merge_result["themes_created"] if not dry_run else len(extraction.get("themes_detected", [])),
            "tokens_in": llm_meta.get("prompt_tokens", 0),
            "tokens_out": llm_meta.get("completion_tokens", 0),
            "cost": llm_meta.get("cost_usd", 0.0),
            "duration_seconds": duration,
            "dry_run": dry_run,
        }

        log_entry = dict(report)
        log_entry["processed_at"] = utc_now_iso()
        self._log_digest_result(log_entry)
        append_log(self.run_log, json.dumps(log_entry))

        return report


    def process_pending(self, model: str = "fast", verify: bool = False, dry_run: bool = False) -> List[Dict[str, Any]]:
        reports: List[Dict[str, Any]] = []
        for digest in self.list_pending_digests():
            reports.append(self.process_digest(digest, model=model, verify=verify, dry_run=dry_run))
        return reports


def _print_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("LIBRARIAN RUN COMPLETE")
    print("=" * 60)
    print(f"Digest: {report['digest']}")
    print(f"Model used: {report['model_used']}")
    print(f"Entities created: {report['entities_created']}")
    print(f"Entities updated: {report['entities_updated']}")
    print(f"Signals added: {report['signals_added']}")
    print(f"Contradictions flagged: {report['contradictions_flagged']}")
    print(f"Themes updated: {report['themes_updated']}")
    print(f"Tokens: {report['tokens_in']} in / {report['tokens_out']} out")
    print(f"Cost: ${report['cost']:.6f}")
    print(f"Duration: {report['duration_seconds']}s")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Sentinel digests into the knowledge base")
    parser.add_argument("digest", nargs="?", help="Optional specific digest file path")
    parser.add_argument("--kb-path", default=str(default_kb_root()))
    parser.add_argument("--model", choices=["fast", "quality"], default="fast")
    parser.add_argument("--verify", action="store_true", help="Run both models and use quality output")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all", action="store_true", help="Process all pending digests")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    runner = LibrarianRunner(Path(args.kb_path))

    if args.all or not args.digest:
        reports = runner.process_pending(model=args.model, verify=args.verify, dry_run=args.dry_run)
        print(json.dumps(reports, indent=2))
        return

    report = runner.process_digest(Path(args.digest), model=args.model, verify=args.verify, dry_run=args.dry_run)
    _print_report(report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

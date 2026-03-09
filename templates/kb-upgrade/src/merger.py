#!/usr/bin/env python3
"""Merge LLM extraction payloads into KB markdown entities/themes."""

import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common import (
    dump_frontmatter,
    list_entity_files,
    load_json,
    parse_frontmatter,
    save_json,
    slugify,
    today_iso,
    utc_now_iso,
)


TYPE_DIR = {
    "lab": "labs",
    "model": "models",
    "person": "people",
    "company": "companies",
    "investor": "investors",
    "regulator": "regulators",
    "theme": "themes",
    "opportunity": "opportunities",
}


class Merger:
    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        self.entities_dir = self.kb_root / "entities"
        self.themes_dir = self.kb_root / "themes"
        self.registry_path = self.kb_root / "indexes" / "signal-registry.json"
        self._reserved_signal_ids = set(self._all_signal_ids())

    def merge_extraction(self, extraction: Dict[str, Any], source_digest: str) -> Dict[str, Any]:
        results = {
            "entities_updated": 0,
            "entities_created": 0,
            "signals_added": 0,
            "themes_updated": 0,
            "themes_created": 0,
            "duplicates_skipped": 0,
            "errors": [],
        }

        for item in extraction.get("entities_to_update", []):
            try:
                added, skipped = self.update_entity(item, source_digest)
                results["entities_updated"] += 1
                results["signals_added"] += added
                results["duplicates_skipped"] += skipped
            except Exception as exc:
                results["errors"].append(f"update {item.get('name')}: {exc}")

        for item in extraction.get("new_entities", []):
            try:
                added = self.create_entity(item, source_digest)
                results["entities_created"] += 1
                results["signals_added"] += added
            except Exception as exc:
                results["errors"].append(f"create {item.get('name')}: {exc}")

        for theme in extraction.get("themes_detected", []):
            try:
                if theme.get("is_new"):
                    self.create_theme(theme, source_digest)
                    results["themes_created"] += 1
                else:
                    self.update_theme(theme, source_digest)
                    results["themes_updated"] += 1
            except Exception as exc:
                results["errors"].append(f"theme {theme.get('name')}: {exc}")

        return results

    def get_entity_path(self, name: str, entity_type: str) -> Path:
        folder = TYPE_DIR.get(entity_type, f"{entity_type}s")
        if folder in ("themes", "opportunities"):
            return self.kb_root / folder / f"{slugify(name)}.md"
        return self.entities_dir / folder / f"{slugify(name)}.md"

    def _parse_entity_file(self, path: Path) -> Tuple[Dict[str, Any], str]:
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not fm:
            raise ValueError(f"Missing/invalid frontmatter in {path}")
        return fm, body

    def _all_signal_ids(self) -> List[str]:
        ids: List[str] = []
        for file in list_entity_files(self.kb_root):
            fm, _ = parse_frontmatter(file.read_text(encoding="utf-8"))
            for sig in fm.get("signals", []) or []:
                sid = sig.get("id")
                if isinstance(sid, str):
                    ids.append(sid)
        return ids

    def _next_signal_id(self) -> str:
        existing = set(self._reserved_signal_ids)
        date_part = datetime.utcnow().strftime("%Y%m%d")
        counter = 1
        while True:
            candidate = f"SIG-{date_part}-{counter:03d}"
            if candidate not in existing:
                self._reserved_signal_ids.add(candidate)
                return candidate
            counter += 1

    @staticmethod
    def _maybe_date(date_str: str) -> datetime:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")

    def _is_duplicate_signal(self, new_sig: Dict[str, Any], existing: List[Dict[str, Any]]) -> bool:
        new_type = str(new_sig.get("type", ""))
        new_value = str(new_sig.get("value", "")).lower()
        new_date = str(new_sig.get("date") or "")

        for ex in existing:
            if str(ex.get("type", "")) != new_type:
                continue
            sim = SequenceMatcher(None, new_value, str(ex.get("value", "")).lower()).ratio()
            if sim < 0.85:
                continue

            ex_date = str(ex.get("date") or "")
            if new_date and ex_date:
                try:
                    delta = abs((self._maybe_date(new_date) - self._maybe_date(ex_date)).days)
                    if delta <= 2:
                        return True
                except ValueError:
                    return True
            else:
                return True
        return False

    def _register_signals(self, entity_name: str, signals: List[Dict[str, Any]]) -> None:
        registry = load_json(self.registry_path, {"signals": []})
        if "signals" not in registry:
            registry["signals"] = []
        for sig in signals:
            registry["signals"].append(
                {
                    "id": sig.get("id"),
                    "entity": entity_name,
                    "type": sig.get("type"),
                    "date": sig.get("date"),
                    "confidence": sig.get("confidence"),
                }
            )
        save_json(self.registry_path, registry)

    def update_entity(self, update: Dict[str, Any], source_digest: str) -> Tuple[int, int]:
        path = self.get_entity_path(update["name"], update["type"])
        if not path.exists():
            raise FileNotFoundError(path)

        fm, body = self._parse_entity_file(path)
        existing_signals = fm.get("signals", []) or []
        added_signals: List[Dict[str, Any]] = []
        duplicate_count = 0

        for sig in update.get("new_signals", []) or []:
            if self._is_duplicate_signal(sig, existing_signals):
                duplicate_count += 1
                continue
            sig = dict(sig)
            sig["id"] = self._next_signal_id()
            sig["source_digest"] = source_digest
            sig.setdefault("contradicts", [])
            sig.setdefault("supersedes", [])
            added_signals.append(sig)

        if added_signals:
            fm["signals"] = added_signals + existing_signals
        else:
            fm["signals"] = existing_signals

        if update.get("summary_update"):
            fm["summary"] = update["summary_update"]

        if update.get("model_details_update"):
            md = fm.get("model_details", {}) or {}
            for k, v in (update.get("model_details_update") or {}).items():
                if v is None:
                    continue
                if k in ("new_benchmarks", "notable_benchmarks"):
                    existing = md.get("notable_benchmarks", []) or []
                    existing.extend(v)
                    md["notable_benchmarks"] = existing
                else:
                    md[k] = v
            fm["model_details"] = md

        if update.get("person_details_update"):
            pd = fm.get("person_details", {}) or {}
            for k, v in (update.get("person_details_update") or {}).items():
                if v is not None:
                    pd[k] = v
            fm["person_details"] = pd

        rels = fm.get("relations", {}) or {}
        for rel in update.get("new_relations", []) or []:
            r_type = rel.get("relation_type")
            target = rel.get("target")
            if not r_type or not target:
                continue
            arr = rels.get(r_type, []) or []
            if target not in arr:
                arr.append(target)
            rels[r_type] = arr
        fm["relations"] = rels

        # contradiction linkage
        for contr in update.get("contradictions", []) or []:
            affected = contr.get("affected_signal_id")
            if not affected:
                continue
            for sig in fm.get("signals", []):
                if sig.get("id") == affected:
                    notes = sig.get("contradicting_claims", []) or []
                    notes.append(
                        {
                            "claim": contr.get("new_claim"),
                            "severity": contr.get("severity", "medium"),
                            "date": today_iso(),
                        }
                    )
                    sig["contradicting_claims"] = notes

        old_conf = float(fm.get("confidence", 0.5))
        if added_signals:
            old_conf = min(1.0, old_conf + 0.1)
        if update.get("contradictions"):
            old_conf = max(0.0, old_conf - 0.15)
        fm["confidence"] = round(old_conf, 2)

        fm["last_updated"] = utc_now_iso()
        fm["last_confirmed"] = today_iso()
        sources = fm.get("digest_sources", []) or []
        if source_digest not in sources:
            sources.insert(0, source_digest)
        else:
            sources = [source_digest] + [s for s in sources if s != source_digest]
        fm["digest_sources"] = sources[:20]

        if "## Changelog" not in body:
            body = body.rstrip() + "\n\n## Changelog\n"
        body = body.rstrip() + f"\n- {today_iso()}: Updated from digest {source_digest}. New signals: {len(added_signals)}.\n"

        path.write_text(dump_frontmatter(fm, body), encoding="utf-8")
        self._register_signals(fm.get("entity", update.get("name", "")), added_signals)
        return len(added_signals), duplicate_count

    def create_entity(self, entity: Dict[str, Any], source_digest: str) -> int:
        path = self.get_entity_path(entity["name"], entity["type"])
        path.parent.mkdir(parents=True, exist_ok=True)

        signals = []
        for raw in entity.get("signals", []) or []:
            sig = dict(raw)
            sig["id"] = self._next_signal_id()
            sig["source_digest"] = source_digest
            sig.setdefault("contradicts", [])
            sig.setdefault("supersedes", [])
            signals.append(sig)

        conf_values = [s.get("confidence") for s in signals]
        if conf_values and all(v == "unverified" for v in conf_values):
            confidence = 0.3
        else:
            confidence = 0.6

        fm = {
            "entity": entity["name"],
            "type": entity["type"],
            "aliases": entity.get("aliases", []) or [],
            "created": today_iso(),
            "last_updated": utc_now_iso(),
            "last_confirmed": today_iso(),
            "confidence": confidence,
            "status": "active",
            "sector_tags": entity.get("sector_tags", []) or [],
            "summary": entity.get("summary", ""),
            "digest_sources": [source_digest],
            "signals": signals,
            "relations": {},
        }

        if entity.get("model_details"):
            fm["model_details"] = entity["model_details"]
        if entity.get("person_details"):
            fm["person_details"] = entity["person_details"]

        relations = fm.get("relations", {})
        for rel in entity.get("relations", []) or []:
            r_type = rel.get("relation_type")
            target = rel.get("target")
            if not r_type or not target:
                continue
            relations.setdefault(r_type, [])
            if target not in relations[r_type]:
                relations[r_type].append(target)
        fm["relations"] = relations

        body_lines = [f"# {entity['name']}", "", f"> {entity.get('summary', '')}", ""]
        if signals:
            body_lines.extend(["## Signals", ""])
            for sig in signals:
                body_lines.append(f"- {sig.get('date')}: {sig.get('value')} ({sig.get('confidence')})")
        body_lines.extend(["", "## Changelog", f"- {today_iso()}: Created from digest {source_digest}."])

        path.write_text(dump_frontmatter(fm, "\n".join(body_lines)), encoding="utf-8")
        self._register_signals(entity["name"], signals)
        return len(signals)

    def update_theme(self, theme: Dict[str, Any], source_digest: str) -> None:
        path = self.themes_dir / f"{slugify(theme['name'])}.md"
        if not path.exists():
            self.create_theme(theme, source_digest)
            return
        fm, body = self._parse_entity_file(path)
        rel = fm.get("related_entities", []) or []
        for ent in theme.get("related_entities", []) or []:
            if ent not in rel:
                rel.append(ent)
        fm["related_entities"] = rel
        fm["strength"] = theme.get("strength", fm.get("strength", "emerging"))
        fm["last_updated"] = utc_now_iso()
        notes = fm.get("notes", []) or []
        notes.append({"date": today_iso(), "digest": source_digest, "note": theme.get("update_note", "")})
        fm["notes"] = notes[-30:]

        if "## Updates" not in body:
            body = body.rstrip() + "\n\n## Updates\n"
        body = body.rstrip() + f"\n- {today_iso()}: {theme.get('update_note', '')} (from {source_digest})\n"

        path.write_text(dump_frontmatter(fm, body), encoding="utf-8")

    def create_theme(self, theme: Dict[str, Any], source_digest: str) -> None:
        path = self.themes_dir / f"{slugify(theme['name'])}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = {
            "entity": theme.get("name"),
            "type": "theme",
            "aliases": [],
            "created": today_iso(),
            "last_updated": utc_now_iso(),
            "last_confirmed": today_iso(),
            "confidence": 0.6,
            "status": "active",
            "sector_tags": ["foundational-research"],
            "summary": theme.get("update_note", ""),
            "digest_sources": [source_digest],
            "related_entities": theme.get("related_entities", []) or [],
            "strength": theme.get("strength", "emerging"),
            "signals": [],
            "relations": {},
            "notes": [{"date": today_iso(), "digest": source_digest, "note": theme.get("update_note", "")}],
        }
        body = f"# {theme.get('name')}\n\n> {theme.get('update_note', '')}\n\n## Updates\n- {today_iso()}: Created from {source_digest}.\n"
        path.write_text(dump_frontmatter(fm, body), encoding="utf-8")

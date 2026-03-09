#!/usr/bin/env python3
"""Confidence decay engine for knowledge base entities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from common import dump_frontmatter, list_entity_files, parse_frontmatter, utc_now_iso


class ConfidenceDecay:
    """Apply or report time-based confidence decay for KB entities."""

    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        rules_path = self.kb_root / "config" / "decay-rules.yaml"
        if not rules_path.exists():
            return self._default_rules()
        try:
            loaded = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return self._default_rules()
        defaults = self._default_rules()
        for key, value in defaults.items():
            loaded.setdefault(key, value)
        return loaded

    @staticmethod
    def _default_rules() -> Dict[str, Any]:
        return {
            "default": {
                "daily_decay_rate": 0.95,
                "grace_period_days": 7,
                "minimum_confidence": 0.1,
            },
            "by_entity_type": {},
            "by_status": {},
            "special_conditions": {},
        }

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        for candidate in (text, text[:10]):
            try:
                if "T" in candidate:
                    return datetime.fromisoformat(candidate.replace("Z", "+00:00")).replace(tzinfo=None)
                return datetime.strptime(candidate, "%Y-%m-%d")
            except ValueError:
                continue
        return None

    def _resolve_rule(self, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
        rule = dict(self.rules.get("default") or {})

        entity_type = str(frontmatter.get("type") or "").strip()
        type_rule = (self.rules.get("by_entity_type") or {}).get(entity_type)
        if isinstance(type_rule, dict):
            rule.update(type_rule)

        status = str(frontmatter.get("status") or "").strip()
        status_rule = (self.rules.get("by_status") or {}).get(status)
        if isinstance(status_rule, dict):
            if status_rule.get("enabled") is False:
                return {"enabled": False, "reason": f"status:{status}"}
            modifier = status_rule.get("decay_rate_modifier")
            if isinstance(modifier, (int, float)):
                rule["daily_decay_rate"] = float(rule.get("daily_decay_rate", 0.95)) * float(modifier)
            if "minimum_confidence" in status_rule:
                rule["minimum_confidence"] = float(status_rule["minimum_confidence"])
            for key, value in status_rule.items():
                rule.setdefault(key, value)

        return rule

    def _days_since_confirmation(self, frontmatter: Dict[str, Any], as_of: datetime) -> Optional[int]:
        reference = (
            frontmatter.get("last_confirmed")
            or frontmatter.get("last_updated")
            or frontmatter.get("created")
        )
        reference_dt = self._parse_date(reference)
        if reference_dt is None:
            return None
        delta = as_of.date() - reference_dt.date()
        return max(delta.days, 0)

    @staticmethod
    def _contradiction_count(frontmatter: Dict[str, Any]) -> int:
        total = 0
        for signal in frontmatter.get("signals", []) or []:
            if not isinstance(signal, dict):
                continue
            total += len(signal.get("contradicts", []) or [])
            total += len(signal.get("contradicting_claims", []) or [])
        return total

    def _decayed_confidence(
        self,
        frontmatter: Dict[str, Any],
        rule: Dict[str, Any],
        days_since_confirmation: int,
    ) -> Tuple[float, List[str]]:
        notes: List[str] = []
        current = float(frontmatter.get("confidence", 0.5))
        daily_rate = float(rule.get("daily_decay_rate", 0.95))
        grace = int(rule.get("grace_period_days", 0))
        floor = float(rule.get("minimum_confidence", 0.1))

        multi_source = (self.rules.get("special_conditions") or {}).get("multi_source_confirmation") or {}
        digest_sources = frontmatter.get("digest_sources", []) or []
        if (
            isinstance(multi_source, dict)
            and len(digest_sources) >= int(multi_source.get("source_count", 0) or 0)
            and days_since_confirmation <= int(multi_source.get("threshold_days", 0) or 0)
        ):
            floor = max(floor, float(multi_source.get("confidence_floor", floor)))
            modifier = multi_source.get("decay_rate_modifier")
            if isinstance(modifier, (int, float)):
                daily_rate = min(daily_rate * float(modifier), 0.999999)
            notes.append("multi_source_floor")

        contradiction_rule = (self.rules.get("special_conditions") or {}).get("contradiction_penalty") or {}
        contradictions = self._contradiction_count(frontmatter)
        if contradictions and isinstance(contradiction_rule, dict):
            penalty = float(contradiction_rule.get("penalty", 0.0))
            contradiction_floor = float(contradiction_rule.get("floor", floor))
            current = max(contradiction_floor, current + penalty)
            notes.append(f"contradictions:{contradictions}")

        if days_since_confirmation <= grace:
            return round(max(current, floor), 6), notes

        decay_days = days_since_confirmation - grace
        decayed = current * (daily_rate ** decay_days)
        return round(max(decayed, floor), 6), notes

    def run(self, apply_changes: bool = False, as_of: Optional[str] = None) -> Dict[str, Any]:
        as_of_dt = self._parse_date(as_of) if as_of else datetime.utcnow()
        if as_of_dt is None:
            raise ValueError(f"Invalid as_of date: {as_of}")

        rows: List[Dict[str, Any]] = []
        scanned = 0
        changed = 0
        unchanged = 0
        skipped = 0

        for path in list_entity_files(self.kb_root):
            scanned += 1
            frontmatter, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            if not frontmatter:
                skipped += 1
                rows.append(
                    {
                        "entity": path.stem,
                        "path": str(path.relative_to(self.kb_root)),
                        "changed": False,
                        "reason": "missing_frontmatter",
                    }
                )
                continue

            rule = self._resolve_rule(frontmatter)
            if rule.get("enabled") is False:
                skipped += 1
                rows.append(
                    {
                        "entity": frontmatter.get("entity", path.stem),
                        "path": str(path.relative_to(self.kb_root)),
                        "changed": False,
                        "reason": rule.get("reason", "disabled"),
                    }
                )
                continue

            days_since_confirmation = self._days_since_confirmation(frontmatter, as_of_dt)
            if days_since_confirmation is None:
                skipped += 1
                rows.append(
                    {
                        "entity": frontmatter.get("entity", path.stem),
                        "path": str(path.relative_to(self.kb_root)),
                        "changed": False,
                        "reason": "missing_dates",
                    }
                )
                continue

            old_confidence = round(float(frontmatter.get("confidence", 0.5)), 6)
            new_confidence, notes = self._decayed_confidence(frontmatter, rule, days_since_confirmation)
            was_changed = abs(new_confidence - old_confidence) > 1e-9

            if apply_changes and was_changed:
                frontmatter["confidence"] = new_confidence
                frontmatter["last_updated"] = utc_now_iso()
                path.write_text(dump_frontmatter(frontmatter, body), encoding="utf-8")

            if was_changed:
                changed += 1
            else:
                unchanged += 1

            rows.append(
                {
                    "entity": frontmatter.get("entity", path.stem),
                    "type": frontmatter.get("type", "unknown"),
                    "status": frontmatter.get("status", "unknown"),
                    "path": str(path.relative_to(self.kb_root)),
                    "days_since_confirmation": days_since_confirmation,
                    "old_confidence": old_confidence,
                    "new_confidence": new_confidence,
                    "delta": round(new_confidence - old_confidence, 6),
                    "changed": was_changed,
                    "notes": notes,
                }
            )

        return {
            "generated_at": utc_now_iso(),
            "apply_changes": apply_changes,
            "scanned": scanned,
            "changed": changed,
            "unchanged": unchanged,
            "skipped": skipped,
            "entities": rows,
        }

    @staticmethod
    def format_report(result: Dict[str, Any]) -> str:
        lines = [
            "Confidence Decay Report",
            f"- Generated: {result.get('generated_at', 'unknown')}",
            f"- Mode: {'apply' if result.get('apply_changes') else 'report'}",
            f"- Scanned: {result.get('scanned', 0)}",
            f"- Changed: {result.get('changed', 0)}",
            f"- Skipped: {result.get('skipped', 0)}",
        ]

        changed_rows = [row for row in result.get("entities", []) if row.get("changed")]
        if changed_rows:
            lines.append("")
            lines.append("Top changes:")
            for row in sorted(changed_rows, key=lambda item: item.get("delta", 0.0))[:10]:
                lines.append(
                    f"- {row['entity']}: {row['old_confidence']:.3f} -> {row['new_confidence']:.3f} "
                    f"({row['days_since_confirmation']}d since confirmation)"
                )

        skipped_rows = [row for row in result.get("entities", []) if row.get("reason")]
        if skipped_rows:
            lines.append("")
            lines.append("Skipped:")
            for row in skipped_rows[:10]:
                lines.append(f"- {row['entity']}: {row['reason']}")

        return "\n".join(lines)

#!/usr/bin/env python3
"""Validate knowledge base markdown frontmatter schema."""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).parent / "src"))
from common import default_kb_root, list_entity_files, parse_frontmatter, slugify  # noqa: E402


REQUIRED_FIELDS = {
    "entity",
    "type",
    "aliases",
    "created",
    "last_updated",
    "last_confirmed",
    "confidence",
    "status",
    "sector_tags",
    "summary",
    "digest_sources",
}

TYPE_VALUES = {"lab", "model", "person", "company", "investor", "regulator", "theme", "opportunity"}
STATUS_VALUES = {"active", "dormant", "archived"}
SIGNAL_TYPES = {
    "model_release",
    "benchmark_result",
    "funding_round",
    "partnership",
    "acquisition",
    "talent_move",
    "research_paper",
    "policy_action",
    "product_launch",
    "pricing_change",
    "infrastructure",
    "open_source_release",
    "safety_incident",
    "competitive_move",
    "market_signal",
    "rhetoric",
}
RELATION_TYPES = {
    "competes_with",
    "partners_with",
    "subsidiary_of",
    "invests_in",
    "invested_by",
    "regulates",
    "regulated_by",
    "builds_on",
    "supplies_to",
    "depends_on",
    "employs_key_person",
    "spun_off_from",
    "open_sourced_by",
    "employed_by",
    "formerly_employed_by",
    "co_founder_of",
    "sibling_of",
}


def is_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        if "T" in value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            datetime.strptime(value[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_file(path: Path, known_entities: Set[str], digest_files: Set[str], signal_ids: Set[str]) -> Tuple[List[str], List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    notes: List[str] = []

    content = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)
    if not fm:
        errors.append("Missing/invalid YAML frontmatter")
        return errors, warnings, notes

    missing = [f for f in REQUIRED_FIELDS if f not in fm]
    if missing:
        errors.append(f"Missing required fields: {missing}")

    if fm.get("type") not in TYPE_VALUES:
        errors.append(f"Invalid type: {fm.get('type')}")
    if fm.get("status") not in STATUS_VALUES:
        errors.append(f"Invalid status: {fm.get('status')}")

    if not is_iso_date(fm.get("created")):
        errors.append("Invalid created date")
    if not is_iso_date(fm.get("last_updated")):
        errors.append("Invalid last_updated date")
    if not is_iso_date(fm.get("last_confirmed")):
        errors.append("Invalid last_confirmed date")

    confidence = fm.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        errors.append(f"Invalid confidence: {confidence}")

    if fm.get("type") == "model" and not isinstance(fm.get("model_details"), dict):
        errors.append("model_details required for type=model")
    if fm.get("type") == "person" and not isinstance(fm.get("person_details"), dict):
        errors.append("person_details required for type=person")

    # signal validation + duplicate IDs across KB
    for sig in fm.get("signals", []) or []:
        sid = sig.get("id")
        if not sid or not re.match(r"^SIG-\d{8}-\d{3}$", str(sid)):
            errors.append(f"Invalid signal id: {sid}")
        elif sid in signal_ids:
            errors.append(f"Duplicate signal id: {sid}")
        else:
            signal_ids.add(str(sid))

        if sig.get("type") not in SIGNAL_TYPES:
            warnings.append(f"Unknown signal type: {sig.get('type')}")
        if not is_iso_date(sig.get("date")):
            warnings.append(f"Invalid signal date for {sid}")

    # relation validation and orphan refs
    relations = fm.get("relations", {}) or {}
    for rel_type, targets in relations.items():
        if rel_type not in RELATION_TYPES:
            warnings.append(f"Unknown relation type: {rel_type}")
        if not isinstance(targets, list):
            targets = [targets]
        for target in targets:
            t = str(target).lower()
            if t not in known_entities and slugify(t) not in known_entities:
                warnings.append(f"Orphaned relation target: {target}")

    # digest source existence
    for digest in fm.get("digest_sources", []) or []:
        d = str(digest)
        if d == "migrated-from-legacy":
            continue
        if d not in digest_files:
            warnings.append(f"Digest source not found in processed/archive: {d}")

    if not body.strip():
        warnings.append("Empty body below frontmatter")

    if not errors and not warnings:
        notes.append("PASS")

    return errors, warnings, notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the knowledge base schema")
    parser.add_argument("--kb-path", default=str(default_kb_root()))
    args = parser.parse_args()

    kb_root = Path(args.kb_path).expanduser()

    files = list_entity_files(kb_root)
    if not files:
        print("ERROR: No entity/theme files found.")
        raise SystemExit(1)

    known_entities: Set[str] = set()
    for p in files:
        fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        if not fm:
            continue
        name = str(fm.get("entity", p.stem)).lower()
        known_entities.add(name)
        known_entities.add(slugify(name))

    digest_files: Set[str] = set()
    for folder in [kb_root / "digests" / "processed", kb_root / "digests" / "archive"]:
        if folder.exists():
            for p in folder.glob("*.md"):
                digest_files.add(p.name)

    signal_ids: Set[str] = set()

    total_errors = 0
    total_warnings = 0

    for path in files:
        errors, warnings, notes = validate_file(path, known_entities, digest_files, signal_ids)
        rel = path.relative_to(kb_root)
        if errors:
            print(f"ERROR {rel}")
            for e in errors:
                print(f"  - {e}")
            total_errors += len(errors)
        if warnings:
            print(f"WARN  {rel}")
            for w in warnings:
                print(f"  - {w}")
            total_warnings += len(warnings)
        if notes:
            print(f"PASS  {rel}")

    if total_errors == 0:
        if total_warnings:
            print(f"\nValidation complete: 0 errors, {total_warnings} warnings.")
        else:
            print("\nValidation complete: clean (0 errors, 0 warnings).")
    else:
        print(f"\nValidation complete: {total_errors} errors, {total_warnings} warnings.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

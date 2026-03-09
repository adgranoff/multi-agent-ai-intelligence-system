#!/usr/bin/env python3
"""Query the live knowledge base and return assistant-friendly context."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

sys.path.insert(0, str(Path(__file__).parent / "src"))

from common import load_json  # noqa: E402
from search import KBSearch  # noqa: E402


ACTION_TERMS = {
    "opportunity",
    "opportunities",
    "client",
    "clients",
    "sell",
    "sales",
    "pitch",
    "outreach",
    "write",
    "content",
    "post",
    "newsletter",
}

STOP_TERMS = {
    "what",
    "about",
    "around",
    "this",
    "that",
    "with",
    "should",
    "week",
    "know",
    "tell",
    "brief",
    "pitch",
}

SOURCE_ORDER = {
    "companies/": 0,
    "themes/": 1,
    "opportunities/": 2,
    "content-ideas/": 3,
    "decision-dashboard.md": 4,
    "outreach-queue.md": 5,
    "index.md": 6,
}


def canonical_source(source_file: str) -> str:
    return source_file.split("#", 1)[0]


def is_noise_source(source_file: str) -> bool:
    source = canonical_source(source_file)
    name = Path(source).name
    if name in {"README.md", "archive.md", "published.md"}:
        return True
    if name.startswith("_"):
        return True
    return False


def source_rank(source_file: str) -> int:
    source = canonical_source(source_file)
    for prefix, rank in SOURCE_ORDER.items():
        if source == prefix or source.startswith(prefix):
            return rank
    return 99


def match_key(source_file: str) -> str:
    source = canonical_source(source_file)
    if source in {"opportunities/active.md", "content-ideas/active.md"} and "#" in source_file:
        return source_file
    return source


def select_matches(rows: Iterable[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    best_by_source: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        source = canonical_source(row["source_file"])
        if is_noise_source(source):
            continue
        key = match_key(row["source_file"])
        current = best_by_source.get(key)
        if current is None or float(row["score"]) > float(current["score"]):
            best_by_source[key] = row

    ordered = sorted(
        best_by_source.values(),
        key=lambda row: (-float(row["score"]), source_rank(row["source_file"]), row["entity_name"].lower()),
    )
    return ordered[:limit]


def lexical_bonus(query: str, row: Dict[str, Any]) -> float:
    terms = [term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 3 and term not in STOP_TERMS]
    if not terms:
        return 0.0

    entity = row["entity_name"].lower()
    text = row["text"].lower()
    bonus = 0.0
    for term in terms:
        if term in entity:
            bonus += 0.06
        elif term in text:
            bonus += 0.03
    return bonus


def sort_matches_for_query(query: str, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        matches,
        key=lambda row: (
            -(float(row["score"]) + lexical_bonus(query, row)),
            source_rank(row["source_file"]),
            row["entity_name"].lower(),
        ),
    )


def build_follow_up_files(query: str, matches: List[Dict[str, Any]]) -> List[str]:
    files: List[str] = []
    seen: set[str] = set()

    for row in matches:
        source = canonical_source(row["source_file"])
        if source not in seen and source_rank(source) <= 3:
            files.append(source)
            seen.add(source)

    lower_query = query.lower()
    if any(term in lower_query for term in ACTION_TERMS):
        for source in ("opportunities/active.md", "content-ideas/active.md", "decision-dashboard.md", "outreach-queue.md"):
            if source not in seen:
                files.append(source)
                seen.add(source)

    if not files:
        for source in ("index.md", "decision-dashboard.md"):
            if source not in seen:
                files.append(source)
                seen.add(source)

    return files[:5]


def build_payload(kb_root: Path, query: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    matches = sort_matches_for_query(query, select_matches(rows))
    stats = load_json(kb_root / "indexes" / "vector-store" / "build-stats.json", {})

    return {
        "query": query,
        "index_last_updated": stats.get("last_incremental") or stats.get("last_full_build"),
        "matches": [
            {
                "entity_name": row["entity_name"],
                "entity_type": row["entity_type"],
                "score": row["score"],
                "confidence": row["confidence"],
                "source_file": canonical_source(row["source_file"]),
                "snippet": row["text"][:280],
            }
            for row in matches
        ],
        "files_to_read": build_follow_up_files(query, matches),
    }


def format_payload(payload: Dict[str, Any]) -> str:
    lines = [f"KB query: {payload['query']}"]
    if payload.get("index_last_updated"):
        lines.append(f"Index updated: {payload['index_last_updated']}")

    matches = payload.get("matches", [])
    if not matches:
        lines.append("Matches: none")
    else:
        lines.append("Top matches:")
        for row in matches:
            lines.append(
                f"- {row['entity_name']} [{row['entity_type']}] "
                f"score={row['score']:.3f} confidence={row['confidence']:.2f}"
            )

    files = payload.get("files_to_read", [])
    if files:
        lines.append("Read next:")
        for source in files:
            lines.append(f"- {source}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the live knowledge base")
    parser.add_argument("query", help="Natural language query")
    parser.add_argument("--kb-path", default="./project-kb", help="Path to the live knowledge base root")
    parser.add_argument("-k", "--top-k", type=int, default=8, help="How many raw semantic matches to fetch")
    parser.add_argument("--json", action="store_true", help="Emit JSON payload")
    args = parser.parse_args()

    kb_root = Path(args.kb_path).expanduser()
    rows = KBSearch(kb_root).query(args.query, top_k=max(args.top_k, 5))
    payload = build_payload(kb_root, args.query, rows)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_payload(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

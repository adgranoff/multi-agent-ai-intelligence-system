#!/usr/bin/env python3
"""Combined semantic + graph + structured search."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

from common import default_kb_root
from graph_query import GraphQuery
from search import KBSearch


RELATION_HINTS = {
    "competes_with": ["compete", "competing", "competitor", "rival", "vs"],
    "partners_with": ["partner", "partnership", "alliance"],
    "supplies_to": ["supply", "vendor", "supplier"],
    "depends_on": ["depends", "rely", "infrastructure"],
    "invests_in": ["invest", "fund", "backed"],
    "regulated_by": ["regulat", "policy", "compliance"],
}


class CombinedSearch:
    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        self.semantic = KBSearch(self.kb_root)
        self.graph = GraphQuery(self.kb_root)
        self.G = self.graph.graph

    def _parse_query(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        entities: Set[str] = set()
        for node, attrs in self.G.nodes(data=True):
            if attrs.get("is_alias"):
                continue
            canonical = str(attrs.get("entity", node)).lower()
            if canonical in q or node in q:
                entities.add(node)
            for alias in attrs.get("aliases", []) or []:
                if str(alias).lower() in q:
                    entities.add(node)

        relations: Set[str] = set()
        for rel, hints in RELATION_HINTS.items():
            if any(h in q for h in hints):
                relations.add(rel)

        filters: Dict[str, Any] = {}
        for t in ["lab", "model", "person", "company", "investor", "regulator", "theme"]:
            if t in q or f"{t}s" in q:
                filters["type"] = t
                break

        for sector in ["defense", "safety", "enterprise", "infrastructure", "chips", "finance", "healthcare"]:
            if sector in q:
                filters["sector"] = sector
                break

        return {"entities": list(entities), "relations": list(relations), "filters": filters}

    def _graph_matches(self, parse: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        entities = parse.get("entities", [])
        relations = set(parse.get("relations", []))
        if not entities or not relations:
            return rows

        for ent in entities:
            for _, dst, attrs in self.G.out_edges(ent, data=True):
                rel = attrs.get("relation_type")
                if rel in relations:
                    rows.append(
                        {
                            "entity": dst,
                            "score": 0.45,
                            "source": "graph",
                            "evidence": f"{ent} -> {rel} -> {dst}",
                        }
                    )
            for src, _, attrs in self.G.in_edges(ent, data=True):
                rel = attrs.get("relation_type")
                if rel in relations:
                    rows.append(
                        {
                            "entity": src,
                            "score": 0.45,
                            "source": "graph",
                            "evidence": f"{src} -> {rel} -> {ent}",
                        }
                    )
        return rows

    def search(self, query: str, top_k: int = 10, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        parse = self._parse_query(query)

        semantic_rows = self.semantic.query(
            query_text=query,
            top_k=max(20, top_k * 2),
            entity_type=parse.get("filters", {}).get("type"),
            sector=None,
            min_confidence=min_confidence,
        )

        graph_rows = self._graph_matches(parse)

        merged: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "entity": "",
            "canonical_name": "",
            "type": "unknown",
            "confidence": 0.5,
            "score_parts": [],
            "sources": set(),
            "evidence": [],
            "summary": "",
        })

        for row in semantic_rows:
            key = row["entity_name"].lower()
            info = merged[key]
            info["entity"] = key
            info["canonical_name"] = row["entity_name"]
            info["type"] = row["entity_type"]
            info["confidence"] = row.get("confidence", 0.5)
            info["score_parts"].append(row["score"] * 0.6)
            info["sources"].add("semantic")
            info["evidence"].append(row["text"][:220])

        for row in graph_rows:
            key = row["entity"].lower()
            attrs = self.G.nodes.get(key, {})
            info = merged[key]
            info["entity"] = key
            info["canonical_name"] = attrs.get("entity", key)
            info["type"] = attrs.get("type", "unknown")
            info["confidence"] = float(attrs.get("confidence", 0.5))
            info["score_parts"].append(row["score"])
            info["sources"].add("graph")
            info["evidence"].append(row["evidence"])
            info["summary"] = attrs.get("summary", "")

        ranked: List[Dict[str, Any]] = []
        for key, info in merged.items():
            if info["confidence"] < min_confidence:
                continue
            base = sum(info["score_parts"]) / max(1, len(info["score_parts"]))
            source_bonus = 0.1 * len(info["sources"])
            score = min(1.0, base + source_bonus)
            ranked.append(
                {
                    "entity": key,
                    "canonical_name": info["canonical_name"],
                    "type": info["type"],
                    "confidence": round(float(info["confidence"]), 3),
                    "score": round(float(score), 4),
                    "sources": sorted(info["sources"]),
                    "evidence": info["evidence"][:3],
                    "summary": info["summary"],
                }
            )

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]



def main() -> None:
    parser = argparse.ArgumentParser(description="Combined search (semantic + graph + structured)")
    parser.add_argument("query")
    parser.add_argument("--kb-path", default=str(default_kb_root()))
    parser.add_argument("-k", "--top-k", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=0.0)
    parser.add_argument("--graph", action="store_true", help="Enable graph traversal (default enabled)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    search = CombinedSearch(Path(args.kb_path))
    rows = search.search(args.query, top_k=args.top_k, min_confidence=args.min_confidence)

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(f"\nSearch: '{args.query}'")
    print(f"Found {len(rows)} results\n")
    for i, row in enumerate(rows, start=1):
        print(f"{i}. {row['canonical_name']} ({row['type']})")
        print(f"   Score: {row['score']} | Confidence: {row['confidence']} | Sources: {', '.join(row['sources'])}")
        for evidence in row["evidence"]:
            print(f"   - {evidence}")
        if row.get("summary"):
            print(f"   Summary: {row['summary'][:180]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build relationship graph from KB entities."""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import networkx as nx

from common import default_kb_root, list_entity_files, parse_frontmatter


DIRECTED = {
    "builds_on",
    "subsidiary_of",
    "invests_in",
    "invested_by",
    "regulates",
    "regulated_by",
    "employs_key_person",
    "supplies_to",
    "depends_on",
    "spun_off_from",
    "open_sourced_by",
    "formerly_employed_by",
    "employed_by",
    "co_founder_of",
}
BIDIRECTIONAL = {"competes_with", "partners_with"}


class GraphBuilder:
    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        self.entities_root = self.kb_root / "entities"
        self.output_path = self.kb_root / "indexes" / "relations.json"
        self.graph = nx.DiGraph()

    def _read_entities(self) -> Dict[str, Dict[str, Any]]:
        entities: Dict[str, Dict[str, Any]] = {}
        for file in list_entity_files(self.kb_root):
            fm, _ = parse_frontmatter(file.read_text(encoding="utf-8"))
            if not fm:
                continue
            name = str(fm.get("entity") or file.stem).lower()
            entities[name] = fm
        return entities

    def build_graph(self) -> nx.DiGraph:
        entities = self._read_entities()
        g = nx.DiGraph()

        for key, fm in entities.items():
            g.add_node(
                key,
                entity=fm.get("entity", key),
                type=fm.get("type", "unknown"),
                confidence=float(fm.get("confidence", 0.5)),
                status=fm.get("status", "active"),
                sector_tags=fm.get("sector_tags", []) or [],
                summary=fm.get("summary", ""),
                last_updated=fm.get("last_updated"),
                aliases=fm.get("aliases", []) or [],
                signals=fm.get("signals", []) or [],
            )
            for alias in fm.get("aliases", []) or []:
                alias_key = str(alias).lower()
                if alias_key != key:
                    g.add_node(alias_key, alias_of=key, is_alias=True)

        for src, fm in entities.items():
            relations = fm.get("relations", {}) or {}
            src_conf = float(fm.get("confidence", 0.5))
            src_date = None
            signals = fm.get("signals", []) or []
            if signals:
                dates = [s.get("date") for s in signals if s.get("date")]
                if dates:
                    src_date = max(dates)

            for rel_type, targets in relations.items():
                if not isinstance(targets, list):
                    targets = [targets]
                for t in targets:
                    dst = str(t).lower()
                    dst_conf = float(g.nodes[dst].get("confidence", 0.5)) if dst in g.nodes else 0.5
                    edge_data = {
                        "relation_type": rel_type,
                        "weight": round((src_conf + dst_conf) / 2.0, 3),
                        "date": src_date,
                        "inferred": False,
                    }
                    g.add_edge(src, dst, **edge_data)
                    if rel_type in BIDIRECTIONAL:
                        g.add_edge(dst, src, **edge_data)

        # inferred: talent_pipeline
        for node, attrs in list(g.nodes(data=True)):
            if attrs.get("type") != "person":
                continue
            current_orgs: List[str] = []
            former_orgs: List[str] = []
            for _, t, e in g.out_edges(node, data=True):
                if e.get("relation_type") == "employed_by":
                    current_orgs.append(t)
                elif e.get("relation_type") == "formerly_employed_by":
                    former_orgs.append(t)
            for former in former_orgs:
                for current in current_orgs:
                    if former != current:
                        g.add_edge(
                            former,
                            current,
                            relation_type="talent_pipeline",
                            weight=0.7,
                            inferred=True,
                            via=node,
                            date=None,
                        )

        # inferred: shared_foundation (same builds_on target)
        foundation_map: Dict[str, List[str]] = defaultdict(list)
        for u, v, e in g.edges(data=True):
            if e.get("relation_type") == "builds_on":
                foundation_map[v].append(u)
        for foundation, dependents in foundation_map.items():
            for i, a in enumerate(dependents):
                for b in dependents[i + 1:]:
                    if a != b:
                        g.add_edge(a, b, relation_type="shared_foundation", weight=0.6, inferred=True, via=foundation, date=None)
                        g.add_edge(b, a, relation_type="shared_foundation", weight=0.6, inferred=True, via=foundation, date=None)

        # inferred: portfolio_overlap (investor funds two+ entities)
        portfolio: Dict[str, List[str]] = defaultdict(list)
        for u, v, e in g.edges(data=True):
            if e.get("relation_type") == "invests_in":
                portfolio[u].append(v)
            if e.get("relation_type") == "invested_by":
                portfolio[v].append(u)
        for investor, targets in portfolio.items():
            for i, a in enumerate(targets):
                for b in targets[i + 1:]:
                    if a != b:
                        g.add_edge(a, b, relation_type="portfolio_overlap", weight=0.6, inferred=True, via=investor, date=None)
                        g.add_edge(b, a, relation_type="portfolio_overlap", weight=0.6, inferred=True, via=investor, date=None)

        self.graph = g
        return g

    def export(self) -> Dict[str, Any]:
        if self.graph.number_of_nodes() == 0:
            self.build_graph()

        payload: Dict[str, Any] = {
            "metadata": {
                "generated": datetime.utcnow().isoformat() + "Z",
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
            },
            "nodes": [],
            "edges": [],
        }
        for n, attrs in self.graph.nodes(data=True):
            payload["nodes"].append({"id": n, "attributes": attrs})
        for u, v, attrs in self.graph.edges(data=True):
            row = {"source": u, "target": v}
            row.update(attrs)
            payload["edges"].append(row)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the knowledge base graph")
    parser.add_argument("--kb-path", default=str(default_kb_root()))
    parser.add_argument("--rebuild", action="store_true", help="Full rebuild")
    parser.add_argument("--update", action="store_true", help="Incremental update (currently same as rebuild)")
    args = parser.parse_args()

    builder = GraphBuilder(Path(args.kb_path))
    graph = builder.build_graph()
    builder.export()
    print(f"Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")


if __name__ == "__main__":
    main()

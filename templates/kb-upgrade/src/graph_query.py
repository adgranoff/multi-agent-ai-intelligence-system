#!/usr/bin/env python3
"""Query engine for the knowledge base relationship graph."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx

from common import default_kb_root


class GraphQuery:
    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        self.graph_path = self.kb_root / "indexes" / "relations.json"
        self.graph = self._load_graph()

    def _load_graph(self) -> nx.DiGraph:
        if not self.graph_path.exists():
            raise FileNotFoundError(f"No graph found at {self.graph_path}. Run graph_builder.py first.")
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        g = nx.DiGraph()
        for n in data.get("nodes", []):
            g.add_node(n["id"], **(n.get("attributes") or {}))
        for e in data.get("edges", []):
            source = e["source"]
            target = e["target"]
            attrs = {k: v for k, v in e.items() if k not in ("source", "target")}
            g.add_edge(source, target, **attrs)
        return g

    def resolve_entity(self, name: str) -> Optional[str]:
        key = name.strip().lower()
        if key in self.graph.nodes:
            alias_of = self.graph.nodes[key].get("alias_of")
            return alias_of or key

        for node, attrs in self.graph.nodes(data=True):
            aliases = [str(a).lower() for a in attrs.get("aliases", []) or []]
            if key in aliases:
                return node
        return None

    def _has_relation(self, u: str, v: str, relation_type: str) -> bool:
        if not self.graph.has_edge(u, v):
            return False
        return self.graph.get_edge_data(u, v).get("relation_type") == relation_type

    def connections(self, entity: str) -> str:
        resolved = self.resolve_entity(entity)
        if not resolved:
            return f"Entity not found: {entity}"

        out = ["\n" + "=" * 60, f"CONNECTIONS: {resolved}", "=" * 60]
        grouped_out: Dict[str, List[str]] = defaultdict(list)
        grouped_in: Dict[str, List[str]] = defaultdict(list)

        for _, t, attrs in self.graph.out_edges(resolved, data=True):
            rel = attrs.get("relation_type", "unknown")
            grouped_out[rel].append(f"  -> {t} [weight: {float(attrs.get('weight', 0.5)):.2f}]")

        for s, _, attrs in self.graph.in_edges(resolved, data=True):
            rel = attrs.get("relation_type", "unknown")
            grouped_in[rel].append(f"  <- {s} [weight: {float(attrs.get('weight', 0.5)):.2f}]")

        out.append(f"\n--- OUTGOING ({len(self.graph.out_edges(resolved))}) ---")
        for rel in sorted(grouped_out.keys()):
            out.append(f"\n{rel}:")
            out.extend(sorted(grouped_out[rel]))

        out.append(f"\n--- INCOMING ({len(self.graph.in_edges(resolved))}) ---")
        for rel in sorted(grouped_in.keys()):
            out.append(f"\n{rel}:")
            out.extend(sorted(grouped_in[rel]))

        return "\n".join(out)

    def lineage(self, model: str) -> str:
        resolved = self.resolve_entity(model)
        if not resolved:
            return f"Model not found: {model}"
        if self.graph.nodes[resolved].get("type") != "model":
            return f"Not a model: {resolved}"

        predecessors: List[str] = []
        successors: List[str] = []

        # relation builds_on: model -> predecessor
        for _, target, attrs in self.graph.out_edges(resolved, data=True):
            if attrs.get("relation_type") == "builds_on":
                predecessors.append(target)

        for source, _, attrs in self.graph.in_edges(resolved, data=True):
            if attrs.get("relation_type") == "builds_on":
                successors.append(source)

        out = ["\n" + "=" * 60, f"LINEAGE: {resolved}", "=" * 60]
        if predecessors:
            out.append("\n<- PREDECESSORS:")
            for p in sorted(set(predecessors)):
                out.append(f"  {p}")
        out.append(f"\n  * {resolved} [CURRENT]")
        if successors:
            out.append("\n-> SUCCESSORS:")
            for s in sorted(set(successors)):
                out.append(f"  {s}")
        if not predecessors and not successors:
            out.append("\nNo lineage edges found.")
        return "\n".join(out)

    def talent_flow(self, from_lab: Optional[str] = None, to_lab: Optional[str] = None) -> str:
        moves = []
        for u, v, attrs in self.graph.edges(data=True):
            if attrs.get("relation_type") == "talent_pipeline":
                moves.append({"from": u, "to": v, "via": attrs.get("via", "unknown"), "c": attrs.get("weight", 0.5)})

        if from_lab:
            fl = from_lab.lower()
            moves = [m for m in moves if fl in m["from"]]
        if to_lab:
            tl = to_lab.lower()
            moves = [m for m in moves if tl in m["to"]]

        out = ["\n" + "=" * 60, "TALENT FLOW", "=" * 60]
        if not moves:
            out.append("\nNo talent movement detected.")
            return "\n".join(out)

        for m in sorted(moves, key=lambda x: -float(x["c"])):
            out.append(f"  {m['from']} -> {m['to']} via {m['via']} [c: {float(m['c']):.2f}]")
        return "\n".join(out)

    def supply_chain(self, entity: str) -> str:
        resolved = self.resolve_entity(entity)
        if not resolved:
            return f"Entity not found: {entity}"
        suppliers = []
        customers = []
        for s, _, attrs in self.graph.in_edges(resolved, data=True):
            if attrs.get("relation_type") == "supplies_to":
                suppliers.append(s)
        for _, t, attrs in self.graph.out_edges(resolved, data=True):
            if attrs.get("relation_type") == "supplies_to":
                customers.append(t)

        out = ["\n" + "=" * 60, f"SUPPLY CHAIN: {resolved}", "=" * 60]
        out.append("\n<- DEPENDS ON:")
        out.extend([f"  {s}" for s in sorted(set(suppliers))] or ["  (none)"])
        out.append("\n-> SUPPLIES TO:")
        out.extend([f"  {c}" for c in sorted(set(customers))] or ["  (none)"])
        return "\n".join(out)

    def landscape(self, entity: str) -> str:
        resolved = self.resolve_entity(entity)
        if not resolved:
            return f"Entity not found: {entity}"

        competitors = set()
        shared_investors = set()
        regulators = set()

        for _, t, attrs in self.graph.out_edges(resolved, data=True):
            rel = attrs.get("relation_type")
            if rel == "competes_with":
                competitors.add(t)
            elif rel == "regulated_by":
                regulators.add(t)

        for c in competitors:
            for _, t, attrs in self.graph.out_edges(c, data=True):
                if attrs.get("relation_type") in ("invested_by", "invests_in"):
                    shared_investors.add(t)
            for _, t, attrs in self.graph.out_edges(c, data=True):
                if attrs.get("relation_type") == "regulated_by":
                    regulators.add(t)

        out = ["\n" + "=" * 60, f"LANDSCAPE: {resolved}", "=" * 60]
        out.append("\nCompetitors:")
        out.extend([f"  - {c}" for c in sorted(competitors)] or ["  (none)"])
        out.append("\nShared Investors:")
        out.extend([f"  - {i}" for i in sorted(shared_investors)] or ["  (none)"])
        out.append("\nRegulatory Overlaps:")
        out.extend([f"  - {r}" for r in sorted(regulators)] or ["  (none)"])
        return "\n".join(out)

    def theme_map(self, theme: str) -> str:
        token = theme.replace("_", "-").lower()
        entities = []
        for n, attrs in self.graph.nodes(data=True):
            if attrs.get("is_alias"):
                continue
            tags = [str(t).lower() for t in attrs.get("sector_tags", []) or []]
            if token in tags:
                score = float(attrs.get("confidence", 0.5)) * (1 + len(attrs.get("signals", []) or []))
                entities.append((n, score, attrs.get("type", "unknown")))
        entities.sort(key=lambda x: -x[1])

        out = ["\n" + "=" * 60, f"THEME MAP: {theme}", "=" * 60]
        if not entities:
            out.append("\nNo entities found with this theme.")
            return "\n".join(out)
        for n, score, t in entities:
            out.append(f"  {n} ({t}) [score: {score:.2f}]")
        return "\n".join(out)

    def anomalies(self) -> str:
        out = ["\n" + "=" * 60, "ANOMALIES", "=" * 60]

        contradictory = []
        for u, v, attrs in self.graph.edges(data=True):
            rel = attrs.get("relation_type")
            if rel == "competes_with" and self._has_relation(u, v, "partners_with"):
                contradictory.append((u, v))
            if rel == "partners_with" and self._has_relation(u, v, "competes_with"):
                contradictory.append((u, v))

        isolated = [n for n in self.graph.nodes if self.graph.degree(n) == 0 and not self.graph.nodes[n].get("is_alias")]

        asymmetric = []
        for u, v, attrs in self.graph.edges(data=True):
            rel = attrs.get("relation_type")
            if rel in ("competes_with", "partners_with") and not self._has_relation(v, u, rel):
                asymmetric.append((u, v, rel))

        models_no_lineage = []
        for n, attrs in self.graph.nodes(data=True):
            if attrs.get("type") != "model":
                continue
            has_lineage = False
            for _, t, e in self.graph.out_edges(n, data=True):
                if e.get("relation_type") == "builds_on":
                    has_lineage = True
            for s, _, e in self.graph.in_edges(n, data=True):
                if e.get("relation_type") == "builds_on":
                    has_lineage = True
            if not has_lineage:
                models_no_lineage.append(n)

        people_no_org = []
        for n, attrs in self.graph.nodes(data=True):
            if attrs.get("type") != "person":
                continue
            connected = False
            for _, _, e in self.graph.out_edges(n, data=True):
                if e.get("relation_type") in ("employed_by", "formerly_employed_by", "co_founder_of"):
                    connected = True
            if not connected:
                people_no_org.append(n)

        out.append(f"\nContradictory relations: {len(contradictory)}")
        for row in contradictory[:10]:
            out.append(f"  - {row[0]} <-> {row[1]}")

        out.append(f"\nIsolated entities: {len(isolated)}")
        for row in isolated[:10]:
            out.append(f"  - {row}")

        out.append(f"\nAsymmetric relations: {len(asymmetric)}")
        for row in asymmetric[:10]:
            out.append(f"  - {row[0]} -> {row[1]} [{row[2]}]")

        out.append(f"\nModels with no lineage: {len(models_no_lineage)}")
        for row in models_no_lineage[:10]:
            out.append(f"  - {row}")

        out.append(f"\nPeople with no org connection: {len(people_no_org)}")
        for row in people_no_org[:10]:
            out.append(f"  - {row}")

        return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge base graph query engine")
    parser.add_argument("--kb-path", default=str(default_kb_root()))
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("connections")
    c.add_argument("entity")

    l = sub.add_parser("lineage")
    l.add_argument("model")

    tf = sub.add_parser("talent-flow")
    tf.add_argument("--from", dest="from_lab")
    tf.add_argument("--to", dest="to_lab")

    sc = sub.add_parser("supply-chain")
    sc.add_argument("entity")

    ls = sub.add_parser("landscape")
    ls.add_argument("entity")

    tm = sub.add_parser("theme-map")
    tm.add_argument("theme")

    sub.add_parser("anomalies")

    args = parser.parse_args()
    q = GraphQuery(Path(args.kb_path))

    if args.command == "connections":
        print(q.connections(args.entity))
    elif args.command == "lineage":
        print(q.lineage(args.model))
    elif args.command == "talent-flow":
        print(q.talent_flow(from_lab=args.from_lab, to_lab=args.to_lab))
    elif args.command == "supply-chain":
        print(q.supply_chain(args.entity))
    elif args.command == "landscape":
        print(q.landscape(args.entity))
    elif args.command == "theme-map":
        print(q.theme_map(args.theme))
    elif args.command == "anomalies":
        print(q.anomalies())


if __name__ == "__main__":
    main()

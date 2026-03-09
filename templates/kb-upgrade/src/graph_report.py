#!/usr/bin/env python3
"""Weekly graph report generator."""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import networkx as nx

from common import default_kb_root
from graph_query import GraphQuery


class GraphReport:
    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        self.relations_path = self.kb_root / "indexes" / "relations.json"
        self.prev_path = self.kb_root / "indexes" / "relations-prev.json"
        self.graph = self._load_graph(self.relations_path)
        self.prev_graph = self._load_graph(self.prev_path) if self.prev_path.exists() else nx.DiGraph()

    @staticmethod
    def _load_graph(path: Path) -> nx.DiGraph:
        if not path.exists():
            return nx.DiGraph()
        data = json.loads(path.read_text(encoding="utf-8"))
        g = nx.DiGraph()
        for n in data.get("nodes", []):
            g.add_node(n["id"], **(n.get("attributes") or {}))
        for e in data.get("edges", []):
            src = e["source"]
            dst = e["target"]
            attrs = {k: v for k, v in e.items() if k not in ("source", "target")}
            g.add_edge(src, dst, **attrs)
        return g

    def _edge_key(self, u: str, v: str, attrs: Dict[str, Any]) -> Tuple[str, str, str]:
        return (u, v, str(attrs.get("relation_type", "unknown")))

    def _new_edges(self) -> List[Tuple[str, str, str]]:
        old = set(self._edge_key(u, v, a) for u, v, a in self.prev_graph.edges(data=True))
        new = [self._edge_key(u, v, a) for u, v, a in self.graph.edges(data=True)]
        return [e for e in new if e not in old]

    def _changed_edges(self) -> List[Tuple[str, str, str]]:
        changed: List[Tuple[str, str, str]] = []
        for u, v, a in self.graph.edges(data=True):
            if not self.prev_graph.has_edge(u, v):
                continue
            old = self.prev_graph.get_edge_data(u, v) or {}
            if old.get("relation_type") != a.get("relation_type") or old.get("weight") != a.get("weight"):
                changed.append(self._edge_key(u, v, a))
        return changed

    def generate(self) -> str:
        now = datetime.utcnow()
        lines: List[str] = [f"# Knowledge Base Graph Report - {now.date().isoformat()}", ""]

        lines.extend([
            "## Graph Overview",
            f"- Nodes: {self.graph.number_of_nodes()}",
            f"- Edges: {self.graph.number_of_edges()}",
            "",
        ])

        new_edges = self._new_edges()
        lines.append("## New Relationships This Week")
        if new_edges:
            for u, v, rel in new_edges[:50]:
                lines.append(f"- {u} -> {v} ({rel})")
        else:
            lines.append("- None")
        lines.append("")

        changed = self._changed_edges()
        lines.append("## Relationship Changes")
        if changed:
            for u, v, rel in changed[:50]:
                lines.append(f"- {u} -> {v} ({rel}) changed")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("## Talent Movements")
        talent = []
        for u, v, a in self.graph.edges(data=True):
            if a.get("relation_type") in ("talent_pipeline", "employs_key_person", "formerly_employed_by"):
                talent.append((u, v, a.get("relation_type")))
        if talent:
            for u, v, rel in talent[:30]:
                lines.append(f"- {u} -> {v} ({rel})")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("## Emerging Clusters")
        undirected = self.graph.to_undirected()
        clusters = sorted(nx.connected_components(undirected), key=len, reverse=True)
        if clusters:
            for i, c in enumerate(clusters[:8], start=1):
                lines.append(f"- Cluster {i} ({len(c)} nodes): {', '.join(sorted(list(c))[:10])}")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("## Centrality Rankings")
        cent = nx.degree_centrality(self.graph) if self.graph.number_of_nodes() else {}
        for n, score in sorted(cent.items(), key=lambda x: -x[1])[:15]:
            lines.append(f"- {n}: {score:.3f}")
        if not cent:
            lines.append("- None")
        lines.append("")

        lines.append("## Anomalies To Resolve")
        try:
            lines.append(GraphQuery(self.kb_root).anomalies())
        except Exception as exc:
            lines.append(f"- Could not compute anomalies: {exc}")

        return "\n".join(lines) + "\n"

    def save(self) -> Path:
        report = self.generate()
        out_dir = self.kb_root / "reports" / "weekly"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"graph-report-{datetime.utcnow().date().isoformat()}.md"
        out_path.write_text(report, encoding="utf-8")

        # Snapshot current relations as previous baseline for next run.
        if self.relations_path.exists():
            self.prev_path.write_text(self.relations_path.read_text(encoding="utf-8"), encoding="utf-8")
        return out_path



def main() -> None:
    parser = argparse.ArgumentParser(description="Generate graph report")
    parser.add_argument("--kb-path", default=str(default_kb_root()))
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    reporter = GraphReport(Path(args.kb_path))
    if args.json:
        print(
            json.dumps(
                {
                    "nodes": reporter.graph.number_of_nodes(),
                    "edges": reporter.graph.number_of_edges(),
                    "generated": datetime.utcnow().isoformat() + "Z",
                },
                indent=2,
            )
        )
    elif args.save:
        path = reporter.save()
        print(f"Report saved to: {path}")
    else:
        print(reporter.generate())


if __name__ == "__main__":
    main()

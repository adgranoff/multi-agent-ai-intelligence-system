#!/usr/bin/env python3
"""Semantic search and entity-context retrieval for the knowledge base."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from common import default_kb_root
from chunker import Chunk
from embedder import Embedder
from index_manager import IndexManager, SearchResult

logger = logging.getLogger(__name__)


class KBSearch:
    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        self.embedder = Embedder(self.kb_root)
        self.index = IndexManager(self.kb_root)

    def get_entity_context(self, entity_names: List[str]) -> Dict[str, str]:
        """Return structured chunk text for each requested entity/alias."""
        chunks = self.index.get_entity_chunks(entity_names, structured_only=True)
        out: Dict[str, str] = {}
        for ch in chunks:
            if ch.entity_name not in out:
                out[ch.entity_name] = ch.text
        return out

    def _embed_query(self, query_text: str) -> List[float]:
        q_chunk = Chunk(
            text=query_text,
            source_file="query",
            chunk_index=0,
            entity_name="query",
            entity_type="query",
            sector_tags=[],
            is_structured=False,
            aliases=[],
            confidence=1.0,
        )
        vectors = self.embedder.embed_chunks([q_chunk], skip_cached=False)
        return list(vectors.values())[0]

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        sector: Optional[str] = None,
        since: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> List[Dict]:
        if self.index.get_index_stats().get("total_chunks", 0) == 0:
            logger.warning("Search index is empty. Run build_index.py first.")
            return []

        query_embedding = self._embed_query(query_text)
        filters = {}
        if entity_type:
            filters["entity_type"] = entity_type
        results = self.index.search(query_embedding, top_k=top_k * 3, filters=filters)

        out: List[Dict] = []
        since_dt: Optional[datetime] = None
        if since:
            try:
                since_dt = datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                since_dt = None

        alias_terms = [t.lower() for t in query_text.split() if len(t) > 2]

        for r in results:
            if sector and sector.lower() not in [s.lower() for s in r.sector_tags]:
                continue
            if min_confidence is not None and r.confidence < min_confidence:
                continue

            if since_dt:
                meta = self.index.metadata().get(r.chunk_id, {})
                date_val = meta.get("last_updated") or meta.get("last_confirmed")
                if isinstance(date_val, str) and date_val:
                    try:
                        if "T" in date_val:
                            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        else:
                            dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
                        if dt.replace(tzinfo=None) < since_dt:
                            continue
                    except Exception:
                        pass

            boost = 0.0
            alias_pool = [r.entity_name.lower()] + [a.lower() for a in r.aliases]
            if any(term in " ".join(alias_pool) for term in alias_terms):
                boost = 0.05

            out.append({
                "chunk_id": r.chunk_id,
                "score": round(float(r.score + boost), 6),
                "entity_name": r.entity_name,
                "entity_type": r.entity_type,
                "source_file": r.source_file,
                "chunk_index": r.chunk_index,
                "is_structured": r.is_structured,
                "text": r.text,
                "aliases": r.aliases,
                "sector_tags": r.sector_tags,
                "confidence": r.confidence,
            })

        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:top_k]

    def format_results(self, rows: List[Dict], compact: bool = False) -> str:
        if not rows:
            return "No results found."
        if compact:
            lines = [f"{'Entity':<28} {'Score':<8} Source", "-" * 80]
            for row in rows:
                lines.append(f"{row['entity_name'][:27]:<28} {row['score']:<8.4f} {row['source_file']}")
            return "\n".join(lines)

        lines: List[str] = []
        for i, row in enumerate(rows, start=1):
            lines.append(f"\n{i}. {row['entity_name']} ({row['entity_type']})")
            lines.append(f"   Score: {row['score']:.4f} | Source: {row['source_file']} [{row['chunk_index']}]")
            lines.append(f"   Text: {row['text'][:220]}")
        return "\n".join(lines)


KBSearcher = KBSearch  # Backward compatibility


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the knowledge base")
    parser.add_argument("query", nargs="?", help="query string")
    parser.add_argument("--entity", nargs="+", help="entity names for structured context")
    parser.add_argument("--include-prose", action="store_true", help="include prose for entity mode")
    parser.add_argument("--type", dest="entity_type")
    parser.add_argument("--sector")
    parser.add_argument("--since")
    parser.add_argument("--min-confidence", type=float)
    parser.add_argument("-k", "--top-k", type=int, default=10)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--kb-path", default=str(default_kb_root()))
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    search = KBSearch(Path(args.kb_path))

    if args.entity:
        chunks = search.index.get_entity_chunks(args.entity, structured_only=not args.include_prose)
        rows = [{
            "chunk_id": c.chunk_id,
            "entity_name": c.entity_name,
            "entity_type": c.entity_type,
            "source_file": c.source_file,
            "chunk_index": c.chunk_index,
            "is_structured": c.is_structured,
            "text": c.text,
            "score": c.score,
            "aliases": c.aliases,
            "sector_tags": c.sector_tags,
            "confidence": c.confidence,
        } for c in chunks]
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"\nFound {len(rows)} chunks for: {', '.join(args.entity)}\n")
            print(search.format_results(rows, compact=True))
        return

    if not args.query:
        raise SystemExit("Provide QUERY or --entity")

    rows = search.query(
        query_text=args.query,
        top_k=args.top_k,
        entity_type=args.entity_type,
        sector=args.sector,
        since=args.since,
        min_confidence=args.min_confidence,
    )

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"\nQuery: '{args.query}'\n")
        print(search.format_results(rows, compact=args.compact))


if __name__ == "__main__":
    main()

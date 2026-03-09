#!/usr/bin/env python3
"""Build and maintain the semantic index for a markdown knowledge base."""

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from chunker import Chunker, Chunk
from common import default_kb_root, ensure_kb_dirs, save_json, load_json
from embedder import Embedder
from index_manager import IndexManager

logger = logging.getLogger(__name__)


class IndexBuilder:
    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root).expanduser()
        ensure_kb_dirs(self.kb_root)

        self.stats_path = self.kb_root / "indexes" / "vector-store" / "build-stats.json"
        self.chunker = Chunker(self.kb_root)
        self.embedder = Embedder(self.kb_root)
        self.index = IndexManager(self.kb_root)
        self.stats = load_json(
            self.stats_path,
            {
                "last_full_build": None,
                "last_incremental": None,
                "total_builds": 0,
                "total_chunks_indexed": 0,
                "last_tokens_used": 0,
                "last_cost_usd": 0.0,
            },
        )

    def _scan(self) -> List[Chunk]:
        chunks = self.chunker.chunk_all()
        logger.info("Scanned %s chunks", len(chunks))
        return chunks

    def _metadata_from_chunks(self, chunks: List[Chunk], embeddings: Dict[str, List[float]]) -> Dict[str, Dict]:
        meta: Dict[str, Dict] = {}
        for chunk in chunks:
            chunk_id = self.embedder._chunk_hash(chunk)
            if chunk_id not in embeddings:
                continue
            meta[chunk_id] = {
                "entity_name": chunk.entity_name,
                "entity_type": chunk.entity_type,
                "source_file": chunk.source_file,
                "chunk_index": chunk.chunk_index,
                "is_structured": chunk.is_structured,
                "aliases": chunk.aliases,
                "sector_tags": chunk.sector_tags,
                "confidence": chunk.confidence,
                "text": chunk.text,
            }
        return meta

    def build_full(self) -> Dict:
        start = time.time()
        chunks = self._scan()
        if not chunks:
            return {
                "status": "empty",
                "mode": "full",
                "files_scanned": 0,
                "chunks_indexed": 0,
                "tokens_used": 0,
                "cost_usd": 0.0,
                "elapsed_seconds": round(time.time() - start, 2),
            }

        self.embedder.clear_cache()
        embeddings = self.embedder.embed_chunks(chunks, skip_cached=False)
        metadata = self._metadata_from_chunks(chunks, embeddings)
        indexed = self.index.rebuild(embeddings, metadata)

        tokens = self.embedder.last_tokens_used
        cost = (tokens / 1_000_000) * self.embedder.EST_COST_PER_M_TOKENS
        self.stats.update(
            {
                "last_full_build": datetime.utcnow().isoformat() + "Z",
                "total_builds": int(self.stats.get("total_builds", 0)) + 1,
                "total_chunks_indexed": indexed,
                "last_tokens_used": tokens,
                "last_cost_usd": round(cost, 6),
            }
        )
        save_json(self.stats_path, self.stats)

        return {
            "status": "success",
            "mode": "full",
            "files_scanned": len({c.source_file for c in chunks}),
            "chunks_indexed": indexed,
            "tokens_used": tokens,
            "cost_usd": round(cost, 6),
            "elapsed_seconds": round(time.time() - start, 2),
        }

    def build_incremental(self) -> Dict:
        start = time.time()
        chunks = self._scan()
        if not chunks:
            return {
                "status": "empty",
                "mode": "incremental",
                "files_scanned": 0,
                "chunks_indexed": 0,
                "tokens_used": 0,
                "cost_usd": 0.0,
                "elapsed_seconds": round(time.time() - start, 2),
            }

        self.embedder.embed_chunks(chunks, skip_cached=True)
        cache = self.embedder.cache()
        all_embeddings: Dict[str, List[float]] = {}
        for chunk in chunks:
            chunk_id = self.embedder._chunk_hash(chunk)
            cached = cache.get(chunk_id)
            if cached and isinstance(cached.get("embedding"), list):
                all_embeddings[chunk_id] = cached["embedding"]

        metadata = self._metadata_from_chunks(chunks, all_embeddings)
        indexed = self.index.rebuild(all_embeddings, metadata)

        tokens = self.embedder.last_tokens_used
        cost = (tokens / 1_000_000) * self.embedder.EST_COST_PER_M_TOKENS
        self.stats.update(
            {
                "last_incremental": datetime.utcnow().isoformat() + "Z",
                "total_builds": int(self.stats.get("total_builds", 0)) + 1,
                "total_chunks_indexed": indexed,
                "last_tokens_used": tokens,
                "last_cost_usd": round(cost, 6),
            }
        )
        save_json(self.stats_path, self.stats)

        return {
            "status": "success",
            "mode": "incremental",
            "files_scanned": len({c.source_file for c in chunks}),
            "chunks_indexed": indexed,
            "tokens_used": tokens,
            "cost_usd": round(cost, 6),
            "elapsed_seconds": round(time.time() - start, 2),
        }

    def get_stats(self) -> Dict:
        return {
            "build_history": self.stats,
            "index": self.index.get_index_stats(),
            "embeddings": {
                "total_cached": len(self.embedder.cache()),
                "model": self.embedder.model,
                "cache_file": str(self.embedder.cache_path),
                "cache_exists": self.embedder.cache_path.exists(),
            },
        }


def _print_result(result: Dict) -> None:
    print("\n=== Build Complete ===")
    print(f"Status: {result.get('status')}")
    print(f"Mode: {result.get('mode')}")
    print(f"Files scanned: {result.get('files_scanned')}")
    print(f"Chunks indexed: {result.get('chunks_indexed')}")
    print(f"Tokens used: {result.get('tokens_used')}")
    print(f"Cost: ${result.get('cost_usd', 0):.6f}")
    print(f"Elapsed: {result.get('elapsed_seconds')}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the KB semantic search index")
    parser.add_argument("--full", action="store_true", help="Full rebuild")
    parser.add_argument("--incremental", action="store_true", help="Incremental rebuild")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    parser.add_argument("--path", default=str(default_kb_root()), help="KB root path")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    builder = IndexBuilder(Path(args.path))

    if args.stats:
        out = builder.get_stats()
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print("\n=== Build Statistics ===\n")
            hist = out["build_history"]
            print(f"Full builds: {hist.get('total_builds', 0)}")
            print(f"Last full build: {hist.get('last_full_build')}")
            print(f"Last incremental: {hist.get('last_incremental')}")
            stats = out["index"]
            print(
                f"Total chunks: {stats.get('total_chunks')} "
                f"(structured {stats.get('structured_chunks')}, prose {stats.get('prose_chunks')})"
            )
        return

    if args.full and args.incremental:
        raise SystemExit("Cannot use --full and --incremental together")

    result = builder.build_full() if args.full else builder.build_incremental()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_result(result)


if __name__ == "__main__":
    main()

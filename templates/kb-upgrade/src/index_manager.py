#!/usr/bin/env python3
"""FAISS index manager for OpenClaw KB."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from common import load_json, save_json

try:
    import faiss  # type: ignore
except Exception as exc:  # pragma: no cover
    raise RuntimeError("faiss-cpu is required") from exc


@dataclass
class SearchResult:
    chunk_id: str
    score: float
    entity_name: str
    entity_type: str
    source_file: str
    chunk_index: int
    is_structured: bool
    text: str
    aliases: List[str]
    sector_tags: List[str]
    confidence: float


class IndexManager:
    EMBEDDING_DIM = 1536

    def __init__(self, kb_root: Path):
        self.kb_root = Path(kb_root)
        self.store_dir = self.kb_root / "indexes" / "vector-store"
        self.index_path = self.store_dir / "index.faiss"
        self.metadata_path = self.store_dir / "metadata.json"
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(self.EMBEDDING_DIM)
        self._metadata: Dict[str, Dict] = load_json(self.metadata_path, {})
        self._id_to_chunk: Dict[int, str] = {}
        self._chunk_to_id: Dict[str, int] = {}

        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            self._index = faiss.read_index(str(self.index_path))
        else:
            self._index = faiss.IndexFlatIP(self.EMBEDDING_DIM)

        self._id_to_chunk = {}
        self._chunk_to_id = {}
        for chunk_id, meta in self._metadata.items():
            faiss_id = meta.get("faiss_id")
            if isinstance(faiss_id, int):
                self._id_to_chunk[faiss_id] = chunk_id
                self._chunk_to_id[chunk_id] = faiss_id

    def _save(self) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self.index_path))
        save_json(self.metadata_path, self._metadata)

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    def rebuild(self, embeddings: Dict[str, List[float]], metadata: Dict[str, Dict]) -> int:
        self._index = faiss.IndexFlatIP(self.EMBEDDING_DIM)
        self._metadata = {}
        self._id_to_chunk = {}
        self._chunk_to_id = {}

        ids = sorted(embeddings.keys())
        if not ids:
            self._save()
            return 0

        vectors = np.array([embeddings[i] for i in ids], dtype=np.float32)
        vectors = self._normalize(vectors)
        self._index.add(vectors)

        for idx, chunk_id in enumerate(ids):
            self._id_to_chunk[idx] = chunk_id
            self._chunk_to_id[chunk_id] = idx
            meta = dict(metadata.get(chunk_id, {}))
            meta["faiss_id"] = idx
            self._metadata[chunk_id] = meta

        self._save()
        return len(ids)

    def add_or_update(self, embeddings: Dict[str, List[float]], metadata: Dict[str, Dict]) -> int:
        """Incremental update by rebuild from current metadata+embeddings.

        Because IndexFlatIP has no safe in-place remove/update mapping, we rebuild
        from provided embeddings for deterministic correctness.
        """
        merged_meta = dict(self._metadata)
        merged_meta.update(metadata)
        return self.rebuild(embeddings, merged_meta)

    def search(self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None) -> List[SearchResult]:
        if self._index.ntotal == 0:
            return []

        q = np.array([query_embedding], dtype=np.float32)
        q = self._normalize(q)
        scores, ids = self._index.search(q, max(top_k * 2, top_k))

        results: List[SearchResult] = []
        filters = filters or {}

        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            chunk_id = self._id_to_chunk.get(int(idx))
            if not chunk_id:
                continue
            meta = self._metadata.get(chunk_id, {})

            if "entity_type" in filters and meta.get("entity_type") != filters["entity_type"]:
                continue
            if filters.get("is_structured") is True and not meta.get("is_structured"):
                continue

            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    score=float(score),
                    entity_name=str(meta.get("entity_name", "")),
                    entity_type=str(meta.get("entity_type", "unknown")),
                    source_file=str(meta.get("source_file", "")),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    is_structured=bool(meta.get("is_structured", False)),
                    text=str(meta.get("text", "")),
                    aliases=[str(a) for a in meta.get("aliases", [])],
                    sector_tags=[str(s) for s in meta.get("sector_tags", [])],
                    confidence=float(meta.get("confidence", 0.5)),
                )
            )
            if len(results) >= top_k:
                break
        return results

    def get_entity_chunks(self, entity_names: List[str], structured_only: bool = True) -> List[SearchResult]:
        wanted = {e.strip().lower() for e in entity_names if e.strip()}
        out: List[SearchResult] = []

        for chunk_id, meta in self._metadata.items():
            name = str(meta.get("entity_name", "")).lower()
            aliases = {str(a).lower() for a in meta.get("aliases", [])}
            if name not in wanted and wanted.isdisjoint(aliases):
                continue
            if structured_only and not meta.get("is_structured"):
                continue
            out.append(
                SearchResult(
                    chunk_id=chunk_id,
                    score=1.0,
                    entity_name=str(meta.get("entity_name", "")),
                    entity_type=str(meta.get("entity_type", "unknown")),
                    source_file=str(meta.get("source_file", "")),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    is_structured=bool(meta.get("is_structured", False)),
                    text=str(meta.get("text", "")),
                    aliases=[str(a) for a in meta.get("aliases", [])],
                    sector_tags=[str(s) for s in meta.get("sector_tags", [])],
                    confidence=float(meta.get("confidence", 0.5)),
                )
            )

        out.sort(key=lambda r: (r.entity_name.lower(), r.chunk_index))
        return out

    def get_index_stats(self) -> Dict:
        entity_types: Dict[str, int] = {}
        structured = 0
        prose = 0
        for meta in self._metadata.values():
            e_type = str(meta.get("entity_type", "unknown"))
            entity_types[e_type] = entity_types.get(e_type, 0) + 1
            if meta.get("is_structured"):
                structured += 1
            else:
                prose += 1
        return {
            "total_chunks": int(self._index.ntotal),
            "structured_chunks": structured,
            "prose_chunks": prose,
            "entity_types": entity_types,
        }

    def metadata(self) -> Dict[str, Dict]:
        return self._metadata

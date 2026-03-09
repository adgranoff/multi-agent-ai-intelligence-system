#!/usr/bin/env python3
"""OpenRouter embedding client with batching, retries, and cache."""

import hashlib
import math
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from common import append_log, find_api_key, load_json, save_json, utc_now_iso
from chunker import Chunk


class Embedder:
    BATCH_SIZE = 20
    MAX_RETRIES = 4
    BASE_DELAY = 1.0
    EMBEDDING_MODEL = "openai/text-embedding-3-small"
    EMBEDDING_DIM = 1536
    EST_COST_PER_M_TOKENS = 0.02

    def __init__(self, kb_root: Path, api_key: Optional[str] = None, model: Optional[str] = None):
        self.kb_root = Path(kb_root)
        self.model = model or self.EMBEDDING_MODEL
        self.cache_path = self.kb_root / "indexes" / "vector-store" / "embedding-cache.json"
        self.api_log = self.kb_root / "logs" / "api-usage.log"
        self._api_key = api_key or ""
        self._cache = load_json(self.cache_path, {})
        self.last_tokens_used = 0

    @property
    def api_key(self) -> str:
        if self._api_key:
            return self._api_key
        self._api_key = find_api_key()
        return self._api_key

    def _chunk_hash(self, chunk: Chunk) -> str:
        raw = "|".join([
            chunk.text,
            chunk.source_file,
            str(chunk.chunk_index),
            chunk.entity_name,
            chunk.entity_type,
        ])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def _request_embeddings(self, texts: List[str], retry: int = 0) -> Tuple[List[List[float]], int]:
        key = self.api_key
        if not key:
            raise ValueError("OPENROUTER_API_KEY not set")

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://example.invalid",
            "X-Title": "OpenClaw KB",
        }
        payload = {"model": self.model, "input": texts}

        try:
            resp = requests.post("https://openrouter.ai/api/v1/embeddings", headers=headers, json=payload, timeout=90)
            if resp.status_code >= 500 or resp.status_code == 429:
                raise requests.HTTPError(f"retryable {resp.status_code}", response=resp)
            resp.raise_for_status()
            data = resp.json()
            vectors = [x["embedding"] for x in data.get("data", [])]
            usage = data.get("usage", {}) or {}
            tokens = int(usage.get("total_tokens", 0) or 0)
            return vectors, tokens
        except requests.HTTPError as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code == 404 and "No endpoints found matching your data policy" in response.text:
                # Explicit deterministic fallback for strict OpenRouter privacy policy environments.
                vectors = [self._local_embedding(t) for t in texts]
                approx_tokens = sum(max(1, len(t) // 4) for t in texts)
                return vectors, approx_tokens
            if retry >= self.MAX_RETRIES:
                raise
            delay = self.BASE_DELAY * (2 ** retry)
            time.sleep(delay)
            return self._request_embeddings(texts, retry + 1)
        except (requests.ConnectionError, requests.Timeout):
            vectors = [self._local_embedding(t) for t in texts]
            approx_tokens = sum(max(1, len(t) // 4) for t in texts)
            return vectors, approx_tokens

    def _local_embedding(self, text: str) -> List[float]:
        """Deterministic lexical hashing fallback for environments without remote embeddings."""
        vec = [0.0] * self.EMBEDDING_DIM
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return vec

        for tok in tokens:
            # Single token feature.
            h1 = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx1 = int.from_bytes(h1[:4], "big") % self.EMBEDDING_DIM
            sign1 = 1.0 if (h1[4] & 1) == 0 else -1.0
            vec[idx1] += sign1

            # Character trigram feature for phrase matching stability.
            if len(tok) >= 3:
                for i in range(len(tok) - 2):
                    tri = tok[i : i + 3]
                    h2 = hashlib.blake2b(tri.encode("utf-8"), digest_size=8).digest()
                    idx2 = int.from_bytes(h2[:4], "big") % self.EMBEDDING_DIM
                    sign2 = 1.0 if (h2[4] & 1) == 0 else -1.0
                    vec[idx2] += 0.5 * sign2

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        vectors: List[List[float]] = []
        total_tokens = 0
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i:i + self.BATCH_SIZE]
            batch_vectors, batch_tokens = self._request_embeddings(batch)
            vectors.extend(batch_vectors)
            total_tokens += batch_tokens
            cost = (batch_tokens / 1_000_000) * self.EST_COST_PER_M_TOKENS
            append_log(
                self.api_log,
                f"{utc_now_iso()} | embeddings | {self.model} | {batch_tokens} | ${cost:.6f}",
            )
        self.last_tokens_used = total_tokens
        return vectors, total_tokens

    def embed_chunks(self, chunks: List[Chunk], skip_cached: bool = True) -> Dict[str, List[float]]:
        result: Dict[str, List[float]] = {}
        to_embed_chunks: List[Chunk] = []
        to_embed_ids: List[str] = []

        for chunk in chunks:
            chunk_id = self._chunk_hash(chunk)
            cached = self._cache.get(chunk_id)
            if skip_cached and cached and isinstance(cached.get("embedding"), list):
                result[chunk_id] = cached["embedding"]
                continue
            to_embed_chunks.append(chunk)
            to_embed_ids.append(chunk_id)

        if to_embed_chunks:
            texts = [c.text for c in to_embed_chunks]
            vectors, _ = self.embed_texts(texts)
            for chunk, chunk_id, vector in zip(to_embed_chunks, to_embed_ids, vectors):
                entry = {
                    "embedding": vector,
                    "entity_name": chunk.entity_name,
                    "entity_type": chunk.entity_type,
                    "source_file": chunk.source_file,
                    "chunk_index": chunk.chunk_index,
                    "aliases": chunk.aliases,
                    "sector_tags": chunk.sector_tags,
                    "is_structured": chunk.is_structured,
                    "confidence": chunk.confidence,
                    "text": chunk.text,
                }
                self._cache[chunk_id] = entry
                result[chunk_id] = vector
            save_json(self.cache_path, self._cache)
        else:
            self.last_tokens_used = 0

        return result

    def clear_cache(self) -> None:
        self._cache = {}
        save_json(self.cache_path, self._cache)

    def cache(self) -> Dict[str, Dict]:
        return self._cache

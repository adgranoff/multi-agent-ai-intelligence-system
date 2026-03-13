from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chunker import Chunker
from common import (
    DEFAULT_PROVIDER_API_BASE_URL,
    dump_frontmatter,
    ensure_kb_dirs,
    parse_frontmatter,
    provider_api_base_url,
    provider_api_url,
)
from build_index import IndexBuilder
from decay import ConfidenceDecay
from graph_builder import GraphBuilder
from graph_query import GraphQuery
from merger import Merger


def _seed_entity(path: Path, entity: str, etype: str) -> None:
    fm = {
        "entity": entity,
        "type": etype,
        "aliases": [],
        "created": "2026-03-07",
        "last_updated": "2026-03-07T00:00:00Z",
        "last_confirmed": "2026-03-07",
        "confidence": 0.8,
        "status": "active",
        "sector_tags": ["enterprise"],
        "summary": f"{entity} summary",
        "digest_sources": ["2026-03-07.md"],
        "signals": [],
        "relations": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_frontmatter(fm, f"# {entity}\n\nBody"), encoding="utf-8")


def test_chunker_structured_chunk(tmp_path: Path):
    kb = tmp_path / "intelligence-kb"
    ensure_kb_dirs(kb)
    entity_path = kb / "entities" / "labs" / "anthropic.md"
    _seed_entity(entity_path, "Anthropic", "lab")

    chunks = Chunker(kb).chunk_all()
    assert chunks
    assert chunks[0].is_structured is True
    assert "Anthropic" in chunks[0].text


def test_merger_path_and_signal_ids(tmp_path: Path):
    kb = tmp_path / "intelligence-kb"
    ensure_kb_dirs(kb)
    _seed_entity(kb / "entities" / "labs" / "anthropic.md", "Anthropic", "lab")

    merger = Merger(kb)
    p = merger.get_entity_path("Anthropic", "lab")
    assert p.name == "anthropic.md"

    a = merger._next_signal_id()
    # create one signal so next differs
    fm, body = merger._parse_entity_file(p)
    fm["signals"] = [{"id": a, "type": "market_signal", "value": "x", "date": "2026-03-07", "confidence": "high", "source_digest": "2026-03-07.md"}]
    p.write_text(dump_frontmatter(fm, body), encoding="utf-8")
    b = merger._next_signal_id()
    assert a != b


def test_build_index_without_network_when_cached(monkeypatch, tmp_path: Path):
    kb = tmp_path / "intelligence-kb"
    ensure_kb_dirs(kb)
    _seed_entity(kb / "entities" / "labs" / "anthropic.md", "Anthropic", "lab")

    def fake_embed(self, chunks, skip_cached=True):
        out = {}
        for c in chunks:
            cid = self._chunk_hash(c)
            vec = np.ones(1536, dtype=np.float32).tolist()
            self._cache[cid] = {
                "embedding": vec,
                "entity_name": c.entity_name,
                "entity_type": c.entity_type,
                "source_file": c.source_file,
                "chunk_index": c.chunk_index,
                "aliases": c.aliases,
                "sector_tags": c.sector_tags,
                "is_structured": c.is_structured,
                "confidence": c.confidence,
                "text": c.text,
            }
            out[cid] = vec
        return out

    monkeypatch.setattr("embedder.Embedder.embed_chunks", fake_embed)
    builder = IndexBuilder(kb)
    result = builder.build_full()
    assert result["status"] == "success"
    assert result["chunks_indexed"] > 0


def test_graph_anomalies_command_runs(tmp_path: Path):
    kb = tmp_path / "intelligence-kb"
    ensure_kb_dirs(kb)
    _seed_entity(kb / "entities" / "labs" / "anthropic.md", "Anthropic", "lab")
    _seed_entity(kb / "entities" / "labs" / "openai.md", "OpenAI", "lab")

    # add relations
    fm, body = parse_frontmatter((kb / "entities" / "labs" / "anthropic.md").read_text(encoding="utf-8"))
    fm["relations"] = {"competes_with": ["openai"], "partners_with": ["openai"]}
    (kb / "entities" / "labs" / "anthropic.md").write_text(dump_frontmatter(fm, body), encoding="utf-8")

    GraphBuilder(kb).build_graph()
    GraphBuilder(kb).export()
    text = GraphQuery(kb).anomalies()
    assert "Contradictory relations" in text


def test_confidence_decay_report_and_apply(tmp_path: Path):
    kb = tmp_path / "intelligence-kb"
    ensure_kb_dirs(kb)
    entity_path = kb / "entities" / "models" / "example-model.md"
    _seed_entity(entity_path, "Example Model", "model")

    fm, body = parse_frontmatter(entity_path.read_text(encoding="utf-8"))
    fm["confidence"] = 0.9
    fm["last_confirmed"] = "2026-01-01"
    entity_path.write_text(dump_frontmatter(fm, body), encoding="utf-8")

    result = ConfidenceDecay(kb).run(apply_changes=False, as_of="2026-03-07")
    assert result["changed"] == 1
    assert result["entities"][0]["new_confidence"] < result["entities"][0]["old_confidence"]

    ConfidenceDecay(kb).run(apply_changes=True, as_of="2026-03-07")
    updated, _ = parse_frontmatter(entity_path.read_text(encoding="utf-8"))
    assert updated["confidence"] < 0.9


def test_provider_api_url_defaults_to_generic_base(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER_API_BASE_URL", raising=False)

    assert provider_api_base_url() == DEFAULT_PROVIDER_API_BASE_URL
    assert provider_api_url("chat/completions") == f"{DEFAULT_PROVIDER_API_BASE_URL}/chat/completions"


def test_provider_api_url_honors_override(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER_API_BASE_URL", "https://provider.example/api/v9/")

    assert provider_api_base_url() == "https://provider.example/api/v9"
    assert provider_api_url("/embeddings") == "https://provider.example/api/v9/embeddings"

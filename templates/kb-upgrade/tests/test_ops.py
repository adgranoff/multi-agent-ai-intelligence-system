from pathlib import Path

import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import kb_ops  # noqa: E402
from common import ensure_kb_dirs  # noqa: E402
from embedder import Embedder  # noqa: E402


def _cosine(a, b) -> float:
    aa = np.array(a, dtype=np.float32)
    bb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    if denom == 0:
        return 0.0
    return float(np.dot(aa, bb) / denom)


def test_local_embedding_fallback_preserves_lexical_similarity(tmp_path: Path):
    kb = tmp_path / "intelligence-kb"
    ensure_kb_dirs(kb)
    emb = Embedder(kb)

    v1 = emb._local_embedding("Kimi K2.5 multimodal model pricing")
    v2 = emb._local_embedding("Kimi model multimodal K2.5 costs")
    v3 = emb._local_embedding("NVIDIA supply chain datacenter chips")

    assert _cosine(v1, v2) > _cosine(v1, v3)


def test_weekly_report_falls_back_when_llm_unreachable(monkeypatch, tmp_path: Path):
    kb = tmp_path / "intelligence-kb"
    ensure_kb_dirs(kb)

    def _raise(*args, **kwargs):
        raise kb_ops.requests.ConnectionError("dns failure")

    monkeypatch.setattr(kb_ops, "find_api_key", lambda: "fake-key")
    monkeypatch.setattr(kb_ops.requests, "post", _raise)

    out = kb_ops._generate_weekly_memo(kb)
    text = out.read_text(encoding="utf-8")

    assert out.exists()
    assert "## EXECUTIVE SUMMARY" in text
    assert "## RECOMMENDED ACTIONS" in text

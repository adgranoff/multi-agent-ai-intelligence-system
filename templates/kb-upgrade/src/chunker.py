#!/usr/bin/env python3
"""Chunking utilities for the knowledge base."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Tuple

from common import parse_frontmatter, list_entity_files


@dataclass
class Chunk:
    text: str
    source_file: str
    chunk_index: int
    entity_name: str
    entity_type: str
    sector_tags: List[str]
    is_structured: bool
    aliases: List[str]
    confidence: float


class Chunker:
    """Create structured and prose chunks from KB markdown files."""

    def __init__(self, kb_root: Path, chunk_size_tokens: int = 500, overlap_tokens: int = 50):
        self.kb_root = Path(kb_root)
        self.chunk_size_tokens = max(100, chunk_size_tokens)
        self.overlap_tokens = max(0, min(overlap_tokens, self.chunk_size_tokens - 1))

    def parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        return parse_frontmatter(content)

    def _structured_text(self, fm: Dict[str, Any]) -> str:
        entity = fm.get("entity", "Unknown Entity")
        e_type = fm.get("type", "entity")
        summary = fm.get("summary", "")
        tags = fm.get("sector_tags", []) or []
        status = fm.get("status", "active")
        conf = fm.get("confidence", 0.5)
        aliases = fm.get("aliases", []) or []

        parts: List[str] = [f"{entity} is a {e_type}."]
        parts.append(f"Confidence: {conf}.")
        parts.append(f"Status: {status}.")
        if aliases:
            parts.append("Aliases: " + ", ".join([str(a) for a in aliases]))
        if tags:
            parts.append("Tags: " + ", ".join([str(t) for t in tags]))
        if summary:
            parts.append(summary)

        signals = fm.get("signals", []) or []
        if signals:
            signal_lines: List[str] = []
            for s in signals[:6]:
                s_type = s.get("type", "signal")
                s_val = s.get("value", "")
                s_date = s.get("date", "")
                s_conf = s.get("confidence", "medium")
                signal_lines.append(f"{s_type}: {s_val} ({s_date}, {s_conf})")
            parts.append("Recent signals: " + "; ".join(signal_lines))

        relations = fm.get("relations", {}) or {}
        if relations:
            rel_lines: List[str] = []
            for k, vals in relations.items():
                if vals:
                    rel_lines.append(f"{k}: {', '.join([str(v) for v in vals])}")
            if rel_lines:
                parts.append("Relations: " + ". ".join(rel_lines))

        if e_type == "model":
            md = fm.get("model_details", {}) or {}
            if md:
                md_parts: List[str] = []
                for field in ["family", "version", "release_date", "parameter_count", "context_window", "license"]:
                    val = md.get(field)
                    if val not in (None, ""):
                        md_parts.append(f"{field.replace('_', ' ').title()}: {val}")
                modalities = md.get("modalities", []) or []
                if modalities:
                    md_parts.append("Modalities: " + ", ".join([str(m) for m in modalities]))
                pricing = md.get("api_pricing", {}) or {}
                if pricing:
                    i_p = pricing.get("input_per_m")
                    o_p = pricing.get("output_per_m")
                    md_parts.append(f"Pricing: input ${i_p}/M, output ${o_p}/M")
                benchmarks = md.get("notable_benchmarks", []) or []
                if benchmarks:
                    btxt = ", ".join([f"{b.get('name')}: {b.get('score')}" for b in benchmarks[:5]])
                    md_parts.append("Benchmarks: " + btxt)
                if md_parts:
                    parts.append("Model details: " + ". ".join(md_parts))

        if e_type == "person":
            pd = fm.get("person_details", {}) or {}
            if pd:
                p_parts: List[str] = []
                if pd.get("current_role"):
                    p_parts.append(f"Role: {pd.get('current_role')}")
                if pd.get("organization"):
                    p_parts.append(f"Organization: {pd.get('organization')}")
                if pd.get("expertise"):
                    p_parts.append("Expertise: " + ", ".join([str(e) for e in pd.get("expertise", [])]))
                if pd.get("influence_tier"):
                    p_parts.append(f"Influence tier: {pd.get('influence_tier')}")
                if p_parts:
                    parts.append("Person details: " + ". ".join(p_parts))

        return " ".join(parts)

    def _chunk_text(self, text: str) -> List[str]:
        words = text.split()
        if not words:
            return []
        chunks: List[str] = []
        i = 0
        step = self.chunk_size_tokens - self.overlap_tokens
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size_tokens]
            chunks.append(" ".join(chunk_words))
            if i + self.chunk_size_tokens >= len(words):
                break
            i += step
        return chunks

    def chunk_file(self, path: Path) -> List[Chunk]:
        content = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        relative = str(path.relative_to(self.kb_root))
        entity_name = fm.get("entity", path.stem)
        entity_type = fm.get("type", "theme" if "themes" in relative else "unknown")
        aliases = fm.get("aliases", []) or []
        sector_tags = fm.get("sector_tags", []) or []
        confidence = float(fm.get("confidence", 0.5)) if fm else 0.5

        chunks: List[Chunk] = []

        if fm:
            chunks.append(
                Chunk(
                    text=self._structured_text(fm),
                    source_file=relative,
                    chunk_index=0,
                    entity_name=entity_name,
                    entity_type=entity_type,
                    sector_tags=[str(t) for t in sector_tags],
                    is_structured=True,
                    aliases=[str(a) for a in aliases],
                    confidence=confidence,
                )
            )

        prose_parts = self._chunk_text(body.strip()) if body.strip() else []
        for i, text in enumerate(prose_parts, start=1):
            chunks.append(
                Chunk(
                    text=text,
                    source_file=relative,
                    chunk_index=i,
                    entity_name=entity_name,
                    entity_type=entity_type,
                    sector_tags=[str(t) for t in sector_tags],
                    is_structured=False,
                    aliases=[str(a) for a in aliases],
                    confidence=confidence,
                )
            )
        return chunks

    def chunk_all(self) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        for file in list_entity_files(self.kb_root):
            all_chunks.extend(self.chunk_file(file))
        return all_chunks

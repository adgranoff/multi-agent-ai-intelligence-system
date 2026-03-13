#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Opportunity:
    title: str
    strength: str
    action: str
    status: str
    signal: str


@dataclass
class ContentIdea:
    title: str
    status: str
    first_seen: str


STRENGTH_SCORE = {"STRONG": 3, "MODERATE": 2, "WEAK": 1}


def parse_sections(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    chunks = re.split(r"^### ", text, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    for chunk in chunks[1:]:
        title, _, body = chunk.partition("\n")
        sections.append((title.strip(), body.strip()))
    return sections


def find_field(body: str, label: str) -> str:
    match = re.search(rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else "Unknown"


def load_opportunities(path: Path) -> list[Opportunity]:
    return [
        Opportunity(
            title=title,
            strength=find_field(body, "Strength").replace("**", ""),
            action=find_field(body, "Action"),
            status=find_field(body, "Status"),
            signal=find_field(body, "Signal"),
        )
        for title, body in parse_sections(path)
    ]


def load_content_ideas(path: Path) -> list[ContentIdea]:
    return [
        ContentIdea(
            title=title,
            status=find_field(body, "Status"),
            first_seen=find_field(body, "First seen"),
        )
        for title, body in parse_sections(path)
    ]


def write_outreach_queue(path: Path, opportunities: list[Opportunity]) -> None:
    ranked = sorted(opportunities, key=lambda item: (STRENGTH_SCORE.get(item.strength.upper(), 0), item.title), reverse=True)[:5]
    lines = ["# Outreach Queue", "", f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_", ""]
    for idx, item in enumerate(ranked, start=1):
        lines.extend([f"## {idx}. {item.title}", f"**Strength:** {item.strength}", f"**Status:** {item.status}", f"**Why now:** {item.signal}", f"**Recommended move:** {item.action}", ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_decision_dashboard(path: Path, opportunities: list[Opportunity], ideas: list[ContentIdea]) -> None:
    ranked = sorted(opportunities, key=lambda item: (STRENGTH_SCORE.get(item.strength.upper(), 0), item.title), reverse=True)
    ready_ideas = [idea for idea in ideas if "READY" in idea.status.upper()]
    developing_ideas = [idea for idea in ideas if "DEVELOPING" in idea.status.upper()]
    lines = ["# Decision Dashboard", "", f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_", "", "## Top Opportunities", ""]
    for item in ranked[:3]:
        lines.append(f"- **{item.title}** ({item.strength}) — {item.action}")
    lines.extend(["", "## Content To Ship", ""])
    if ready_ideas:
        for idea in ready_ideas[:3]:
            lines.append(f"- **{idea.title}** — {idea.status} (first seen {idea.first_seen})")
    else:
        lines.append("- No READY ideas today.")
    lines.extend(["", "## Developing Themes", ""])
    if developing_ideas:
        for idea in developing_ideas[:3]:
            lines.append(f"- **{idea.title}** — {idea.status}")
    else:
        lines.append("- No DEVELOPING ideas today.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    kb_root = Path(os.environ.get("KB_ROOT", str(Path.cwd() / "knowledge-base")))
    opportunities = load_opportunities(kb_root / "opportunities/active.md")
    ideas = load_content_ideas(kb_root / "content-ideas/active.md")
    write_outreach_queue(kb_root / "outreach-queue.md", opportunities)
    write_decision_dashboard(kb_root / "decision-dashboard.md", opportunities, ideas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class FileSummary:
    title: str
    rel_path: str
    entry_count: int
    last_updated: str
    status: str


ACRONYM_MAP = {
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "cio": "CIO",
    "cios": "CIOs",
    "cto": "CTO",
    "gpt": "GPT",
    "hipaa": "HIPAA",
    "ip": "IP",
    "latam": "LatAm",
    "llm": "LLM",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_sections(text: str) -> list[tuple[str, str]]:
    chunks = re.split(r"^### ", text, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    for chunk in chunks[1:]:
        title, _, body = chunk.partition("\n")
        sections.append((title.strip(), body.strip()))
    return sections


def count_entries(path: Path) -> int:
    return len(parse_sections(read_text(path)))


def find_first(pattern: str, text: str, default: str = "None") -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else default


def last_updated_label(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def humanize_slug(slug: str) -> str:
    parts = slug.replace("-", " ").split()
    words = [ACRONYM_MAP.get(part.lower(), part.capitalize()) for part in parts]
    return " ".join(words)


def company_status(entry_count: int) -> str:
    if entry_count >= 6:
        return "Hot"
    return "Active"


def theme_status(title: str, entry_count: int) -> str:
    if entry_count >= 5:
        return "TRENDING"
    if "emerging" in title.lower():
        return "Active"
    return "Active"


def list_company_files(companies_dir: Path, kb_root: Path) -> list[FileSummary]:
    files = []
    for path in sorted(companies_dir.glob("*.md")):
        if path.name.startswith("_") or path.name == "README.md":
            continue
        entry_count = count_entries(path)
        if entry_count == 0:
            continue
        files.append(
            FileSummary(
                title=humanize_slug(path.stem),
                rel_path=str(path.relative_to(kb_root)),
                entry_count=entry_count,
                last_updated=last_updated_label(path),
                status=company_status(entry_count),
            )
        )
    return files


def count_bullets(text: str) -> int:
    return len(re.findall(r"^- ", text, flags=re.MULTILINE))


def normalize_status(text: str) -> str:
    upper = text.upper()
    if "WATCH-LIST" in upper:
        return "WATCH-LIST"
    if "TRENDING" in upper:
        return "TRENDING"
    if "ACTIVE" in upper:
        return "ACTIVE"
    return text.strip()


def list_theme_files(themes_dir: Path, kb_root: Path) -> tuple[list[FileSummary], list[FileSummary]]:
    core_files = []
    emerging_files = []
    for path in sorted(themes_dir.glob("*.md")):
        if path.name.startswith("_archive") or path.name == "README.md":
            continue
        if path.name == "_emerging-themes.md":
            for title, body in parse_sections(read_text(path)):
                status = normalize_status(find_first(r"^\*\*Status:\*\*\s*(.+)$", body, "ACTIVE"))
                emerging_files.append(
                    FileSummary(
                        title=title.split("—", 1)[0].strip(),
                        rel_path=str(path.relative_to(kb_root)),
                        entry_count=count_bullets(body),
                        last_updated=last_updated_label(path),
                        status=status,
                    )
                )
            continue

        entry_count = count_entries(path)
        if entry_count == 0:
            continue
        title = humanize_slug(path.stem)
        core_files.append(
            FileSummary(
                title=title,
                rel_path=str(path.relative_to(kb_root)),
                entry_count=entry_count,
                last_updated=last_updated_label(path),
                status=theme_status(title, entry_count),
            )
        )
    return core_files, emerging_files


def load_active_sections(path: Path) -> list[tuple[str, str]]:
    return parse_sections(read_text(path))


def count_recent_updates(root: Path, days: int = 7) -> int:
    cutoff = datetime.now() - timedelta(days=days)
    total = 0
    for path in root.rglob("*.md"):
        if path.name == "README.md":
            continue
        if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
            total += 1
    return total


def current_timestamp_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_index(kb_root: Path) -> str:
    companies = list_company_files(kb_root / "companies", kb_root)
    core_themes, emerging_themes = list_theme_files(kb_root / "themes", kb_root)
    active_emerging = [theme for theme in emerging_themes if theme.status != "WATCH-LIST"]
    watchlist_emerging = [theme for theme in emerging_themes if theme.status == "WATCH-LIST"]
    themes = core_themes + active_emerging
    opportunities = load_active_sections(kb_root / "opportunities" / "active.md")
    ideas = load_active_sections(kb_root / "content-ideas" / "active.md")
    outreach_text = read_text(kb_root / "outreach-queue.md") if (kb_root / "outreach-queue.md").exists() else ""
    dashboard_text = read_text(kb_root / "decision-dashboard.md") if (kb_root / "decision-dashboard.md").exists() else ""

    total_entries = (
        sum(item.entry_count for item in companies)
        + sum(item.entry_count for item in themes)
        + len(opportunities)
        + len(ideas)
    )
    recent_files = count_recent_updates(kb_root)
    top_companies = sorted(companies, key=lambda item: (item.entry_count, item.last_updated, item.title), reverse=True)[:3]
    top_themes = sorted(themes, key=lambda item: (item.entry_count, item.last_updated, item.title), reverse=True)[:3]
    top_outreach = find_first(r"^## 1\. (.+)$", outreach_text)
    ready_idea = find_first(r"^- \*\*(.+?)\*\* — READY", dashboard_text)
    strongest_signal = find_first(r"^\*\*Why now:\*\*\s*(.+)$", outreach_text)

    lines = [
        "# AI Intelligence Knowledge Base",
        "",
        "Curated strategic memory derived from recurring intelligence runs.",
        "",
        "---",
        "",
        "## Health Snapshot",
        f"**Last updated:** {current_timestamp_label()}",
        "**Status:** Active",
        "",
        "### Weekly Stats",
        f"- Tracked companies: {len(companies)}",
        f"- Active themes: {len(themes)}",
        f"- Active opportunities: {len(opportunities)}",
        f"- Active content ideas: {len(ideas)}",
        f"- Total indexed entries: {total_entries}",
        f"- Files touched in last 7 days: {recent_files}",
        "",
        "### Front Page",
    ]
    lines.append(
        f"1. **Leading company:** {top_companies[0].title} ({top_companies[0].entry_count} entries)"
        if top_companies
        else "1. **Leading company:** None yet"
    )
    lines.append(
        f"2. **Leading theme:** {top_themes[0].title} ({top_themes[0].entry_count} signals)"
        if top_themes
        else "2. **Leading theme:** None yet"
    )
    lines.append(f"3. **Priority outreach:** {top_outreach}")
    lines.append(f"4. **Content ready:** {ready_idea}")

    lines.extend([
        "",
        "---",
        "",
        "## Companies",
        "",
        f"### Tracked Companies ({len(companies)})",
        "| Company | Entries | Last Updated | Status |",
        "|---------|---------|--------------|--------|",
    ])
    for item in sorted(companies, key=lambda entry: entry.title):
        lines.append(
            f"| **[{item.title}]({item.rel_path})** | {item.entry_count} | {item.last_updated} | {item.status} |"
        )

    other_companies_path = kb_root / "companies" / "_other-companies.md"
    other_companies = count_entries(other_companies_path) if other_companies_path.exists() else 0
    lines.extend([
        "",
        f"### Other Mentions ({other_companies})",
        "- See [_other-companies.md](companies/_other-companies.md)",
        "",
        "---",
        "",
        "## Themes",
        "",
        f"### Core Themes ({len(core_themes)})",
        "| Theme | Entries | Status |",
        "|-------|---------|--------|",
    ])
    for item in sorted(core_themes, key=lambda entry: entry.title):
        lines.append(f"| **[{item.title}]({item.rel_path})** | {item.entry_count} | {item.status} |")

    lines.extend([
        "",
        f"### Emerging Themes ({len(active_emerging)})",
        "| Theme | Signals | Status |",
        "|-------|---------|--------|",
    ])
    for item in sorted(active_emerging, key=lambda entry: (entry.entry_count, entry.title), reverse=True):
        lines.append(f"| **[{item.title}]({item.rel_path})** | {item.entry_count} | {item.status} |")
    if watchlist_emerging:
        watchlist_labels = ", ".join(f"**{item.title}**" for item in sorted(watchlist_emerging, key=lambda entry: entry.title))
        lines.extend([
            "",
            f"**Watch-list themes:** {watchlist_labels}",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## Opportunities",
        "",
        f"### Active Opportunities ({len(opportunities)})",
    ])
    if opportunities:
        lines.append("| Opportunity | Status |")
        lines.append("|-------------|--------|")
        for title, body in opportunities:
            status = find_first(r"^\*\*Status:\*\*\s*(.+)$", body)
            lines.append(f"| {title} | {status} |")
    else:
        lines.append("- None")

    lines.extend([
        "",
        f"**Strongest Signal:** {strongest_signal}",
        "",
        "---",
        "",
        "## Content Ideas",
        "",
        f"### Active Ideas ({len(ideas)})",
    ])
    if ideas:
        lines.append("| Topic | Status |")
        lines.append("|-------|--------|")
        for title, body in ideas:
            status = find_first(r"^\*\*Status:\*\*\s*(.+)$", body)
            lines.append(f"| {title} | {status} |")
    else:
        lines.append("- None")

    lines.extend([
        "",
        f"**Ready to Publish:** {ready_idea}",
        "",
        "---",
        "",
        "## Operator Notes",
        "",
        "- Start in [decision-dashboard.md](decision-dashboard.md) for weekly priorities.",
        "- Use [outreach-queue.md](outreach-queue.md) as the ranked action list.",
        "- Regenerate this file after canonical KB updates, not before.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    kb_root = Path(os.environ.get("KB_ROOT", str(Path.cwd() / "knowledge-base")))
    index_path = kb_root / "index.md"
    index_path.write_text(build_index(kb_root), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

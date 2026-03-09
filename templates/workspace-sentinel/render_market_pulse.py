#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

MAX_CHARS = 1200


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def friendly_date(source_date: str) -> str:
    try:
        return datetime.strptime(source_date, "%Y-%m-%d").strftime("%b %-d")
    except ValueError:
        return source_date


def clean_field(line: str) -> str:
    text = line.strip().strip("[]")
    text = re.sub(r"^[A-Z][A-Z ]+:\s*", "", text)
    return normalize(text)


def clean_confidence(line: str) -> str:
    text = normalize(line.split(":", 1)[1] if ":" in line else line)
    text = re.sub(r"^[^A-Za-z]+", "", text)
    return text or "Unknown"


def parse_items(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                items.append(current)
                current = {}
            continue

        upper = line.upper()
        if line.startswith("[HEADLINE:") or upper.startswith("HEADLINE:"):
            current["headline"] = clean_field(line)
        elif line.startswith("[WHY IT MATTERS:") or upper.startswith("WHY IT MATTERS:"):
            current["why"] = clean_field(line)
        elif line.startswith("[TAG:") or upper.startswith("TAG:"):
            current["tag"] = clean_field(line)
        elif upper.startswith("CONFIDENCE:"):
            current["confidence"] = clean_confidence(line)

    if current:
        items.append(current)
    return [item for item in items if item.get("headline")]


def parse_freshness(manifest: dict[str, object]) -> str:
    sources = manifest.get("sources", {}) if isinstance(manifest, dict) else {}
    parts = []
    for name in ("ainews", "xdigest", "youtube"):
        status = "unknown"
        if isinstance(sources, dict):
            info = sources.get(name, {})
            if isinstance(info, dict):
                status = str(info.get("status") or "unknown")
        parts.append(f"{name}={status}")
    return " | ".join(parts)


def select_top_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = []
    for item in items:
        tags = {part.strip().lower() for part in item.get("tag", "").split(",")}
        if "content-idea" in tags:
            continue
        selected.append(item)
        if len(selected) == 3:
            break
    return selected or items[:3]


def select_watch_item(items: list[dict[str, str]], selected: list[dict[str, str]]) -> str | None:
    selected_headlines = {item.get("headline") for item in selected}
    for item in items:
        tags = {part.strip().lower() for part in item.get("tag", "").split(",")}
        if "watch-list" in tags and item.get("headline") not in selected_headlines:
            return item.get("headline")
    for item in items:
        if item.get("headline") not in selected_headlines:
            return item.get("headline")
    return None


def trim(text: str) -> str:
    stripped = text.strip()
    if len(stripped) <= MAX_CHARS:
        return stripped
    return stripped[: MAX_CHARS - 3].rstrip() + "..."


def main() -> int:
    base = Path(os.environ.get("PIPELINE_ROOT", Path.cwd()))
    shared = Path(os.environ.get("SHARED", str(base / "shared")))
    collector_manifest_path = Path(
        os.environ.get("COLLECTOR_MANIFEST_FILE", str(shared / "collector-manifest-latest.json"))
    )
    sentinel_output = Path(os.environ.get("SENTINEL_OUTPUT_DIR", str(shared / "sentinel-output")))

    if not collector_manifest_path.exists():
        print("Market pulse unavailable: collector manifest missing.")
        return 0

    manifest = json.loads(collector_manifest_path.read_text(encoding="utf-8"))
    source_date = str(manifest.get("sourceDate") or "unknown")
    digest_path = sentinel_output / f"digest-{source_date}.md"
    freshness = parse_freshness(manifest)

    if not digest_path.exists():
        print(trim(f"Market pulse unavailable for {source_date}. Freshness: {freshness}."))
        return 0

    digest_text = digest_path.read_text(encoding="utf-8", errors="ignore")
    items = parse_items(digest_text)
    if not items:
        print(
            trim(
                f"Market pulse {friendly_date(source_date)}: digest exists but no structured items were parsed. "
                f"Freshness: {freshness}."
            )
        )
        return 0

    top_items = select_top_items(items)
    watch_item = select_watch_item(items, top_items)

    blocks = [f"AI Market Pulse - {friendly_date(source_date)}"]
    for idx, item in enumerate(top_items, start=1):
        blocks.append(f"{idx}. {item['headline']}")
        if item.get("why"):
            blocks.append(f"Why: {item['why']}")
    if watch_item:
        blocks.append(f"Watch: {watch_item}")
    blocks.append(f"Freshness: {freshness}")
    print(trim("\n".join(blocks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

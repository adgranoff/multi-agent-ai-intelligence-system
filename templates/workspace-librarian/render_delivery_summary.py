#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def find_first(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else "None"


def main() -> int:
    base = Path(os.environ.get("PIPELINE_ROOT", Path.cwd()))
    kb_root = Path(os.environ.get("KB_ROOT", str(base / "knowledge-base")))
    sentinel_manifest_path = Path(os.environ.get("SENTINEL_MANIFEST_FILE", str(base / "shared/sentinel-output/manifest-latest.json")))

    outreach_text = (kb_root / "outreach-queue.md").read_text(encoding="utf-8", errors="ignore")
    dashboard_text = (kb_root / "decision-dashboard.md").read_text(encoding="utf-8", errors="ignore")

    top_outreach = find_first(r"^## 1\. (.+)$", outreach_text)
    ready_idea = find_first(r"^- \*\*(.+?)\*\* — READY", dashboard_text)

    source_date = "unknown"
    freshness = "unknown"
    if sentinel_manifest_path.exists():
        manifest = json.loads(sentinel_manifest_path.read_text(encoding="utf-8"))
        source_date = str(manifest.get("sourceDate") or "unknown")
        freshness = " | ".join(
            f"{key}={manifest.get('sourceFreshness', {}).get(key, {}).get('status', 'unknown')}"
            for key in ("ainews", "xdigest", "youtube")
        )

    summary = (
        f"KB refreshed from {source_date}. "
        f"Top outreach: {top_outreach}. "
        f"Content ready: {ready_idea}. "
        f"Freshness: {freshness}."
    )
    print(summary[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SourceSpec:
    name: str
    filename: str
    expected_header: str
    count_pattern: str
    quiet_markers: tuple[str, ...]
    failure_markers: tuple[str, ...]


SOURCE_SPECS = (
    SourceSpec("ainews", "collector-ainews-{date}.md", "# AI News", r"^- \*\*", (), ("# AI News fetch failed",)),
    SourceSpec(
        "xdigest",
        "collector-xdigest-{date}.md",
        "# X/Twitter AI Digest",
        r"^- \[",
        ("No new posts from tracked accounts in this window.",),
        ("# X Digest fetch failed",),
    ),
    SourceSpec(
        "youtube",
        "collector-youtube-{date}.md",
        "# YouTube Digest",
        r"^### ",
        ("No new videos since last digest.",),
        ("# YouTube Digest fetch failed",),
    ),
)


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_items(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.MULTILINE))


def classify_source(path: Path, spec: SourceSpec) -> dict[str, object]:
    if not path.exists():
        return {"status": "missing", "valid": False, "itemCount": 0, "path": str(path), "summary": "file missing"}

    text = path.read_text(encoding="utf-8", errors="replace")
    item_count = count_items(text, spec.count_pattern)
    status = "fresh"
    summary = "items available"
    valid = True

    if any(text.startswith(marker) for marker in spec.failure_markers):
        status = "failed"
        summary = "fetch failed placeholder"
    elif any(marker in text for marker in spec.quiet_markers):
        status = "quiet"
        summary = "no new items in this window"
    elif "Parse error:" in text and item_count == 0:
        status = "failed"
        summary = "source parse error"
    elif not text.startswith(spec.expected_header):
        status = "invalid"
        summary = "unexpected header"
        valid = False
    elif item_count == 0:
        status = "invalid"
        summary = "no parsed items and no quiet marker"
        valid = False

    stat_result = path.stat()
    return {
        "status": status,
        "valid": valid,
        "itemCount": item_count,
        "path": str(path),
        "sha256": compute_sha256(path),
        "sizeBytes": stat_result.st_size,
        "modifiedAt": datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
    }


def build_status_line(source_date: str, sources: dict[str, dict[str, object]], overall: str) -> str:
    prefix = "COLLECTOR_OK" if overall == "ok" else "COLLECTOR_DEGRADED"
    parts = []
    for name in ("ainews", "xdigest", "youtube"):
        info = sources[name]
        status = str(info["status"])
        count = int(info.get("itemCount", 0))
        parts.append(f"{name}=fresh({count})" if status == "fresh" else f"{name}={status}")
    return f"{prefix} {source_date} | " + " ".join(parts)


def run_fetch(workspace: Path) -> None:
    completed = subprocess.run(["bash", str(workspace / "fetch-ai-all.sh")], check=False, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout.strip(), file=sys.stderr)
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    base = Path(os.environ.get("PIPELINE_ROOT", Path.cwd()))
    workspace = Path(os.environ.get("WORKSPACE", str(base / "workspace-collector")))
    shared = Path(os.environ.get("SHARED", str(base / "shared")))
    source_date = os.environ.get("COLLECTOR_DATE", datetime.now().strftime("%Y-%m-%d"))
    manifest_dir = shared / "manifests"
    latest_manifest_path = shared / "collector-manifest-latest.json"

    run_fetch(workspace)

    manifest_dir.mkdir(parents=True, exist_ok=True)
    sources: dict[str, dict[str, object]] = {}
    for spec in SOURCE_SPECS:
        sources[spec.name] = classify_source(shared / spec.filename.format(date=source_date), spec)

    overall = "ok"
    if any(not bool(info["valid"]) for info in sources.values()) or any(str(info["status"]) in {"failed", "missing"} for info in sources.values()):
        overall = "degraded"

    manifest = {
        "schemaVersion": 1,
        "generatedAt": iso_now(),
        "sourceDate": source_date,
        "overallStatus": overall,
        "sources": sources,
    }

    (manifest_dir / f"collector-manifest-{source_date}.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    latest_manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(build_status_line(source_date, sources, overall))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

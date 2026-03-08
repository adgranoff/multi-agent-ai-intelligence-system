#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    base = Path(os.environ.get("PIPELINE_ROOT", Path.cwd()))
    shared = Path(os.environ.get("SHARED", str(base / "shared")))
    collector_manifest_path = shared / "collector-manifest-latest.json"
    sentinel_output = shared / "sentinel-output"

    if not collector_manifest_path.exists():
        raise SystemExit(f"collector manifest missing: {collector_manifest_path}")

    collector_manifest = json.loads(collector_manifest_path.read_text(encoding="utf-8"))
    source_date = str(collector_manifest.get("sourceDate") or "").strip()
    if not source_date:
        raise SystemExit("collector manifest missing sourceDate")

    digest_path = sentinel_output / f"digest-{source_date}.md"
    if not digest_path.exists():
        raise SystemExit(f"sentinel digest missing: {digest_path}")

    sentinel_output.mkdir(parents=True, exist_ok=True)
    digest_latest_path = sentinel_output / "digest-latest.md"
    manifest_latest_path = sentinel_output / "manifest-latest.json"

    shutil.copyfile(digest_path, digest_latest_path)

    manifest = {
        "sourceDate": source_date,
        "generatedAt": iso_now(),
        "digestPath": str(digest_path),
        "latestDigestPath": str(digest_latest_path),
        "sourceFreshness": {
            name: {
                "status": details.get("status"),
                "itemCount": details.get("itemCount"),
                "summary": details.get("summary"),
            }
            for name, details in collector_manifest.get("sources", {}).items()
        },
    }
    manifest_latest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"SENTINEL_PUBLISHED {source_date} -> {digest_latest_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"SYNTHETIC_E2E_FAIL: {message}")


def run(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, capture_output=True)
    if completed.returncode != 0:
        fail(
            "command failed: "
            + " ".join(cmd)
            + f"\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON at {path}: {exc}")


def assert_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        fail(f"missing or empty file: {path}")


def validate_collector_manifest(data: dict) -> None:
    required_top = ["schemaVersion", "generatedAt", "sourceDate", "overallStatus", "sources"]
    for key in required_top:
        if key not in data:
            fail(f"collector manifest missing key: {key}")
    for source in ("ainews", "xdigest", "youtube"):
        if source not in data["sources"]:
            fail(f"collector manifest missing source: {source}")
        source_info = data["sources"][source]
        for key in ("status", "valid", "itemCount", "path", "summary"):
            if key not in source_info:
                fail(f"collector source missing key: {source}.{key}")


def validate_sentinel_manifest(data: dict) -> None:
    for key in ("sourceDate", "generatedAt", "digestPath", "latestDigestPath", "sourceFreshness"):
        if key not in data:
            fail(f"sentinel manifest missing key: {key}")
    for source in ("ainews", "xdigest", "youtube"):
        if source not in data["sourceFreshness"]:
            fail(f"sentinel manifest missing freshness source: {source}")


def validate_editor_artifacts(actions: dict, verification: dict) -> None:
    for key in ("version", "date", "mode", "summary", "actions"):
        if key not in actions:
            fail(f"editor actions missing key: {key}")
    for key in (
        "version",
        "date",
        "mode",
        "memoPath",
        "actionsPath",
        "logPath",
        "derivedRefreshComplete",
        "runtimeRefreshComplete",
        "status",
    ):
        if key not in verification:
            fail(f"editor verification missing key: {key}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    templates_root = repo_root / "templates"

    with tempfile.TemporaryDirectory(prefix="maais-e2e-") as tmp:
        root = Path(tmp)
        shared = root / "shared"
        kb_root = root / "knowledge-base"

        for name in ("workspace-collector", "workspace-sentinel", "workspace-librarian", "workspace-editor", "knowledge-base"):
            shutil.copytree(templates_root / name, root / name)

        (shared / "manifests").mkdir(parents=True, exist_ok=True)
        (shared / "sentinel-output").mkdir(parents=True, exist_ok=True)

        source_date = "2026-01-15"
        base_env = os.environ.copy()
        base_env.update(
            {
                "PIPELINE_ROOT": str(root),
                "WORKSPACE": str(root / "workspace-collector"),
                "SHARED": str(shared),
                "COLLECTOR_DATE": source_date,
                "DATE": source_date,
            }
        )

        run([sys.executable, "collector_run.py"], cwd=root / "workspace-collector", env=base_env)

        collector_manifest_path = shared / "collector-manifest-latest.json"
        assert_file(collector_manifest_path)
        collector_manifest = read_json(collector_manifest_path)
        validate_collector_manifest(collector_manifest)

        digest_path = shared / "sentinel-output" / f"digest-{source_date}.md"
        digest_path.write_text(
            "\n".join(
                [
                    "1)",
                    "HEADLINE: Example model release from Vendor A",
                    "WHY IT MATTERS: Affects delivery timelines for enterprise copilots.",
                    "RECOMMENDED ACTION: Update migration guidance this week.",
                    "TAG: strategy, watch-list",
                    "CONFIDENCE: High",
                    "",
                    "2)",
                    "HEADLINE: New inference pricing pressure",
                    "WHY IT MATTERS: Lower margin assumptions may become outdated.",
                    "RECOMMENDED ACTION: Recalculate pricing benchmarks.",
                    "TAG: economics",
                    "CONFIDENCE: Medium",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        run([sys.executable, "publish_latest_digest.py"], cwd=root / "workspace-sentinel", env=base_env)
        sentinel_manifest_path = shared / "sentinel-output" / "manifest-latest.json"
        assert_file(sentinel_manifest_path)
        sentinel_manifest = read_json(sentinel_manifest_path)
        validate_sentinel_manifest(sentinel_manifest)

        pulse = run([sys.executable, "render_market_pulse.py"], cwd=root / "workspace-sentinel", env=base_env)
        if "AI Market Pulse" not in pulse.stdout:
            fail("sentinel pulse renderer did not return expected output")

        opportunities_path = kb_root / "opportunities" / "active.md"
        opportunities_path.write_text(
            "\n".join(
                [
                    "# Active Opportunities",
                    "",
                    "### Inference Cost Optimization Sprint",
                    "**Strength:** STRONG",
                    "**Status:** ACTIVE",
                    "**Signal:** Repeated pricing pressure across providers",
                    "**Action:** Propose a 2-week optimization engagement",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        ideas_path = kb_root / "content-ideas" / "active.md"
        ideas_path.write_text(
            "\n".join(
                [
                    "# Active Content Ideas",
                    "",
                    "### How to price copilots in a falling-token market",
                    "**Status:** READY",
                    "**First seen:** 2026-01-15",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        librarian_env = os.environ.copy()
        librarian_env.update({"KB_ROOT": str(kb_root)})

        run([sys.executable, "generate_kb_views.py"], cwd=root / "workspace-librarian", env=librarian_env)
        run([sys.executable, "generate_kb_index.py"], cwd=root / "workspace-librarian", env=librarian_env)

        assert_file(kb_root / "outreach-queue.md")
        assert_file(kb_root / "decision-dashboard.md")
        assert_file(kb_root / "index.md")

        editor_date = source_date
        weekly_dir = kb_root / "weekly-memos"
        weekly_dir.mkdir(parents=True, exist_ok=True)
        memo_path = weekly_dir / f"editor-week-{editor_date}.md"
        actions_path = weekly_dir / f"editor-actions-{editor_date}.json"
        verification_path = weekly_dir / f"editor-verification-{editor_date}.json"

        memo_path.write_text("# Weekly Editorial Memo\n\nSynthetic test memo.\n", encoding="utf-8")

        actions = {
            "version": 1,
            "date": editor_date,
            "mode": "rerun-verification",
            "summary": "Synthetic rerun verification",
            "actions": [],
        }
        actions_path.write_text(json.dumps(actions, indent=2) + "\n", encoding="utf-8")

        verification = {
            "version": 1,
            "date": editor_date,
            "mode": "rerun-verification",
            "memoPath": str(memo_path),
            "actionsPath": str(actions_path),
            "logPath": str(kb_root / "memory-bank" / "curation-log.md"),
            "derivedRefreshComplete": True,
            "runtimeRefreshComplete": True,
            "status": "ok",
            "notes": "Synthetic e2e verification",
        }
        verification_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")

        curation_log = kb_root / "memory-bank" / "curation-log.md"
        curation_log.parent.mkdir(parents=True, exist_ok=True)
        if not curation_log.exists():
            curation_log.write_text("# Curation Log\n\n", encoding="utf-8")
        with curation_log.open("a", encoding="utf-8") as handle:
            handle.write(f"## {editor_date} - rerun-verification\n- Summary: Synthetic e2e run\n")

        validate_editor_artifacts(actions, verification)

    print("SYNTHETIC_E2E_OK collector sentinel librarian editor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

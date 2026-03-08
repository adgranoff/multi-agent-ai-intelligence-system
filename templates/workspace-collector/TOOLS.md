# TOOLS.md - Collector Ops

## Mission
Collect and normalize daily AI inputs for Sentinel.

## Required Outputs
- `~/.openclaw/shared/collector-ainews-{date}.md`
- `~/.openclaw/shared/collector-xdigest-{date}.md`
- `~/.openclaw/shared/collector-youtube-{date}.md`
- `~/.openclaw/shared/manifests/collector-manifest-{date}.json`
- `~/.openclaw/shared/collector-manifest-latest.json`

## Execution
- Run `python3 ~/.openclaw/workspace-collector/collector_run.py`
- Treat collector output files as canonical artifacts
- Preserve partial success if one source fails
- End with one status line only

## Quality Gates
- No empty outputs
- Every source classified in the manifest
- Latest manifest updated on every run


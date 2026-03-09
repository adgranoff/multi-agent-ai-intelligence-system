# TOOLS.md - Collector Ops

## Mission
Collect and normalize daily AI inputs for Sentinel.

## Required Outputs
- `shared/collector-ainews-{date}.md`
- `shared/collector-xdigest-{date}.md`
- `shared/collector-youtube-{date}.md`
- `shared/manifests/collector-manifest-{date}.json`
- `shared/collector-manifest-latest.json`

## Execution
- Run `python3 workspace-collector/collector_run.py`
- Treat collector output files as canonical artifacts
- Preserve partial success if one source fails
- End with one status line only

## Quality Gates
- No empty outputs
- Every source classified in the manifest
- Latest manifest updated on every run

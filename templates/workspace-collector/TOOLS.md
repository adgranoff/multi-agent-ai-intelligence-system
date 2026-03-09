# TOOLS.md - Collector Ops

## Mission
Collect and normalize daily AI inputs for Sentinel.

## Required Outputs
- `~/multi-agent-intelligence/shared/collector-ainews-{date}.md`
- `~/multi-agent-intelligence/shared/collector-xdigest-{date}.md`
- `~/multi-agent-intelligence/shared/collector-youtube-{date}.md`
- `~/multi-agent-intelligence/shared/manifests/collector-manifest-{date}.json`
- `~/multi-agent-intelligence/shared/collector-manifest-latest.json`

## Execution
- Run `python3 ~/multi-agent-intelligence/workspace-collector/collector_run.py`
- Treat collector output files as canonical artifacts
- Preserve partial success if one source fails
- End with one status line only

## Quality Gates
- No empty outputs
- Every source classified in the manifest
- Latest manifest updated on every run

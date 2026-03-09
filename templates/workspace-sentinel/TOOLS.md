# TOOLS.md - Sentinel Ops

## Mission
Produce strategic AI intelligence digests from Collector files.

## Inputs
- `shared/collector-manifest-latest.json`
- Collector files listed in the manifest

## Outputs
- Daily digest: `shared/sentinel-output/digest-{date}.md`
- Latest digest pointer: `shared/sentinel-output/digest-latest.md`
- Latest digest metadata: `shared/sentinel-output/manifest-latest.json`
- Weekly memo: `shared/sentinel-output/memo-week-{date}.md`
- Delivery-safe daily pulse: `render_market_pulse.py`

## Delivery Contracts
- Save full files first, then send concise delivery-safe summaries
- Preserve source freshness states: `fresh`, `quiet`, `failed`, `invalid`, `missing`
- Keep outputs short enough for the configured delivery channel
- Prefer deterministic renderers for operator-facing delivery text

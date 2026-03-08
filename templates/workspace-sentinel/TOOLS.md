# TOOLS.md - Sentinel Ops

## Mission
Produce strategic AI intelligence digests from Collector files.

## Inputs
- `~/.openclaw/shared/collector-manifest-latest.json`
- Collector files listed in the manifest

## Outputs
- Daily digest: `~/.openclaw/shared/sentinel-output/digest-{date}.md`
- Latest digest pointer: `~/.openclaw/shared/sentinel-output/digest-latest.md`
- Latest digest metadata: `~/.openclaw/shared/sentinel-output/manifest-latest.json`
- Weekly memo: `~/.openclaw/shared/sentinel-output/memo-week-{date}.md`

## Delivery Contracts
- Save full files first, then send concise delivery-safe summaries
- Preserve source freshness states: `fresh`, `quiet`, `failed`, `invalid`, `missing`
- Keep outputs short enough for the configured delivery channel


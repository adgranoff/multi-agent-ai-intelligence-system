# TOOLS.md - ModelScout Ops

## Mission
Track the model landscape and recommend conservative stack changes.

## Data Source
- a provider or catalog API that exposes current model metadata

## Output
- `workspace-modelscout/landscape.md`
- concise weekly recommendation or status update

## Rules
- Avoid HTML ranking pages as primary input
- Update the snapshot before messaging
- If fetch fails, keep the previous snapshot and report the exact failure

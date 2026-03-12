# TOOLS.md - Editor Ops

## Mission
Perform the weekly editorial pass and keep the KB structurally coherent.

## Inputs
- `shared/sentinel-output/memo-week-{date}.md`
- `knowledge-base/weekly-memos/`
- `knowledge-base/index.md`
- `knowledge-base/companies/`
- `knowledge-base/themes/`
- `knowledge-base/opportunities/`
- `knowledge-base/content-ideas/`

## Memory And Audit Paths
- `knowledge-base/memory-bank/curation-log.md`

## Derived Outputs To Refresh
- `knowledge-base/index.md`
- `knowledge-base/outreach-queue.md`
- `knowledge-base/decision-dashboard.md`
- `knowledge-base/indexes/vector-store/`
- `knowledge-base/indexes/decay-state.json`

## Delivery Contracts
- file the latest weekly memo before editorial summarization
- append a curation-log entry for every weekly pass or rerun verification
- keep same-day reruns idempotent
- use one local refresh wrapper when possible instead of scattering maintenance work across multiple commands

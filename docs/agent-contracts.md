# Agent Contracts

This document defines explicit success, failure, and idempotency contracts for the four agents.

Use these contracts when building orchestration in another environment.

## Collector Contract

### Inputs

- source-fetch configuration
- run date (ISO `YYYY-MM-DD`)

### Required Outputs

- `shared/collector-ainews-YYYY-MM-DD.md`
- `shared/collector-xdigest-YYYY-MM-DD.md`
- `shared/collector-youtube-YYYY-MM-DD.md`
- `shared/collector-manifest-latest.json`
- `shared/manifests/collector-manifest-YYYY-MM-DD.json`

### Success Conditions

- manifest exists and validates against `collector-manifest.schema.json`
- each source has a classified status (`fresh`, `quiet`, `failed`, `invalid`, `missing`)
- one-line terminal status is emitted

### Failure Conditions

- manifest missing or invalid JSON
- required source metadata missing in manifest
- process exits non-zero before manifest write

### Idempotency Rule

- reruns for the same date update dated artifacts and latest manifest in place
- reruns must not create conflicting duplicate manifest names for the same date

## Sentinel Contract

### Inputs

- `shared/collector-manifest-latest.json`
- collector artifacts listed in that manifest

### Required Outputs

- `shared/sentinel-output/digest-YYYY-MM-DD.md`
- `shared/sentinel-output/digest-latest.md`
- `shared/sentinel-output/manifest-latest.json`
- weekly run: `shared/sentinel-output/memo-week-YYYY-MM-DD.md`

### Success Conditions

- dated digest exists and is non-empty
- latest digest pointer matches dated digest content
- manifest exists and validates against `sentinel-manifest.schema.json`
- delivery summary is bounded and non-empty for delivery-facing runs

### Failure Conditions

- missing dated artifact or stale latest pointer
- manifest missing required keys (`sourceDate`, `generatedAt`, `digestPath`, `latestDigestPath`, `sourceFreshness`)
- blank or unusable delivery summary on a delivery-facing run

### Idempotency Rule

- reruns for same source date rewrite dated digest and latest pointers atomically
- latest pointers must always reference the most recent successful run

## Librarian Contract

### Inputs

- `shared/sentinel-output/digest-latest.md`
- `shared/sentinel-output/manifest-latest.json`

### Required Outputs

- updated canonical files in `knowledge-base/`
- refreshed `knowledge-base/index.md`
- refreshed `knowledge-base/outreach-queue.md`
- refreshed `knowledge-base/decision-dashboard.md`
- run report object that validates against `librarian-update.schema.json`

### Success Conditions

- canonical files updated without corrupting markdown structure
- derived views regenerated
- run report includes changed files and source date

### Failure Conditions

- digest missing or incompatible
- canonical update incomplete while run is marked successful
- derived views stale or missing after curation

### Idempotency Rule

- reruns with unchanged digest should converge to stable canonical files
- reruns should prefer merge/update over duplicate entry creation

## Editor Contract

### Inputs

- weekly memo artifact
- canonical KB state

### Required Outputs

- `knowledge-base/weekly-memos/editor-week-YYYY-MM-DD.md`
- `knowledge-base/weekly-memos/editor-actions-YYYY-MM-DD.json`
- rerun verification object matching `editor-verification.schema.json`
- updated `knowledge-base/memory-bank/curation-log.md`

### Success Conditions

- first run writes memo + actions manifest and updates curation log
- same-day rerun writes verification entry without creating a second editorial memo
- maintenance refresh completes after editorial actions

### Failure Conditions

- editorial memo missing on first run
- actions manifest invalid against `editor-actions.schema.json`
- rerun creates duplicate memo for same date

### Idempotency Rule

- one editorial memo per date
- reruns append verification evidence, do not re-curate from scratch

## Runtime Refresh Contract

The KB runtime is not a fifth agent, but it is part of pipeline correctness.

### Required Behavior

- runs after Librarian daily and after Editor weekly
- refreshes vector index, metadata, and decay state from canonical KB
- fails loudly on missing dependencies or stale upstream artifacts

### Idempotency Rule

- reruns with unchanged KB state should produce equivalent retrieval outputs

## Build-System Guidance

If you use this repo as a coding-agent brief:

- generate scheduler jobs from these contracts, not from natural language prompts alone
- validate every handoff artifact with schema checks
- treat non-zero exit and contract violations as hard run failures

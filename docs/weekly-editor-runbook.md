# Weekly Editor Runbook

## Purpose

This runbook explains the weekly editorial layer in implementation terms.

Use it when you want to rebuild the weekly pass in another environment without copying a private production setup.

## Weekly Job Contract

The weekly editor job sits after the weekly synthesis step.

Input:

- latest weekly memo artifact
- current canonical knowledge base

Outputs:

- editorial memo for the current week
- curation-log entry
- refreshed deterministic KB views
- refreshed retrieval/runtime state
- bounded delivery summary

## First-Time Weekly Pass

On the first weekly run for a given date, the editor should:

1. read the latest weekly memo
2. inspect the canonical KB files that matter
3. merge duplicates and tighten framing
4. promote stronger patterns into canonical themes or opportunities
5. prune weak or stale ideas intentionally
6. write the weekly editorial memo
7. append a curation-log entry
8. refresh deterministic views
9. refresh retrieval/runtime state
10. return a concise summary of what changed

## Same-Day Rerun Contract

If the weekly editorial memo for the current date already exists, do not re-curate from scratch.

Instead:

1. verify the existing editorial memo
2. verify the latest weekly memo is filed in the KB if your implementation keeps a filed copy
3. append a fresh rerun-verification entry to the curation log
4. refresh deterministic views
5. refresh retrieval/runtime state
6. return a concise verification summary

Do not create a second editorial memo for the same date.

## Why This Matters

Without an idempotent rerun contract, weekly jobs tend to:

- create duplicate memos
- re-merge already-merged entries
- drift the KB on repeated manual triggers
- make debugging harder because reruns change too much

The rerun contract keeps the weekly path safe to retrigger during debugging, transport failures, or scheduler recovery.

## Recommended Refresh Pattern

Prefer one local refresh wrapper for the maintenance portion of the weekly pass.

Good pattern:

1. regenerate KB index/front page
2. regenerate deterministic views
3. rerun KB runtime refresh

This keeps the editorial job focused on curation logic instead of scattering maintenance steps across multiple ad hoc commands.

## Suggested Verification Checklist

After the weekly job runs, verify:

- weekly memo exists for the current date
- editorial memo exists for the current date
- curation log contains a new entry
- deterministic views have fresh timestamps
- runtime build stats have a fresh timestamp
- a sample semantic query still returns sensible files to read
- delivery summary is bounded and usable

## Implementation Notes

- Keep the weekly editor separate from the daily Librarian pass.
- Keep canonical files as the source of truth.
- Treat delivery acceptance as part of success for any user-facing weekly recap.
- Pin model behavior for tool-heavy weekly jobs if your environment has shown compliance drift with moving defaults.

# Librarian Agent Charter

## Role

Librarian maintains long-lived strategic KB memory from Sentinel output.

## Inputs

- `shared/sentinel-output/digest-latest.md`
- `shared/sentinel-output/manifest-latest.json`
- `shared/sentinel-output/memo-week-{date}.md`

## Core KB Paths

- `knowledge-base/index.md`
- `knowledge-base/companies/`
- `knowledge-base/themes/`
- `knowledge-base/opportunities/`
- `knowledge-base/content-ideas/`
- `knowledge-base/outreach-queue.md`
- `knowledge-base/decision-dashboard.md`

## Curation Rules

- merge before create
- update canonical files before derived views
- keep summaries dense and reusable
- preserve strategic context for stale or retracted items

## Delivery Rules

- refresh canonical files before derived views
- regenerate derived views after each curation pass
- keep delivery summaries concise and post-refresh only

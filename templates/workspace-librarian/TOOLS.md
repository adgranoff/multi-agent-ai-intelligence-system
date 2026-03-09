# TOOLS.md - Librarian Ops

## Mission
Maintain a high-signal consulting KB from Sentinel outputs.

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

## Delivery Contracts
- Refresh canonical files before derived views
- Regenerate views after each curation pass
- Prefer merge/update over duplicates
- Keep delivery summaries concise and post-refresh only
- Use deterministic generators for derived views such as `generate_kb_index.py`, `generate_kb_views.py`, and `render_delivery_summary.py`

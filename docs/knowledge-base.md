# Knowledge Base

## Goal

The knowledge base is not an article dump. It is durable strategic memory.

It should answer:

- what matters now
- what keeps recurring
- which entities and themes are heating up
- what is commercially actionable
- what has started to go stale

## Canonical KB Structure

- `companies/`
- `themes/`
- `opportunities/`
- `content-ideas/`
- `daily-digests/`
- `weekly-memos/`
- `index.md`

These are the files Librarian curates directly.

## Derived Views

- `decision-dashboard.md`
- `outreach-queue.md`
- `indexes/vector-store/`
- `indexes/decay-state.json`
- optional relation graph exports

These are regenerated or refreshed from the canonical KB. They are not the primary truth.

## Curation Rules

- update existing files before creating new ones
- merge recurring signals rather than duplicating them
- keep canonical files dense and client-usable
- regenerate derived views after canonical updates
- let decay surface stale claims instead of silently hiding them

## Retrieval Rules

The operator-facing assistant should not guess from memory.

For KB questions it should:

1. run semantic retrieval over the live KB
2. read the top canonical files returned by retrieval
3. answer with dates, confidence, and strategic context

That pattern keeps interactive answers aligned with the actual maintained KB.

## Suggested Graduation Rules

- promote a company when it recurs enough to matter strategically
- promote a theme when cross-entity recurrence becomes meaningful
- create or strengthen an opportunity when the signal becomes commercially actionable
- move content ideas forward when evidence becomes durable enough to publish from

## Output Expectations

The KB should make it easy to answer:

- what changed today
- what matters this week
- what the operator should do next
- what is worth writing about
- what prior intelligence is semantically similar
- what claims need reconfirmation

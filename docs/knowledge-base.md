# Knowledge Base

## Goal

The knowledge base is not a dump of articles. It is a consulting memory system backed by structure, retrieval, and maintenance logic.

It should answer:

- what matters strategically
- what keeps recurring
- which companies and themes are heating up
- what outreach or content opportunities exist now

## Core Directories

- `companies/`
- `themes/`
- `opportunities/`
- `content-ideas/`
- `daily-digests/`
- `weekly-memos/`

## Structured Data Model

The advanced KB layer adds a typed model on top of markdown:

- entities: labs, models, people, companies, investors, regulators, themes, opportunities
- signals: dated facts with type, confidence, and source digest
- relations: competitor, partnership, lineage, supply, investment, regulatory, and talent links

This structure is what enables semantic search, graph queries, contradiction tracking, and confidence decay.

## Canonical Versus Derived Content

### Canonical

- company files
- theme files
- active opportunities
- active content ideas

### Derived

- `outreach-queue.md`
- `decision-dashboard.md`
- vector indexes and embedding cache under `indexes/vector-store/`
- relation graph export under `indexes/relations.json`

Derived views should be regenerated from canonical files, not edited as primary truth.

## Curation Rules

- update existing files before creating new ones
- promote recurring signals into canonical files
- avoid one-off duplicate files
- group by consulting usefulness, not source feed
- preserve `digest_sources`, signal ids, confidence, and relation context
- let decay and validation surface stale items instead of hiding them

## Suggested Graduation Rules

- create a company file when it appears repeatedly across digests
- create a theme file when cross-company recurrence is strong enough to matter strategically
- create or update relations when repeated signals show a stable connection
- lower confidence or flag for review when a claim stops being reconfirmed

## Output Expectations

The KB should make it easy to answer:

- what changed today
- what matters this week
- what is commercially actionable
- what should be published or sent to clients
- what old claims are becoming stale
- which entities are connected by graph structure
- what semantically similar prior intelligence already exists

# Architecture

## System Overview

This workflow has five layers:

1. Collector
2. Sentinel
3. Librarian
4. Knowledge base runtime
5. Operator assistant

Each layer has one job. That separation is what keeps the system understandable and recoverable.

## Layer Responsibilities

### Collector

Collector is ingestion-only.

Responsibilities:

- gather source material
- normalize outputs
- publish a freshness manifest

Collector should not improvise analysis or touch the KB.

### Sentinel

Sentinel is the synthesis layer.

Responsibilities:

- transform source artifacts into daily and weekly intelligence
- write dated artifacts first
- update latest pointers
- render bounded delivery summaries afterward

### Librarian

Librarian is the curation layer.

Responsibilities:

- convert short-lived digests into long-lived strategic memory
- update canonical company, theme, opportunity, and content files
- regenerate deterministic views

### Knowledge Base Runtime

The KB runtime is the maintenance and retrieval layer.

Responsibilities:

- refresh semantic search state over the live KB
- maintain confidence decay state
- expose retrieval utilities for downstream use
- optionally maintain graph and hybrid retrieval if relation structure is mature enough

This runtime should sit on top of the same KB that Librarian curates. It should not become a separate competing data store.

### Operator Assistant

The operator assistant is the interface layer.

Responsibilities:

- receive interactive questions
- detect when a query should use the KB
- run retrieval first
- read the top canonical files
- answer with context, dates, and confidence

## Data Flow

```text
external sources
  -> Collector artifacts
  -> Collector manifest
  -> Sentinel digest / memo artifacts
  -> latest pointers
  -> Librarian canonical KB updates
  -> deterministic derived views
  -> KB runtime refresh
  -> operator assistant queries over the live KB
```

## Canonical Versus Derived

Canonical data:

- company files
- theme files
- active opportunities
- active content ideas
- dated digest archives

Derived data:

- dashboard and outreach views
- vector index files
- decay state
- optional graph exports

Derived files should be regenerated, not hand-maintained as truth.

## Reliability Boundaries

- Collector succeeds only if the manifest is valid.
- Sentinel succeeds only if the digest artifact exists.
- Librarian succeeds only if canonical files and views refresh cleanly.
- KB runtime succeeds only if retrieval state refreshes cleanly.
- delivery-facing jobs are not successful unless the final payload is actually usable.

## Recommended Scheduling Pattern

```text
Collector
  -> buffer
Sentinel
  -> buffer
Librarian
  -> buffer
KB runtime
```

Use real buffers between steps. Do not stack jobs back-to-back just because median runtime looks fine.

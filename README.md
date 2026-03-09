# Multi-Agent AI Intelligence System

This repository is a sanitized reference implementation for a narrow workflow:

```text
Collector -> Sentinel -> Librarian -> Knowledge Base Runtime -> Operator Assistant
```

It is not a general-purpose agent starter kit. It is a production-shaped pattern for turning recurring market signals into durable, queryable memory.

## What This System Does

This system turns raw AI market signals into:

- a daily market-awareness pulse delivered through a messaging channel of your choice
- a maintained knowledge base
- semantic retrieval over that knowledge base
- a weekly recap
- on-demand KB answers through an operator-facing assistant

The result is a workflow that pushes high-signal updates on a schedule while still supporting interactive queries later.

## End-to-End Daily Flow

```text
11:30 AM
Collector
  gathers raw source files from the configured source set
  writes collector artifacts + freshness manifest
        |
        v
12:15 PM
Sentinel Daily
  reads collector manifest + raw source files
  writes:
  - shared/sentinel-output/digest-YYYY-MM-DD.md
  - shared/sentinel-output/digest-latest.md
  - shared/sentinel-output/manifest-latest.json
  sends a daily market pulse through the configured delivery channel
        |
        v
1:00 PM
Librarian Daily
  reads sentinel latest digest + manifest
  updates canonical KB files:
  - companies/*.md
  - themes/*.md
  - opportunities/active.md
  - content-ideas/active.md
  - daily-digests/YYYY-MM-DD.md
  rebuilds:
  - index.md
  - decision-dashboard.md
  - outreach-queue.md
        |
        v
1:30 PM
KB Runtime Daily
  reads the live knowledge-base/
  refreshes:
  - indexes/vector-store/index.faiss
  - indexes/vector-store/metadata.json
  - indexes/vector-store/embedding-cache.json
  - indexes/decay-state.json
```

## Assistant Query Path

```text
Operator
   |
   v
Operator Assistant
  detects AI / market / company / strategy / opportunity questions
  runs a live KB query:
  python3 kb-runtime/query_live_kb.py "<question>" --json
   |
   v
Semantic KB Runtime
  searches the live vector index
  returns top matches + files_to_read
   |
   v
Operator Assistant
  reads the top canonical KB files
  answers with dates, confidence, and context
```

## Weekly Flow

```text
Sunday 2:00 PM
Sentinel Weekly
  reads recent daily digests + KB context
  writes a weekly memo artifact
  sends a weekly market recap through the configured delivery channel
```

## Why The Timing Matters

- Collector finishes before Sentinel starts
- Sentinel writes artifacts before Librarian reads them
- Librarian updates canonical KB files before the KB runtime refreshes retrieval state
- delivery-facing summaries happen before maintenance-only jobs
- runtime buffers matter more than exact clock times

## System Layers

### 1. Collector

Collector is bounded ingestion.

It should:

- gather raw source material
- normalize output shape
- write dated artifacts
- publish a manifest that records freshness, failures, and counts

Collector should stay deterministic and cheap.

### 2. Sentinel

Sentinel is the synthesis layer.

It should:

- read only the source artifacts listed in the Collector manifest
- write a dated daily digest
- write a dated weekly memo
- publish latest pointers for downstream consumers
- render concise delivery-safe summaries after artifacts exist

### 3. Librarian

Librarian is the curation layer.

It should:

- read the latest digest artifact
- merge recurring signals into canonical KB files
- preserve dated archives
- regenerate deterministic views such as the dashboard and outreach queue

Librarian should update existing files before creating new ones.

### 4. Knowledge Base Runtime

The KB runtime is the retrieval and maintenance plane behind Librarian.

It should:

- build and refresh embeddings over the live KB
- maintain a vector index for semantic retrieval
- track confidence decay so stale claims do not look permanently current
- optionally maintain a relation graph when the underlying KB structure supports it cleanly

This runtime should operate on the same knowledge base that Librarian curates. The clean end state is one canonical KB, not two competing stores.

### 5. Operator Assistant

The operator assistant sits on top of the KB.

It should:

- detect when a question is really a KB query
- run semantic retrieval first
- read the top canonical files returned by retrieval
- answer with dates, confidence, and strategic context

This keeps the scheduled intelligence workflow and the interactive query workflow connected.

## Live Advanced KB Capabilities Represented Here

- markdown-first canonical KB
- Collector intake with manifest-driven freshness tracking
- daily market pulse delivery from Sentinel
- daily Librarian KB maintenance
- deterministic dashboard and outreach generation
- vector-backed semantic retrieval
- query helper for an operator assistant
- confidence decay over live KB content
- optional graph and hybrid retrieval when relations are mature enough to justify them
- failure-alert friendly workflow boundaries

## Design Principles

- one canonical KB
- deterministic work stays deterministic
- artifacts are written before summaries are delivered
- latest pointers are part of the contract
- merge-first curation beats duplicate creation
- retrieval quality depends on structure, not embeddings alone
- scheduled success is not real success unless the final output is actually usable

## Meaning

- Collector finds the raw signals
- Sentinel turns them into market intelligence
- Librarian turns that into durable knowledge memory
- the KB runtime makes that memory searchable by meaning
- the operator assistant becomes the phone-facing interface to all of it

## Repository Layout

```text
docs/
  architecture.md
  advanced-kb.md
  cron-and-delivery.md
  getting-started.md
  knowledge-base.md
examples/
  .env.example
  schedule.md
  sample-digest.md
  sample-entity-lab.md
skills/
  delivery-debugging/
  digest-pipeline/
  librarian-kb-curation/
  scheduler-runbook/
  wrapper-hardening/
templates/
  knowledge-base/
  shared/
  workspace-collector/
  workspace-sentinel/
  workspace-librarian/
  workspace-modelscout/
  kb-upgrade/
```

## What Is Included

- sanitized Collector, Sentinel, Librarian, and model-landscape templates
- knowledge-base templates and example files
- advanced KB runtime code for indexing, search, decay, and maintenance
- deterministic reference scripts for market-pulse rendering and KB index generation
- workflow docs and runbooks
- synthetic examples only

## What Is Excluded

- runtime secrets or credentials
- real delivery endpoints
- local machine paths
- private digests, memos, or KB contents
- generated indexes, caches, logs, and backups
- personal notes, session history, or operator identity details

## Recommended Reading Order

1. [docs/architecture.md](docs/architecture.md)
2. [docs/knowledge-base.md](docs/knowledge-base.md)
3. [docs/advanced-kb.md](docs/advanced-kb.md)
4. [docs/cron-and-delivery.md](docs/cron-and-delivery.md)
5. [docs/getting-started.md](docs/getting-started.md)

## Before You Publish Your Own Version

1. Re-read [SANITIZATION.md](SANITIZATION.md).
2. Remove all generated runtime artifacts.
3. Replace every transport, scheduler, and provider detail with your own environment-specific settings.
4. Re-run a leakage search across the repo before publishing.

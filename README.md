# Multi-Agent AI Intelligence System

This repository is a sanitized implementation kit for a narrow 4-agent workflow:

```text
Collector -> Sentinel -> Librarian -> Knowledge Base Runtime
                       \
                        -> Editor Weekly -> Knowledge Base Runtime
```

It is intended to be studied, adapted, and rebuilt inside another environment by a coding workflow or engineering team. It is not a turnkey platform. It is a production-shaped pattern for turning recurring market signals into durable, queryable memory.

## What This System Does

This system turns raw AI market signals into:

- a daily market-awareness pulse delivered through a messaging channel of your choice
- a maintained knowledge base
- semantic retrieval over that knowledge base
- a weekly recap
- stable contracts between the four pipeline agents

The result is a workflow that pushes high-signal updates on a schedule while keeping handoffs explicit and testable.

## How To Use This Repository

Use this repository as:

- an architecture reference for the end-to-end workflow
- a template pack for the four workspaces and runtime layer
- an implementation brief for an AI coding workflow that will rebuild the system in a different environment

Naming note:

- `workspace-*` directory names in this template are placeholders. Rename them to any structure your environment prefers.

Do not use it as:

- a drop-in production deployment
- a bundle of live credentials, delivery targets, or private data
- a promise that every implementation should use the exact same scheduler, transport, or model provider

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

## Weekly Flow

```text
Sunday 2:00 PM
Sentinel Weekly
  reads recent daily digests + KB context
  writes a weekly memo artifact
  sends a weekly market recap through the configured delivery channel

Sunday 2:30 PM
Editor Weekly
  reads the weekly memo + live KB
  performs high-order curation or an idempotent rerun verification
  appends a curation-log entry
  refreshes deterministic KB views
  refreshes KB runtime state so retrieval matches the curated KB
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
- treat a delivery-facing run as successful only when the summary is usable and accepted by the configured delivery path

### 3. Librarian

Librarian is the curation layer.

It should:

- read the latest digest artifact
- merge recurring signals into canonical KB files
- preserve dated archives
- regenerate deterministic views such as the dashboard and outreach queue

Librarian should update existing files before creating new ones.

### 4. Editor Weekly

Editor is the weekly high-order curation layer.

It should:

- read the latest weekly memo plus relevant canonical KB files
- merge duplicates, tighten summaries, and promote durable patterns
- append a weekly curation-log entry
- support idempotent same-day reruns that verify state instead of re-curating from scratch
- refresh the same derived views and retrieval state the workflow depends on

### 5. Knowledge Base Runtime

The KB runtime is the retrieval and maintenance plane behind Librarian.

It should:

- build and refresh embeddings over the live KB
- maintain a vector index for semantic retrieval
- track confidence decay so stale claims do not look permanently current
- optionally maintain a relation graph when the underlying KB structure supports it cleanly

This runtime should operate on the same knowledge base that Librarian curates. The clean end state is one canonical KB, not two competing stores.

## Handoff Contracts

Machine-readable schemas are included for artifact boundaries:

- [docs/contracts/collector-manifest.schema.json](docs/contracts/collector-manifest.schema.json)
- [docs/contracts/sentinel-manifest.schema.json](docs/contracts/sentinel-manifest.schema.json)
- [docs/contracts/librarian-update.schema.json](docs/contracts/librarian-update.schema.json)
- [docs/contracts/editor-actions.schema.json](docs/contracts/editor-actions.schema.json)
- [docs/contracts/editor-verification.schema.json](docs/contracts/editor-verification.schema.json)

Contract usage guide:

- [docs/contracts.md](docs/contracts.md)

## Agent Reliability Contracts

Per-agent success, failure, and idempotency behavior:

- [docs/agent-contracts.md](docs/agent-contracts.md)

## Live Advanced KB Capabilities Represented Here

- markdown-first canonical KB
- Collector intake with manifest-driven freshness tracking
- daily market pulse delivery from Sentinel
- daily Librarian KB maintenance
- deterministic dashboard and outreach generation
- vector-backed semantic retrieval
- query helper with exact-entity boosts and absolute file-path follow-ups
- confidence decay over live KB content
- weekly editorial curation and rerun verification
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
- Editor performs weekly high-order curation
- the KB runtime makes that memory searchable by meaning

## Repository Layout

```text
docs/
  advanced-kb.md
  agent-contracts.md
  architecture.md
  contracts.md
  contracts/
    collector-manifest.schema.json
    sentinel-manifest.schema.json
    librarian-update.schema.json
    editor-actions.schema.json
    editor-verification.schema.json
  cron-and-delivery.md
  getting-started.md
  knowledge-base.md
  weekly-editor-runbook.md
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
  workspace-editor/
  workspace-sentinel/
  workspace-librarian/
  kb-upgrade/
tests/
  synthetic_e2e.py
```

## What Is Included

- sanitized Collector, Sentinel, Librarian, and Editor templates
- sanitized weekly Editor templates and rerun pattern
- knowledge-base templates and example files
- advanced KB runtime code for indexing, search, decay, and maintenance
- deterministic reference scripts for market-pulse rendering and KB index generation
- machine-readable handoff contracts
- synthetic end-to-end harness
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
2. [docs/agent-contracts.md](docs/agent-contracts.md)
3. [docs/contracts.md](docs/contracts.md)
4. [docs/knowledge-base.md](docs/knowledge-base.md)
5. [docs/advanced-kb.md](docs/advanced-kb.md)
6. [docs/cron-and-delivery.md](docs/cron-and-delivery.md)
7. [docs/weekly-editor-runbook.md](docs/weekly-editor-runbook.md)
8. [docs/getting-started.md](docs/getting-started.md)

## Before You Publish Your Own Version

1. Re-read [SANITIZATION.md](SANITIZATION.md).
2. Remove all generated runtime artifacts.
3. Replace every transport, scheduler, and provider detail with your own environment-specific settings.
4. Re-run a leakage search across the repo before publishing.

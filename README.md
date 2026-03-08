# OpenClaw Multi-Agent AI Intelligence System

OpenClaw Multi-Agent AI Intelligence System is a narrow, production-oriented overlay for one specific workflow:

`Collector -> Sentinel -> advanced knowledge base`

It is not a general OpenClaw starter kit. It excludes personal assistants, messaging automations, device control, unrelated agents, and bundled upstream code. This repo exists to show how to run a repeatable AI intelligence pipeline that turns daily source noise into durable strategic memory.

## What This System Actually Does

The system has three operating agents and one persistent intelligence layer:

1. `Collector`
   - fetches and normalizes source material
   - writes dated raw artifacts
   - validates freshness, completeness, and failure states
   - publishes a manifest as the contract for downstream stages
2. `Sentinel`
   - reads Collector artifacts and freshness metadata
   - produces daily digests and weekly memos
   - writes latest pointers for downstream consumption
   - renders concise delivery-safe summaries
3. `Librarian`
   - ingests Sentinel output into the knowledge base
   - merges recurring signals into canonical entities and themes
   - refreshes deterministic views like outreach and dashboard summaries
4. `Advanced KB Engine`
   - maintains embeddings and a semantic index
   - builds a relationship graph across labs, models, companies, people, regulators, and themes
   - supports semantic search, graph queries, and combined search
   - decays stale confidence over time to keep the KB current

## Why The KB Layer Matters

Most intelligence systems stop at “generate a digest.” This one does not.

The knowledge base is treated as the durable product:

- digests are short-lived inputs
- entities and themes are long-lived memory
- semantic retrieval makes old intelligence usable
- graph structure turns isolated facts into relationship intelligence
- confidence decay prevents stale claims from looking permanently true

That is the main differentiator of this system.

## Advanced KB Capabilities Included

- `Schema-driven entities`
  The KB tracks typed entities such as labs, models, people, companies, investors, regulators, themes, and opportunities.
- `Structured signals`
  Each entity can accumulate dated signals with confidence, source digests, contradictions, and supersession links.
- `Embeddings + vector index`
  Chunks are embedded and stored in a FAISS-backed vector index with an embedding cache.
- `Semantic search`
  Queries can retrieve the most relevant KB chunks, filtered by entity type, sector, date window, and minimum confidence.
- `Relationship graph`
  A directed graph captures explicit and inferred relations such as competition, partnerships, supply dependencies, model lineage, talent flows, and portfolio overlap.
- `Combined search`
  Queries can mix semantic evidence and graph traversal to answer higher-level questions like “who competes with X and shares the same infrastructure.”
- `Confidence decay`
  Entity confidence degrades according to time, type, status, and special conditions so stale intelligence is surfaced and revalidation is encouraged.
- `Operational reporting`
  The KB exposes status, validation, anomaly detection, model snapshots, theme reports, and weekly memo generation.

## Design Principles

- Deterministic work stays deterministic.
- Artifacts are written before summaries are delivered.
- The latest pointer is part of the contract, not a convenience.
- KB curation is merge-first, not create-first.
- Search quality depends on structure, not just embeddings.
- Cron success is not success unless the output is actually deliverable.

## Included In This Export

- sanitized templates for `workspace-collector`, `workspace-sentinel`, and `workspace-librarian`
- sanitized runtime files for agent boot order, role doctrine, and ops contracts
- workflow-specific custom OpenClaw skills
- sanitized KB engine code for embeddings, indexing, graphing, decay, validation, and operations
- knowledge-base layout templates
- architecture, cron, delivery, and KB documentation

## Excluded On Purpose

- bundled OpenClaw package code
- unrelated agents and automations
- personal memory, session history, and run logs
- secrets, tokens, and local config values
- private digests, memos, and client-specific KB content
- real delivery endpoints and chat identifiers
- generated indexes, caches, backups, and other live runtime artifacts

## Repository Layout

```text
docs/
  getting-started.md
  architecture.md
  cron-and-delivery.md
  knowledge-base.md
  advanced-kb.md
templates/
  shared/
    USER.md
    BOOTSTRAP.md
  workspace-collector/
    SOUL.md
    TOOLS.md
    USER.md
  workspace-sentinel/
    SOUL.md
    TOOLS.md
    USER.md
  workspace-librarian/
    SOUL.md
    TOOLS.md
    USER.md
  workspace-modelscout/
    AGENTS.md
    SOUL.md
    TOOLS.md
    USER.md
  knowledge-base/
  kb-upgrade/
    config/
    src/
    tests/
    openclaw.py
    validate_schema.py
    build_index.py
    daily_run.sh
    setup.sh
skills/
  openclaw-cron-runbook/
  openclaw-delivery-debugging/
  openclaw-wrapper-hardening/
  openclaw-digest-pipeline/
  openclaw-librarian-kb-curation/
examples/
  .env.example
  schedule.md
```

## End-To-End Flow

### Collector

Collector is ingestion-only and should be cheap, bounded, and deterministic.

Expected outputs:

- `shared/collector-ainews-YYYY-MM-DD.md`
- `shared/collector-xdigest-YYYY-MM-DD.md`
- `shared/collector-youtube-YYYY-MM-DD.md`
- `shared/collector-manifest-latest.json`
- `shared/manifests/collector-manifest-YYYY-MM-DD.json`

The manifest tells downstream stages whether each source is `fresh`, `quiet`, `failed`, `invalid`, or `missing`.

### Sentinel

Sentinel turns source artifacts into strategic intelligence artifacts.

Expected outputs:

- `shared/sentinel-output/digest-YYYY-MM-DD.md`
- `shared/sentinel-output/digest-latest.md`
- `shared/sentinel-output/manifest-latest.json`
- `shared/sentinel-output/memo-week-YYYY-MM-DD.md`

Sentinel should write the artifact first and only then render a concise delivery-safe summary.

### Librarian

Librarian is the curation layer. It promotes recurring signals into durable memory.

Primary responsibilities:

- file dated daily digests and weekly memos
- update canonical entity and theme files
- merge recurring evidence instead of creating duplicates
- refresh deterministic views like `outreach-queue.md` and `decision-dashboard.md`

### Advanced KB Runtime

The KB runtime is the retrieval and maintenance plane behind Librarian:

- `config/schema.yaml` defines the entity, signal, and relation model
- `src/embedder.py` handles embedding generation and caching
- `src/index_manager.py` and `build_index.py` maintain the vector store
- `src/search.py` performs semantic retrieval
- `src/graph_builder.py` and `src/graph_query.py` maintain and query the relation graph
- `src/combined_search.py` merges graph evidence with semantic evidence
- `src/decay.py` finds stale or low-confidence entities and can apply decay updates
- `openclaw.py` provides a single operational CLI over the whole KB engine

## Custom Skills Included

These skills teach OpenClaw how to operate this workflow reliably:

- `openclaw-cron-runbook`
- `openclaw-delivery-debugging`
- `openclaw-wrapper-hardening`
- `openclaw-digest-pipeline`
- `openclaw-librarian-kb-curation`

They are custom skills, not bundled-package edits, so they survive OpenClaw upgrades when stored in `~/.openclaw/skills` or workspace-local `skills/` directories.

## How To Use This Repo

1. Install upstream OpenClaw separately.
2. Copy the Collector, Sentinel, Librarian, KB, and skill templates into your own `~/.openclaw` layout.
3. Add your own fetchers, model settings, digests, and delivery endpoints.
4. Keep every secret in local-only config.
5. Treat this repo as the workflow overlay, not as a replacement for upstream OpenClaw.

Start with [docs/getting-started.md](docs/getting-started.md) if you want a concrete path from clone to first dry run.

## Before You Publish Your Own Version

1. Re-read [SANITIZATION.md](SANITIZATION.md).
2. Confirm no digests, logs, indexes, or backups are present.
3. Replace placeholder delivery targets and local paths with your own values.
4. Keep upstream OpenClaw attribution via [ATTRIBUTION.md](ATTRIBUTION.md).

## Best Fit

This system fits operators who want:

- repeatable AI market and product intelligence
- a daily intelligence pipeline instead of ad hoc browsing
- a reusable consulting KB instead of a pile of markdown digests
- retrieval over past intelligence through semantic search and graph structure
- a workflow that cleanly separates bounded automation from LLM judgment

## Attribution

This repository is an overlay and workflow template built on top of upstream OpenClaw. It is not a fork of the full OpenClaw codebase.

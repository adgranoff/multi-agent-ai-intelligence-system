# Architecture

## System Overview

This workflow is a compact multi-agent intelligence system with three operational agents, one shared artifact layer, and one advanced knowledge-base runtime.

### Collector

Purpose:

- gather source material
- normalize outputs
- publish a freshness manifest

Collector should be shell-first and deterministic.

### Sentinel

Purpose:

- transform source files into daily and weekly intelligence
- publish latest pointers used by downstream stages

Sentinel is the main synthesis layer.

### Librarian

Purpose:

- convert short-lived digests into long-lived consulting memory
- update canonical company and theme files
- refresh deterministic dashboards

Librarian is the curation layer.

### Advanced KB Runtime

Purpose:

- maintain the typed entity store behind Librarian
- build and refresh embeddings, vector indexes, and graph indexes
- expose semantic, graph, and hybrid retrieval
- keep stale intelligence visible through confidence decay

This runtime is the retrieval and maintenance layer, not a separate conversational agent.

## Data Flow

```text
external sources
  -> Collector raw artifacts
  -> collector manifest
  -> Sentinel digest / memo artifacts
  -> Sentinel latest pointers
  -> Librarian KB updates
  -> advanced KB indexes and relation graph
  -> derived operational views
  -> delivery-safe summaries
```

## Artifact Contracts

### Collector contract

Collector writes dated source files and a manifest that records:

- `sourceDate`
- `overallStatus`
- per-source status
- item counts
- file metadata

### Sentinel contract

Sentinel writes:

- a dated digest or weekly memo
- `digest-latest.md`
- a lightweight manifest for downstream freshness awareness

### Librarian contract

Librarian updates:

- canonical KB files
- dated archive copies
- deterministic views like outreach queue and decision dashboard

### Advanced KB contract

The KB runtime maintains:

- schema-governed entity files
- signal histories and relation data
- `indexes/vector-store/` for semantic retrieval
- `indexes/relations.json` for graph traversal
- stale/low-confidence reporting for ongoing curation

## Reliability Philosophy

- bounded jobs should execute one primary path
- artifact validation is mandatory
- delivery payloads should be rendered, not improvised
- stale latest pointers count as failure
- embeddings and search should degrade visibly, not silently
- graph inference should be explicit enough to inspect and validate

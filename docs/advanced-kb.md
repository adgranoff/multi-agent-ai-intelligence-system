# Advanced KB

## Purpose

The advanced KB runtime is the maintenance and retrieval layer behind the digest pipeline.

Its job is to make a live markdown KB:

- searchable by meaning
- age-aware through confidence decay
- optionally relation-aware when graph structure is worth the operational complexity

## Clean End State

The preferred architecture is:

```text
canonical markdown KB
  -> semantic index
  -> decay state
  -> optional graph exports
```

That means one source of truth for knowledge and a separate runtime for retrieval artifacts.

## Core Capabilities

### Semantic Retrieval

The runtime can:

- chunk canonical KB files
- generate embeddings
- store vectors in a local index
- retrieve relevant KB sections for operator questions or downstream agents

Relevant files:

- [templates/kb-upgrade/src/chunker.py](../templates/kb-upgrade/src/chunker.py)
- [templates/kb-upgrade/src/embedder.py](../templates/kb-upgrade/src/embedder.py)
- [templates/kb-upgrade/src/index_manager.py](../templates/kb-upgrade/src/index_manager.py)
- [templates/kb-upgrade/src/search.py](../templates/kb-upgrade/src/search.py)

### Live-KB Query Helper

The runtime includes a query helper for operator-facing assistants.

Its job is to:

- run semantic search first
- collapse noisy duplicate chunks
- return the best matches
- suggest which canonical files the assistant should read next

Relevant file:

- [templates/kb-upgrade/query_live_kb.py](../templates/kb-upgrade/query_live_kb.py)

### Confidence Decay

The KB should not treat old claims as permanently current.

Decay can:

- lower confidence when claims are not reconfirmed
- apply different rates by entity type
- surface stale or low-confidence records for review

Relevant files:

- [templates/kb-upgrade/src/decay.py](../templates/kb-upgrade/src/decay.py)
- [templates/kb-upgrade/config/decay-rules.yaml](../templates/kb-upgrade/config/decay-rules.yaml)

### Graph And Hybrid Retrieval

Graph support is useful when your KB contains stable, inspectable relation structure.

Good use cases:

- model lineage
- competitor and partner maps
- supply dependencies
- investor overlap
- talent movement

But graph should be optional. If your canonical KB is not relation-rich enough yet, do not force graph into production just to claim a feature.

Relevant files:

- [templates/kb-upgrade/src/graph_builder.py](../templates/kb-upgrade/src/graph_builder.py)
- [templates/kb-upgrade/src/graph_query.py](../templates/kb-upgrade/src/graph_query.py)
- [templates/kb-upgrade/src/combined_search.py](../templates/kb-upgrade/src/combined_search.py)

## How It Fits The Workflow

```text
Collector -> Sentinel -> Librarian -> canonical KB -> KB runtime -> operator assistant
```

Meaning:

- Collector finds the inputs
- Sentinel turns them into intelligence
- Librarian writes durable memory
- the runtime makes that memory retrievable
- the assistant uses retrieval to answer interactive questions

## What To Publish

Safe to publish:

- templates
- schemas
- query helpers
- example layouts
- documentation

Do not publish:

- generated vector indexes
- embedding caches
- decay state from a live system
- live entity files
- logs, reports, or operator-specific analysis

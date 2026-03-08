# Advanced KB

## Purpose

The advanced KB is the persistence and retrieval layer behind the Collector -> Sentinel -> Librarian workflow.

Its job is to turn dated intelligence artifacts into structured, queryable memory:

- entities that persist over time
- signals that record what changed and when
- relations that connect entities across the market
- indexes that let you retrieve meaning, not just filenames
- decay logic that keeps stale intelligence from looking permanently current

## Core Capabilities

### Schema-Driven Knowledge

The KB is not freeform markdown only. It is governed by a schema in [templates/kb-upgrade/config/schema.yaml](../templates/kb-upgrade/config/schema.yaml).

The schema defines:

- entity types such as `lab`, `model`, `person`, `company`, `investor`, `regulator`, `theme`, and `opportunity`
- required metadata like `confidence`, `status`, `created`, and `last_confirmed`
- structured signal blocks
- relation types
- type-specific blocks for models and people

### Embeddings And Vector Search

The semantic layer uses:

- chunking for entity content
- embeddings from OpenRouter by default
- a local deterministic fallback in strict or offline environments
- FAISS for vector storage
- an embedding cache so repeated rebuilds stay cheap

Relevant files:

- [embedder.py](../templates/kb-upgrade/src/embedder.py)
- [index_manager.py](../templates/kb-upgrade/src/index_manager.py)
- [build_index.py](../templates/kb-upgrade/build_index.py)
- [config.yaml](../templates/kb-upgrade/config/config.yaml)

### Graph Intelligence

The graph layer exports entity relationships into `indexes/relations.json` and supports both explicit and inferred edges.

Examples of graph use:

- model lineage
- competitors and partnerships
- supply dependencies
- investor portfolio overlap
- talent movement between labs
- shared foundations across model families

Relevant files:

- [graph_builder.py](../templates/kb-upgrade/src/graph_builder.py)
- [graph_query.py](../templates/kb-upgrade/src/graph_query.py)

### Hybrid Retrieval

The KB supports both:

- pure semantic search over chunk embeddings
- combined search that merges semantic evidence with graph traversal

That lets the system answer queries like:

- “Which labs are competing with OpenAI?”
- “What models build on the same foundation?”
- “Which companies share investors and infrastructure exposure?”

Relevant files:

- [search.py](../templates/kb-upgrade/src/search.py)
- [combined_search.py](../templates/kb-upgrade/src/combined_search.py)

### Confidence Decay

The KB does not assume truth stays fresh forever.

Confidence decay:

- lowers confidence when an entity has not been reconfirmed
- uses different rates for different entity types
- supports overrides for status and signal types
- highlights stale or below-threshold entities for review

Relevant files:

- [decay.py](../templates/kb-upgrade/src/decay.py)
- [decay-rules.yaml](../templates/kb-upgrade/config/decay-rules.yaml)

## Runtime Layout

The public template includes the KB engine under `templates/kb-upgrade/`.

Key parts:

- `openclaw.py`
  One CLI for process, search, graph, decay, validation, status, reports, and backup flows.
- `src/`
  Implementation modules for extraction, merging, indexing, graphing, search, and reporting.
- `config/`
  Schema, embeddings/index settings, and decay rules.

The live data plane is separate:

- `entities/`
- `themes/`
- `digests/`
- `indexes/`
- `reports/`
- `logs/`

Those runtime outputs are intentionally not published in this export.

## How It Fits The Agent Workflow

### Collector

Collector does not touch embeddings or graph logic directly. Its job is to produce trustworthy source artifacts and freshness metadata.

### Sentinel

Sentinel turns source artifacts into digests and memos that are structured enough for Librarian to ingest cleanly.

### Librarian

Librarian is the writer into the KB. It updates canonical entities, themes, signals, and relations.

### KB Engine

The engine makes Librarian’s output usable:

- semantic retrieval over prior intelligence
- graph traversal for relationship questions
- anomaly and contradiction detection
- decay-driven revalidation

## Operating Loop

Typical loop:

1. Sentinel drops a new digest into the incoming area.
2. Librarian extracts and merges signals into canonical entity files.
3. The index is rebuilt or incrementally refreshed.
4. The graph is rebuilt.
5. Decay and validation are run on schedule.
6. Status, snapshots, and weekly reports summarize the health of the KB.

## Public Sharing Boundary

Safe to publish:

- schema
- code
- templates
- sample folder layouts
- operational documentation

Do not publish:

- embedding caches
- live vector indexes
- logs
- private entity files
- digests and memos containing private analysis
- real delivery targets or credentials

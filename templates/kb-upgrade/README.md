# Enhanced Knowledge Base Template

Sanitized KB engine template for the Collector -> Sentinel -> Librarian workflow.

## What It Does

- Ingests Sentinel digests from `intelligence-kb/digests/incoming/`
- Uses Librarian extraction + merger to update structured entities/themes
- Maintains semantic index (FAISS + embedding cache)
- Maintains relationship graph (NetworkX + JSON export)
- Supports semantic search, graph queries, combined search, decay, validation, reporting, and operations CLI

## Template Layout

- `intelligence-kb/` : data plane (entities, themes, digests, indexes, reports, logs, config)
- `src/` : implementation modules
- `tests/` : regression coverage for indexing, graph, and fallback behavior
- `kb_ops.py` : master operations CLI
- `validate_schema.py` : schema validator
- `daily_run.sh` : daily automation script
- `setup.sh` : bootstrap script

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python kb_ops.py status
python kb_ops.py rebuild --full
python kb_ops.py graph rebuild
python kb_ops.py search "Claude pricing"
```

## Core Commands

```bash
# Process digests
python kb_ops.py process
python kb_ops.py process intelligence-kb/digests/incoming/2026-03-07.md
python kb_ops.py process --quality
python kb_ops.py process --verify

# Search
python kb_ops.py search "inference cost race"
python kb_ops.py search "labs competing with OpenAI" --graph

# Graph
python kb_ops.py graph rebuild
python kb_ops.py graph connections anthropic
python kb_ops.py graph lineage "claude sonnet 4"
python kb_ops.py graph anomalies

# Maintenance
python kb_ops.py validate
python kb_ops.py decay --report
python kb_ops.py decay --apply
python kb_ops.py status

# Reports
python kb_ops.py report weekly
python kb_ops.py report models
python kb_ops.py report themes
```

## Testing

```bash
source .venv/bin/activate
python -m pytest tests -q
```

## Notes

- Requires `OPENROUTER_API_KEY` for live embeddings and LLM extraction.
- Data outputs are written under `intelligence-kb/`.
- Runtime data, reports, logs, and indexes are intentionally excluded from this public export.

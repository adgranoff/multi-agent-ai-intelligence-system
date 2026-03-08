# OpenClaw Enhanced Knowledge Base Template

Sanitized KB engine template for the Collector -> Sentinel -> Librarian workflow.

## What It Does

- Ingests Sentinel digests from `openclaw-kb/digests/incoming/`
- Uses Librarian extraction + merger to update structured entities/themes
- Maintains semantic index (FAISS + embedding cache)
- Maintains relationship graph (NetworkX + JSON export)
- Supports semantic search, graph queries, combined search, decay, validation, reporting, and operations CLI

## Template Layout

- `openclaw-kb/` : data plane (entities, themes, digests, indexes, reports, logs, config)
- `src/` : implementation modules
- `tests/` : regression coverage for indexing, graph, and fallback behavior
- `openclaw.py` : master operations CLI
- `validate_schema.py` : schema validator
- `daily_run.sh` : daily automation script
- `setup.sh` : bootstrap script

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python openclaw.py status
python openclaw.py rebuild --full
python openclaw.py graph rebuild
python openclaw.py search "Claude pricing"
```

## Core Commands

```bash
# Process digests
python openclaw.py process
python openclaw.py process openclaw-kb/digests/incoming/2026-03-07.md
python openclaw.py process --quality
python openclaw.py process --verify

# Search
python openclaw.py search "inference cost race"
python openclaw.py search "labs competing with OpenAI" --graph

# Graph
python openclaw.py graph rebuild
python openclaw.py graph connections anthropic
python openclaw.py graph lineage "claude sonnet 4"
python openclaw.py graph anomalies

# Maintenance
python openclaw.py validate
python openclaw.py decay --report
python openclaw.py decay --apply
python openclaw.py status

# Reports
python openclaw.py report weekly
python openclaw.py report models
python openclaw.py report themes
```

## Testing

```bash
source .venv/bin/activate
python -m pytest tests -q
```

## Notes

- Requires `OPENROUTER_API_KEY` for live embeddings and LLM extraction.
- Data outputs are written under `openclaw-kb/`.
- Runtime data, reports, logs, and indexes are intentionally excluded from this public export.

# Knowledge Base Runtime Template

Sanitized runtime template for the digest-to-KB workflow.

## What It Represents

This template shows how to layer retrieval and maintenance on top of a canonical markdown KB.

Core functions:

- process incoming digests into KB updates
- refresh semantic search state
- apply confidence decay
- optionally build relation and hybrid retrieval layers
- support an operator-facing query helper

## Template Layout

- `src/` : implementation modules
- `tests/` : regression coverage
- `kb_ops.py` : operations CLI
- `query_live_kb.py` : operator-assistant query helper
- `validate_schema.py` : schema validator
- `daily_run.sh` : example maintenance script
- `setup.sh` : bootstrap script

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python kb_ops.py status
python kb_ops.py rebuild --full
python query_live_kb.py "What changed this week?"
```

## Core Commands

```bash
# Digest processing
python kb_ops.py process
python kb_ops.py process project-kb/digests/incoming/2026-03-07.md

# Search
python kb_ops.py search "inference cost race"
python query_live_kb.py "What should the operator read next?"

# Optional graph
python kb_ops.py graph rebuild
python kb_ops.py graph anomalies

# Maintenance
python kb_ops.py validate
python kb_ops.py decay --report
python kb_ops.py decay --apply
python kb_ops.py status
```

## Notes

- Keep the canonical KB separate from generated indexes and logs.
- Keep provider credentials and delivery adapters outside the public template.
- Use graph only when your canonical KB carries stable relation structure.
- The workspace templates include deterministic examples for daily pulse rendering and KB front-page generation.

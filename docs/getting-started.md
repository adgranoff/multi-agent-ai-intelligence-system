# Getting Started

This repository is a workflow template pack, not a complete platform.

Use it if you want:

- a Collector that gathers source artifacts
- a Sentinel that turns them into daily and weekly intelligence
- a Librarian that curates a durable KB
- a KB runtime that adds semantic retrieval and decay
- an operator-facing assistant that can query that KB

## Prerequisites

- Python 3.10+
- a shell environment on macOS or Linux
- your own source-fetching logic
- your own scheduler and delivery layer
- an embedding provider or local embedding model if you want semantic retrieval

## Suggested Project Layout

```text
project-root/
  workspace-collector/
  workspace-sentinel/
  workspace-librarian/
  workspace-modelscout/
  shared/
  knowledge-base/
  skills/
```

Use relative paths inside your own project rather than hard-coding machine-specific paths.

## Fastest Path

1. Copy the templates you need into your own project.
2. Start with Collector, Sentinel, Librarian, and the KB templates.
3. Replace the stub fetchers with your real collectors.
4. Run one end-to-end dry run before wiring a scheduler or delivery adapter.
5. Add the KB runtime after the core pipeline is stable.
6. Add the operator-assistant query path last.

## Example Bootstrap

```bash
mkdir -p project-root
cp -R templates/workspace-collector project-root/
cp -R templates/workspace-sentinel project-root/
cp -R templates/workspace-librarian project-root/
cp -R templates/workspace-modelscout project-root/
cp -R templates/knowledge-base project-root/knowledge-base
cp -R templates/shared project-root/shared-templates
cp -R templates/kb-upgrade project-root/kb-runtime
cp -R skills project-root/
```

Then adapt the copied files to your environment.

## Configure Environment

Start from [examples/.env.example](../examples/.env.example).

Keep these values local:

- provider credentials
- transport endpoints
- scheduler-specific settings
- machine-specific paths

## First Dry Run

Collector:

```bash
python3 workspace-collector/collector_run.py
```

Sentinel latest-pointer publish helper:

```bash
python3 workspace-sentinel/publish_latest_digest.py
python3 workspace-sentinel/render_market_pulse.py
```

Librarian deterministic views:

```bash
python3 workspace-librarian/generate_kb_index.py
python3 workspace-librarian/generate_kb_views.py
python3 workspace-librarian/render_delivery_summary.py
```

KB runtime:

```bash
cd kb-runtime
./setup.sh
python3 query_live_kb.py "What changed this week?"
```

## What You Must Customize

- source fetchers
- scheduler implementation
- delivery transport
- embedding provider or local embedding model
- model choices
- domain-specific KB conventions

## What You Should Not Copy Blindly

- machine-specific paths
- provider defaults
- transport assumptions
- sample schedules without runtime buffer
- graph logic if your KB does not yet contain stable relation structure

## Minimal Success Criteria

You should consider the system minimally working only when:

1. Collector writes dated artifacts plus a valid manifest
2. Sentinel writes a dated digest
3. latest pointers are refreshed
4. Librarian updates canonical KB files and derived views
5. the KB runtime refreshes semantic retrieval state
6. the operator assistant can answer one KB query from the live system

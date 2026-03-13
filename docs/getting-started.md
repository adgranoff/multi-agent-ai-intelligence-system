# Getting Started

This repository is a workflow template pack, not a complete platform.

Treat it as an implementation kit:

- a human engineer can adapt it directly
- a coding agent can use it as a build brief plus template source
- the final production shape should be fitted to your scheduler, delivery channel, storage layout, and risk posture

Use it if you want:

- a Collector that gathers source artifacts
- a Sentinel that turns them into daily and weekly intelligence
- a Librarian that curates a durable KB
- an Editor that performs weekly high-order curation
- a KB runtime that adds semantic retrieval and decay

## Builder Readiness (Codex/Agent Build)

You can use this repo as a starter brief for a coding agent, but you still need engineering work to ship a real system.

Expected remaining work:

1. implement real source collectors (replace stubs)
2. wire a real scheduler/orchestrator with retries and buffers
3. wire a real delivery adapter (chat/email/webhook)
4. add environment-specific auth and secret handling
5. harden runtime, observability, and deployment operations

If those are missing, treat this as a skeleton and architecture reference, not a deployable product.

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
  workspace-editor/
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
6. Add weekly Editor automation once the daily pipeline is reliable.
7. Add your query client integration last.

## Example Bootstrap

```bash
mkdir -p project-root
cp -R templates/workspace-collector project-root/
cp -R templates/workspace-sentinel project-root/
cp -R templates/workspace-librarian project-root/
cp -R templates/workspace-editor project-root/
cp -R templates/knowledge-base project-root/knowledge-base
cp -R templates/shared project-root/shared-templates
cp -R templates/kb-upgrade project-root/kb-runtime
cp -R skills project-root/
```

Then adapt the copied files to your environment.

Good adaptation pattern:

1. keep the workflow ordering
2. rename paths and transports to fit your environment
3. preserve artifact-first and latest-pointer contracts
4. preserve idempotent weekly rerun behavior
5. preserve explicit success/failure contracts per agent

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

Weekly editor refresh wrapper:

```bash
bash workspace-editor/run-weekly-refresh.sh
```

Contract and synthetic harness checks:

```bash
python3 tests/synthetic_e2e.py
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
2. Sentinel writes a dated digest and latest pointers
3. Librarian updates canonical KB files and derived views
4. Editor writes weekly curation state or rerun verification
5. the KB runtime refreshes semantic retrieval state
6. contract validation and synthetic e2e checks pass

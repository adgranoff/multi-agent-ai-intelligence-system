# Getting Started

This repo is a workflow overlay, not a full replacement for upstream OpenClaw.

Use it if you want to build a system with:

- a Collector that gathers source artifacts
- a Sentinel that turns them into daily and weekly intelligence
- a Librarian that curates a durable KB
- an optional advanced KB runtime with embeddings, semantic search, graph queries, and decay

## Prerequisites

- upstream OpenClaw installed separately
- Python 3.10+
- a shell environment on macOS or Linux
- an OpenRouter API key if you want live KB extraction or embeddings
- your own source-fetching logic for AI news, X, and YouTube

## Fastest Path

1. Clone this repo somewhere outside your live `~/.openclaw` if you want to inspect it first.
2. Copy the templates you want into your own OpenClaw home.
3. Start with the Collector, Sentinel, and Librarian templates.
4. Replace the stub fetchers with your real source collectors.
5. Run one end-to-end dry run before wiring cron or delivery.

## Suggested Layout

```text
~/.openclaw/
  workspace-collector/
  workspace-sentinel/
  workspace-librarian/
  workspace-modelscout/
  shared/
  knowledge-base/
  skills/
```

## Copy The Template Layer

Example approach:

```bash
mkdir -p ~/.openclaw
cp -R templates/workspace-collector ~/.openclaw/
cp -R templates/workspace-sentinel ~/.openclaw/
cp -R templates/workspace-librarian ~/.openclaw/
cp -R templates/workspace-modelscout ~/.openclaw/
cp -R templates/knowledge-base ~/.openclaw/knowledge-base
cp -R skills ~/.openclaw/
```

Then copy and adapt:

- `templates/shared/USER.md`
- `templates/shared/BOOTSTRAP.md`

## Configure Environment

Start from [examples/.env.example](../examples/.env.example).

Recommended process:

```bash
cp examples/.env.example .env
```

Then set only the values you actually need.

## Replace The Collector Stub Fetchers

The public repo includes safe placeholder fetchers:

- `templates/workspace-collector/fetch-ainews.sh`
- `templates/workspace-collector/fetch-x-digest.sh`
- `templates/workspace-collector/fetch-youtube-digest.sh`

They are intentionally minimal and do not include your real source list.

Replace them with your own logic while preserving the output contract:

- `collector-ainews-{date}.md`
- `collector-xdigest-{date}.md`
- `collector-youtube-{date}.md`

## First Dry Run

Collector:

```bash
python3 ~/.openclaw/workspace-collector/collector_run.py
```

Sentinel publish helper:

```bash
python3 ~/.openclaw/workspace-sentinel/publish_latest_digest.py
```

Librarian derived views:

```bash
python3 ~/.openclaw/workspace-librarian/generate_kb_views.py
python3 ~/.openclaw/workspace-librarian/render_delivery_summary.py
```

Advanced KB setup:

```bash
cd templates/kb-upgrade
./setup.sh
```

## What You Need To Customize

- source fetchers
- model choices
- delivery mechanism
- KB entity standards for your own domain
- cron schedules

## What You Should Not Copy Blindly

- local paths without checking your environment
- transport assumptions like Telegram
- model choices without validating your own cost and provider constraints
- KB schema if your domain is not AI intelligence

## If You Are Using Codex Or Claude Code

This repo is strong input for an agent-assisted build because it includes:

- architecture docs
- runtime doctrine
- workflow skills
- code templates
- KB engine code

Good prompts to start with:

- "Port this OpenClaw workflow into a plain Python + cron setup"
- "Replace the Collector stub fetchers with RSS and YouTube API integrations"
- "Adapt this KB schema for cybersecurity intelligence"
- "Build a local-first version without Telegram delivery"

## First Meaningful Success

You should consider the system minimally working only when:

1. Collector writes all expected artifacts
2. Sentinel writes a dated digest
3. `digest-latest.md` is updated
4. Librarian refreshes canonical KB plus derived views
5. your final delivery summary is bounded and readable


---
name: openclaw-cron-runbook
description: Inspect, rerun, edit, and debug OpenClaw cron jobs and schedule ownership. Use when a user asks why a scheduled job failed or missed, wants to list next runs, manually rerun or edit a cron job, or needs to trace a job from name to id to runs to agent session.
---

# OpenClaw Cron Runbook

Use this skill for OpenClaw scheduler work, not for generic OS cron.

## Workflow

1. Inspect the schedule with `openclaw cron list`.
2. Resolve the exact job id from the name before any `run` or `edit`.
3. Inspect recent runs with `openclaw cron runs <job-id>`.
4. If needed, inspect the run log and agent session log.
5. Prefer fixing wrappers and renderers before changing prompt text for deterministic jobs.

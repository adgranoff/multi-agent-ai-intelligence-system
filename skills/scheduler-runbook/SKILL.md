---
name: scheduler-runbook
description: Inspect, rerun, edit, and debug scheduled jobs and schedule ownership. Use when a user asks why a scheduled job failed or missed, wants to list next runs, manually rerun or edit a scheduled job, or needs to trace a job from name to run logs and artifacts.
---

# Scheduler Runbook

## Workflow

1. Inspect the scheduler or cron source of truth first.
2. Resolve the exact job identifier from the job name before any rerun or edit.
3. Inspect recent runs and their logs.
4. If needed, inspect the job wrapper, artifact paths, and session logs.
5. Prefer fixing wrappers and renderers before changing prompt text for deterministic jobs.

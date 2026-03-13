---
name: wrapper-hardening
description: Design or tighten deterministic wrapper and renderer patterns for notification-facing jobs. Use when adding or fixing a scheduled job that should run one script, validate artifacts, and print exactly one delivery-safe payload with no extra commentary.
---

# Wrapper Hardening

## Contract

1. Run the real script.
2. Validate the output artifact exists and is non-empty.
3. Render a plain-text summary.
4. Print that summary and nothing else.

#!/usr/bin/env bash
set -euo pipefail

DATE="${DATE:-$(date +%Y-%m-%d)}"

cat <<EOF
# AI News

This is a stub fetcher.

Replace this script with your own AI news collection logic.

Expected output shape:
- one markdown artifact per run
- stable header
- list items or structured sections that downstream stages can parse

Example item:
- **Example AI vendor released a new model** — replace with your real source collection

Generated: ${DATE}
EOF


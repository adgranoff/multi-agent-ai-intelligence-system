#!/usr/bin/env bash
set -euo pipefail

DATE="${DATE:-$(date +%Y-%m-%d)}"

cat <<EOF
# X/Twitter AI Digest

This is a stub fetcher.

Replace this script with your own tracked-account and post-collection logic.

Expected output shape:
- markdown digest with one entry per relevant post
- stable header
- safe to classify as \`quiet\` when there are no new posts

- [Example source post] Replace with your own collected posts

Generated: ${DATE}
EOF


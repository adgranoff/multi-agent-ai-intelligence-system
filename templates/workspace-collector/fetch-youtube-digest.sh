#!/usr/bin/env bash
set -euo pipefail

DATE="${DATE:-$(date +%Y-%m-%d)}"
WORKSPACE="${WORKSPACE:-$(pwd)}"
OUTPUT_PATH="${WORKSPACE}/youtube-digest.md"

cat > "$OUTPUT_PATH" <<EOF
# YouTube Digest

This is a stub fetcher.

Replace this script with your own channel, transcript, or video-note collection logic.

### Example Video
- Title: Example AI Weekly Roundup
- Why it matters: Replace with your own extracted takeaways

Generated: ${DATE}
EOF

echo "Stub YouTube digest written to ${OUTPUT_PATH}"


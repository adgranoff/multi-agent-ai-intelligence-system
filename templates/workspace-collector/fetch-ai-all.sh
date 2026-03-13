#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-$(pwd)/workspace-collector}"
SHARED="${SHARED:-$(pwd)/shared}"
DATE="${DATE:-$(date +%Y-%m-%d)}"
LOCK_FILE="${LOCK_FILE:-$WORKSPACE/.fetch-ai-all.lock}"
LOCK_STALE_AFTER_SEC="${LOCK_STALE_AFTER_SEC:-7200}"

mkdir -p "$SHARED"

if [[ -f "$LOCK_FILE" ]]; then
  now_epoch="$(date +%s)"
  lock_mtime="$(stat -f %m "$LOCK_FILE" 2>/dev/null || echo 0)"
  if [[ "$lock_mtime" =~ ^[0-9]+$ ]] && (( now_epoch - lock_mtime > LOCK_STALE_AFTER_SEC )); then
    rm -f "$LOCK_FILE"
  else
    echo "[Collector] Existing run lock found. Skipping duplicate run."
    exit 0
  fi
fi
touch "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

run_or_placeholder() {
  local script_path="$1"
  local output="$2"
  local label="$3"

  if bash "$script_path" > "$output" 2>/dev/null; then
    return 0
  fi

  {
    echo "# ${label} fetch failed"
    echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "$output"
  return 1
}

AINEWS_OUT="$SHARED/collector-ainews-$DATE.md"
XDIGEST_OUT="$SHARED/collector-xdigest-$DATE.md"
YOUTUBE_OUT="$SHARED/collector-youtube-$DATE.md"

run_or_placeholder "$WORKSPACE/fetch-ainews.sh" "$AINEWS_OUT" "AI News" || true
run_or_placeholder "$WORKSPACE/fetch-x-digest.sh" "$XDIGEST_OUT" "X Digest" || true
run_or_placeholder "$WORKSPACE/fetch-youtube-digest.sh" "$YOUTUBE_OUT" "YouTube Digest" || true

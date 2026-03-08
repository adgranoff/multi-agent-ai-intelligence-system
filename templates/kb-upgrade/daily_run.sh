#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
KB_PATH="${KB_PATH:-./openclaw-kb}"
OPENCLAW_BIN="${OPENCLAW_BIN:-openclaw}"
SEND_REPORTS_TELEGRAM="${SEND_REPORTS_TELEGRAM:-0}"
TELEGRAM_CHANNEL="${TELEGRAM_CHANNEL:-telegram}"
TELEGRAM_TARGET="${TELEGRAM_TARGET:-CHANGE_ME}"

send_report_to_telegram() {
  local report_path="$1"
  local report_label="$2"

  if [ "$SEND_REPORTS_TELEGRAM" != "1" ]; then
    return 0
  fi

  if [ ! -f "$report_path" ]; then
    echo "report-send: missing file: $report_path" >&2
    return 1
  fi

  "$OPENCLAW_BIN" message send \
    --channel "$TELEGRAM_CHANNEL" \
    --target "$TELEGRAM_TARGET" \
    --message "OpenClaw report ready: $report_label ($(date +%Y-%m-%d)). Sending file now." \
    >/dev/null

  "$OPENCLAW_BIN" message send \
    --channel "$TELEGRAM_CHANNEL" \
    --target "$TELEGRAM_TARGET" \
    --message "Attached: $(basename "$report_path")" \
    --media "$report_path" \
    >/dev/null
}

$PYTHON_BIN openclaw.py --kb-path "$KB_PATH" process --fast
$PYTHON_BIN openclaw.py --kb-path "$KB_PATH" graph rebuild
$PYTHON_BIN openclaw.py --kb-path "$KB_PATH" graph anomalies >> "$KB_PATH/logs/$(date +%Y-%m-%d).log"

if [ "${FORCE_WEEKLY:-0}" = "1" ] || [ "$(date +%u)" = "7" ]; then
  $PYTHON_BIN openclaw.py --kb-path "$KB_PATH" decay --apply
  weekly_out="$($PYTHON_BIN openclaw.py --kb-path "$KB_PATH" report weekly)"
  echo "$weekly_out"
  weekly_path="$(printf '%s\n' "$weekly_out" | sed -n 's/^Report saved: //p' | tail -n1)"
  send_report_to_telegram "$weekly_path" "weekly memo"

  models_out="$($PYTHON_BIN openclaw.py --kb-path "$KB_PATH" report models)"
  echo "$models_out"
  models_path="$(printf '%s\n' "$models_out" | sed -n 's/^Report saved: //p' | tail -n1)"
  send_report_to_telegram "$models_path" "model snapshot"

  themes_out="$($PYTHON_BIN openclaw.py --kb-path "$KB_PATH" report themes)"
  echo "$themes_out"
  themes_path="$(printf '%s\n' "$themes_out" | sed -n 's/^Report saved: //p' | tail -n1)"
  send_report_to_telegram "$themes_path" "theme snapshot"

  $PYTHON_BIN openclaw.py --kb-path "$KB_PATH" backup
fi

find "$KB_PATH/digests/processed" -name "*.md" -mtime +30 -exec mv {} "$KB_PATH/digests/archive/" \;
$PYTHON_BIN openclaw.py --kb-path "$KB_PATH" status >> "$KB_PATH/logs/$(date +%Y-%m-%d).log"

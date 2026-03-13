#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
KB_PATH="${KB_PATH:-./intelligence-kb}"
SEND_REPORTS_HOOK="${SEND_REPORTS_HOOK:-0}"
REPORT_DELIVERY_HOOK="${REPORT_DELIVERY_HOOK:-}"

send_report() {
  local report_path="$1"
  local report_label="$2"

  if [ "$SEND_REPORTS_HOOK" != "1" ]; then
    return 0
  fi

  if [ ! -f "$report_path" ]; then
    echo "report-send: missing file: $report_path" >&2
    return 1
  fi

  if [ -z "$REPORT_DELIVERY_HOOK" ] || [ ! -x "$REPORT_DELIVERY_HOOK" ]; then
    echo "report-send: REPORT_DELIVERY_HOOK is not set to an executable file" >&2
    return 1
  fi

  "$REPORT_DELIVERY_HOOK" "$report_path" "$report_label"
}

$PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" process --fast
$PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" graph rebuild
$PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" graph anomalies >> "$KB_PATH/logs/$(date +%Y-%m-%d).log"

if [ "${FORCE_WEEKLY:-0}" = "1" ] || [ "$(date +%u)" = "7" ]; then
  $PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" decay --apply
  weekly_out="$($PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" report weekly)"
  echo "$weekly_out"
  weekly_path="$(printf '%s\n' "$weekly_out" | sed -n 's/^Report saved: //p' | tail -n1)"
  send_report "$weekly_path" "weekly memo"

  models_out="$($PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" report models)"
  echo "$models_out"
  models_path="$(printf '%s\n' "$models_out" | sed -n 's/^Report saved: //p' | tail -n1)"
  send_report "$models_path" "model snapshot"

  themes_out="$($PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" report themes)"
  echo "$themes_out"
  themes_path="$(printf '%s\n' "$themes_out" | sed -n 's/^Report saved: //p' | tail -n1)"
  send_report "$themes_path" "theme snapshot"

  $PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" backup
fi

find "$KB_PATH/digests/processed" -name "*.md" -mtime +30 -exec mv {} "$KB_PATH/digests/archive/" \;
$PYTHON_BIN kb_ops.py --kb-path "$KB_PATH" status >> "$KB_PATH/logs/$(date +%Y-%m-%d).log"

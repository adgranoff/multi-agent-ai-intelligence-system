#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
else
  echo "Python 3 is required"
  exit 1
fi

$PYTHON_BIN - <<'PY'
import sys
v = sys.version_info
if (v.major, v.minor) < (3, 10):
    print(f"Warning: Python {v.major}.{v.minor} detected; 3.10+ recommended")
else:
    print(f"Python OK: {v.major}.{v.minor}")
PY

$PYTHON_BIN -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdir -p openclaw-kb/{entities/{labs,models,people,companies,investors,regulators},themes,opportunities,digests/{incoming,processed,archive},indexes/vector-store,reports/{weekly,snapshots},config,logs}

echo "If needed, add OPENROUTER_API_KEY to .env"
python validate_schema.py --kb-path ./openclaw-kb || true

echo "Setup complete. Sentinel should deposit digests to openclaw-kb/digests/incoming/."
echo "Run './.venv/bin/python openclaw.py --kb-path ./openclaw-kb process' to start."

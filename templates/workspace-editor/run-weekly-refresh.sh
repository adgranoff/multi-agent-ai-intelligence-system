#!/usr/bin/env bash
set -euo pipefail

python3 ../workspace-librarian/generate_kb_index.py
python3 ../workspace-librarian/generate_kb_views.py
bash ../kb-upgrade/daily_run.sh

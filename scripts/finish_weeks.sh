#!/usr/bin/env bash
# Live measurements the recording cannot stand in for.
# Run from anywhere. Uses the repo venv if it exists.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python labs/week01/starter/00_preflight.py
python labs/week04/starter/01_run.py --model qwen2.5:7b
python labs/week04/starter/01_run.py --model qwen3:4b-instruct
python labs/week04/starter/01_run.py --no-tools --model qwen2.5:7b
python labs/week04/starter/02_defend.py
python labs/week05/starter/01_compare.py --runs 3
python -m project.verify
python scripts/fill_live_addendum.py

echo
echo "Live files:"
echo "  artifacts/week04_agent_live_qwen2.5_7b.json"
echo "  artifacts/week04_agent_live_qwen3_4b-instruct.json"
echo "  artifacts/week04_agent_notools.json"
echo "  artifacts/week04_defenses.json"
echo "  artifacts/week05_architectures.json"
echo "DECISIONS.md addenda updated. Read them, then commit and push."

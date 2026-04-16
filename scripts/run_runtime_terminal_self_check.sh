#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/mnt/user-data/workspace/Ai_Videos_Replication"
VENV_ACTIVATE="/mnt/user-data/workspace/.venv/bin/activate"

cd "$REPO_ROOT"
source "$VENV_ACTIVATE"
python scripts/runtime_terminal_self_check.py "$@"

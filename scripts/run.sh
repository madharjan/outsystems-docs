#!/usr/bin/env bash
# Run OutSystems-Docs MCP using the project-local .venv (created on first run)
# Usage: ./scripts/run.sh --sync
#        ./scripts/run.sh --agent-interactive
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[*] .venv not found, creating it..."
    uv sync
fi

exec "$VENV_PYTHON" src/osdocs_mcp.py "$@"

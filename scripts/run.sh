#!/usr/bin/env bash
# Run OutSystems-Docs MCP using the project-local .venv (created on first run)
# Usage: ./scripts/run.sh --sync
#        ./scripts/run.sh --agent-interactive
# Note: --directml is Windows-only (DirectML) — use scripts\run.cmd --directml there instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[*] .venv not found, creating it..."
    uv sync
fi

ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--directml" ]]; then
        echo "ERROR: --directml swaps to onnxruntime-directml, which is Windows-only. Use scripts\\run.cmd --directml instead." >&2
        exit 1
    else
        ARGS+=("$arg")
    fi
done

exec "$VENV_PYTHON" src/osdocs_mcp.py "${ARGS[@]}"

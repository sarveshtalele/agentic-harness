#!/usr/bin/env bash
# ==============================================================================
# azure_convert_and_deploy.sh - Wrapper for Azure Kudu conversion and deployment
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Resolve Python 3 executable
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo "ERROR: Python 3 is required but neither python3 nor python was found." >&2
    exit 1
fi

"$PY_BIN" "$SCRIPT_DIR/azure_convert_and_deploy.py" "$@"

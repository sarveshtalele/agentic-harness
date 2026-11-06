#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================================="
echo " Agentic QE Platform - Azure Kudu Packaging Automation"
echo "=================================================================="

# Ensure Python 3 is available
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python 3 is required but neither python3 nor python was found."
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"
echo "Executing package_azure_kudu.py..."

"$PYTHON_CMD" "$SCRIPT_DIR/package_azure_kudu.py" "$@"

echo "Packaging script completed successfully."

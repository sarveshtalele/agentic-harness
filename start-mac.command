#!/bin/sh
# Double-click to start Agentic QE Platform & Claude Code Desktop Harness on macOS
cd "$(dirname "$0")" || exit 1
chmod +x run.sh bin/harness harness
exec ./run.sh

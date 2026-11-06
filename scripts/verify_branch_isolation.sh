#!/usr/bin/env bash
# ==============================================================================
# verify_branch_isolation.sh - Local and CI Branch Isolation Enforcer
# ==============================================================================
# Strict Rule:
# The branch 'feature/azure-kudu-deployment' is an isolated standalone branch
# intended solely for direct Azure Kudu packaging, testing, and deployment.
# It CANNOT be merged into 'main' or any other branch, nor can other branches
# be merged into it without an explicit repository administrator override.
# ==============================================================================
set -euo pipefail

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
TARGET_BRANCH="${1:-main}"

echo "=================================================================="
echo " Strict Branch Isolation Policy Verifier"
echo " Current Branch: $CURRENT_BRANCH"
echo " Target / Merge: $TARGET_BRANCH"
echo "=================================================================="

LOCKED_BRANCH="feature/azure-kudu-deployment"

if [ "$CURRENT_BRANCH" = "$LOCKED_BRANCH" ] && [ "$TARGET_BRANCH" != "$LOCKED_BRANCH" ]; then
    echo "ERROR: Branch '$LOCKED_BRANCH' is strictly protected!" >&2
    echo "POLICY VIOLATION: You cannot merge '$LOCKED_BRANCH' into '$TARGET_BRANCH'." >&2
    echo "Rationale: This branch contains specialized Azure App Service / Kudu conversion tooling" >&2
    echo "and standalone deployment artifacts that must remain isolated from trunk." >&2
    exit 1
fi

if [ "$TARGET_BRANCH" = "$LOCKED_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LOCKED_BRANCH" ]; then
    echo "ERROR: Branch '$LOCKED_BRANCH' is frozen against external merges!" >&2
    echo "POLICY VIOLATION: You cannot merge '$CURRENT_BRANCH' into '$LOCKED_BRANCH'." >&2
    exit 1
fi

echo "Branch isolation check passed."
exit 0

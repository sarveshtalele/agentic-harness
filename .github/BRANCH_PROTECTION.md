# 🔒 Strict Branch Protection & Isolation Policy

## 1. Executive Summary & Policy Mandate
The branch **`feature/azure-kudu-deployment`** is an **immutable, isolated deployment branch** dedicated exclusively to Azure App Service / Kudu packaging, standalone artifact generation, and cloud provisioning.

> [!CAUTION]
> **STRICT MERGE RESTRICTION:**
> Per Enterprise Architectural Governance, **`feature/azure-kudu-deployment` CANNOT be merged into `main` or any other branch.**
> Likewise, no other branch may be merged into `feature/azure-kudu-deployment` without direct approval from the Infrastructure Architecture Board.

---

## 2. Rationale for Strict Isolation

1. **Standalone Production Packaging:**
   This branch contains specialized Azure App Service orchestration scripts (`scripts/azure_convert_and_deploy.py`), 1-time resource provisioning automation (`deploy/azure/setup_azure_infrastructure.sh`), and dedicated CI/CD workflows (`.github/workflows/azure-deploy.yml`) designed to convert the application directly from `clone -> zip -> deploy to kudu`.
2. **Preventing Configuration Drift on Trunk:**
   The `main` branch is maintained as the clean multi-platform core (supporting local Docker, macOS, Windows, and Linux local environments). Introducing cloud-specific deployment hooks directly into `main` creates lockfile contention and shadows monorepo tooling.
3. **Reproducible Cloud Release Artifacts:**
   By isolating `feature/azure-kudu-deployment`, cloud releases can be tagged, built, and deployed deterministically without risks of regressions introduced from ongoing development on `main`.

---

## 3. Automated Enforcement Mechanisms

### A. GitHub Actions Pull Request Merge Lock Guard
The workflow `.github/workflows/branch-lock-check.yml` automatically executes on all pull requests. If a pull request attempts to:
* Merge `feature/azure-kudu-deployment` into `main`, `master`, `develop`, or any release branch -> **Job immediately fails and blocks merging.**
* Merge any other branch into `feature/azure-kudu-deployment` -> **Job immediately fails.**

### B. Pre-Merge Verification Script
A shell verification script is provided at `scripts/verify_branch_isolation.sh`. It can be wired into local git hooks or CI runners:
```bash
./scripts/verify_branch_isolation.sh <target-branch>
```
If executed on `feature/azure-kudu-deployment` targeting `main`, the script exits with code `1` and prints:
```
ERROR: Branch 'feature/azure-kudu-deployment' is strictly protected!
POLICY VIOLATION: You cannot merge 'feature/azure-kudu-deployment' into 'main'.
```

### C. Recommended GitHub Repository Settings
Repository Administrators should configure the following rules under **Settings > Branches > Branch protection rules** on GitHub:
1. Target: `main`
   - Check: `Require a pull request before merging`
   - Check: `Require status checks to pass before merging`
   - Select check: `Enforce Strict Branch Isolation Rule`
2. Target: `feature/azure-kudu-deployment`
   - Check: `Lock branch` (Read-only for pull requests)
   - Restrict pushes to authorized deployer accounts or CI/CD Service Principals.

---

## 4. Operational Usage: How to Work With This Branch

Developers and Cloud Operations engineers should use this branch directly:

```bash
# 1. Check out the isolated branch
git clone -b feature/azure-kudu-deployment https://github.com/sarveshtalele/agentic-harness.git
cd agentic-harness

# 2. Package standalone artifacts
./scripts/azure_convert_and_deploy.sh --convert --build-frontend

# 3. Deploy directly to Azure Kudu
python3 scripts/azure_convert_and_deploy.py --deploy \
  --resource-group rg-agentic-harness-eastus2 \
  --backend-app agentic-backend \
  --frontend-app agentic-frontend
```

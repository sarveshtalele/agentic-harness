# ☁️ Azure Kudu Standalone Deployment Branch
### Active Git Branch: `feature/azure-kudu-deployment`

> [!CAUTION]
> **STRICT BRANCH MERGE LOCK POLICY:**
> Per Enterprise Architectural Governance, **this branch CANNOT be merged into `main` or any other branch.**
> It is an immutable, isolated deployment branch containing standalone packaging tools, Next.js 16 standalone build configurations, and Azure App Service Kudu automation.
> See [`.github/BRANCH_PROTECTION.md`](.github/BRANCH_PROTECTION.md) for full compliance details.

---

## 📌 Executive Summary

The `feature/azure-kudu-deployment` branch provides an automated, reproducible bridge between the Agentic QE Platform codebase and Microsoft Azure App Service. It enables developers and cloud operators to perform a zero-friction **Clone -> Zip -> Deploy** pipeline into Azure Kudu Linux App Services.

### Key Capabilities Included in This Branch
* **Zero-Friction Conversion & Packaging Tooling:** `scripts/azure_convert_and_deploy.py` and `scripts/azure_convert_and_deploy.sh` turn the monorepo into production-ready Kudu zip archives (`dist/azure_backend.zip` and `dist/azure_frontend.zip`).
* **Next.js 16 Standalone Pre-Compiler (`--build-frontend`):** Compiles the Next.js frontend with pruned standalone production dependencies and static assets. Eliminates Oryx build out-of-memory errors on cost-effective B1 (1.75 GB RAM) App Service plans.
* **1-Time Infrastructure Automation:** 1-click provisioning scripts (`deploy/azure/setup_azure_infrastructure.sh` for Linux/macOS and `deploy/azure/setup_azure_infrastructure.ps1` for Windows PowerShell).
* **Automated CI/CD Workflow:** `.github/workflows/azure-deploy.yml` with dual Kudu ZipDeploy triggers and post-deployment smoke verification.
* **Persistent Multi-Agent Database Storage:** Pre-configured SQLite WAL mode mounted at persistent App Service storage `/home/atlas/data`, eliminating database locks during concurrent agent runs.

---

## 🚀 Rapid 3-Step Runbook: Clone -> Zip -> Deploy

### Step 1: 1-Time Azure Setup (Run Once)
Log in to Azure and run the provisioning script to create the Resource Group, shared Linux App Service Plan, and WebApps:

```bash
# Authenticate with Azure CLI
az login

# On Linux or macOS:
chmod +x deploy/azure/setup_azure_infrastructure.sh
./deploy/azure/setup_azure_infrastructure.sh

# On Windows PowerShell:
.\deploy\azure\setup_azure_infrastructure.ps1
```

*Default Provisioned Resources:*
* **Resource Group:** `rg-agentic-harness-eastus2` (East US 2)
* **App Service Plan:** `asp-agentic-harness-b1` (Linux Basic B1 ~$12.41/month)
* **Backend WebApp:** `agentic-backend` (Python 3.12, Port 8000, Persistent Storage `/home/atlas/data`)
* **Frontend WebApp:** `agentic-frontend` (Node 20 LTS, Port 3000, Proxy bound to backend)

---

### Step 2: Clone & Package (Standalone Conversion)
Clone this isolated branch and execute the packaging tool:

```bash
# Clone directly from this feature branch
git clone -b feature/azure-kudu-deployment https://github.com/sarveshtalele/agentic-harness.git
cd agentic-harness

# Run conversion & package standalone bundles
./scripts/azure_convert_and_deploy.sh --convert --build-frontend
```

*Output Artifacts in `dist/`:*
* **`dist/azure_backend.zip`** (FastAPI Core, MAF 2.0 multi-agent engine, Prompts, Skills, Templates, Evals, `startup.sh`, `startup.py`, `.deployment`, `web.config`)
* **`dist/azure_frontend.zip`** (Next.js 16 standalone server bundle, `.next/static/`, `public/`, `startup.sh`, `startup.js`, `.deployment`)

---

### Step 3: Deploy to Azure Kudu

Choose whichever deployment method fits your workflow:

#### Option A: Direct CLI Deployment via Conversion Script
```bash
python3 scripts/azure_convert_and_deploy.py --deploy \
  --resource-group rg-agentic-harness-eastus2 \
  --backend-app agentic-backend \
  --frontend-app agentic-frontend
```

#### Option B: Drag-and-Drop via Kudu Web UI
1. Open Backend Kudu ZipDeploy endpoint:
   `https://agentic-backend.scm.azurewebsites.net/ZipDeploy`
2. Drag and drop `dist/azure_backend.zip` directly onto the browser file manager.
3. Open Frontend Kudu ZipDeploy endpoint:
   `https://agentic-frontend.scm.azurewebsites.net/ZipDeploy`
4. Drag and drop `dist/azure_frontend.zip`.
5. Access your live deployment at `https://agentic-frontend.azurewebsites.net`.

#### Option C: Automated GitHub Actions CI/CD
1. Navigate to your GitHub repository **Settings > Secrets and variables > Actions**.
2. Add secrets:
   - `AZURE_BACKEND_PUBLISH_PROFILE`: Downloaded from Backend WebApp in Azure Portal.
   - `AZURE_FRONTEND_PUBLISH_PROFILE`: Downloaded from Frontend WebApp in Azure Portal.
3. Trigger `.github/workflows/azure-deploy.yml` via manual `workflow_dispatch` or push.

---

## 📂 Branch File Manifest & Specialized Tooling

| File Path | Description |
|---|---|
| [`scripts/azure_convert_and_deploy.py`](scripts/azure_convert_and_deploy.py) | Master conversion, packaging, preflight verification, and Kudu deployment script. |
| [`scripts/azure_convert_and_deploy.sh`](scripts/azure_convert_and_deploy.sh) | Executable bash runner for the conversion script. |
| [`scripts/verify_branch_isolation.sh`](scripts/verify_branch_isolation.sh) | Git hook and CLI guard enforcing branch merge isolation. |
| [`deploy/azure/setup_azure_infrastructure.sh`](deploy/azure/setup_azure_infrastructure.sh) | 1-time Azure infrastructure automation script (Bash). |
| [`deploy/azure/setup_azure_infrastructure.ps1`](deploy/azure/setup_azure_infrastructure.ps1) | 1-time Azure infrastructure automation script (PowerShell). |
| [`deploy/azure/backend_startup.py`](deploy/azure/backend_startup.py) | Dynamic PYTHONPATH and database directory initializer for Azure App Service. |
| [`deploy/azure/frontend_startup.js`](deploy/azure/frontend_startup.js) | Standalone Next.js server launcher and static asset resolver. |
| [`deploy/azure/frontend_startup.sh`](deploy/azure/frontend_startup.sh) | Azure App Service startup script for Node 20 runtime. |
| [`.github/workflows/azure-deploy.yml`](.github/workflows/azure-deploy.yml) | GitHub Actions CI/CD pipeline for building and deploying to Azure App Service. |
| [`.github/workflows/branch-lock-check.yml`](.github/workflows/branch-lock-check.yml) | GitHub Actions pull request gate preventing merge into `main` or other branches. |
| [`.github/BRANCH_PROTECTION.md`](.github/BRANCH_PROTECTION.md) | Policy documentation explaining the strict branch protection rule. |
| [`tests/test_azure_kudu_packaging.py`](tests/test_azure_kudu_packaging.py) | Unit test suite verifying packaging logic, CRC checks, and setup generators. |
| [`docs/AZURE_DEPLOYMENT_GUIDE.md`](docs/AZURE_DEPLOYMENT_GUIDE.md) | Azure deployment with costs, portal steps and a UI tour. |

---

## 🔒 Strict Merge Prohibition Notice

```
                ┌──────────────────────────────────────┐
                │   feature/azure-kudu-deployment      │
                │   (Isolated Deployment Branch)       │
                └──────────────────┬───────────────────┘
                                   │
                                   ▼
                            [ CANNOT MERGE ]
                                   │
                ┌──────────────────┴───────────────────┐
                ▼                                      ▼
     main / master / develop               other feature branches
     (BLOCKED BY POLICY & CI)               (BLOCKED BY POLICY & CI)
```

1. **Do not create pull requests from `feature/azure-kudu-deployment` into `main`.** The CI workflow `.github/workflows/branch-lock-check.yml` will fail the check and block merging.
2. **Do not merge other feature branches into `feature/azure-kudu-deployment`.**
3. If enhancements are made to core backend or frontend code, merge them on `main` first, and then rebase or re-apply updates onto this deployment branch.

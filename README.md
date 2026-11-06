# Agentic QE Platform & Autonomous Multi-Agent Harness

[![CI](https://github.com/sarveshtalele/agentic-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/sarveshtalele/agentic-harness/actions/workflows/ci.yml)
[![MAF 2.0](https://img.shields.io/badge/MAF-2.0%20Native-blue.svg)](https://github.com/microsoft/agent-framework)
[![ChromaDB](https://img.shields.io/badge/RAG-ChromaDB%20Persistent-emerald.svg)](https://www.trychroma.com/)
[![NVIDIA Skill Specter](https://img.shields.io/badge/Security-NVIDIA%20Skill%20Specter%20A%2B-purple.svg)](docs/SECURITY_GOVERNANCE_AND_AUDIT.md)

An enterprise-grade, cryptographically governed **Autonomous Quality Engineering (AQE) Platform & Multi-Agent Harness** built natively on the **Microsoft Agent Framework (MAF 2.0)** in Python with a **Next.js 16 (React 19)** web command center, **ChromaDB persistent RAG vector store**, **real NVIDIA Skill Specter AST security scanning**, and a first-class **Headless Terminal CLI (`bin/harness`)**.

The platform orchestrates the complete software quality lifecycle across **8 Human-in-the-Loop Quality Gates (G0–G7)** using **12 Specialized Agent Personas** and **59+ Dynamic Domain Skills**.

---

## 🏛️ Core Architectural Pillars

1. **Strict Microsoft Agent Framework (MAF 2.0) Architecture:**
   * Built on official MAF primitives: `Agent`, `ContextProvider`, `FunctionInvocationContext`, `SlidingWindowStrategy`, and `function_middleware`.
   * Workflows built with `WorkflowBuilder`, `WorkflowContext`, and `FileCheckpointStorage` for crash-resilient state recovery.
   * Agent Skills loaded via MAF's official `FileSkillsSource` and `SkillsSourceContext`.
   * Real-time AG-UI SSE protocol streaming powered by `agent_framework.ag_ui.AgentFrameworkAgent`.

2. **ChromaDB Persistent RAG Vector Store & 4-Tier Grounding:**
   * Automatic semantic chunking along Markdown heading hierarchies (`#`, `##`, `###`) and paragraphs.
   * Persistent per-project collections stored in `data/chromadb` (`proj_{project_id}`) with cosine similarity search.
   * Unified 4-tier grounding combining ChromaDB semantic vectors, SQLite governed document versions, static AST codebase discovery endpoints, and active quality gate metrics.

3. **Real NVIDIA Skill Specter AST Security Audit Engine:**
   * Python AST Node Visitor (`PythonASTSecurityVisitor`) performing static code inspection.
   * **CWE-94 (Dynamic RCE):** Prohibits `eval()`, `exec()`, `compile()`, and `__import__()`.
   * **CWE-78 (Shell Injection):** Prohibits `subprocess.*(shell=True)`, `os.system()`, and `os.popen()`.
   * **OWASP LLM01 (Prompt Injection & Demarcation):** Audits `SKILL.md` frontmatter and flags injection delimiters.
   * **CWE-798 & CWE-22:** Detects hardcoded API keys/secrets and blocks path traversal (`../`).
   * **Risk Scoring Semantics:**
     * `0 – 15` Risk Score: **CLEAN / VERIFIED / PRODUCTION READY (Grade A+)** — Execution Allowed.
     * `40 – 100` Risk Score: **CRITICAL / NOT READY FOR USE (Grade FAIL)** — Hard-Blocked.

4. **Autonomous Skill Creator & Evaluator Studio (`/skills/studio`):**
   * Synthesizes production-ready Agent Skills from BRDs, user stories, and specs.
   * Scaffolds triple-artifact bundles: `SKILL.md` (metadata & prompt), `scripts/run.py` (sandboxed runner), and `evals/evals.json` (benchmark evals).
   * Generates deterministic test case matrices and binds them directly to project QE workflows.

5. **Dual Interface Command Center:**
   * **Web Command Center (`/harness`):** 3-column desktop layout with streaming thoughts, todos tracking, quick goal cards, and live tool inspectors.
   * **Headless Terminal CLI (`bin/harness`):** Interactive REPL and scripted execution for CI/CD pipelines.

---

## 💻 Complete Setup Guide: Windows

### Prerequisites
* **Python:** Version 3.10, 3.11, or 3.12 (Ensure `Add Python to PATH` was selected during installation).
* **Node.js:** Version 20+ LTS (Includes `npm`).
* **Git:** Installed and available in PATH.
* **C++ Build Tools (Recommended for Windows):** Visual Studio C++ Build Tools or prebuilt wheel support.

### Step 1: Clone Repository
Open PowerShell or Command Prompt:
```cmd
git clone https://github.com/sarveshtalele/agentic-harness.git
cd agentic-harness
```

### Step 2: Set Up Python Virtual Environment
```cmd
python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip setuptools
pip install -r requirements.txt
```

### Step 3: Install Frontend Dependencies & Build
```cmd
cd src\frontend
npm install
npm run build
cd ..\..
```

### Step 4: Configure Environment Variables
Create a `.env` file in the project root:
```ini
# Administrator Authentication (Required)
ATLAS_ADMIN_USERNAME=admin
ATLAS_ADMIN_PASSWORD=YourSecurePassword123!

# Security & Encryption
ATLAS_SECRET_KEY=generate-a-random-32-character-secret-key-string

# Model Endpoint (OpenAI / Azure OpenAI / Local Ollama or vLLM)
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4o-mini

# Database & Ports
ATLAS_HOST=127.0.0.1
ATLAS_PORT=8000
ATLAS_UI_PORT=3000
ATLAS_SQLITE_JOURNAL=wal
```

### Step 5: Start the Application

#### Option A: Quick Launcher (One-Click)
Double-click `start-windows.bat` in the project root.

#### Option B: Terminal Dev Orchestrator
```cmd
call venv\Scripts\activate
python scripts\dev.py up
```

#### Option C: Dual Terminal Launch
* **Terminal 1 (Backend):**
  ```cmd
  call venv\Scripts\activate
  set PYTHONPATH=src
  python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
  ```
* **Terminal 2 (Frontend):**
  ```cmd
  cd src\frontend
  npm run dev
  ```

Access the Web Command Center at **`http://localhost:3000`** and sign in using your configured credentials.

---

## 🍎 Complete Setup Guide: macOS & Linux

### Prerequisites
* **Homebrew (macOS):** `brew install python@3.12 node git`
* **Python:** 3.10, 3.11, or 3.12 (`python3 --version`).
* **Node.js:** 20+ LTS (`node -v`).
* **Git:** `git --version`.

### Step 1: Clone Repository
```bash
git clone https://github.com/sarveshtalele/agentic-harness.git
cd agentic-harness
```

### Step 2: Set Up Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip setuptools
pip install -r requirements.txt
```

### Step 3: Install Frontend Dependencies & Build
```bash
npm --prefix src/frontend install
npm --prefix src/frontend run build
```

### Step 4: Configure Environment Variables
Create `.env` in the project root:
```bash
cat << 'EOF' > .env
ATLAS_ADMIN_USERNAME=admin
ATLAS_ADMIN_PASSWORD=YourSecurePassword123!
ATLAS_SECRET_KEY=$(openssl rand -hex 24)
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4o-mini
ATLAS_HOST=127.0.0.1
ATLAS_PORT=8000
ATLAS_UI_PORT=3000
ATLAS_SQLITE_JOURNAL=wal
EOF
```

### Step 5: Start the Application

#### Option A: Quick Launcher
Make executable and launch:
```bash
chmod +x start-mac.command bin/harness
./start-mac.command
```

#### Option B: Terminal Dev Orchestrator
```bash
source venv/bin/activate
python3 scripts/dev.py up
```

#### Option C: Dual Terminal Launch
* **Terminal 1 (FastAPI Backend):**
  ```bash
  source venv/bin/activate
  PYTHONPATH=src python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
  ```
* **Terminal 2 (Next.js Frontend):**
  ```bash
  npm --prefix src/frontend run dev
  ```

Open your browser to **`http://localhost:3000`** and sign in.

---

## ⚡ How to Use the Key Features

### 1. Autonomous QE Harness (`/harness`)
Navigate to `/harness` to access the full multi-agent workspace:
* **Quick Goal Cards:** One-click activation for Create BRD, Create PRD, Run Testing Lifecycle, Feature Building, Bug Fixing & PR, Security Audit, Repo Scan, and Create Agent Skill.
* **Direct Document Ingestion:** Drag and drop any `.md`, `.docx`, `.pdf`, or `.txt` file into the Harness input area:
  * Automatically creates a versioned document in SQLite with a project Governance ID (`MCPM-DOC-xxx`).
  * Automatically segments text into semantic chunks and indexes into ChromaDB.
* **Live Skill Execution:** Run any skill via slash command:
  ```text
  /test_skill settlement-idempotency-verifier
  /run_skill payment-reconciliation-engine
  ```
  Or click **"Test Skill Live"** in the Inspector drawer to run the sandboxed runner (`scripts/run.py`), benchmark `evals/evals.json`, and run the real NVIDIA Skill Specter AST audit.
* **Slash Commands:**
  * `/help` — View available commands and skills.
  * `/mode plan` or `/mode execute` — Switch between Plan Mode (discovery) and Execute Mode (modifications).
  * `/todos` — View and manage the active Magentic-One task ledger.
  * `/gates` — View Quality Gate approval statuses.

### 2. Skill Creator & Evaluator Studio (`/skills/studio`)
* **Grounded Synthesis:** Select an existing project specification or upload a BRD to ground your new skill.
* **Architecture & Metadata:** Define skill display name, SDLC category, capability description, and step-by-step task checklist.
* **Automated Scaffolding:** Click **"Scaffold Agent Skill & Test Cases"** to generate:
  1. `SKILL.md`: Frontmatter, trigger rules, and workflow checklist.
  2. `scripts/run.py`: Sandboxed executable runner.
  3. `evals/evals.json`: Benchmark test evaluations.
* **Attach to QE Workflow:** Click **"Attach Test Cases to Project"** to bind generated deterministic test scenarios directly into the project's quality pipeline.

### 3. Headless Terminal CLI (`bin/harness`)
Run the autonomous harness directly from your terminal:
```bash
# Interactive REPL mode
./bin/harness

# List indexed SQLite projects
./bin/harness /projects

# Load a specific project context
./bin/harness /project prj_agentic_qe

# List all 59+ registered agent skills
./bin/harness /skills

# Run security audit on workspace
./bin/harness /security-audit

# Free-form agent prompt
./bin/harness "Perform boundary value analysis on payment settlement logic"
```

---

## 🧪 Comprehensive Verification & Testing

Run all test suites locally:

```bash
# 1. New Specter AST, ChromaDB RAG, and Live Skills test suite
pytest tests/test_harness_specter_rag_and_skills.py -v

# 2. Platform Core Test Suite (107 tests)
pytest tests/test_core.py -v

# 3. Universal Harness & HITL Suite (37 tests)
npm run test:unit

# 4. Playwright End-to-End Browser Suite (7 tests)
npx playwright test

# 5. Offline Platform CI Suite (577 tests)
pytest tests -q -m "not e2e and not live and not smoke"

# 6. Frontend Linting & Typecheck
cd src/frontend && npx eslint . && npm run build
```

---

## ☁️ Azure App Service & Kudu Production Deployment

Deploy to Azure App Service (Linux B1 plan, ~$12.41/mo) with our 1-click conversion and deployment tooling:

### 1. One-Time Azure Infrastructure Setup
```bash
# Run 1-time setup for Resource Group, B1 App Service Plan, WebApps, and persistent DB storage
chmod +x deploy/azure/setup_azure_infrastructure.sh
./deploy/azure/setup_azure_infrastructure.sh
```
*(On Windows, run `.\deploy\azure\setup_azure_infrastructure.ps1`)*

### 2. Clone -> Zip -> Deploy to Azure Kudu
```bash
# 1. Package repository into ready-to-deploy Azure Kudu ZIP bundles
./scripts/azure_convert_and_deploy.sh --convert --build-frontend

# 2. Deploy directly to Azure App Service via Azure CLI or Kudu REST API
./scripts/azure_convert_and_deploy.sh --deploy \
  --resource-group rg-agentic-harness-eastus2 \
  --backend-app agentic-harness-backend-prod \
  --frontend-app agentic-harness-frontend-prod
```
Or upload `dist/azure_backend.zip` and `dist/azure_frontend.zip` directly via Kudu Web UI at `https://<app-name>.scm.azurewebsites.net/ZipDeploy`.

For full step-by-step instructions, environment configuration, and GitHub Actions CI/CD setup, see [`docs/AZURE_ENTERPRISE_DEPLOYMENT_GUIDE.md`](docs/AZURE_ENTERPRISE_DEPLOYMENT_GUIDE.md).

---

## 📚 Canonical Documentation Library

In accordance with the project's **1 Single Document for Each Architectural Purpose** policy, refer to the authoritative specifications:

| Canonical Document | Scope & Focus |
|---|---|
| [`docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md`](docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md) | Platform master architecture, Next.js/FastAPI, MAF 2.0 orchestration, ChromaDB RAG vector store, direct document ingestion, AST discovery, and 8 Quality Gates. |
| [`docs/SECURITY_GOVERNANCE_AND_AUDIT.md`](docs/SECURITY_GOVERNANCE_AND_AUDIT.md) | Security specification: Real NVIDIA Skill Specter AST scanner (CWE-94, CWE-78, OWASP LLM01), Cloudflare Zero-Trust perimeter, and HMAC cryptographic audit ledger. |
| [`docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`](docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md) | Agent skills technical guide: MAF `FileSkillsSource`, progressive disclosure, live skill testing runner, Skill Creator Studio, and the Evaluator skill. |
| [`docs/AZURE_ENTERPRISE_DEPLOYMENT_GUIDE.md`](docs/AZURE_ENTERPRISE_DEPLOYMENT_GUIDE.md) | Enterprise Azure guide: App Service Linux B1, persistent Azure Files storage mount (`/data`), role-based MCP server governance, and step-by-step Azure CLI runbook. |
| [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) | Comprehensive code structure mapping every directory, module, and cross-import. |

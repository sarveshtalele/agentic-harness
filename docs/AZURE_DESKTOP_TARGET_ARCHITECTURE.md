# Target Architecture: Azure Cloud + Desktop App

Status: **design, not built.** Written 2026-11-10.

Today the zip packages are verified end to end through the real `startup.py` and `startup.js` (`docs/evidence/runs/2026-11-10-1747-*/NOTES.md`). The app still stores everything in SQLite and on local disk. This document is the plan to run it fully on Azure for many users, with a desktop app for users and admins.

## Goals

- **Users and admins** sign in with their company account and use the same app on the web or as a desktop app.
- **Every document** (BRD, PRD, plans, test cases, Gherkin, generated skills) is stored in Azure with immutable versions: SHA-256, author, prompt reference, and a ledger entry. History cannot be edited.
- **Admins** control which plugins, skills, MCP servers, and models each user or role may use, and see the audit trail.
- **Repository code** runs in isolated jobs, never on the web server, so untrusted users can be admitted.

## Azure components

| Concern | Today | Target on Azure | Why |
|---|---|---|---|
| Sign-in | Local admin from env + local accounts | Microsoft Entra ID (OIDC). App roles `admin`, `qe_lead`, `developer`, `ba`, `viewer` map to the existing roles in `core/auth.py` | One identity for web and desktop; admins manage people in Entra |
| API | FastAPI on App Service B1 (zip + Kudu) | Same FastAPI on Azure Container Apps (or App Service P1v3), more than one replica | Workflows move to a queue, so the API can scale out |
| UI | Next.js on App Service (zip + Kudu) | Same Next.js standalone on Container Apps or Static Web Apps + API | Unchanged code |
| Database | SQLite on the `/home` share (DELETE journal) | **Azure Database for PostgreSQL Flexible Server** | Many writers, point-in-time restore, zone-redundant HA |
| Document versions | `document_versions` rows in SQLite | Same table in PostgreSQL: `(document_id, version)` primary key, `sha256`, `author`, `prompt_ref`, `created_at`. Content over a size limit goes to Blob | Versions are inserts only; a database role without UPDATE or DELETE on the table enforces immutability |
| Files and artifacts | `data/` on disk | **Azure Blob Storage** with blob versioning and soft delete; a time-based immutability policy on the evidence and ledger exports container | Uploaded sources, exports, JUnit, screenshots, skill packages |
| Ledger | Hash-chained table | Same chain in PostgreSQL + daily export to the immutable container | Tamper evidence that survives a database restore |
| Secrets | Fernet with a key file | **Azure Key Vault** (managed identity); app settings hold Key Vault references | No secret in app settings or code |
| Model | LiteLLM proxy | Azure OpenAI or Foundry deployment, called with a managed identity | Data stays in the tenant; per-model quotas |
| Sandbox / repository code | Git worktrees on the API host | **Container Apps Jobs**: one job per run, no secrets, egress limited, results to Blob | Required before untrusted users (CLAUDE.md security rule) |
| Workflows | In-process with `FileCheckpointStorage` | Azure Service Bus queue + worker container; MAF checkpoints in Blob | Survives restarts; API replicas stay stateless |
| Harness state | `data/harness/<project>/` files | Blob container per project (MAF `AgentFileStore` over Blob) or PostgreSQL tables for todos and history | Shared by all replicas and the desktop app |
| MCP | Not connected | Remote MCP servers over `MCPStreamableHTTPTool`; stdio MCP only in the desktop profile | No process spawning on the cloud API |
| Observability | `agent_calls`, `tool_calls`, app log | Same tables + OpenTelemetry to Application Insights | Traces link UI rows to spans |
| Edge | App Service URLs | Azure Front Door with WAF; the API is reachable only from Front Door | Matches the "backend behind an access restriction" rule |

## Desktop app (Electron)

This follows the DeepSeek Harness pattern: Electron main plus a private desktop host running the same web app.

- **Cloud mode (default for users).** The window loads the Azure UI; sign-in goes through Entra (system browser, PKCE). Nothing runs locally. Admin screens appear for the `admin` role.
- **Local mode (developers and admins).** Electron starts the bundled backend (PyInstaller) and the Next.js standalone build on loopback ports, with the `desktop` profile: stdio MCP allowed, local repositories, and a local SQLite store. **Sync:** documents are saved to Azure through the API, so versions stay in one place. Local mode does not keep its own document versions.
- **Build and release.** One CI matrix builds signed installers for Windows (MSIX or NSIS), macOS (signed and notarized DMG), and Linux (AppImage). Updates come from Azure Blob through electron-updater.

## Migration steps (each one is a plan phase with tests)

1. **Repository layer.** Hide SQLite behind `db.py` functions; run the offline suite against PostgreSQL in CI through a service container.
2. **Entra ID sign-in** next to local sign-in, behind a setting.
3. **Blob storage** for uploads, exports, evidence and harness state.
4. **Key Vault** references; managed identity for the model and storage.
5. **Container Apps Jobs** for sandbox runs, with Service Bus workflows.
6. **Electron desktop shell** in cloud mode first, then local mode.
7. **Cutover.** A one-time export from SQLite to PostgreSQL that copies document versions with their SHA-256 values and re-verifies the ledger chain.

## Open decisions for the owner

| # | Decision |
|---|---|
| A | Azure Container Apps (scale-out) or App Service (simpler, the current scripts) for the API? |
| B | Entra ID tenant and app registration owner |
| C | Model: Azure OpenAI or Foundry deployment, or keep the LiteLLM proxy |
| D | Desktop local mode: needed for all users, or only for developers and admins? |
| E | Region and data residency |

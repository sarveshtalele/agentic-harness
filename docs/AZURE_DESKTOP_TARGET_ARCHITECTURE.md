# Azure and desktop: end-to-end guide

This guide takes Agentic QE Platform from a laptop to a team web app on Azure (East US 2), plus a desktop app for each person, using the Azure portal. GitHub never connects to Azure: you build zips and installers, and you upload them.

Every step is marked:
- **Works now:** the code supports it today; verify as you go.
- **After H6:** the target design. The database and file layers for it (`docs/MASTER_PLAN.md`, phase H6) are not built yet. Do these steps only when H6 is done.

The quick path is in `docs/AZURE_POC_PORTAL_GUIDE.md`. This guide is the full picture.

## 1. Architecture

```text
 People ── browser ──▶ UI web app (Next.js) ──▶ API web app (FastAPI + MAF) ──▶ model endpoint
                                 │                       │
                                 │                       ├─▶ SQLite on /home (now) │ PostgreSQL Flexible Server (after H6)
                                 │                       ├─▶ files on /home (now)  │ Blob Storage containers (after H6)
                                 │                       ├─▶ Key Vault (secrets, via app settings references)
                                 │                       └─▶ Application Insights (optional, OpenTelemetry)
                                 └─▶ login page reads Blob "downloads" (desktop installers)

 Each person (optional) ── desktop app (Electron) ──▶ its own local backend + UI on 127.0.0.1, own data, full harness
```

| Concern | Now | Target | Why |
|---|---|---|---|
| Compute | One Linux App Service plan B1, two web apps | Same; P1v3 or Container Apps when many people run workflows at once | Cheapest that runs both apps |
| Database | SQLite on `/home` (`ATLAS_SQLITE_JOURNAL=DELETE`) | PostgreSQL Flexible Server, Burstable B1ms | More than one writer; point-in-time restore |
| Files | `/home/atlas/data` | Blob Storage: `documents`, `uploads`, `evidence`, `skills`, `workspaces` | Survives a plan change; versioning and soft delete |
| Installers | Blob container `downloads` | Same | The login page links them |
| Secrets | App settings, optionally Key Vault references | Key Vault references with managed identity | No secret stored in plain text in app settings |
| Sign-in | Built-in accounts; the admin comes from settings | Same; Entra ID later | Works without a tenant app registration |
| Sandboxes | On the API host, at most `ATLAS_MAX_SANDBOXES` (5) at once | Container Apps Jobs, one per run | Required before untrusted users |
| Observability | In-app Trace Explorer (`/traces`) and logs | Plus Application Insights through OTLP | Cross-service traces |
| Harness | On the web with 5 sandbox slots; stdio MCP, npx and plugin installs off | Same | Shared server safety |
| Desktop | Electron app with a local backend, full harness | Signed installers | Personal workspace |

## 2. Before you start (your machine)

**Works now.**

1. **Read the settings:** `deploy/environments/azure.appsettings.example` lists every setting, without values.
2. **Build both zips:**
   ```bash
   python scripts/package_azure_kudu.py
   ```
   This writes `dist/azure_backend.zip` and `dist/azure_frontend.zip`.
3. **Prove them locally** in the web profile:
   ```bash
   ATLAS_ADMIN_USERNAME=<name> ATLAS_ADMIN_PASSWORD=<12+ chars> python scripts/dev.py azure-local --check
   ```
   On Windows PowerShell, set the two variables with `$env:ATLAS_ADMIN_USERNAME="<name>"` and `$env:ATLAS_ADMIN_PASSWORD="<12+ chars>"` first.

   The check must print `API health: 200; UI /login: 200`.
4. **Make two random values,** one for `ATLAS_SECRET_KEY` and one for the admin password. Run this command twice:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

## 3. Resource group and plan

**Works now.**

1. Search **Resource groups**, then **Create**. Name it `rg-agentic-qe`, choose region **East US 2**, then **Review + create** and **Create**.
2. Search **App Service plans**, then **Create**:
   - **Resource group:** `rg-agentic-qe`.
   - **Name:** `plan-agentic-qe`.
   - **Operating System:** Linux.
   - **Region:** East US 2.
   - **Pricing plan:** **Basic B1**.

   Then **Review + create**, **Create**.

## 4. Key Vault for secrets

**Works now.** This step is optional for the proof of concept and recommended for anything shared.

1. **Create the vault.** Search **Key vaults**, then **Create**:
   - **Resource group:** `rg-agentic-qe`.
   - **Name:** `kv-agentic-qe-<unique>`.
   - **Region:** East US 2.
   - **Pricing tier:** Standard.
   - On the **Access configuration** tab, choose **Azure role-based access control**.

   Then **Create**.
2. **Give yourself access.** Open the vault, then **Access control (IAM)**, **Add role assignment**: role **Key Vault Secrets Officer**, member your own account.
3. **Add the secrets.** Under **Objects, Secrets**, select **Generate/Import** and add each one:
   - `atlas-admin-password`;
   - `atlas-secret-key`;
   - (after H6) `atlas-database-url`.
4. **Grant the app access later.** After step 5 creates the API app's identity, return here: **Access control (IAM)**, **Add role assignment**, role **Key Vault Secrets User**, member the **managed identity** of the API web app.

## 5. API web app

**Works now.**

1. **Create the app.** Search **App Services**, then **Create**, **Web App**:
   - **Name:** `aqe-api-<unique>`.
   - **Publish:** Code.
   - **Runtime stack:** Python 3.12.
   - **Operating System:** Linux.
   - **Region:** East US 2.
   - **Plan:** `plan-agentic-qe`.

   Then **Review + create**, **Create**.
2. **Turn on its identity.** Open the app, then **Settings, Identity**. Under **System assigned**, set **Status** to **On** and **Save**. Then finish step 4.4.
3. **Configuration, General settings:**
   - **Startup Command:** `python /home/site/wwwroot/startup.py`;
   - **Always on:** On;
   - **HTTPS Only:** On.

   Then **Save**.
4. **Environment variables, App settings.** For each setting below, select **+ Add**, enter it, then **Apply**:

   | Name | Value |
   |---|---|
   | `ATLAS_PROFILE` | `web` |
   | `ATLAS_DATA_DIR` | `/home/atlas/data` |
   | `ATLAS_SQLITE_JOURNAL` | `DELETE` |
   | `ATLAS_ADMIN_USERNAME` | your admin name |
   | `ATLAS_ADMIN_PASSWORD` | `@Microsoft.KeyVault(VaultName=kv-agentic-qe-<unique>;SecretName=atlas-admin-password)` or the value itself (12+ characters, different from the username) |
   | `ATLAS_SECRET_KEY` | `@Microsoft.KeyVault(VaultName=kv-agentic-qe-<unique>;SecretName=atlas-secret-key)` or the value |
   | `ATLAS_ADMIN_EMAIL` | the admin's email (optional) |
   | `ATLAS_ALLOWED_HOSTS` | `aqe-api-<unique>.azurewebsites.net` |
   | `ATLAS_ALLOWED_ORIGINS` | `https://aqe-ui-<unique>.azurewebsites.net` |
   | `ATLAS_MAX_SANDBOXES` | `5` |
   | `ATLAS_INSTALL_EVALS` | `1` to install RAGAS on first start (optional) |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
   | `WEBSITES_PORT` | `8000` |

   **Check the Key Vault references.** A Key Vault reference shows a green tick in the **Source** column once the identity can read it. A red cross means step 4.4 is missing.
5. **Deploy the zip.** Open `https://aqe-api-<unique>.scm.azurewebsites.net/ZipDeployUI`, drag `dist/azure_backend.zip` onto it, wait for it to finish, then select **Restart** on the app.
6. **Verify.**
   - **Monitoring, Log stream** shows "Environment built", then "Starting API on port 8000". The first start takes several minutes; longer with RAGAS.
   - Then `https://aqe-api-<unique>.azurewebsites.net/api/health` returns `"status": "ok"`.
7. **Check the settings** without seeing values. Open **Development Tools, SSH**, then **Go**, and run:
   ```bash
   python /home/site/wwwroot/scripts/env_check.py --env azure
   ```
   It must print `azure: OK`.

## 6. UI web app

**Works now.**

1. **Create the app.** **Create**, **Web App**:
   - **Name:** `aqe-ui-<unique>`.
   - **Runtime:** Node 20 LTS.
   - **Linux**, **East US 2**.
   - **Plan:** the same `plan-agentic-qe`.
2. **Configuration, General settings:** **Startup Command** `node /home/site/wwwroot/startup.js`, **Always on** On, **HTTPS Only** On.
3. **App settings:**

   | Name | Value |
   |---|---|
   | `ATLAS_BACKEND_URL` | `https://aqe-api-<unique>.azurewebsites.net` |
   | `ATLAS_DOWNLOADS_URL` | the `downloads` container URL from step 8 (optional) |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
   | `WEBSITES_PORT` | `3000` |

4. **Deploy and verify.** Deploy `dist/azure_frontend.zip` through `https://aqe-ui-<unique>.scm.azurewebsites.net/ZipDeployUI`, then **Restart**. **Log stream** ends with "Starting UI on port 3000".

## 7. Let only the UI reach the API

**Works now.**

1. Open the **UI** app, then **Settings, Properties**. Copy every **Outbound IP address** and **Additional Outbound IP address**.
2. Open the **API** app, then **Settings, Networking**, **Public network access**, **Access restriction**:
   - set **Unmatched rule action** to **Deny**;
   - add one **Allow** rule per UI address;
   - on the **Advanced tool site** tab, allow only your own IP.

## 8. Storage account

- **Works now:** the `downloads` container.
- **After H6:** the other containers.

1. **Create the account.** Search **Storage accounts**, then **Create**:
   - **Name:** `stagenticqe<unique>`.
   - **Region:** East US 2.
   - **Performance:** Standard.
   - **Redundancy:** LRS.
   - On the **Data protection** tab, turn on **Enable versioning for blobs** and **Enable soft delete for blobs** (7 days).

   Then **Create**.
2. **The `downloads` container** (works now, for the desktop installers on the login page):
   - **Settings, Configuration:** set **Allow Blob anonymous access** to **Enabled**, then **Save**.
   - **Containers**, then **+ Container**: name `downloads`, anonymous access level **Blob**. Never choose "Container".
   - Uploading installers is in `docs/DESKTOP_RELEASE_GUIDE.md`.
3. **The other containers** (after H6): create `documents`, `uploads`, `evidence`, `skills` and `workspaces`, all **Private**.
4. **App access** (after H6): in **Access control (IAM)**, **Add role assignment**, give the role **Storage Blob Data Contributor** to the API app's managed identity. Then set the API app setting `ATLAS_STORAGE_URL=https://stagenticqe<unique>.blob.core.windows.net`. The app uses its identity, so there is no storage key anywhere.

## 9. PostgreSQL Flexible Server

**After H6.** Until then the app uses SQLite on `/home`.

1. **Create the server.** Search **Azure Database for PostgreSQL flexible servers**, then **Create**:
   - **Resource group:** `rg-agentic-qe`.
   - **Server name:** `pg-agentic-qe-<unique>`.
   - **Region:** East US 2.
   - **PostgreSQL version:** 16.
   - **Workload type:** Development.
   - **Compute + storage:** **Burstable, B1ms**, 32 GiB, backups 7 days.
   - **Authentication:** PostgreSQL authentication, with an admin user and a long password.
2. **Networking tab:**
   - **Public access**;
   - add a firewall rule for each API app outbound IP (on the **API** app's **Settings, Properties** page).

   Do not use "Allow public access from any Azure service".
3. **Create the database.** After creation, open **Settings, Databases**, then **+ Add**, and name it `agentic_qe`.
4. **Connection string.** Save `postgresql://<admin>:<password>@pg-agentic-qe-<unique>.postgres.database.azure.com:5432/agentic_qe?sslmode=require` as the Key Vault secret `atlas-database-url`. Then set the API app setting:
   ```
   ATLAS_DATABASE_URL=@Microsoft.KeyVault(VaultName=kv-agentic-qe-<unique>;SecretName=atlas-database-url)
   ```
5. **Move existing data.** The H6 cutover tool copies an existing SQLite store, keeping document versions with their SHA-256 values, and re-verifies the ledger chain.

## 10. Observability

- **Works now:** the in-app trace explorer, logs and the optional OTLP export.

1. **In the app.**
   - Admins see every trace at `/traces` and download logs on **Settings**: `app-DAY.jsonl` holds requests; `errors-DAY.jsonl` holds errors with stack traces.
   - Members see only their own runs.
2. **Application Insights** (optional):
   - search **Application Insights**, then **Create**, in East US 2;
   - set `OTEL_EXPORTER_OTLP_ENDPOINT` (your collector or Azure Monitor OTLP endpoint) and `OTEL_SERVICE_NAME=agentic-qe-api` on the API app.

## 11. First sign-in, people and permissions

**Works now.**

1. **Sign in.** Open `https://aqe-ui-<unique>.azurewebsites.net` and sign in as the admin. If the admin password is weak, a red banner says so.
2. **Settings:**
   - enter the model endpoint, model name and key, then **Test connection**;
   - tick the models people may use;
   - under **Plugins**, grant plugins per role if needed.
3. **Users, Add user:** username, temporary password, email and role (`qe_lead`, `ba`, `developer` or `viewer`).
4. **Each project, Members:** add the people who may see it. Approvals show the approver's name, role and email.
5. **Settings, Gate roles:** choose who may sign gates G0 to G5. Agents never sign.
6. **MCP:** add remote (HTTP) MCP servers, connect them, and grant tools per role. stdio servers run only in the desktop app.

## 12. Using the app: a tour of the UI

**Works now.** The same pages run locally, on Azure and in the desktop app. Screenshots are from real runs in `docs/evidence/`. Pages without a screenshot are not captured yet.

| Page | Who | What you do there | Screenshot |
|---|---|---|---|
| `/login` | everyone | Sign in. The **Desktop app** section lists installers when `ATLAS_DOWNLOADS_URL` is set | [login](evidence/22a-login.png) |
| `/projects` | members | Create a project, then attach a repository: a zip upload or a GitHub URL | [list](evidence/05-projects-list.png), [zip](evidence/03-repository-zip.png), [GitHub](evidence/04-repository-github.png) |
| Project, **Harness** | members | Chat with the project harness. Type `/` for commands. Status lines appear while it works. Risky tools stop for **Approve** or **Reject**. **Tasks** shows the todo list; **Skills** shows the loaded skills | [harness](evidence/screens/harness.png), [slash menu](evidence/evidence_harness_fixed_slash_palette.png), [tasks](evidence/evidence_harness_tasks_completed.png) |
| Project, **BA** | BA, QE lead | Requirements documents (BRDs) and Gherkin, then sign gate G1. Every save is a new version | [BA](evidence/screens/project_ba.png), [Gherkin](evidence/08-gherkin-editor.png), [history](evidence/09-document-history.png) |
| Project, **Bugs** and **Feature** | developers | Bug scan findings; generated changes land on a separate branch as a diff | [scan](evidence/10-bug-scan.png), [diff](evidence/11-feature-diff.png) |
| Project, **QE** | QE lead | The QE lifecycle with gates G0 to G5, each signed by a named person. The QE Cycle UI is on hold until the harness runs the whole plugin | [QE](evidence/screens/project_qe.png), [gate 5](evidence/14-qe-gate5.png) |
| Project, **Approvals** and **Governance** | approvers | Pending approvals, with the approver's name, role and email; the hash-chained ledger | [approvals](evidence/06b-approvals-page.png), [governance](evidence/19-governance.png) |
| `/skills/studio` | admin, QE lead | Skill Creator Studio: source, kind (instructions or scripts), plan, approve, generate, test (with **Repair from test failures**), evaluate, publish. Hidden inside projects | [request](evidence/us-51-1-source-kind-request.png), [plan](evidence/us-51-2-plan-draft.png), [published](evidence/us-51-4-published.png), [evaluation](evidence/us-53-1-evaluation.png) |
| `/skills` | everyone | Published skills and their versions; zip download and upload | [skills](evidence/screens/skills_list.png) |
| `/agents` | everyone | 15 governed agents. Each score tile shows `n` and the judge, or the reason it is blank | [agents](evidence/screens/agents.png) |
| `/mcp` | admin | Add an MCP server, **Connect**, then grant each listed tool per role | [empty](evidence/screens/us-55-mcp-empty.png), [connected](evidence/screens/us-55-mcp-connected.png), [granted](evidence/screens/us-55-mcp-granted.png) |
| `/traces` | admin: all; member: own | Trace explorer: the run list, a span tree and a waterfall | not captured yet |
| `/observability`, `/usage` | admin | Runs, errors and token budgets per person | [observability](evidence/21d-observability-all.png) |
| `/settings` | admin | Model, plugins, gate roles, application log download | [settings](evidence/06-settings.png) |
| `/users`, `/account` | admin; each person | Add people with role and email; change your own password and email | [users](evidence/22b-users.png) |
| `/capabilities` | everyone | Capability registry: every tool, agent, skill, command and workflow, with links. **Being built** (`docs/MASTER_PLAN.md`, Phase R) | not built yet |

## 13. Desktop app for each person

**Works now in developer mode. Installers come from CI.** Follow `docs/DESKTOP_RELEASE_GUIDE.md`:
1. GitHub Actions builds the MSI and DMG.
2. You check their SHA-256 values.
3. You upload them and `latest.json` to `downloads`.
4. You set `ATLAS_DOWNLOADS_URL` on the UI app.

The login page then offers the downloads. The desktop app runs everything locally, including stdio MCP, npx and plugin installs.

## 14. Updates, backup, cost, teardown

- **Update.**
  1. Change and test locally (`python scripts/dev.py test`).
  2. Build the zips and run `azure-local --check`.
  3. Deploy both zips through `ZipDeployUI`, then restart both apps.
- **Backup (now).** In Kudu **Debug console**, download `/home/atlas/data/atlas.sqlite3` while no workflow runs. Also check each app's **Backups** page for what your tier offers.
- **Backup (after H6).** PostgreSQL point-in-time restore (7 days), and Blob versioning with soft delete.
- **Cost.** One B1 plan; storage pennies; Key Vault per operation; PostgreSQL B1ms only after H6. Check the Azure pricing calculator for East US 2.
- **Teardown.** Delete the resource group `rg-agentic-qe`. That removes everything in it.

## 15. Open decisions

| # | Decision | State |
|---|---|---|
| A | App Service or Container Apps | App Service B1 for now (owner, 2026-11-11) |
| B | Entra ID sign-in | Later; built-in accounts now |
| C | Model provider | The existing endpoint, set on Settings |
| D | Desktop local mode for everyone | Yes; the harness runs on the web too, with 5 sandbox slots |
| E | Region | **East US 2** (owner, 2026-11-11) |

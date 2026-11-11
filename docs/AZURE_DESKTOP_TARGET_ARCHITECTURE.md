# Azure and desktop: the standard deployment guide (East US 2)

This guide is the one standard for deploying Agentic QE Platform to Azure. It takes the platform from a laptop to a team web app on **PostgreSQL, Blob Storage and Key Vault** in **East US 2**, plus a desktop app for each person, using the Azure portal. GitHub never connects to Azure: you build zips and installers, and you upload them.

**Status of each part:**
- **Works now:** verified locally on 2026-11-11.
  - **PostgreSQL:** the whole test suite runs against a real PostgreSQL.
  - **Key Vault at startup.**
  - **Zip deployment.**
  - **The `downloads` container.**
- **Not yet run on Azure itself:** the steps are written for the portal as it is today. Check each "Verify" line as you go.
- **After G6:** application files in Blob containers. Until the storage layer (`docs/MASTER_PLAN.md`, Part 3, G6) is built, documents and evidence stay on the App Service `/home` share.

## 1. Architecture

```text
 People ── browser ──▶ UI web app (Next.js) ──▶ API web app (FastAPI + MAF) ──▶ model endpoint
                                 │                       │
                                 │                       ├─▶ Azure Database for PostgreSQL Flexible Server (B1ms)
                                 │                       ├─▶ Key Vault: admin password, secret key, database URL (read at startup)
                                 │                       ├─▶ /home share: workspaces and files (Blob containers after G6)
                                 │                       └─▶ Application Insights (optional, OpenTelemetry)
                                 └─▶ login page reads the Blob "downloads" container (desktop installers)

 Each person (optional) ── desktop app ──▶ its own backend, UI and local PostgreSQL on 127.0.0.1
```

| Part | Choice | Why |
|---|---|---|
| Compute | One Linux App Service plan **B1**, two web apps (API and UI) | Cheapest plan that runs both |
| Database | **PostgreSQL Flexible Server, Burstable B1ms**, 32 GiB, version 16 or 17 | The only database the app supports (SQLite was removed). Point-in-time restore, many writers |
| Secrets | **Key Vault Standard**, read by the app with its managed identity (`ATLAS_KEY_VAULT_URL`) | No secret in app settings |
| Files | **Storage account, Standard LRS, Hot**: the `downloads` container now; `documents`, `uploads`, `evidence`, `skills` after G6 | Installers for the login page; later the app's files |
| Sign-in | Built-in accounts; the first admin's password comes from Key Vault | Works without an Entra app registration |
| Harness | Web profile: every feature, with at most 5 sandbox jobs at once (`ATLAS_MAX_SANDBOXES`); stdio MCP, npx and plugin installs are desktop only | Shared-server safety |

## 2. Monthly cost (East US 2)

Prices are pay-as-you-go in US dollars. They were read on **2026-11-11** from the Azure Retail Prices API (`prices.azure.com`), for 730 hours a month. Check the [pricing calculator](https://azure.microsoft.com/pricing/calculator/) before you create anything; prices change.

| Resource | Meter | Price | About per month |
|---|---|---|---|
| App Service plan B1, Linux (both web apps share it) | B1 | $0.017 per hour | **$12.41** |
| PostgreSQL Flexible Server, Burstable B1ms | B1MS compute | $0.017 per hour | **$12.41** |
| PostgreSQL storage, 32 GiB | Storage Data Stored | $0.115 per GB a month | **$3.68** |
| PostgreSQL backups, 7 days | Backup Storage LRS | backup storage up to the provisioned size is included; above it, $0.095 per GB a month | usually **$0** |
| Blob Storage, Hot LRS (installers, about 1 GB) | Hot LRS Data Stored | $0.0184 per GB a month; writes $0.05 per 10,000; reads $0.004 per 10,000 | **under $0.10** |
| Key Vault Standard | Operations | $0.03 per 10,000 (the app reads 3 or 4 secrets per start) | **under $0.01** |
| **Total** | | | **about $28.50** |

Optional items:
- Application Insights is billed per GB ingested.
- Outbound data above the free allowance is billed per GB.

To pay nothing, stop the PostgreSQL server and the App Service plan, or delete the resource group (section 15).

## 3. Before you start (your machine)

1. **Read the settings.** `deploy/environments/azure.appsettings.example` lists every app setting, without values.
2. **Build both zips:**
   ```bash
   python scripts/package_azure_kudu.py
   ```
   This writes `dist/azure_backend.zip` and `dist/azure_frontend.zip`.
3. **Prove them locally.** This runs both zips through their own startup scripts in the web profile, with a local PostgreSQL standing in for Azure's:
   ```bash
   ATLAS_ADMIN_USERNAME=<name> ATLAS_ADMIN_PASSWORD=<12+ chars> python scripts/dev.py azure-local --check
   ```
   On Windows PowerShell, set the two variables first: `$env:ATLAS_ADMIN_USERNAME="<name>"` and `$env:ATLAS_ADMIN_PASSWORD="<12+ chars>"`.

   **Verify:** the check prints `API health: 200; UI /login: 200`.
4. **Make two random values,** one for the secret key and one for the admin password. Run this twice:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

## 4. Resource group

1. In the portal, search **Resource groups**, then **Create**.
2. Name it `rg-agentic-qe`, choose region **East US 2**, then **Review + create** and **Create**.

## 5. Key Vault

1. **Create it.** Search **Key vaults**, then **Create**:
   - **Resource group:** `rg-agentic-qe`.
   - **Name:** `kv-agentic-qe-<unique>`.
   - **Region:** East US 2.
   - **Pricing tier:** Standard.
   - **Access configuration** tab: **Azure role-based access control**.

   Then **Create**.
2. **Give yourself access.** Open the vault, then **Access control (IAM)**, **Add role assignment**. Choose the role **Key Vault Secrets Officer**, with your own account as the member.
3. **Add two secrets.** Under **Objects, Secrets**, select **Generate/Import** for each:
   - `atlas-admin-password`: the admin password from section 3.4 (12+ characters, different from the username);
   - `atlas-secret-key`: the other random value. It encrypts stored secrets and signs sessions. If it is lost, stored secrets cannot be read.

   `atlas-database-url` is added in section 6.

## 6. PostgreSQL Flexible Server

1. **Create it.** Search **Azure Database for PostgreSQL flexible servers**, then **Create**:
   - **Resource group:** `rg-agentic-qe`.
   - **Server name:** `pg-agentic-qe-<unique>`.
   - **Region:** East US 2.
   - **PostgreSQL version:** 17 (16 also works).
   - **Workload type:** Development.
   - **Compute + storage:** select **Configure server**. Choose **Burstable**, **Standard_B1ms**, storage **32 GiB**, backup retention **7 days**, then **Save**.
   - **Authentication:** PostgreSQL authentication only. Choose an admin user name (not `admin` or `postgres`) and a long password.
2. **Networking** tab:
   - choose **Public access (allowed IP addresses)**;
   - leave "Allow public access from any Azure service" **off**.

   You add the API app's addresses in section 10.
3. **Create the server.** Select **Review + create**, then **Create**. It takes several minutes.
4. **Create the database.** When the server is ready, open **Settings, Databases**, then **+ Add**, and name it `agentic_qe`.
5. **Save the connection URL in Key Vault.** In the vault, **Generate/Import** a secret named `atlas-database-url` with this value:
   ```text
   postgresql://<admin user>:<password>@pg-agentic-qe-<unique>.postgres.database.azure.com:5432/agentic_qe?sslmode=require
   ```
   If the password has characters such as `@`, `:` or `/`, percent-encode them (for example `@` is `%40`).

The app creates its tables on first start (`backend/migrations/postgres/`, applied once each, under a lock).

## 7. Storage account

1. **Create it.** Search **Storage accounts**, then **Create**:
   - **Name:** `stagenticqe<unique>`.
   - **Region:** East US 2.
   - **Performance:** Standard.
   - **Redundancy:** Locally-redundant storage (LRS).
   - **Data protection** tab: turn on **Enable versioning for blobs** and **Enable soft delete for blobs** (7 days).

   Then **Create**.
2. **The `downloads` container** (works now; the login page links the desktop installers from it):
   - **Settings, Configuration:** set **Allow Blob anonymous access** to **Enabled**, then **Save**.
   - **Containers**, then **+ Container**: name `downloads`, anonymous access level **Blob** (never "Container").
   - Uploading installers is in `docs/DESKTOP_RELEASE_GUIDE.md`.
3. **After G6:** create the containers `documents`, `uploads`, `evidence` and `skills`, all **Private**. Then give the API app's managed identity the role **Storage Blob Data Contributor** (section 9.2), and add the Key Vault secret `atlas-storage-url` with the value `https://stagenticqe<unique>.blob.core.windows.net`.

## 8. App Service plan

1. Search **App Service plans**, then **Create**:
   - **Resource group:** `rg-agentic-qe`.
   - **Name:** `plan-agentic-qe`.
   - **Operating System:** Linux.
   - **Region:** East US 2.
   - **Pricing plan:** **Basic B1**.
2. Select **Review + create**, then **Create**.

## 9. API web app

1. **Create it.** Search **App Services**, then **Create**, **Web App**:
   - **Name:** `aqe-api-<unique>`.
   - **Publish:** Code.
   - **Runtime stack:** Python 3.12.
   - **Operating System:** Linux.
   - **Region:** East US 2.
   - **Plan:** `plan-agentic-qe`.
   - **Monitoring** tab: Application Insights is optional (section 12).

   Then **Create**.
2. **Turn on its identity and let it read the vault.**
   - In the app, open **Settings, Identity**. Set **System assigned** to **On**, then **Save**.
   - In the vault, open **Access control (IAM)**, **Add role assignment**. Choose **Key Vault Secrets User**, with the API app's managed identity as the member.
3. **Configuration, General settings:**
   - **Startup Command:** `python /home/site/wwwroot/startup.py`;
   - **Always on:** On;
   - **HTTPS Only:** On.

   Then **Save**.
4. **Environment variables, App settings.** Select **+ Add** for each, then **Apply**:

   | Name | Value |
   |---|---|
   | `ATLAS_KEY_VAULT_URL` | `https://kv-agentic-qe-<unique>.vault.azure.net`. At startup the app reads `atlas-admin-password`, `atlas-secret-key` and `atlas-database-url` from it. Do **not** add those three as app settings |
   | `ATLAS_PROFILE` | `web` |
   | `ATLAS_DATA_DIR` | `/home/atlas/data` (workspaces and files, until G6) |
   | `ATLAS_ADMIN_USERNAME` | the first admin's username |
   | `ATLAS_ADMIN_EMAIL` | the admin's email (optional) |
   | `ATLAS_ALLOWED_HOSTS` | `aqe-api-<unique>.azurewebsites.net` |
   | `ATLAS_ALLOWED_ORIGINS` | `https://aqe-ui-<unique>.azurewebsites.net` |
   | `ATLAS_MAX_SANDBOXES` | `5` |
   | `ATLAS_INSTALL_EVALS` | `1` to install RAGAS on first start (optional; a few minutes more) |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
   | `WEBSITES_PORT` | `8000` |

5. **Deploy the zip.**
   1. Open `https://aqe-api-<unique>.scm.azurewebsites.net/ZipDeployUI` and drag `dist/azure_backend.zip` onto it.
   2. When it finishes, select **Restart** on the app.
6. **Verify.**
   - **Monitoring, Log stream** shows "Environment built", then "Starting API on port 8000". The first start takes several minutes.
   - If Key Vault or the database cannot be reached, the log says which, and how to fix it. For example: "Give the web app's identity the role Key Vault Secrets User", or a PostgreSQL connection error, which means section 10 is not done yet.

## 10. Let the API reach PostgreSQL, and only the UI reach the API

1. **Copy the API's addresses.** Open the **API** app, **Settings, Properties**. Copy every **Outbound IP address** and **Additional Outbound IP address**.
2. **Open the PostgreSQL firewall to them.** In the PostgreSQL server, open **Settings, Networking**. Add one firewall rule per address (start and end both that address), then **Save**. Restart the API app.

   **Verify:** `https://aqe-api-<unique>.azurewebsites.net/api/health` returns `"status": "ok"`.
3. **Create the UI web app.** **Create**, **Web App**:
   - **Name:** `aqe-ui-<unique>`.
   - **Runtime:** Node 20 LTS.
   - **Linux**, **East US 2**, plan `plan-agentic-qe`.

   Then set:
   - **Startup Command:** `node /home/site/wwwroot/startup.js`, with **Always on** and **HTTPS Only** both On;
   - app settings `ATLAS_BACKEND_URL=https://aqe-api-<unique>.azurewebsites.net`, `ATLAS_DOWNLOADS_URL=<the downloads container URL>`, `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` and `WEBSITES_PORT=3000`.

   Deploy `dist/azure_frontend.zip` through `https://aqe-ui-<unique>.scm.azurewebsites.net/ZipDeployUI`, then **Restart**. **Log stream** ends with "Starting UI on port 3000".
4. **Lock the API to the UI.**
   - Copy the **UI** app's outbound addresses, as in step 1.
   - In the **API** app, open **Settings, Networking**, **Public network access**, **Access restriction**:
     - set **Unmatched rule action** to **Deny**;
     - add one **Allow** rule per UI address;
     - on the **Advanced tool site** tab, allow only your own IP (you need Kudu for deployments).

   **Verify:** the health URL now answers 403 from your browser, and the UI still works.

## 11. Check the settings, and move existing data

1. **Check the settings.** In the **API** app, open **Development Tools, SSH**, then **Go**, and run:
   ```bash
   python /home/site/wwwroot/scripts/env_check.py --env azure
   ```
   It prints which settings came from Key Vault, by name only, and then `azure: OK`.
2. **Move an existing SQLite store (once).** Only if you ran an earlier version that kept `atlas.sqlite3`:
   1. Upload the old `atlas.sqlite3` to `/home/atlas/data/` with Kudu's **Debug console**.
   2. In the SSH console, run:
      ```bash
      cd /home/site/wwwroot && python scripts/sqlite_to_postgres.py /home/atlas/data/atlas.sqlite3
      ```

   It refuses a database that already holds data. It copies every table, then checks the row counts, every project's ledger hash chain and every document version's SHA-256, and prints "Copy complete and verified".

## 12. Observability

1. **In the app.**
   - Admins see every trace at `/traces`, and download logs on **Settings**: `app-DAY.jsonl` for requests, `errors-DAY.jsonl` for errors with stack traces.
   - Members see only their own runs.
2. **Application Insights** (optional):
   - create it in East US 2;
   - on the API app, set `OTEL_EXPORTER_OTLP_ENDPOINT` (your collector or Azure Monitor's OTLP endpoint) and `OTEL_SERVICE_NAME=agentic-qe-api`.

## 13. First sign-in, people and permissions

1. **Sign in.** Open `https://aqe-ui-<unique>.azurewebsites.net`. The landing page has **Sign in** and the desktop downloads. Sign in as the admin.
2. **Settings:**
   - enter the model endpoint, model name and key, then **Test connection**;
   - tick the models people may use;
   - under **Plugins**, grant plugins per role if needed.
3. **Users, Add user:** username, temporary password, email and role (`qe_lead`, `ba`, `developer` or `viewer`).
4. **Each project, Members:** add the people who may see it. Approvals show the approver's name, role and email.
5. **Settings, Gate roles:** choose who may sign gates G0 to G5. Agents never sign.
6. **MCP:** add remote (HTTP) MCP servers and grant tools per role. stdio servers run only in the desktop app.

## 14. Using the app: a tour of the UI

The same pages run locally, on Azure and in the desktop app. Screenshots are from real runs in `docs/evidence/`; pages without one are not captured yet.

| Page | Who | What you do there | Screenshot |
|---|---|---|---|
| `/` | everyone | Landing page: what the platform does, macOS and Windows downloads, **Sign in** | [dark](evidence/screens/landing-dark.png), [light](evidence/screens/landing-light.png), [phone](evidence/screens/landing-phone.png) |
| `/login` | everyone | Sign in | [login](evidence/22a-login.png) |
| `/projects` | members | Create a project, then attach a repository: a zip upload or a GitHub URL | [list](evidence/05-projects-list.png), [zip](evidence/03-repository-zip.png), [GitHub](evidence/04-repository-github.png) |
| Project, **Harness** | members | Chat with the project harness. Type `/` for commands; a plugin command stays active until the next one. Status lines appear while it works. Risky tools and every file write or shell command stop for **Approve** or **Reject** | [harness](evidence/screens/harness.png), [slash menu](evidence/evidence_harness_fixed_slash_palette.png), [tasks](evidence/evidence_harness_tasks_completed.png) |
| Project, **BA** | BA, QE lead | Requirements documents (BRDs) and Gherkin, then sign gate G1. Every save is a new version | [BA](evidence/screens/project_ba.png), [Gherkin](evidence/08-gherkin-editor.png), [history](evidence/09-document-history.png) |
| Project, **Bugs** and **Feature** | developers | Bug scan findings; generated changes land on a separate branch as a diff | [scan](evidence/10-bug-scan.png), [diff](evidence/11-feature-diff.png) |
| Project, **QE** | QE lead | Gates G0 to G5, each signed by a named person | [QE](evidence/screens/project_qe.png), [gate 5](evidence/14-qe-gate5.png) |
| Project, **Approvals** and **Governance** | approvers | Pending approvals with the approver's name, role and email; the hash-chained ledger | [approvals](evidence/06b-approvals-page.png), [governance](evidence/19-governance.png) |
| `/skills/studio` | admin, QE lead | Skill Creator Studio: source, kind, plan, approve, generate, test (with **Repair from test failures**), evaluate, publish | [request](evidence/us-51-1-source-kind-request.png), [plan](evidence/us-51-2-plan-draft.png), [published](evidence/us-51-4-published.png), [evaluation](evidence/us-53-1-evaluation.png) |
| `/skills` | everyone | Published skills and their versions | [skills](evidence/screens/skills_list.png) |
| `/agents` | everyone | 15 governed agents; each score tile shows `n` and the judge, or why it is blank | [agents](evidence/screens/agents.png) |
| `/mcp` | admin | Add an MCP server, **Connect**, grant each tool per role | [connected](evidence/screens/us-55-mcp-connected.png), [granted](evidence/screens/us-55-mcp-granted.png) |
| `/traces` | admin: all; member: own | Trace explorer: runs, span tree, waterfall | not captured yet |
| `/capabilities` | everyone | Capability registry: every tool, agent, skill, command and workflow, with links | not captured yet |
| `/settings`, `/users`, `/account` | admin; each person | Model, plugins, gate roles, logs; people with role and email; your own password and email | [settings](evidence/06-settings.png), [users](evidence/22b-users.png) |

## 15. Desktop app, updates, backup, teardown

- **Desktop app.**
  - **Building:** GitHub Actions builds the DMGs (Apple silicon and Intel) and the MSI on every push that changes the app; a `v*` tag publishes a GitHub Release. See `docs/DESKTOP_RELEASE_GUIDE.md`.
  - **Database:** the desktop app keeps its data in a local PostgreSQL cluster in the user's app folder. **For now it needs PostgreSQL 16 or newer installed on the computer:**
    - macOS: `brew install postgresql@17`;
    - Windows: the installer from postgresql.org.

    Bundling PostgreSQL inside the installer is owner decision D-P1 in `docs/MASTER_PLAN.md`.
- **Update.**
  1. Change and test locally: `python scripts/dev.py db`, then `python scripts/dev.py test`.
  2. Build the zips and run `azure-local --check`.
  3. Deploy both zips through `ZipDeployUI` and restart both apps.

  New tables are added automatically on start.
- **Backup.**
  - PostgreSQL keeps 7 days of point-in-time restore: **Settings, Backup and restore**, then **Restore**.
  - Blob versioning and soft delete keep the installers.
  - The `/home` share holds workspaces and files: check each app's **Backups** page.
- **Stop paying.** Stop the PostgreSQL server (**Overview, Stop**; it restarts by itself after 7 days), or delete the resource group `rg-agentic-qe`, which removes everything in it.

## 16. Open decisions

| # | Decision | State |
|---|---|---|
| A | App Service or Container Apps | App Service B1 (owner, 2026-11-11) |
| B | Entra ID sign-in | Later; built-in accounts now |
| C | Model provider | The existing endpoint, set on Settings |
| D-P1 | Desktop database | A local cluster using the installed PostgreSQL now; bundled PostgreSQL binaries is the proposed default |
| E | Region | **East US 2** (owner, 2026-11-11) |

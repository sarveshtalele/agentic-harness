# Azure deployment guide (East US 2)

This is the one guide for deploying Agentic QE Platform to Azure. It covers the price, building the two zips, every step in the Azure portal, first start (toolchains), sign-in, checking each feature, and updating, rolling back and removing it.

The deployment runs on one App Service plan (B1) with **two web apps on App Service's built-in images** (no Docker, no container registry): the **API** on the built-in Python 3.12 image, and the **UI** on the built-in Node 22 LTS image. PostgreSQL and Key Vault complete it, all in **East US 2**. You build two zips on your computer and deploy them with zip deploy through Kudu. GitHub never connects to Azure.

**What has been verified, and what has not (2026-11-14):**
- **Verified on a local machine:**
  - both zips start through their own startup scripts in the web profile against PostgreSQL (`azure-local --check` prints `API health: 200; UI /login: 200`, re-run on 2026-11-14 after the toolchain change);
  - the toolchain downloader refuses a wrong checksum and leaves nothing behind, and downloads, verifies, extracts and is idempotent for Node 22.12.0 (checked on macOS with a local copy of the vendor tarball, because the sandbox's proxy truncated the live download; the extracted Linux binary was not run, as the machine is not Linux);
  - the sandbox environment test (`tests/test_redblue_sandbox.py`) passes with the toolchain variables allow-listed.
- **Not yet run on Azure, and the first deploy must prove these:**
  1. the built-in Python image runs the startup command **as root** and `apt` reaches its mirrors (needed once per start for Chromium's system libraries, section 12);
  2. `github.com` (JDK download), `nodejs.org`, `go.dev`, `builds.dotnet.microsoft.com`, `archive.apache.org` and Playwright's CDN are reachable from the app;
  3. the .NET SDK and Temurin JDK run on the image's libc.

  If any of these fails, use the fallback in section 12.4: greenfield end-to-end runs locally only, and Azure shows their evidence.
- **No screenshots of the portal yet.** They need a real subscription. The portal steps follow the portal as it is today, but nobody has run them end to end in a subscription. Check each **Verify** line as you go.
- **Not built yet:** a friendly "database is stopped (outside working hours)" page. While PostgreSQL is stopped, the API answers with a database error (section 13).

---

## Contents

1. [Architecture](#1-architecture)
2. [Monthly cost](#2-monthly-cost-east-us-2)
3. [Before you start](#3-before-you-start)
4. [Build and check the zips](#4-build-and-check-the-zips)
5. [Resource group](#5-resource-group)
6. [Key Vault](#6-key-vault)
7. [PostgreSQL Flexible Server](#7-postgresql-flexible-server)
8. [App Service plan](#8-app-service-plan)
9. [API web app](#9-api-web-app)
10. [Let the API reach PostgreSQL](#10-let-the-api-reach-postgresql)
11. [UI web app, and lock the API to the UI](#11-ui-web-app-and-lock-the-api-to-the-ui)
12. [First start: toolchains for greenfield runs](#12-first-start-toolchains-for-greenfield-runs)
13. [Stop PostgreSQL outside working hours (stays under $25)](#13-stop-postgresql-outside-working-hours)
14. [Check the settings, and move old data](#14-check-the-settings-and-move-old-data)
15. [First sign-in, people, permissions, and checking each feature](#15-first-sign-in-people-and-permissions)
16. [A tour of the UI](#16-a-tour-of-the-ui)
17. [Observability](#17-observability)
18. [Update, roll back, back up, stop paying](#18-update-roll-back-back-up-stop-paying)
19. [Troubleshooting](#19-troubleshooting)
20. [Decisions](#20-decisions)

---

## 1. Architecture

```text
 People ── browser ──▶ UI web app (built-in Node 22, Next.js) ──▶ API web app (built-in Python 3.12, FastAPI + MAF)
                                                                    ├─▶ model endpoint
                                                                    ├─▶ PostgreSQL Flexible Server (Burstable B1ms, pgvector)
                                                                    ├─▶ Key Vault: admin password, secret key, database URL (read at startup)
                                                                    ├─▶ /home/atlas/data: projects, documents, per-project sandboxes
                                                                    ├─▶ /home/tools: Node 22, JDK 21, Maven, .NET 8, Go, Playwright Chromium
                                                                    └─▶ Application Insights (optional, OpenTelemetry)
```

| Part | Choice | Why |
|---|---|---|
| Compute | One Linux App Service plan **B1**, with two web apps on the **built-in** Python 3.12 and Node 22 LTS images | The cheapest plan that runs both, with no registry to pay for or maintain (owner, 2026-11-14) |
| Toolchains | Downloaded once into `/home/tools` by `startup.py` (`toolchains.py`), each checked against the vendor's SHA | The built-in image has Python only. `/home` survives restarts, so the download happens once |
| Database | **PostgreSQL Flexible Server, Burstable B1ms**, 32 GiB, version 17 (16 also works), with the `vector` extension allow-listed | The only database the app supports. It gives point-in-time restore, many writers, and pgvector for document search |
| Secrets | **Key Vault Standard**, read by the API with its managed identity (`ATLAS_KEY_VAULT_URL`) | No secret in app settings |
| Sign-in | Built-in accounts. The first admin's password comes from Key Vault | Works without an Entra app registration |
| Greenfield runs | **Every greenfield application is set up and run in the project's own sandbox**, under `/home/atlas/data/projects/<id>/sandbox`, with the sandbox's clean environment (section 12.3) | Generated code never runs with the platform's own environment or secrets |
| Load | **One greenfield run at a time** (the backend enforces it), and at most 5 sandbox jobs (`ATLAS_MAX_SANDBOXES`) | B1 has 1.75 GB of memory, which two apps, Chromium and a JDK or .NET build must share |

**Security limit.** Repository code runs on the same machine as the API until isolated sandbox jobs exist. Admit only people you trust.

---

## 2. Monthly cost (East US 2)

Prices are pay-as-you-go for 730 hours a month, in US dollars and Indian rupees. Both price lists were read live from the Azure Retail Prices API (`prices.azure.com`, `currencyCode=USD` and `currencyCode=INR`) on **2026-11-12 at 07:43 UTC**. They **exclude taxes**: for example, 18% GST applies when you are billed in India. Prices change, so check them before you create anything (the command is at the end of this section).

The proposal workbook `docs/proposal/Agentic_QE_Azure_Proposal.xlsx` has the same figures as live formulas. Its sheets are: cost per line, assumptions you can change, the raw API rows, architecture, deployment steps, UI guide, and review gaps. The same sheets are also saved as plain CSVs in `docs/proposal/csv/`.

### The standard deployment: under the $25 cap

PostgreSQL compute is billed only while the server runs. The standard stops it outside working hours: it runs 12 hours a day on 22 weekdays, which is 264 hours a month (section 13). Its storage is still billed while it is stopped.

| Resource | Meter | Price (USD / INR) | Per month (USD) | Per month (INR) |
|---|---|---|---|---|
| App Service plan B1, Linux (both built-in-image web apps share it) | B1 | $0.017 / ₹1.6189 an hour | **$12.41** | **₹1,181.80** |
| PostgreSQL B1ms compute, 264 hours | B1MS | $0.017 / ₹1.6189 an hour | **$4.49** | **₹427.39** |
| PostgreSQL storage, 32 GiB | Storage Data Stored | $0.115 / ₹10.9513 per GB a month | **$3.68** | **₹350.44** |
| PostgreSQL backups, 7 days | Backup Storage LRS | Included up to the provisioned size; above it $0.095 / ₹9.0467 per GB | **$0** | **₹0** |
| Key Vault Standard | Operations | $0.03 / ₹2.8569 per 10,000 (the API reads 3 secrets at each start) | **under $0.01** | **₹0.03** |
| Azure Automation (the start and stop jobs) | Basic Runtime | First 500 minutes a month free, then $0.002 / ₹0.1905 a minute; about 44 minutes are used | **$0** | **₹0** |
| **Total** | | | **$20.58** | **₹1,959.66** |

That is $246.96 (₹23,515.92) a year before taxes. The built-in images add nothing to this table: the plan and the PostgreSQL tier are the ones already listed, and there is no container registry (the custom-container version's GHCR storage line, up to about $0.50 a month, is gone). Downloading the toolchains is inbound traffic and free.

### Disk: what the toolchains use of the plan's storage

The B1 plan includes **10 GB of storage, shared by all apps in the plan** (each app's `/home` share counts). Nothing extra is billed while you stay inside it. The sizes below are **estimates** from the vendors' archives, not measured on Azure (the extracted Node 22.12.0 was measured: 202 MB):

| Item | Where | Estimated size on disk |
|---|---|---|
| Node 22.12.0 | `/home/tools/node-22.12.0` | 0.2 GB (measured) |
| Temurin JDK 21.0.13 | `/home/tools/jdk-21.0.13` | 0.35 GB |
| Maven 3.9.9 | `/home/tools/maven-3.9.9` | 0.01 GB |
| .NET SDK 8.0.428 | `/home/tools/dotnet-8.0.428` | 0.5 GB |
| Go 1.23.4 | `/home/tools/go-1.23.4` | 0.25 GB |
| Playwright Chromium and headless shell | `/home/tools/ms-playwright` | 0.6 GB |
| **Toolchains subtotal** | | **about 1.9 GB** |
| Python environment (`requirements.txt`) | `/home/atlas/venv` | about 0.8 GB |
| Built UI (Next.js standalone) | UI app's `/home/atlas/frontend` | about 0.3 GB |
| Code zips, logs, workspaces, evidence | `/home/site/wwwroot`, `/home/atlas/data` | 0.5 GB to start, grows with projects |
| **Total at the start** | | **about 3.5 GB of 10 GB** |

Each greenfield project adds its sandbox (a repository clone, dependencies, build output). Watch the web app's **Monitoring, Quotas** page. If the 10 GB ever run out, delete finished projects' sandboxes; more storage means a larger plan (B1 to S1 gives 50 GB), which needs the owner's yes.

### Other choices

| Choice | Per month (USD) | Per month (INR) | Within the $25 cap? |
|---|---|---|---|
| PostgreSQL 8 hours on weekdays (176 hours) | $19.12 | ₹1,820.78 | Yes |
| PostgreSQL always on (730 hours) | $28.54 | ₹2,717.65 | No |
| Upgrade: App Service plan **B2** (2 cores, 3.5 GB) at $0.034 / ₹3.2378 an hour, PostgreSQL 12 hours on weekdays | $33.03 | ₹3,145.04 | No, needs the owner's yes |
| Upgrade: App Service plan **P0v3** at $0.0775 / ₹7.3802 an hour, PostgreSQL **B2s** at $0.068 / ₹6.4756 an hour, always on | $109.93 | ₹10,468.79 | No, needs the owner's yes |

### Costs that depend on use

- **Outbound data.** The first 100 GB a month are free. After that, $0.087 (₹8.2849) per GB with Microsoft network routing. Toolchain downloads are inbound to Azure and free.
- **Application Insights** (optional). The first 5 GB of logs a month are free. After that, $2.76 (₹262.83) per GB ingested.
- **Model tokens** are billed by your model provider, not by Azure. The **Usage** page limits tokens per person and model.

**Two things that do not save money:**
- **Stopping a web app.** The App Service plan is billed while it exists, even with both apps stopped.
- **Stopping the PostgreSQL server for more than 7 days.** Azure starts it again by itself after 7 days.

### Re-check the prices

The commands below print the current hourly price of B1 and B1MS in East US 2. They work in Terminal (macOS, Linux) and in PowerShell 7 (Windows), as long as `curl` and Python are installed.

```bash
curl -sG "https://prices.azure.com/api/retail/prices" --data-urlencode "\$filter=armRegionName eq 'eastus2' and priceType eq 'Consumption' and (skuName eq 'B1' or skuName eq 'B1MS')" -o prices.json
python -c "import json; [print(i['productName'], i['skuName'], i['unitPrice'], i['unitOfMeasure']) for i in json.load(open('prices.json'))['Items']]"
```

Multiply an hourly price by 730 for a full month.

---

---

## 3. Before you start

You need:
- **An Azure subscription** where you can create resources.
- **This repository** on your computer, set up with `python scripts/dev.py setup` (see `README.md`).
- **PostgreSQL 16 or newer installed locally.** It is needed only for the local check in section 4.
- **Azure CLI** (`az`), signed in to your subscription, to deploy the zips (section 9.5).
- **Two random values:** one for the secret key and one for the admin credential. Run this twice and keep both values somewhere safe:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

**Names used in this guide.** Replace `<unique>` with a short tag of your own, for example your initials and a number. Web app, vault and server names must be unique across all of Azure.

| Resource | Name |
|---|---|
| Resource group | `rg-agentic-qe` |
| Key Vault | `kv-agentic-qe-<unique>` |
| PostgreSQL server | `pg-agentic-qe-<unique>` |
| App Service plan | `plan-agentic-qe` |
| API web app | `aqe-api-<unique>` |
| UI web app | `aqe-ui-<unique>` |
| Automation account | `aa-agentic-qe` |

`deploy/environments/azure.appsettings.example` lists every app setting, with no values.

---

## 4. Build and check the zips

**On macOS or Linux:**

```bash
python scripts/package_azure_kudu.py
ATLAS_ADMIN_USERNAME=<name> ATLAS_ADMIN_PASSWORD=<12+ chars> python scripts/dev.py azure-local --check
```

**On Windows, in PowerShell from the repository folder:**

```powershell
py scripts\package_azure_kudu.py
$env:ATLAS_ADMIN_USERNAME = "<name>"
$env:ATLAS_ADMIN_PASSWORD = "<12+ chars>"
py scripts\dev.py azure-local --check
Remove-Item Env:ATLAS_ADMIN_PASSWORD
```

**What this does:**
- **`package_azure_kudu.py`** writes two zips:
  - `dist/azure_backend.zip`: the API. It holds `startup.py` (the one startup; `startup.sh` only calls it), `toolchains.py`, `.deployment`, `web.config`, `requirements.txt`, the backend code, prompts, templates (including `templates/stacks`), skills, evals, and `plugins/agentic-qe` (read at run time by the QE cycle).
  - `dist/azure_frontend.zip`: the UI. It holds `startup.js`, `startup.sh`, `.deployment`, `web.config` and the Next.js source.
- **The zips are built for the Linux App Service:**
  - paths use forward slashes;
  - only files Git tracks or would track are included, so `.env`, `data/` and build folders are never in a zip;
  - `.deployment` turns Kudu's build off, so Kudu only unzips; the startup scripts build once, themselves (Python environment in `/home/atlas/venv`; the UI is built on local disk and its output kept in `/home/atlas/frontend`).
- **`azure-local --check`** unzips both packages into `data/azure-local`, starts each one through its own startup script in the web profile with a local PostgreSQL, and checks both. On a computer that is not Linux x64 the toolchain step logs that it is skipped, so the check downloads nothing.

**Verify:**
- the check prints `API health: 200; UI /login: 200`;
- the top level of the backend zip holds `.deployment`, `requirements.txt`, `startup.py`, `startup.sh`, `toolchains.py` and `web.config`:
  ```bash
  python -c "import zipfile; print(sorted(n for n in zipfile.ZipFile('dist/azure_backend.zip').namelist() if '/' not in n))"
  ```

**Common mistakes:**
- **Zipping with Explorer** (**Send to, Compressed folder**) or Finder. Those zips use backslashes or include build folders, and the app does not start. Always use the script.
- **The wrong runtime stack.** The API is Python 3.12; the UI is Node 22 LTS.
- **A missing startup command** (sections 9 and 11).
- **Kudu's build turned on.** `SCM_DO_BUILD_DURING_DEPLOYMENT` must be `false` on both apps.

---

## 5. Resource group

1. In the [Azure portal](https://portal.azure.com), search **Resource groups**, then select **Create**.
2. Fill in:
   - **Subscription:** yours;
   - **Resource group:** `rg-agentic-qe`;
   - **Region:** **East US 2**.
3. Select **Review + create**, then **Create**.

**Verify:** `rg-agentic-qe` is listed under **Resource groups**, in East US 2.

---

## 6. Key Vault

1. **Create the vault.** Search **Key vaults**, then select **Create**.
   - **Basics** tab:
     - **Resource group:** `rg-agentic-qe`;
     - **Key vault name:** `kv-agentic-qe-<unique>`;
     - **Region:** East US 2;
     - **Pricing tier:** Standard.
   - **Access configuration** tab: **Permission model: Azure role-based access control**.
   - Select **Review + create**, then **Create**.
2. **Give yourself access.**
   1. Open the vault, then **Access control (IAM)**, then **Add, Add role assignment**.
   2. Choose the role **Key Vault Secrets Officer**, then **Next**.
   3. Choose **User, group, or service principal**, then **Select members**, and pick your own account.
   4. Select **Review + assign**.
3. **Add two secrets.** Open **Objects, Secrets**, then **Generate/Import**, once for each:
   - **Name** `atlas-admin-password`, with the admin password from section 3. It must be at least 12 characters and differ from the username.
   - **Name** `atlas-secret-key`, with the other random value. It encrypts stored secrets and signs sessions. **If it is lost, stored secrets cannot be read.**

   The third secret, `atlas-database-url`, is added in section 7.

   **Stronger, recommended (R6):** keep only a hash of the admin password, and add a pepper.
   1. On your computer run `python scripts/dev.py admin-password`. It prints a random password once (store it in your password manager) and its hash.
   2. Add the secret `atlas-admin-password-hash` with that hash (instead of `atlas-admin-password`), and `atlas-password-pepper` with another random value (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). If you set the pepper, run step 1 with `ATLAS_PASSWORD_PEPPER` set to the same value. **If the pepper is lost, every member must have their password reset.**
   3. In section 9.4, set `ATLAS_KEY_VAULT_SECRETS` to `atlas-admin-password-hash,atlas-password-pepper,atlas-secret-key,atlas-database-url,atlas-storage-url`.
   Optional settings: `ATLAS_SCRYPT_N` (password hashing cost; raising it rehashes each account at its next sign-in), `ATLAS_BREACHED_PASSWORDS_FILE` (a list of breached passwords, one per line).

**Verify:** **Objects, Secrets** lists both secrets as **Enabled**.

---

## 7. PostgreSQL Flexible Server

1. **Create the server.** Search **Azure Database for PostgreSQL flexible servers**, then select **Create**.
   - **Basics** tab:
     - **Resource group:** `rg-agentic-qe`;
     - **Server name:** `pg-agentic-qe-<unique>`;
     - **Region:** East US 2;
     - **PostgreSQL version:** 17;
     - **Workload type:** Development;
     - **Compute + storage:** select **Configure server**, then choose **Burstable**, **Standard_B1ms**, storage **32 GiB**, and backup retention **7 days**. Select **Save**;
     - **Authentication method:** PostgreSQL authentication only;
     - **Admin username:** a name of your own (not `admin` or `postgres`);
     - **Password:** a long password.
   - **Networking** tab:
     - **Connectivity method:** **Public access (allowed IP addresses)**;
     - leave **Allow public access from any Azure service within Azure to this server** turned **off**. The API's addresses are added in section 10.
   - Select **Review + create**, then **Create**. This takes several minutes.
2. **Create the database.** When the server is ready, open **Settings, Databases**, then **+ Add**. Name it `agentic_qe` and select **Save**.
3. **Store the connection URL in Key Vault.** In the vault, open **Objects, Secrets**, then **Generate/Import**:
   - **Name:** `atlas-database-url`;
   - **Secret value:**
     ```text
     postgresql://<admin user>:<password>@pg-agentic-qe-<unique>.postgres.database.azure.com:5432/agentic_qe?sslmode=require
     ```
   - If the password contains `@`, `:`, `/`, `?` or `#`, percent-encode them. For example, `@` becomes `%40`.

4. **Allow the `vector` extension (pgvector).** Document search needs it, and Azure refuses `CREATE EXTENSION` for anything not allow-listed.
   1. In the server, open **Settings, Server parameters**.
   2. Search `azure.extensions`, tick **VECTOR** in its value list, then **Save**. No restart is needed for this parameter.
   3. Optional check: connect with `psql` as the admin and run `SHOW azure.extensions;`. It lists `vector`. The app runs `CREATE EXTENSION IF NOT EXISTS vector` itself at start.

The API creates its tables on its first start (from `backend/migrations/postgres/`, each applied once, under a lock).

**Verify:** the server's **Overview** shows **Status: Ready**, and **Settings, Databases** lists `agentic_qe`.

---

---

## 8. App Service plan

1. Search **App Service plans**, then select **Create**.
2. Fill in:
   - **Resource group:** `rg-agentic-qe`;
   - **Name:** `plan-agentic-qe`;
   - **Operating System:** Linux;
   - **Region:** East US 2;
   - **Pricing plan:** **Basic B1**. Select **Explore pricing plans** if B1 is not shown.
3. Select **Review + create**, then **Create**.

**Verify:** the plan's **Overview** shows **Basic (B1)** and **Linux**.

---

## 9. API web app

1. **Create the app.** Search **App Services**, then select **Create, Web App**.
   - **Basics** tab:
     - **Resource group:** `rg-agentic-qe`;
     - **Name:** `aqe-api-<unique>`;
     - **Publish:** Code;
     - **Runtime stack:** Python 3.12;
     - **Operating System:** Linux;
     - **Region:** East US 2;
     - **Linux Plan:** `plan-agentic-qe`.
   - **Deployment** tab: leave continuous deployment **off**.
   - **Monitoring** tab: Application Insights is optional (section 17).
   - Select **Review + create**, then **Create**.
2. **Turn on its identity, and let it read the vault.**
   1. In the app, open **Settings, Identity**. On the **System assigned** tab, set **Status** to **On**, then **Save** and **Yes**.
   2. In the vault, open **Access control (IAM)**, then **Add, Add role assignment**.
   3. Choose the role **Key Vault Secrets User**, then **Next**.
   4. Choose **Managed identity**, then **Select members**, pick **App Service** and `aqe-api-<unique>`.
   5. Select **Review + assign**.
3. **General settings.** In the app, open **Settings, Configuration, General settings**:
   - **Startup Command:** `python /home/site/wwwroot/startup.py`;
   - **Always on:** On;
   - **HTTPS Only:** On;
   - **Health check path** (optional): `/api/health`.

   Select **Save**.
4. **App settings.** Open **Settings, Environment variables, App settings**. Select **+ Add** for each row below, then **Apply** and **Confirm**.

   | Name | Value |
   |---|---|
   | `ATLAS_KEY_VAULT_URL` | `https://kv-agentic-qe-<unique>.vault.azure.net`. At startup the API reads `atlas-admin-password`, `atlas-secret-key` and `atlas-database-url` from it. Do **not** add those three as app settings |
   | `ATLAS_PROFILE` | `web` |
   | `ATLAS_DATA_DIR` | `/home/atlas/data` (projects, workspaces, sandboxes, files) |
   | `ATLAS_ADMIN_USERNAME` | the first admin's username |
   | `ATLAS_ADMIN_EMAIL` | the admin's email (optional) |
   | `ATLAS_ALLOWED_HOSTS` | `aqe-api-<unique>.azurewebsites.net` |
   | `ATLAS_ALLOWED_ORIGINS` | `https://aqe-ui-<unique>.azurewebsites.net` |
   | `ATLAS_MAX_SANDBOXES` | `5` |
   | `ATLAS_INSTALL_TOOLCHAINS` | `all` (the default). `none` installs nothing, and greenfield runs then report the missing tools. Or a comma list of `node,java,maven,dotnet,go,chromium` |
   | `ATLAS_INSTALL_EVALS` | `1` to install RAGAS on first start (optional; it adds a few minutes) |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true`, so `/home` survives restarts |
   | `WEBSITES_PORT` | `8000` |
   | `WEBSITES_CONTAINER_START_TIME_LIMIT` | `1800` (the maximum, in seconds). The first start builds the Python environment, which takes several minutes. Toolchains install in the background and do not count |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` |
   | `ENABLE_ORYX_BUILD` | `false` |

   **One greenfield run at a time.** The backend refuses a second greenfield build while one runs. Do not add a second instance: the plan is B1 with one instance, and running workflows live in the API process.
5. **Deploy the zip** `dist/azure_backend.zip` from section 4. Either way:
   - **Option A, Azure CLI** (works on Linux apps):
     ```bash
     az webapp deploy --resource-group rg-agentic-qe --name aqe-api-<unique> --src-path dist/azure_backend.zip --type zip
     ```
   - **Option B, Kudu:** open `https://aqe-api-<unique>.scm.azurewebsites.net/ZipDeployUI` and drag the zip onto it. Microsoft documents this drag-and-drop page as unreliable on Linux apps; if it does not accept the zip, use option A.

   Then, in the app's **Overview**, select **Restart**.
6. **Watch the first start.** Open **Monitoring, Log stream**. It shows, in order:
   1. `Building environment in /home/atlas/venv. The first run takes several minutes`, then `Environment built`;
   2. `Toolchains: installing in the background into /home/tools ...` (section 12);
   3. `Starting API on port 8000`.

   - Until section 10 is done, the log shows a PostgreSQL connection error. That is expected.
   - If Key Vault cannot be read, the log says so and how to fix it, for example "Give the web app's identity the role Key Vault Secrets User".

---

## 10. Let the API reach PostgreSQL

1. **Copy the API's outbound addresses.** In the **API** app, open **Settings, Properties**. Copy every address under **Outbound IP addresses** and **Additional Outbound IP addresses**.
2. **Add them to the PostgreSQL firewall.**
   1. In the PostgreSQL server, open **Settings, Networking**.
   2. Under **Firewall rules**, add one rule per address, with that address as both **Start IP address** and **End IP address**.
   3. Select **Save**.
3. **Restart** the API app.

**Verify:** `https://aqe-api-<unique>.azurewebsites.net/api/health` returns `"status": "ok"` (before you lock the API in section 11.5).

---

## 11. UI web app, and lock the API to the UI

1. **Create the UI app.** Select **Create, Web App**:
   - **Resource group:** `rg-agentic-qe`;
   - **Name:** `aqe-ui-<unique>`;
   - **Publish:** Code;
   - **Runtime stack:** Node 22 LTS (Node 20 LTS also builds the UI);
   - **Operating System:** Linux;
   - **Region:** East US 2;
   - **Linux Plan:** `plan-agentic-qe`.

   Select **Review + create**, then **Create**.
2. **General settings:**
   - **Startup Command:** `node /home/site/wwwroot/startup.js`;
   - **Always on:** On;
   - **HTTPS Only:** On.

   Select **Save**.
3. **App settings:**

   | Name | Value |
   |---|---|
   | `ATLAS_BACKEND_URL` | `https://aqe-api-<unique>.azurewebsites.net` (no trailing slash) |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
   | `WEBSITES_PORT` | `3000` |
   | `WEBSITES_CONTAINER_START_TIME_LIMIT` | `1800` (the first start runs `npm ci` and the Next.js build) |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` (`startup.js` runs `npm ci` and the build itself, on local disk) |
   | `ENABLE_ORYX_BUILD` | `false` |

4. **Deploy the zip.** Run `az webapp deploy --resource-group rg-agentic-qe --name aqe-ui-<unique> --src-path dist/azure_frontend.zip --type zip`, then **Restart** the app.

   **Verify:** **Log stream** ends with "Starting UI on port 3000", and `https://aqe-ui-<unique>.azurewebsites.net/login` shows the sign-in page.
5. **Lock the API to the UI.**
   1. Copy the **UI** app's outbound addresses, the same way as in section 10.
   2. In the **API** app, open **Settings, Networking**. Under **Public network access**, open **Access restriction**.
   3. On the **Main site** tab:
      - set **Unmatched rule action** to **Deny**;
      - add one **Allow** rule per UI address.
   4. On the **Advanced tool site** tab, allow only your own IP address. You need it to reach Kudu for deployments.
   5. Select **Save**.
   6. Do the same **Advanced tool site** restriction on the UI app. Leave its **Main site** open to everyone (people sign in with their own accounts).

   **Verify:** the API health URL now answers **403** in your browser, and the UI still works.

---

## 12. First start: toolchains for greenfield runs

Greenfield runs build and test generated applications. That needs more than Python: Node 22 (also for the agentic-qe plugin's TypeScript and the Next.js template), JDK 21 and Maven (Spring Boot template), .NET 8, Go (`templates/stacks/*/stack.json` lists them), and Chromium for browser tests. The built-in image has none of these, so `startup.py` installs them, once.

### 12.1 What happens at each start

1. `startup.py` builds the Python environment (skipped when `requirements.txt` is unchanged).
2. It starts `toolchains.py` **in the background** and starts the API at once, so a slow download never delays the app or hits the start time limit.
3. `toolchains.py`, for each tool, skips it if it is already in `/home/tools`. Otherwise it downloads the pinned version, checks the vendor's SHA-256 or SHA-512 (a wrong checksum deletes the file and installs nothing), unpacks into a temporary folder, and renames it into place. An interrupted run leaves no half-installed tool.
4. For Chromium it runs `python -m playwright install chromium` into `/home/tools/ms-playwright`. Chromium's **system libraries** live outside `/home`, so they are gone after each restart: if `ldd` shows a missing library and the process is root, it runs `python -m playwright install-deps chromium` (apt). That costs about a minute at each restart.
5. Everything is logged with the prefix `[agentic-qe toolchains]`, and `/home/tools/status.json` records `ok` and a detail line for each tool. A failure is never skipped silently: the API still starts, and the failed tool stays missing.

Pinned versions (in `deploy/azure/toolchains.py`, checked 2026-11-14): Node 22.12.0, Temurin 21.0.13+9, Maven 3.9.9, .NET SDK 8.0.428, Go 1.23.4, and the Chromium that matches the `playwright` version in `requirements.txt`. To change one, change its version, URL and digest together, and rebuild the zip.

The downloads need outbound access to `nodejs.org`, `github.com` (Temurin), `archive.apache.org`, `builds.dotnet.microsoft.com`, `go.dev`, Playwright's CDN, and the OS package mirrors. They total about 0.7 GB.

### 12.2 Check it worked (do this on the first deploy)

1. Watch **Log stream** (section 9.6). Within about 10 to 15 minutes the log ends with `ready: node, java, maven, dotnet, go, chromium`. If it says `NOT ready: ...`, read the `FAILED:` lines above it.
2. In the API app, open **Development Tools, SSH**, then **Go**:
   ```bash
   cat /home/tools/status.json
   id -u            # 0 means root, which install-deps needs
   ls /home/tools
   ```
3. In the app, open a project with a greenfield stack. The stack's toolchain check names every missing tool and version (the same check the QE cycle runs before it starts a greenfield build).

### 12.3 Where greenfield code runs: the project's sandbox

Every greenfield application is set up and run in that project's own sandbox, never in the API's own environment:
- **Where:** `/home/atlas/data/projects/<project id>/sandbox` (`ATLAS_DATA_DIR` plus `projects/<id>/sandbox`), created by `initialize_sandbox` (`src/backend/repos/sandbox/setup.py`).
- **What runs there:** installing dependencies, building, starting the app on a loopback port, and the unit, integration and end-to-end tests, all through the sandbox's command runner (`commands.execute_command` and `run_tests`).
- **With which environment:** `clean_sandbox_env` (`src/backend/repos/sandbox/env.py`). It passes only an allowlist: `PATH`, `PLAYWRIGHT_BROWSERS_PATH`, `JAVA_HOME`, `GOROOT`, `DOTNET_ROOT`, the .NET switches and a few basics. It removes everything that looks like a credential (`ATLAS_*`, keys, tokens, passwords) and drops the platform's own Python environment from `PATH`.
- **How the tools get there:** `startup.py` puts `/home/tools/<tool>/bin` on the API process's `PATH` and sets `JAVA_HOME`, `GOROOT`, `DOTNET_ROOT` and `PLAYWRIGHT_BROWSERS_PATH=/home/tools/ms-playwright`. The sandbox inherits exactly those through `clean_sandbox_env`, and nothing else from the platform.

### 12.4 If Chromium's libraries cannot be installed (fallback)

If the first deploy shows that the process is not root, or `apt` is unreachable (the log says `chromium: FAILED: ... not root`, or `install-deps` fails), Chromium cannot start on this image. Then:
- set `ATLAS_INSTALL_TOOLCHAINS` to `node,java,maven,dotnet,go` so the log stays clean;
- run greenfield **end-to-end** tests only on a developer computer (with a local Chromium), and attach their evidence to the project on Azure;
- unit and integration tests for the Java, .NET, Go, Node and Python stacks still run in the Azure sandbox, because they need no browser.

Moving to a custom container would change the owner's no-Docker decision, so it is not part of this guide.

### 12.5 Disk and memory

About 1.9 GB of `/home/tools` (section 2). Do not start a greenfield build while the first toolchain download is still running: B1 has 1.75 GB of memory shared by both apps, and the UI build uses up to 1 GB. The API refuses a second greenfield run, and the UI build happens only on the first start and after a UI update.

---

## 13. Stop PostgreSQL outside working hours

This schedule keeps the standard deployment under $25 a month. An Automation account starts the server at 08:00 and stops it at 20:00, Monday to Friday.

1. **Create the Automation account.** Search **Automation Accounts**, then select **Create**:
   - **Resource group:** `rg-agentic-qe`;
   - **Name:** `aa-agentic-qe`;
   - **Region:** East US 2;
   - **Advanced** tab: **System assigned** identity turned on.

   Select **Review + create**, then **Create**.
2. **Let it start and stop the server.**
   1. In the PostgreSQL server, open **Access control (IAM)**, then **Add, Add role assignment**.
   2. On the **Privileged administrator roles** tab, choose **Contributor**, then **Next**.
   3. Choose **Managed identity**, then **Select members**, pick **Automation Account** and `aa-agentic-qe`.
   4. Select **Review + assign**.

   The role is scoped to this one server only.
3. **Create the runbook.**
   1. In the Automation account, open **Process Automation, Runbooks**, then **Create a runbook**.
   2. Set **Name** to `pg-start-stop`, **Runbook type** to **PowerShell**, and **Runtime version** to **7.2**. Select **Create**.
   3. Paste this code, replacing the three values on the first lines:
      ```powershell
      param([Parameter(Mandatory)][ValidateSet("start", "stop")][string]$Action)
      $subscription = "<subscription id>"
      $group = "rg-agentic-qe"
      $server = "pg-agentic-qe-<unique>"
      Connect-AzAccount -Identity | Out-Null
      $path = "/subscriptions/$subscription/resourceGroups/$group/providers/Microsoft.DBforPostgreSQL/flexibleServers/$server/$($Action)?api-version=2022-12-01"
      $response = Invoke-AzRestMethod -Method POST -Path $path
      "PostgreSQL $Action answered HTTP $($response.StatusCode)"
      if ($response.StatusCode -ge 400) { throw $response.Content }
      ```
   4. Select **Save**, then **Publish**, and **Yes**.
4. **Test it.**
   1. Select **Start**, set **ACTION** to `stop`, then **OK**.
   2. When the job finishes, its **Output** shows `HTTP 202`, and the server's **Overview** shows **Stopped**.
   3. Run it again with `start` to bring the server back.
5. **Add the two schedules.** In the runbook, open **Resources, Schedules**, then **Add a schedule**, twice:
   - **Start:** **Link a schedule to your runbook**, then **Add a schedule**:
     - **Name:** `pg-start-weekdays`;
     - **Starts:** tomorrow at 08:00, in your time zone;
     - **Recurrence:** Recurring, every 1 week, on Monday to Friday.

     Select **Create**, then under **Parameters and run settings** set **ACTION** to `start`, and select **OK**.
   - **Stop:** the same steps, with the name `pg-stop-weekdays`, at 20:00, and **ACTION** set to `stop`.

**While the server is stopped:**
- The app cannot reach the database. Pages that need data show an error whose message names PostgreSQL. A friendly "outside working hours" page is planned, not built.
- If the app restarts while the server is stopped, its first requests fail until the server starts again.
- To work outside the hours, open the server's **Overview** and select **Start**. Stop it again when you are done.

To change the hours, edit the two schedules. The cost for any schedule is the number of hours a month × $0.017, plus the fixed items in section 2.

---

---

## 14. Check the settings, and move old data

1. **Check the settings.** In the API app, open **Development Tools, SSH**, then **Go**, and run:
   ```bash
   cd /home/site/wwwroot && /home/atlas/venv/bin/python scripts/env_check.py --env azure
   ```
   It prints which settings came from Key Vault, by name only, then `azure: OK`.
2. **Move an old SQLite store (once).** Do this only if an earlier version of the app kept `atlas.sqlite3`:
   1. Upload the old `atlas.sqlite3` to `/home/atlas/data/` with Kudu's **Debug console**.
   2. In the SSH console, run:
      ```bash
      cd /home/site/wwwroot && /home/atlas/venv/bin/python scripts/sqlite_to_postgres.py /home/atlas/data/atlas.sqlite3
      ```
   It refuses a database that already holds data. It copies every table, then checks the row counts, every project's ledger hash chain and every document version's SHA-256, and prints "Copy complete and verified".

---

---

## 15. First sign-in, people and permissions

1. **Sign in.** Open `https://aqe-ui-<unique>.azurewebsites.net`. Sign in as the admin, with the password stored in `atlas-admin-password`.
2. **Settings:**
   - enter the model endpoint, model name and key, then select **Test connection**;
   - tick the models people may use;
   - under **Plugins**, grant plugins to roles if needed.
3. **Users, Add user:** username, a temporary password, email, and role (`qe_lead`, `ba`, `developer` or `viewer`).
4. **In each project, Members:** add the people who may see it. Approvals show the approver's name, role and email.
5. **Settings, Gate roles:** choose who may sign gates G0 to G5. Agents never sign.
   **Settings, Features:** choose what each role may use (BA Studio, QE cycle, Skill Studio, MCP, Documents and more), and allow or deny one feature for one member.
6. **MCP:** add remote (HTTP) MCP servers, and grant each tool to roles. stdio servers do not run on the shared server.
   **Jira and Confluence (optional):** add `https://mcp.atlassian.com/v2/mcp` (transport http) and tick "Each member signs in with OAuth". Select **Sign in** (your Atlassian account), then **Connect** to list its tools, and grant them to the roles that use BA Studio. Each member then connects their own Atlassian account from BA Studio; the platform never sees their password and keeps their token encrypted.

**Verify each feature, end to end:**

1. **Both apps up.** The API's health URL is blocked from your browser (403, section 11.5); the UI at `https://aqe-ui-<unique>.azurewebsites.net/login` loads and you can sign in.
2. **Model.** **Settings, Test connection** succeeds.
3. **QE brownfield, with a downloaded result.**
   1. Create a project and attach an existing repository (zip upload or GitHub URL).
   2. Open the project's **QE** page and start the cycle. Sign each gate, G0 to G5, as a named person.
   3. At the end, download the run's evidence from the QE page. It must contain the signed gates and the validator results. Zero executed tests must read `INCONCLUSIVE`, never `PASS`.

   Brownfield needs only Python and Node (the plugin's TypeScript checks). It works as soon as the API is up and `node` is `"ok": true` in `/home/tools/status.json`.
4. **QE greenfield (needs section 12 to be ready).**
   1. Check `/home/tools/status.json`: every tool you plan to use is `"ok": true`.
   2. Create a greenfield project, pick a stack, and run the cycle. The sandbox appears at `/home/atlas/data/projects/<id>/sandbox` (check with `ls` in SSH).
   3. Unit and integration results come from commands run in that sandbox; end-to-end results need Chromium.
   4. If Chromium is not ready (section 12.4), run the end-to-end step on a developer computer and attach the evidence; Azure then shows it.
5. **Document search.** Upload a document and search it; this proves the `vector` extension.

---

## 16. A tour of the UI

The same pages run locally and on Azure. The screenshots are from real local runs in `docs/evidence/`.

| Page | Who | What you do there | Screenshot |
|---|---|---|---|
| `/` | everyone | Landing page: what the platform does, **Sign in** | [dark](evidence/screens/landing-dark.png), [light](evidence/screens/landing-light.png), [phone](evidence/screens/landing-phone.png) |
| `/login` | everyone | Sign in | [login](evidence/22a-login.png) |
| `/projects` | members | Create a project, then attach a repository: a zip upload or a GitHub URL | [list](evidence/05-projects-list.png), [zip](evidence/03-repository-zip.png), [GitHub](evidence/04-repository-github.png) |
| Project, **BA** | BA, QE lead | Requirements documents (BRDs) and Gherkin, then sign gate G1. Every save is a new version | [BA](evidence/screens/project_ba.png), [Gherkin](evidence/08-gherkin-editor.png), [history](evidence/09-document-history.png) |
| Project, **Bugs** and **Feature** | developers | Bug scan findings. Generated changes land on a separate branch, shown as a diff | [scan](evidence/10-bug-scan.png), [diff](evidence/11-feature-diff.png) |
| Project, **QE** | QE lead | Gates G0 to G5, each signed by a named person | [QE](evidence/screens/project_qe.png), [gate 5](evidence/14-qe-gate5.png) |
| Project, **Approvals** and **Governance** | approvers | Pending approvals with the approver's name, role and email; the hash-chained ledger | [approvals](evidence/06b-approvals-page.png), [governance](evidence/19-governance.png) |
| `/skills/studio` | admin, QE lead | Skill Creator Studio: source, kind, plan, approve, generate, test (with **Repair from test failures**), evaluate, publish | [request](evidence/us-51-1-source-kind-request.png), [plan](evidence/us-51-2-plan-draft.png), [published](evidence/us-51-4-published.png), [evaluation](evidence/us-53-1-evaluation.png) |
| `/skills` | everyone | Published skills and their versions | [skills](evidence/screens/skills_list.png) |
| `/agents` | everyone | The governed agents. Each score tile shows `n` and the judge, or why it is blank | [agents](evidence/screens/agents.png) |
| `/mcp` | admin | Add an MCP server, **Connect**, then grant each tool to roles | [connected](evidence/screens/us-55-mcp-connected.png), [granted](evidence/screens/us-55-mcp-granted.png) |
| `/traces` | admin: all; member: own | Trace explorer: runs, span tree, waterfall | not captured yet |
| `/capabilities` | everyone | Every tool, agent, skill, command and workflow, with links | not captured yet |
| `/settings`, `/users`, `/account` | admin; each person | Model, plugins, gate roles, logs; people with role and email; your own password and email | [settings](evidence/06-settings.png), [users](evidence/22b-users.png) |

---

---

## 17. Observability

- **In the app.**
  - Admins see every trace at `/traces`, and download logs on **Settings**: `app-DAY.jsonl` for requests, and `errors-DAY.jsonl` for errors with stack traces.
  - Members see only their own runs.
- **App Service logs.** **Monitoring, Log stream** shows the live output of both processes. Kudu (`https://<app>.scm.azurewebsites.net`) has **Log stream** and **Debug console** too.
- **Application Insights** (optional, billed per GB, see section 2):
  1. Create it in East US 2, in `rg-agentic-qe`.
  2. On the web app, add the settings `OTEL_EXPORTER_OTLP_ENDPOINT` (your collector or Azure Monitor's OTLP endpoint) and `OTEL_SERVICE_NAME=agentic-qe-api`.

---

---

## 18. Update, roll back, back up, stop paying

**Update the app:**
1. Change and test locally: `python scripts/dev.py db`, then `python scripts/dev.py test`.
2. Build the zips and run `azure-local --check` (section 4). Keep the zips: they are your rollback.
3. If the PostgreSQL server is stopped, start it first. Deploy the API zip (section 9.5) and the UI zip (section 11.4), then restart both apps.
4. The Python environment is rebuilt only when `requirements.txt` changed; the UI is rebuilt when its files or `ATLAS_BACKEND_URL` changed; toolchains are installed again only when a pinned version changed.

New tables are added automatically on start.

**Roll back:** deploy the previous zip the same way (`az webapp deploy ... --src-path <old zip> --type zip`) and restart. Keep each release's zips under a dated name, for example `azure_backend-2026-11-14.zip`. Database changes are additive; if one must be undone, use point-in-time restore (below).

**Backup:**
- **PostgreSQL** keeps 7 days of point-in-time restore: open **Settings, Backup and restore**, then **Restore**.
- **The `/home` share** holds workspaces, files and the toolchains: check each app's **Backups** page. The toolchains can always be downloaded again.
- **Key Vault** keeps deleted secrets for 90 days (soft delete).

**Stop paying:**
- Deleting the resource group `rg-agentic-qe` removes everything in it and stops all charges.
- Stopping the web apps does **not** stop the plan's charge (section 2).

---

## 19. Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| Application error page, and **Log stream** says Key Vault access was denied | The API's identity cannot read secrets | Give `aqe-api-<unique>` the role **Key Vault Secrets User** on the vault (section 9.2), then restart |
| Log shows "PostgreSQL ... did not answer within 30 seconds" or a connection timeout | Firewall rule missing, or the server is stopped | Add the API's outbound addresses (section 10); start the server from its **Overview** |
| Log shows `password authentication failed` | Wrong `atlas-database-url` | Fix the secret (section 7.3), percent-encoding special characters, then restart |
| Health answers but the UI shows "cannot reach the API" | `ATLAS_BACKEND_URL` is wrong, or the access restriction blocks the UI | Check the setting, and that every UI outbound address is allowed (section 11.5) |
| The app never starts, and the log shows Oryx or `pip` building | Kudu's build is on | Set `SCM_DO_BUILD_DURING_DEPLOYMENT=false` and `ENABLE_ORYX_BUILD=false`, then deploy the zip again |
| `startup.py` or `startup.js` is not found | Wrong startup command, or a zip made with Explorer or Finder | Use the commands in sections 9.3 and 11.2, and build with `package_azure_kudu.py` |
| The app restarts in a loop during the first start | The first start is longer than the start time limit | Set `WEBSITES_CONTAINER_START_TIME_LIMIT=1800` (sections 9.4 and 11.3) |
| Log shows `[agentic-qe toolchains] <tool>: FAILED: ... mismatch` | The download is not the pinned file (a proxy, or the vendor re-published it) | Nothing was installed. Restart to retry; if it repeats, check the pin in `toolchains.py` against the vendor's checksum file |
| Log shows `[agentic-qe toolchains] <tool>: FAILED: could not download` | The vendor host is not reachable from the app | Check outbound access to the hosts in section 12.1, then restart |
| `chromium: FAILED: ... not root`, or `install-deps` fails | The image does not start as root, or `apt` is unreachable | Section 12.4 (greenfield E2E runs locally; Azure shows the evidence) |
| A greenfield run says a toolchain is missing, though the log said it was installed | The API has not been restarted since the install, or the version is below what the template needs | Restart the API app so `PATH` is rebuilt; check `/home/tools/status.json` and the minimum in `templates/stacks/<id>/stack.json` |
| Sandbox commands cannot find a tool the API can | `clean_sandbox_env` passes only its allowlist | A new tool needs its `*_HOME` variable added to the allowlist in `src/backend/repos/sandbox/env.py` |
| The log shows "no space left", or **Quotas** shows `/home` full | The plan's 10 GB are used | Delete finished projects' sandboxes; see the disk table in section 2 |
| Log shows `extension "vector" is not allow-listed` | `azure.extensions` does not include VECTOR | Section 7.4, then restart |
| The start and stop runbook fails with 403 | The Automation account lacks rights on the server | Assign **Contributor** on the PostgreSQL server to `aa-agentic-qe` (section 13.2) |

---

## 20. Decisions

| # | Decision | State |
|---|---|---|
| A | App Service or Container Apps | App Service B1 (owner, 2026-11-11) |
| B | Entra ID sign-in | Later; built-in accounts for now |
| C | Model provider | The existing endpoint, set on **Settings** |
| E | Region | **East US 2** (owner, 2026-11-11) |
| F | Cost cap | At most **$25 a month**, through the PostgreSQL stop schedule (owner, 2026-11-12). Any change that raises it needs the owner's yes |
| G | Packaging | **No Docker** (owner, 2026-11-14): two zips on the built-in Python 3.12 and Node 22 images, zip deploy through Kudu. Replaces the custom-container packaging of commit 02b55f6; Azure cost unchanged |
| H | Greenfield execution | In each project's sandbox with `clean_sandbox_env`, using the toolchains in `/home/tools` (owner, 2026-11-14) |

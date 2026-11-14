# Azure deployment guide (East US 2)

This is the one guide for deploying Agentic QE Platform to Azure. It covers the price, building the container image, every step in the Azure portal, first sign-in, a tour of the UI, and running, updating and removing it.

The deployment runs on one App Service plan (B1) with **one web app that runs a custom container**, plus PostgreSQL and Key Vault, all in **East US 2**. GitHub Actions builds the image and stores it in GitHub Container Registry (GHCR); Azure only pulls it. No Azure credential is ever stored in GitHub.

**What has been verified, and what has not (2026-11-14):**
- **Verified on a local machine:**
  - the earlier zip packaging starts both processes through their own startup scripts in the web profile against PostgreSQL (`azure-local --check` prints `API health: 200; UI /login: 200`, re-run on 2026-11-14);
  - the full test suite runs against PostgreSQL;
  - Key Vault secrets are loaded at startup.
- **Not yet run:** the container image. `deploy/azure/Dockerfile` and `.github/workflows/container.yml` are written, but the image has not been built (Docker is not installed on the development machine and the workflow has not run), and nothing has run on Azure itself. Check each **Verify** line as you go.
- **No screenshots of the portal yet.** They need a real subscription.
- **Not built yet:** a friendly "database is stopped (outside working hours)" page. While PostgreSQL is stopped, the API answers with a database error (section 13).

---

## Contents

1. [Architecture](#1-architecture)
2. [Monthly cost](#2-monthly-cost-east-us-2)
3. [Before you start](#3-before-you-start)
4. [Build and check the image](#4-build-and-check-the-image)
5. [Resource group](#5-resource-group)
6. [Key Vault](#6-key-vault)
7. [PostgreSQL Flexible Server](#7-postgresql-flexible-server)
8. [Container registry access (GHCR)](#8-container-registry-access-ghcr)
9. [App Service plan](#9-app-service-plan)
10. [The container web app](#10-the-container-web-app)
11. [Database firewall](#11-let-the-app-reach-postgresql)
12. [Lock down the Kudu site](#12-lock-down-the-kudu-site)
13. [Stop PostgreSQL outside working hours (stays under $25)](#13-stop-postgresql-outside-working-hours)
14. [Check the settings, and move old data](#14-check-the-settings-and-move-old-data)
15. [First sign-in, people and permissions](#15-first-sign-in-people-and-permissions)
16. [A tour of the UI](#16-a-tour-of-the-ui)
17. [Observability](#17-observability)
18. [Update, backup, stop paying](#18-update-backup-stop-paying)
19. [Troubleshooting](#19-troubleshooting)
20. [Decisions](#20-decisions)

---

## 1. Architecture

```text
 People ── browser ──▶ App Service B1, one custom container (image from ghcr.io/sarveshtalele/agentic-qe)
                        │   UI (Next.js)  0.0.0.0:3000  ← the only public port (WEBSITES_PORT=3000)
                        │   API (FastAPI + MAF) 127.0.0.1:8000  ← reached by the UI over loopback, never exposed
                        │        ├─▶ model endpoint
                        │        ├─▶ PostgreSQL Flexible Server (Burstable B1ms, pgvector)
                        │        ├─▶ Key Vault: admin password, secret key, database URL (read at startup)
                        │        ├─▶ /home share: workspaces and files
                        │        ├─▶ Chromium, Node 22, JDK 21, .NET 8, Go 1.23 inside the image (generated apps are built and tested there)
                        │        └─▶ Application Insights (optional, OpenTelemetry)
 GitHub Actions ── builds and pushes the image ──▶ GHCR  (App Service pulls it; GitHub never connects to Azure)
```

| Part | Choice | Why |
|---|---|---|
| Compute | One Linux App Service plan **B1**, with one web app running the custom container (UI and API as two processes) | The cheapest plan that runs both. The container carries the browsers and compilers the greenfield runs need |
| Database | **PostgreSQL Flexible Server, Burstable B1ms**, 32 GiB, version 17 (16 also works), with the `vector` extension allow-listed | The only database the app supports. It gives point-in-time restore, many writers, and pgvector for document search |
| Secrets | **Key Vault Standard**, read by the API with its managed identity (`ATLAS_KEY_VAULT_URL`) | No secret in app settings |
| Image | `deploy/azure/Dockerfile`, built by `.github/workflows/container.yml`, stored in GHCR | Free for this use, no Azure container registry to pay for |
| Sign-in | Built-in accounts. The first admin's password comes from Key Vault | Works without an Entra app registration |
| Load | **One greenfield run at a time** (the backend enforces it), and at most 5 sandbox jobs (`ATLAS_MAX_SANDBOXES`) | B1 has 1.75 GB of memory, which Chromium, a JDK and the app must share |

**Security limit.** Repository code runs on the same machine as the API until isolated sandbox jobs exist. Admit only people you trust.

---

## 2. Monthly cost (East US 2)

Prices are pay-as-you-go for 730 hours a month, in US dollars and Indian rupees. Both price lists were read live from the Azure Retail Prices API (`prices.azure.com`, `currencyCode=USD` and `currencyCode=INR`) on **2026-11-12 at 07:43 UTC**. They **exclude taxes**: for example, 18% GST applies when you are billed in India. Prices change, so check them before you create anything (the command is at the end of this section).

The proposal workbook `docs/proposal/Agentic_QE_Azure_Proposal.xlsx` has the same figures as live formulas. Its sheets are: cost per line, assumptions you can change, the raw API rows, architecture, deployment steps, UI guide, and review gaps. The same sheets are also saved as plain CSVs in `docs/proposal/csv/`.

### The standard deployment: under the $25 cap

PostgreSQL compute is billed only while the server runs. The standard stops it outside working hours: it runs 12 hours a day on 22 weekdays, which is 264 hours a month (section 13). Its storage is still billed while it is stopped.

| Resource | Meter | Price (USD / INR) | Per month (USD) | Per month (INR) |
|---|---|---|---|---|
| App Service plan B1, Linux (both web apps share it) | B1 | $0.017 / ₹1.6189 an hour | **$12.41** | **₹1,181.80** |
| PostgreSQL B1ms compute, 264 hours | B1MS | $0.017 / ₹1.6189 an hour | **$4.49** | **₹427.39** |
| PostgreSQL storage, 32 GiB | Storage Data Stored | $0.115 / ₹10.9513 per GB a month | **$3.68** | **₹350.44** |
| PostgreSQL backups, 7 days | Backup Storage LRS | Included up to the provisioned size; above it $0.095 / ₹9.0467 per GB | **$0** | **₹0** |
| Key Vault Standard | Operations | $0.03 / ₹2.8569 per 10,000 (the API reads 3 secrets at each start) | **under $0.01** | **₹0.03** |
| Azure Automation (the start and stop jobs) | Basic Runtime | First 500 minutes a month free, then $0.002 / ₹0.1905 a minute; about 44 minutes are used | **$0** | **₹0** |
| **Total** | | | **$20.58** | **₹1,959.66** |

That is $246.96 (₹23,515.92) a year before taxes. The container change adds nothing to this table: the plan and the PostgreSQL tier are the ones already listed, GitHub Container Registry is not an Azure resource, and the Blob Storage line (desktop installers, $0.04 a month) is gone because the installers were removed. For a **private** GHCR package, the GitHub plan's included storage applies (500 MB on Free, 2 GB on Pro and Team); the image is about 2 GB compressed, and beyond the quota GitHub bills about $0.25 per GB a month, so the worst case is about $0.50 a month, which still leaves the total under $25. Making the package public costs nothing, but then anyone can pull the image (it holds code and prompts, no secrets). Check your GitHub plan's quota before choosing.

### Other choices

| Choice | Per month (USD) | Per month (INR) | Within the $25 cap? |
|---|---|---|---|
| PostgreSQL 8 hours on weekdays (176 hours) | $19.12 | ₹1,820.78 | Yes |
| PostgreSQL always on (730 hours) | $28.54 | ₹2,717.65 | No |
| Upgrade: App Service plan **B2** (2 cores, 3.5 GB) at $0.034 / ₹3.2378 an hour, PostgreSQL 12 hours on weekdays | $33.03 | ₹3,145.04 | No, needs the owner's yes |
| Upgrade: App Service plan **P0v3** at $0.0775 / ₹7.3802 an hour, PostgreSQL **B2s** at $0.068 / ₹6.4756 an hour, always on | $109.93 | ₹10,468.79 | No, needs the owner's yes |

### Costs that depend on use

- **Outbound data.** The first 100 GB a month are free. After that, $0.087 (₹8.2849) per GB with Microsoft network routing. Image pulls from GHCR are inbound to Azure and free.
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

## 3. Before you start

You need:
- **An Azure subscription** where you can create resources.
- **This repository** on your computer, set up with `python scripts/dev.py setup` (see `README.md`).
- **PostgreSQL 16 or newer installed locally.** It is needed only for the local check in section 4.
- **Docker** (optional): only to build and try the image on your own computer. CI builds the real one.
- **Two random values:** one for the secret key and one for the admin password. Run this twice and keep both values somewhere safe:
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
| Web app (container) | `aqe-<unique>` |
| Automation account | `aa-agentic-qe` |

`deploy/environments/azure.appsettings.example` lists every app setting, with no values.

---

## 4. Build and check the image

The image is built by GitHub Actions, not on your computer. `.github/workflows/container.yml` runs on every push to `feature/maf-harness-platform` (never on `main`), and pushes `ghcr.io/sarveshtalele/agentic-qe` with two tags: the full commit SHA (`sha-<40 hex>`, use this one in Azure so an update is a visible change) and the branch (`feature-maf-harness-platform`, moves with each push). It signs in to GHCR with the workflow's built-in `GITHUB_TOKEN` (permission `packages: write`); the file holds no secret.

**What is in the image** (`deploy/azure/Dockerfile`):
- base `mcr.microsoft.com/playwright/python:v1.65.0-noble` (Ubuntu 24.04, Python 3.12, Chromium, Firefox, WebKit; the tag matches the Playwright version in `requirements.txt`);
- Node 22.12.0, JDK 21 (Ubuntu package), .NET SDK 8 (Ubuntu package) and Go 1.23.4;
- the backend and `requirements.txt` in `/opt/venv`, and the Next.js UI built into a standalone server in `/opt/ui`;
- the user `pwuser` (not root). `/home/atlas` is the persistent App Service `/home` share at run time.
- **Size:** about 5 GB uncompressed and about 2 GB compressed in GHCR (an estimate: the image has not been built yet). The B1 plan has 10 GB of disk for images.

**Processes and ports** are the same as the zip deployment, in one container (`deploy/azure/container_start.py`): the API on `127.0.0.1:8000` and the UI on `0.0.0.0:3000`. The UI proxies `/api/*` to the API over loopback, so `ATLAS_BACKEND_URL` is not set in Azure. The container stops if either process exits, so App Service restarts it.

**Check on your computer (optional, needs Docker):**

```bash
docker build -f deploy/azure/Dockerfile -t agentic-qe-local .
docker run --rm -p 3000:3000 -e ATLAS_ADMIN_USERNAME=<name> -e ATLAS_ADMIN_PASSWORD=<12+ chars> -e ATLAS_SECRET_KEY=<random> -e ATLAS_DATABASE_URL=<local PostgreSQL URL> agentic-qe-local
curl http://127.0.0.1:3000/api/health
```

**Check without Docker:** `python scripts/dev.py azure-local --check` runs the same two processes from the zip packaging against a local PostgreSQL. It prints `API health: 200; UI /login: 200`. It does not test the image itself.

**Common mistakes:**
- **Using the moving branch tag in Azure.** Restarting then pulls whatever is newest. Pin the `sha-` tag.
- **A missing pull credential for a private package** (section 8). The log says `unauthorized`.

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
   3. In section 10, set `ATLAS_KEY_VAULT_SECRETS` to `atlas-admin-password-hash,atlas-password-pepper,atlas-secret-key,atlas-database-url,atlas-storage-url`.
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
     - leave **Allow public access from any Azure service within Azure to this server** turned **off**. The API's addresses are added in section 11.
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

## 8. Container registry access (GHCR)

The image lives in GitHub Container Registry, free for this use. App Service pulls it; nothing is pushed from Azure.

1. **First build.** Push to `feature/maf-harness-platform` (or run the **Container image** workflow by hand) and wait for it to finish. The package `agentic-qe` then appears under your GitHub profile, **Packages**. Note the tag `sha-<40 hex>` of the build you want to deploy.
2. **Choose public or private.** In the package's **Package settings, Danger zone**:
   - **Public:** App Service needs no credential. Anyone can pull the image (code, prompts and templates, no secrets). Free.
   - **Private (recommended):** continue below. Counts against your GitHub plan's package storage (section 2).
3. **Private only: create a pull credential.** The workflow's `GITHUB_TOKEN` cannot be reused by Azure, so make a separate one:
   1. In GitHub, open **Settings, Developer settings, Personal access tokens, Fine-grained tokens, Generate new token**.
   2. Set **Expiration** to 90 days (put the renewal date in your calendar), and **Resource owner** to your account.
   3. Fine-grained tokens cannot yet be granted `read:packages`. If **Permissions** does not offer **Packages**, use a **classic** token with only the `read:packages` scope instead. Never give it `write:packages`, `repo` or any other scope.
   4. Copy the token once. You will paste it into the Azure portal in section 10, and nowhere else: never into this repository, a script, a URL or a command line.
4. **Revoke on leaving.** When someone who made the token leaves, or the token may have leaked, delete it in GitHub and make a new one (section 10 step 4).

**Verify:** the package lists the `sha-...` tag, and its **Visibility** is what you chose.

---

## 9. App Service plan

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

## 10. The container web app

1. **Create the app.** Search **App Services**, then select **Create, Web App**.
   - **Basics** tab:
     - **Resource group:** `rg-agentic-qe`;
     - **Name:** `aqe-<unique>`;
     - **Publish:** **Container**;
     - **Operating System:** Linux;
     - **Region:** East US 2;
     - **Linux Plan:** `plan-agentic-qe` (B1).
   - **Container** tab:
     - **Image Source:** **Other container registries**;
     - **Access Type:** **Public** or **Private** (section 8);
     - **Registry server URL:** `https://ghcr.io`;
     - **Image and tag:** `sarveshtalele/agentic-qe:sha-<40 hex>`;
     - private only: **Username** your GitHub username, **Password** the token from section 8 (typed into the portal; the portal stores it as an app setting, `DOCKER_REGISTRY_SERVER_PASSWORD`, which only people with access to the app can read);
     - **Startup command:** leave **empty**. The image's entrypoint (`python3 /app/container_start.py`) starts both processes. If you set one, use exactly `python3 /app/container_start.py`.
   - Select **Review + create**, then **Create**.
   - **Switching an existing B1 web app instead:** open it, **Deployment, Deployment Center**, set **Source** to **Container registry** with the same values, then **Save**. App settings from the old zip deployment (`ATLAS_BACKEND_URL`, `ATLAS_DOWNLOADS_URL`, `SCM_DO_BUILD_DURING_DEPLOYMENT`, `ENABLE_ORYX_BUILD`) are no longer used: delete them, and clear the old **Startup Command**.
2. **Turn on its identity, and let it read the vault.**
   1. In the app, open **Settings, Identity**. On the **System assigned** tab, set **Status** to **On**, then **Save** and **Yes**.
   2. In the vault, open **Access control (IAM)**, then **Add, Add role assignment**.
   3. Choose the role **Key Vault Secrets User**, then **Next**.
   4. Choose **Managed identity**, then **Select members**, pick **App Service** and `aqe-<unique>`.
   5. Select **Review + assign**.
3. **General settings.** Open **Settings, Configuration, General settings**: **Always on:** On; **HTTPS Only:** On; **Health check path** (optional): `/api/health`. Select **Save**.
4. **App settings.** Open **Settings, Environment variables, App settings**. Select **+ Add** for each row below, then **Apply** and **Confirm**.

   | Name | Value |
   |---|---|
   | `WEBSITES_PORT` | `3000`. The container listens on 3000 (UI); the API stays on loopback 8000 |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true`, so `/home` (workspaces and files) survives restarts |
   | `WEBSITES_CONTAINER_START_TIME_LIMIT` | `600`. The first start loads secrets and creates tables |
   | `ATLAS_KEY_VAULT_URL` | `https://kv-agentic-qe-<unique>.vault.azure.net`. At startup the API reads `atlas-admin-password`, `atlas-secret-key` and `atlas-database-url` from it. Do **not** add those three as app settings |
   | `ATLAS_PROFILE` | `web` (already the image default) |
   | `ATLAS_DATA_DIR` | `/home/atlas/data` (already the image default) |
   | `ATLAS_ADMIN_USERNAME` | the first admin's username |
   | `ATLAS_ADMIN_EMAIL` | the admin's email (optional) |
   | `ATLAS_ALLOWED_HOSTS` | `aqe-<unique>.azurewebsites.net` |
   | `ATLAS_ALLOWED_ORIGINS` | `https://aqe-<unique>.azurewebsites.net` |
   | `ATLAS_MAX_SANDBOXES` | `5` (already the image default) |
   | `ATLAS_INSTALL_EVALS` | not used by the image. RAGAS is only installed if you add `requirements-evals.txt` to the Dockerfile |
   | `DOCKER_REGISTRY_SERVER_URL`, `DOCKER_REGISTRY_SERVER_USERNAME`, `DOCKER_REGISTRY_SERVER_PASSWORD` | private package only. The portal sets them from step 1; the password is the GitHub token and is never put in the repository |

   **One greenfield run at a time.** The backend refuses a second greenfield build while one runs (Chromium, a JDK or .NET build and the app share 1.75 GB). Do not add a second instance: the plan is B1 with one instance, and running workflows live in the API process.
5. **Watch the first start.** Open **Monitoring, Log stream**. App Service pulls the image first (a few minutes for about 2 GB), then the log shows `API on 127.0.0.1:8000, UI on 0.0.0.0:3000`.
   - Until section 11 is done, the log shows a PostgreSQL connection error. That is expected.
   - `unauthorized` or `denied` while pulling: the pull credential is wrong or expired (section 8).
   - If Key Vault cannot be read, the log says so and how to fix it, for example "Give the web app's identity the role Key Vault Secrets User".
   - The container exits if either process exits, and App Service restarts it. Repeated restarts mean the API or UI is crashing: read the lines above the exit.

---

## 11. Let the app reach PostgreSQL

1. **Copy the app's outbound addresses.** In the web app, open **Settings, Properties**. Copy every address under **Outbound IP addresses** and **Additional Outbound IP addresses**.
2. **Add them to the PostgreSQL firewall.**
   1. In the PostgreSQL server, open **Settings, Networking**.
   2. Under **Firewall rules**, add one rule per address, with that address as both **Start IP address** and **End IP address**.
   3. Select **Save**.
3. **Restart** the web app.

**Verify:** `https://aqe-<unique>.azurewebsites.net/api/health` returns `"status": "ok"`.

---

## 12. Lock down the Kudu site

The public site is the UI. The API is not reachable from outside (it listens on loopback only), and every API path still requires sign-in (`core/auth.py`). What is left to restrict is the Kudu site, which can read and change the running container.

1. In the web app, open **Settings, Networking**. Under **Public network access**, open **Access restriction**.
2. On the **Advanced tool site** tab, allow only your own IP address, and leave unmatched traffic **Denied**. Select **Save**.
3. Leave the **Main site** tab open to everyone (people sign in with their own accounts).

**Verify:** `https://aqe-<unique>.azurewebsites.net` shows the sign-in page, `https://aqe-<unique>.azurewebsites.net/api/health` returns `"status": "ok"`, and `https://aqe-<unique>.scm.azurewebsites.net` answers 403 from another network.

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

## 14. Check the settings, and move old data

1. **Check the settings.** In the web app, open **Development Tools, SSH**, then **Go**, and run:
   ```bash
   cd /app && python3 scripts/env_check.py --env azure
   ```
   It prints which settings came from Key Vault, by name only, then `azure: OK`.
2. **Move an old SQLite store (once).** Do this only if an earlier version of the app kept `atlas.sqlite3`:
   1. Upload the old `atlas.sqlite3` to `/home/atlas/data/` with Kudu's **Debug console**.
   2. In the SSH console, run:
      ```bash
      cd /app && python3 scripts/sqlite_to_postgres.py /home/atlas/data/atlas.sqlite3
      ```
   It refuses a database that already holds data. It copies every table, then checks the row counts, every project's ledger hash chain and every document version's SHA-256, and prints "Copy complete and verified".

---

## 15. First sign-in, people and permissions

1. **Sign in.** Open `https://aqe-<unique>.azurewebsites.net`. Sign in as the admin, with the password stored in `atlas-admin-password`.
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

**Verify, end to end:**
1. Create a project and attach a repository.
2. Open the project's **QE** page and start the cycle.

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

## 17. Observability

- **In the app.**
  - Admins see every trace at `/traces`, and download logs on **Settings**: `app-DAY.jsonl` for requests, and `errors-DAY.jsonl` for errors with stack traces.
  - Members see only their own runs.
- **App Service logs.** **Monitoring, Log stream** shows the live output of both processes. Kudu (`https://<app>.scm.azurewebsites.net`) has **Log stream** and **Debug console** too.
- **Application Insights** (optional, billed per GB, see section 2):
  1. Create it in East US 2, in `rg-agentic-qe`.
  2. On the web app, add the settings `OTEL_EXPORTER_OTLP_ENDPOINT` (your collector or Azure Monitor's OTLP endpoint) and `OTEL_SERVICE_NAME=agentic-qe-api`.

---

## 18. Update, backup, stop paying

**Update the app:**
1. Change and test locally: `python scripts/dev.py db`, then `python scripts/dev.py test`.
2. Push to `feature/maf-harness-platform`. The **Container image** workflow builds and pushes the image. Wait for it to turn green.
3. In the web app, open **Deployment, Deployment Center**, change the **Image and tag** to the new `sha-<40 hex>`, then **Save**. App Service pulls the image and restarts. If the PostgreSQL server is stopped, start it first.
4. **Roll back** by setting the previous `sha-` tag the same way.

New tables are added automatically on start.

**Backup:**
- **PostgreSQL** keeps 7 days of point-in-time restore: open **Settings, Backup and restore**, then **Restore**.
- **Images** stay in GHCR under their `sha-` tags, so any earlier build can be redeployed (older untagged versions are removed by GitHub's package retention, not by this guide).
- **The `/home` share** holds workspaces and files: check the web app's **Backups** page.
- **Key Vault** keeps deleted secrets for 90 days (soft delete).

**Stop paying:**
- Deleting the resource group `rg-agentic-qe` removes everything in it and stops all charges.
- Stopping the web app does **not** stop the plan's charge (section 2).

---

## 19. Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| Application error page, and **Log stream** says Key Vault access was denied | The API's identity cannot read secrets | Give `aqe-<unique>` the role **Key Vault Secrets User** on the vault (section 10.2), then restart |
| Log shows "PostgreSQL ... did not answer within 30 seconds" or a connection timeout | Firewall rule missing, or the server is stopped | Add the app's outbound addresses (section 11); start the server from its **Overview** |
| Log shows `password authentication failed` | Wrong `atlas-database-url` | Fix the secret (section 7.3), percent-encoding special characters, then restart |
| Log shows `unauthorized` or `denied` while pulling the image | The GHCR pull credential is missing, expired or has too few rights | Make a new token with `read:packages` (section 8) and update `DOCKER_REGISTRY_SERVER_PASSWORD`; or make the package public |
| The app restarts in a loop, and the log says the container did not answer on port 3000 | `WEBSITES_PORT` is not `3000`, or the start limit is too short | Set `WEBSITES_PORT=3000` and `WEBSITES_CONTAINER_START_TIME_LIMIT=600` (section 10.4) |
| The UI shows "cannot reach the API" | The API process crashed inside the container (the container exits and restarts when either process stops) | Read **Log stream** above the exit line: usually the database URL, Key Vault, or a missing setting |
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
| G | Packaging | One custom container on the existing B1 plan, image in GHCR (QE v2 step 10, `docs/QE_V2_PLAN.md` section 8). Replaces the two zips; Azure cost unchanged |

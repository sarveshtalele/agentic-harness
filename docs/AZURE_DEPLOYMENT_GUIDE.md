# Azure deployment guide (East US 2)

This is the one guide for deploying Agentic QE Platform to Azure. It covers the price, packaging the app on your own machine (macOS, Linux or Windows), every step in the Azure portal, first sign-in, a tour of the UI, and running, updating and removing it.

The deployment runs on one App Service plan with two web apps, plus PostgreSQL, Blob Storage and Key Vault, all in **East US 2**. GitHub never connects to Azure. You build two zips on your computer and upload them in the browser.

**What has been verified, and what has not (2026-11-12):**
- **Verified on a local machine:**
  - both zips start through their own startup scripts in the web profile against PostgreSQL (`azure-local --check` prints `API health: 200; UI /login: 200`);
  - the full test suite runs against PostgreSQL;
  - Key Vault secrets are loaded at startup;
  - the login page reads the `downloads` container's `latest.json`.
- **Verified in GitHub Actions:** the macOS DMGs (Apple silicon and Intel) and the Windows MSI are built on every change to the desktop app, and tag `v0.1.0` publishes a GitHub Release.
- **Not yet run on Azure itself.** The portal steps below follow the portal as it is today, but no one has run them end to end in a subscription yet. Check each **Verify** line as you go.
- **No screenshots of the portal yet.** They need a real subscription.
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
8. [Storage account and desktop downloads](#8-storage-account-and-desktop-downloads)
9. [App Service plan](#9-app-service-plan)
10. [API web app](#10-api-web-app)
11. [Database firewall](#11-let-the-api-reach-postgresql)
12. [UI web app, and lock the API to the UI](#12-ui-web-app-and-lock-the-api-to-the-ui)
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
 People ── browser ──▶ UI web app (Next.js) ──▶ API web app (FastAPI + MAF) ──▶ model endpoint
                                 │                       │
                                 │                       ├─▶ PostgreSQL Flexible Server (Burstable B1ms)
                                 │                       ├─▶ Key Vault: admin password, secret key, database URL (read at startup)
                                 │                       ├─▶ /home share: workspaces and files
                                 │                       └─▶ Application Insights (optional, OpenTelemetry)
                                 └─▶ landing page reads the Blob "downloads" container (desktop installers)

 Each person (optional) ── desktop app ──▶ its own API, UI and local PostgreSQL on 127.0.0.1
```

| Part | Choice | Why |
|---|---|---|
| Compute | One Linux App Service plan **B1**, with two web apps (API and UI) | The cheapest plan that runs both |
| Database | **PostgreSQL Flexible Server, Burstable B1ms**, 32 GiB, version 17 (16 also works) | The only database the app supports. It gives point-in-time restore and many writers |
| Secrets | **Key Vault Standard**, read by the API with its managed identity (`ATLAS_KEY_VAULT_URL`) | No secret in app settings |
| Files | **Storage account, Standard LRS, Hot**, with a `downloads` container | Desktop installers for the landing page. Documents and evidence stay on the App Service `/home` share for now |
| Sign-in | Built-in accounts. The first admin's password comes from Key Vault | Works without an Entra app registration |
| Harness | Web profile: every feature, with at most 5 sandbox jobs at once (`ATLAS_MAX_SANDBOXES`). stdio MCP servers, `npx` installs and plugin installs run only in the desktop app | Safety on a shared server |

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
| Blob Storage, Hot LRS (installers, about 2 GB) | Hot LRS Data Stored, writes, reads | $0.0184 / ₹1.7522 per GB a month; writes $0.05 / ₹4.7614 and reads $0.004 / ₹0.3809 per 10,000 | **$0.04** | **₹3.59** |
| Key Vault Standard | Operations | $0.03 / ₹2.8569 per 10,000 (the API reads 3 secrets at each start) | **under $0.01** | **₹0.03** |
| Azure Automation (the start and stop jobs) | Basic Runtime | First 500 minutes a month free, then $0.002 / ₹0.1905 a minute; about 44 minutes are used | **$0** | **₹0** |
| **Total** | | | **$20.62** | **₹1,963.25** |

That is $247.39 (₹23,558.96) a year before taxes.

### Other choices

| Choice | Per month (USD) | Per month (INR) | Within the $25 cap? |
|---|---|---|---|
| PostgreSQL 8 hours on weekdays (176 hours) | $19.12 | ₹1,820.78 | Yes |
| PostgreSQL always on (730 hours) | $28.54 | ₹2,717.65 | No |
| Upgrade: App Service plan **B2** (2 cores, 3.5 GB) at $0.034 / ₹3.2378 an hour, PostgreSQL 12 hours on weekdays | $33.03 | ₹3,145.04 | No, needs the owner's yes |
| Upgrade: App Service plan **P0v3** at $0.0775 / ₹7.3802 an hour, PostgreSQL **B2s** at $0.068 / ₹6.4756 an hour, always on | $109.93 | ₹10,468.79 | No, needs the owner's yes |

### Costs that depend on use

- **Outbound data.** The first 100 GB a month are free. After that, $0.087 (₹8.2849) per GB with Microsoft network routing. A desktop installer download is 164 to 195 MB (release v0.1.0), so about 500 downloads a month stay inside the free 100 GB.
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
- **Two random values:** one for the secret key and one for the admin password. Run this twice and keep both values somewhere safe:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

**Names used in this guide.** Replace `<unique>` with a short tag of your own, for example your initials and a number. Web app, vault, server and storage names must be unique across all of Azure.

| Resource | Name |
|---|---|
| Resource group | `rg-agentic-qe` |
| Key Vault | `kv-agentic-qe-<unique>` |
| PostgreSQL server | `pg-agentic-qe-<unique>` |
| Storage account | `stagenticqe<unique>` (lowercase letters and digits only) |
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
  - `dist/azure_backend.zip`: the API. It holds `startup.py`, `startup.sh`, `.deployment`, `web.config`, `requirements.txt`, the backend code, prompts, templates, skills and evals.
  - `dist/azure_frontend.zip`: the UI. It holds `startup.js`, `startup.sh`, `.deployment`, `web.config` and the Next.js source.
- **The zips are built for the Linux App Service:**
  - paths use forward slashes;
  - startup scripts keep LF line endings;
  - only files Git tracks or would track are included, so `.env`, `data/` and build folders are never in a zip;
  - `.deployment` turns Kudu's build off, so Kudu only unzips; the startup script builds once on first start.
- **`azure-local --check`** unzips both packages into `data/azure-local`, starts each one through its own startup script in the web profile with a local PostgreSQL, and checks both.

**Verify:**
- the check prints `API health: 200; UI /login: 200`;
- the top level of the backend zip holds `.deployment`, `requirements.txt`, `startup.py`, `startup.sh` and `web.config`:
  ```bash
  python -c "import zipfile; print(sorted(n for n in zipfile.ZipFile('dist/azure_backend.zip').namelist() if '/' not in n))"
  ```

**Common mistakes:**
- **Zipping with Explorer** (**Send to, Compressed folder**) or Finder. Those zips use backslashes or include build folders, and the app does not start. Always use the script.
- **The wrong runtime stack.** The API is Python 3.12; the UI is Node 20 LTS.
- **A missing startup command** (sections 10 and 12).
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
   3. In section 10, set `ATLAS_KEY_VAULT_SECRETS` to `atlas-admin-password-hash,atlas-password-pepper,atlas-secret-key,atlas-database-url,atlas-storage-url`.
   Optional settings: `ATLAS_SCRYPT_N` (password hashing cost; raising it rehashes each account at its next sign-in), `ATLAS_BREACHED_PASSWORDS_FILE` (a list of breached passwords, one per line), `ATLAS_DESKTOP_SESSION_DAYS` (how long a desktop sign-in lasts, 7 by default).

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

The API creates its tables on its first start (from `backend/migrations/postgres/`, each applied once, under a lock).

**Verify:** the server's **Overview** shows **Status: Ready**, and **Settings, Databases** lists `agentic_qe`.

---

## 8. Storage account and desktop downloads

1. **Create the account.** Search **Storage accounts**, then select **Create**.
   - **Basics** tab:
     - **Resource group:** `rg-agentic-qe`;
     - **Storage account name:** `stagenticqe<unique>`;
     - **Region:** East US 2;
     - **Primary service:** Azure Blob Storage or Azure Data Lake Storage Gen 2;
     - **Performance:** Standard;
     - **Redundancy:** Locally-redundant storage (LRS).
   - **Data protection** tab: turn on **Enable versioning for blobs**, and **Enable soft delete for blobs** with 7 days.
   - Select **Review + create**, then **Create**.
2. **Allow anonymous read on the account.** Open **Settings, Configuration**, set **Allow Blob anonymous access** to **Enabled**, then **Save**. This only allows it; each container still decides for itself.
3. **Create the `downloads` container.**
   1. Open **Data storage, Containers**, then **+ Container**.
   2. Set **Name** to `downloads`.
   3. Set **Anonymous access level** to **Blob (anonymous read access for blobs only)**. Never choose **Container**, which would let anyone list every file.
   4. Select **Create**.
4. **Get the installers.**
   1. Open the GitHub Release on the repository's **Releases** page, for example **v0.1.0**.
   2. Download the two DMGs (Apple silicon and Intel), the macOS zips, the MSI and `latest.json`.
5. **Upload them.**
   1. Open the `downloads` container, then select **Upload**.
   2. Add all the downloaded files and tick **Overwrite if files already exist**.
   3. Under **Advanced**, keep **Blob type: Block blob**, then select **Upload**.
   4. Open `latest.json`, select **Properties**, set **Cache-Control** to `no-cache`, then **Save**. Without this, browsers can keep showing the old version for a while.
   5. Copy the container URL from the container's **Properties**, for example `https://stagenticqe<unique>.blob.core.windows.net/downloads`. It is needed in section 12.

**Verify:** `<container URL>/latest.json` opens in a private browser window.

The installers are not signed yet. On macOS, open the app the first time with right-click, then **Open**. On Windows, SmartScreen warns: choose **More info**, then **Run anyway**.

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

## 10. API web app

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
   - **HTTPS Only:** On.

   Select **Save**.
4. **App settings.** Open **Settings, Environment variables, App settings**. Select **+ Add** for each row below, then **Apply** and **Confirm**.

   | Name | Value |
   |---|---|
   | `ATLAS_KEY_VAULT_URL` | `https://kv-agentic-qe-<unique>.vault.azure.net`. At startup the API reads `atlas-admin-password`, `atlas-secret-key` and `atlas-database-url` from it. Do **not** add those three as app settings |
   | `ATLAS_PROFILE` | `web` |
   | `ATLAS_DATA_DIR` | `/home/atlas/data` (workspaces and files) |
   | `ATLAS_ADMIN_USERNAME` | the first admin's username |
   | `ATLAS_ADMIN_EMAIL` | the admin's email (optional) |
   | `ATLAS_ALLOWED_HOSTS` | `aqe-api-<unique>.azurewebsites.net` |
   | `ATLAS_ALLOWED_ORIGINS` | `https://aqe-ui-<unique>.azurewebsites.net` |
   | `ATLAS_MAX_SANDBOXES` | `5` |
   | `ATLAS_INSTALL_EVALS` | `1` to install RAGAS on first start (optional; it adds a few minutes) |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
   | `WEBSITES_PORT` | `8000` |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` |
   | `ENABLE_ORYX_BUILD` | `false` |

5. **Deploy the zip.**
   1. Open `https://aqe-api-<unique>.scm.azurewebsites.net/ZipDeployUI` in your browser.
   2. Drag `dist/azure_backend.zip` onto the page, and wait until it finishes.
   3. In the app's **Overview**, select **Restart**.
6. **Watch the first start.** Open **Monitoring, Log stream**. The first start takes several minutes while `startup.py` builds the Python environment.
   - It shows "Environment built", then "Starting API on port 8000".
   - Until section 11 is done, the log shows a PostgreSQL connection error. That is expected.
   - If Key Vault cannot be read, the log says so and how to fix it, for example "Give the web app's identity the role Key Vault Secrets User".

---

## 11. Let the API reach PostgreSQL

1. **Copy the API's outbound addresses.** In the **API** app, open **Settings, Properties**. Copy every address under **Outbound IP addresses** and **Additional Outbound IP addresses**.
2. **Add them to the PostgreSQL firewall.**
   1. In the PostgreSQL server, open **Settings, Networking**.
   2. Under **Firewall rules**, add one rule per address, with that address as both **Start IP address** and **End IP address**.
   3. Select **Save**.
3. **Restart** the API app.

**Verify:** `https://aqe-api-<unique>.azurewebsites.net/api/health` returns `"status": "ok"`.

---

## 12. UI web app, and lock the API to the UI

1. **Create the UI app.** Select **Create, Web App**:
   - **Resource group:** `rg-agentic-qe`;
   - **Name:** `aqe-ui-<unique>`;
   - **Publish:** Code;
   - **Runtime stack:** Node 20 LTS;
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
   | `ATLAS_BACKEND_URL` | `https://aqe-api-<unique>.azurewebsites.net` |
   | `ATLAS_DOWNLOADS_URL` | the `downloads` container URL from section 8, with no trailing slash |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
   | `WEBSITES_PORT` | `3000` |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` (`startup.js` runs `npm ci` and the build itself, on local disk) |
   | `ENABLE_ORYX_BUILD` | `false` |

4. **Deploy the zip.** Open `https://aqe-ui-<unique>.scm.azurewebsites.net/ZipDeployUI`, drag `dist/azure_frontend.zip` onto it, then **Restart** the app.

   **Verify:** **Log stream** ends with "Starting UI on port 3000", and `https://aqe-ui-<unique>.azurewebsites.net` shows the landing page with the desktop downloads.
5. **Lock the API to the UI.**
   1. Copy the **UI** app's outbound addresses, the same way as in section 11.
   2. In the **API** app, open **Settings, Networking**. Under **Public network access**, open **Access restriction**.
   3. On the **Main site** tab:
      - set **Unmatched rule action** to **Deny**;
      - add one **Allow** rule per UI address.
   4. On the **Advanced tool site** tab, allow only your own IP address. You need it to reach Kudu for deployments.
   5. Select **Save**.

   **Verify:** the API health URL now answers **403** in your browser, and the UI still works.

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
- The API cannot reach the database. Pages that need data show an error whose message names PostgreSQL. A friendly "outside working hours" page is planned, not built.
- If the API restarts while the server is stopped, its first requests fail until the server starts again.
- To work outside the hours, open the server's **Overview** and select **Start**. Stop it again when you are done.

To change the hours, edit the two schedules. The cost for any schedule is the number of hours a month × $0.017, plus the fixed items in section 2.

---

## 14. Check the settings, and move old data

1. **Check the settings.** In the **API** app, open **Development Tools, SSH**, then **Go**, and run:
   ```bash
   python /home/site/wwwroot/scripts/env_check.py --env azure
   ```
   It prints which settings came from Key Vault, by name only, then `azure: OK`.
2. **Move an old SQLite store (once).** Do this only if an earlier version of the app kept `atlas.sqlite3`:
   1. Upload the old `atlas.sqlite3` to `/home/atlas/data/` with Kudu's **Debug console**.
   2. In the SSH console, run:
      ```bash
      cd /home/site/wwwroot && python scripts/sqlite_to_postgres.py /home/atlas/data/atlas.sqlite3
      ```
   It refuses a database that already holds data. It copies every table, then checks the row counts, every project's ledger hash chain and every document version's SHA-256, and prints "Copy complete and verified".

---

## 15. First sign-in, people and permissions

1. **Sign in.** Open `https://aqe-ui-<unique>.azurewebsites.net`. The landing page has **Sign in** and the desktop downloads. Sign in as the admin, with the password stored in `atlas-admin-password`.
2. **Settings:**
   - enter the model endpoint, model name and key, then select **Test connection**;
   - tick the models people may use;
   - under **Plugins**, grant plugins to roles if needed.
3. **Users, Add user:** username, a temporary password, email, and role (`qe_lead`, `ba`, `developer` or `viewer`).
4. **In each project, Members:** add the people who may see it. Approvals show the approver's name, role and email.
5. **Settings, Gate roles:** choose who may sign gates G0 to G5. Agents never sign.
   **Settings, Features:** choose what each role may use (Harness, BA Studio, QE cycle, Skill Studio, MCP, Documents, Desktop downloads and more), and allow or deny one feature for one member. Members without **Desktop downloads** do not see the installers on their Home page.
6. **MCP:** add remote (HTTP) MCP servers, and grant each tool to roles. stdio servers run only in the desktop app.
   **Jira and Confluence (optional):** add `https://mcp.atlassian.com/v2/mcp` (transport http) and tick "Each member signs in with OAuth". Select **Sign in** (your Atlassian account), then **Connect** to list its tools, and grant them to the roles that use BA Studio. Each member then connects their own Atlassian account from BA Studio; the platform never sees their password and keeps their token encrypted.
7. **Desktop app:** members sign in to the desktop app with this server's address (`https://aqe-ui-<unique>.azurewebsites.net`), their username and password. The app keeps only a signed sign-in from the server, never the password; **Sign out** in its menu removes it. The admin account works in the browser only.

**Verify, end to end:**
1. Create a project and attach a repository.
2. Send one harness message, and approve one file write.
3. Open the project's **QE** page and start the cycle.

---

## 16. A tour of the UI

The same pages run locally, on Azure and in the desktop app. The screenshots are from real local runs in `docs/evidence/`.

| Page | Who | What you do there | Screenshot |
|---|---|---|---|
| `/` | everyone | Landing page: what the platform does, macOS and Windows downloads, **Sign in** | [dark](evidence/screens/landing-dark.png), [light](evidence/screens/landing-light.png), [phone](evidence/screens/landing-phone.png) |
| `/login` | everyone | Sign in | [login](evidence/22a-login.png) |
| `/projects` | members | Create a project, then attach a repository: a zip upload or a GitHub URL | [list](evidence/05-projects-list.png), [zip](evidence/03-repository-zip.png), [GitHub](evidence/04-repository-github.png) |
| Project, **Harness** | members | Chat with the project harness. Type `/` for commands; a plugin command stays active until the next one. Status lines appear while it works. Every file write and shell command stops for **Approve** or **Reject** | [harness](evidence/screens/harness.png), [slash menu](evidence/evidence_harness_fixed_slash_palette.png), [tasks](evidence/evidence_harness_tasks_completed.png) |
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
- **App Service logs.** **Monitoring, Log stream** shows each app's live output. Kudu (`https://<app>.scm.azurewebsites.net`) has **Log stream** and **Debug console** too.
- **Application Insights** (optional, billed per GB, see section 2):
  1. Create it in East US 2, in `rg-agentic-qe`.
  2. On the API app, add the settings `OTEL_EXPORTER_OTLP_ENDPOINT` (your collector or Azure Monitor's OTLP endpoint) and `OTEL_SERVICE_NAME=agentic-qe-api`.

---

## 18. Update, backup, stop paying

**Update the app:**
1. Change and test locally: `python scripts/dev.py db`, then `python scripts/dev.py test`.
2. Build the zips and run `azure-local --check` (section 4).
3. Deploy both zips through `ZipDeployUI`, and restart both apps. If the PostgreSQL server is stopped, start it first.

New tables are added automatically on start.

**Update the desktop installers:** push a new `v*` tag. GitHub Actions builds the DMGs and the MSI and publishes a Release. Then upload the new files and `latest.json` to the `downloads` container (section 8).

**Backup:**
- **PostgreSQL** keeps 7 days of point-in-time restore: open **Settings, Backup and restore**, then **Restore**.
- **Blob versioning and soft delete** protect the installers.
- **The `/home` share** holds workspaces and files: check each app's **Backups** page.
- **Key Vault** keeps deleted secrets for 90 days (soft delete).

**Stop paying:**
- Deleting the resource group `rg-agentic-qe` removes everything in it and stops all charges.
- Stopping the web apps does **not** stop the plan's charge (section 2).

---

## 19. Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| Application error page, and **Log stream** says Key Vault access was denied | The API's identity cannot read secrets | Give `aqe-api-<unique>` the role **Key Vault Secrets User** on the vault (section 10.2), then restart |
| Log shows "PostgreSQL ... did not answer within 30 seconds" or a connection timeout | Firewall rule missing, or the server is stopped | Add the API's outbound addresses (section 11); start the server from its **Overview** |
| Log shows `password authentication failed` | Wrong `atlas-database-url` | Fix the secret (section 7.3), percent-encoding special characters, then restart |
| Health answers but the UI shows "cannot reach the API" | `ATLAS_BACKEND_URL` is wrong, or the access restriction blocks the UI | Check the setting, and that every UI outbound address is allowed (section 12.5) |
| The app never starts, and the log shows Oryx or `pip` building | Kudu's build is on | Set `SCM_DO_BUILD_DURING_DEPLOYMENT=false` and `ENABLE_ORYX_BUILD=false`, then deploy the zip again |
| `startup.py` or `startup.js` is not found | Wrong startup command, or a zip made with Explorer or Finder | Use the commands in sections 10.3 and 12.2, and build with `package_azure_kudu.py` |
| The landing page says "No desktop installer is published yet" | `latest.json` is missing, or `ATLAS_DOWNLOADS_URL` is wrong | Open `<container URL>/latest.json` in the browser; fix the setting (no trailing slash), then restart the UI |
| The harness refuses stdio MCP or `npx` installs | The web profile allows them only in the desktop app | Use a remote (HTTP) MCP server, or the desktop app |
| The start and stop runbook fails with 403 | The Automation account lacks rights on the server | Assign **Contributor** on the PostgreSQL server to `aa-agentic-qe` (section 13.2) |

---

## 20. Decisions

| # | Decision | State |
|---|---|---|
| A | App Service or Container Apps | App Service B1 (owner, 2026-11-11) |
| B | Entra ID sign-in | Later; built-in accounts for now |
| C | Model provider | The existing endpoint, set on **Settings** |
| D | Desktop database | A local cluster that uses the PostgreSQL installed on the computer (`brew install postgresql@17` on macOS, the postgresql.org installer on Windows). Bundling PostgreSQL in the installer is planned |
| E | Region | **East US 2** (owner, 2026-11-11) |
| F | Cost cap | At most **$25 a month**, through the PostgreSQL stop schedule (owner, 2026-11-12). Any change that raises it needs the owner's yes |

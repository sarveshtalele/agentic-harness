# Azure proof of concept: step-by-step in the Azure portal

This guide deploys Agentic QE Platform as a browser link for a small team at the lowest cost. It follows `docs/MASTER_PLAN.md` phase M6.

## What you get

| Part | Choice | Why |
|---|---|---|
| Compute | **One** Linux App Service plan, tier **B1**, hosting **two** web apps (API and UI) | Both apps share one plan, so you pay for one small machine |
| Database | SQLite on the app's persistent `/home` share (`ATLAS_SQLITE_JOURNAL=DELETE`) | No database server to pay for. Fine for a proof of concept with a few users |
| Cache | None | Not needed at this size |
| Model | Your existing model endpoint, entered on the Settings page after the first sign-in | No Azure OpenAI resource is required |
| Profile | `ATLAS_PROFILE=web` | **The harness, sandbox script runs and stdio MCP servers are switched off on the web.** They need a dedicated workspace per person, so they run in the desktop app (`docs/MASTER_PLAN.md` M7) |
| Access | Every person signs in. What they see follows their project membership and role | The rules live in `src/backend/core/auth` (deny by default) |

**Cost.** One B1 Linux plan is the only charged resource. Check the current price for your region in the [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/) before you create it. Prices differ by region and change over time. Stop or delete the plan when you are not using it.

**When to upgrade.** Move on when you see many concurrent users, several people running workflows at once, or a need for zero-downtime restarts. The path is PostgreSQL, Blob Storage and Container Apps Jobs, in `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md`.

## Before you start

1. **Build the two zips** on your machine, from the repository root:
   ```bash
   python scripts/package_azure_kudu.py
   ```
   This writes `dist/azure_backend.zip` and `dist/azure_frontend.zip`. They contain only files tracked in Git.
2. **Prove them locally first** (section 10). Do not deploy a package that has not run locally.
3. **Pick and keep these values:**
   - a resource group name, for example `rg-agentic-qe-poc`;
   - two globally unique app names, for example `aqe-api-<yourname>` and `aqe-ui-<yourname>`;
   - one region close to your users.

## 1. Create the resource group

1. In the portal, search **Resource groups** and select **Create**.
2. Choose your subscription, enter the resource group name, and pick the region.
3. Select **Review + create**, then **Create**.

## 2. Create the App Service plan (B1)

1. Search **App Service plans**, select **Create**.
2. Choose your resource group and name the plan, for example `plan-agentic-qe-poc`.
3. **Operating System:** Linux. **Region:** the same region.
4. **Pricing plan:** select **Explore pricing plans**, choose **Basic B1**, and select **Select**.
5. Select **Review + create**, then **Create**.

## 3. Create the API web app

1. Search **App Services**, select **Create**, then **Web App**.
2. **Basics** tab:
   - **Resource group:** yours.
   - **Name:** the API name, for example `aqe-api-<yourname>`.
   - **Publish:** Code.
   - **Runtime stack:** Python 3.12.
   - **Operating System:** Linux.
   - **Region:** the same region.
   - **Linux Plan:** the B1 plan from step 2.
3. **Monitoring** tab: Application Insights is optional, and it adds cost when it ingests data. Leave it off for the proof of concept.
4. Select **Review + create**, then **Create**.
5. When it is ready, open the app. Go to **Settings, Configuration, General settings**:
   - **Startup Command:** `python /home/site/wwwroot/startup.py`
   - **Always on:** On. B1 supports it, and it keeps the first request fast.
   - **HTTPS Only:** On.

   Select **Save**.

## 4. Configure the API

Open **Settings, Environment variables** and add these **App settings**. Select **Apply** after each group.

| Name | Value | Notes |
|---|---|---|
| `ATLAS_PROFILE` | `web` | Harness, script runs and stdio MCP off |
| `ATLAS_ADMIN_USERNAME` | the first administrator's username | Used only to create the first admin |
| `ATLAS_ADMIN_PASSWORD` | a long, unique password | Stored as an app setting; it never appears in logs. Change it later on the Account page |
| `ATLAS_SECRET_KEY` | a long random value | Encrypts stored secrets and signs sessions. If you lose it, stored secrets cannot be read |
| `ATLAS_DATA_DIR` | `/home/atlas/data` | `/home` survives restarts and deployments |
| `ATLAS_SQLITE_JOURNAL` | `DELETE` | The `/home` share has no shared memory, so WAL is not used |
| `ATLAS_ALLOWED_HOSTS` | `aqe-api-<yourname>.azurewebsites.net` | Hosts the API answers to |
| `ATLAS_ALLOWED_ORIGINS` | `https://aqe-ui-<yourname>.azurewebsites.net` | The UI address, for browser requests |
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` | Keeps `/home` persistent |
| `WEBSITES_PORT` | `8000` | The port the startup script listens on |

Make a random secret on your machine. Then paste it into the portal; do not save it in a file in the repository.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 5. Deploy the API zip

1. Open `https://aqe-api-<yourname>.scm.azurewebsites.net/ZipDeployUI` (Kudu) and sign in with the same Azure account.
2. Drag `dist/azure_backend.zip` onto the page and wait for the deployment to finish.
3. Back in the portal, open the API app and select **Restart**.
4. Open **Monitoring, Log stream**.
   - The first start builds the Python environment, which takes several minutes. You should see "Environment built", then "Starting API on port 8000".
5. Open `https://aqe-api-<yourname>.azurewebsites.net/api/health`. It must answer `{"status": "ok", ...}`.

## 6. Create and deploy the UI web app

1. Create a second web app exactly as in step 3, with these differences:
   - **Name:** `aqe-ui-<yourname>`.
   - **Runtime stack:** Node 20 LTS.
   - **Linux Plan:** the **same** B1 plan.
2. **Configuration, General settings:**
   - **Startup Command:** `node /home/site/wwwroot/startup.js`
   - **Always on:** On.
   - **HTTPS Only:** On.

   Select **Save**.
3. **Environment variables, App settings:**

   | Name | Value |
   |---|---|
   | `ATLAS_BACKEND_URL` | `https://aqe-api-<yourname>.azurewebsites.net` |
   | `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
   | `WEBSITES_PORT` | `3000` |

4. Deploy `dist/azure_frontend.zip` through `https://aqe-ui-<yourname>.scm.azurewebsites.net/ZipDeployUI`, then **Restart**.
5. Watch **Log stream**. The first start builds the UI, which takes several minutes, and then shows "Starting UI on port 3000".

## 7. Let only the UI reach the API

The API should not be reachable from the internet directly.

1. Open the **UI** app, **Settings, Properties**. Copy every address under **Outbound IP addresses** (and **Additional Outbound IP addresses**).
2. Open the **API** app, **Settings, Networking**, **Public network access**, **Access restriction**.
3. Under **Site access and rules**:
   - Set **Unmatched rule action** to **Deny**.
   - Add one **Allow** rule per UI outbound address, each with a priority and a name such as `ui-1`.
4. On the **Advanced tool site** tab (Kudu), keep access for yourself, or allow only your own public IP. You need Kudu for zip deployments.
5. Check the result. `https://aqe-api-<yourname>.azurewebsites.net/api/health` from your browser now returns 403. The UI still works.

## 8. First sign-in and the model

1. Open `https://aqe-ui-<yourname>.azurewebsites.net` and sign in with `ATLAS_ADMIN_USERNAME` and `ATLAS_ADMIN_PASSWORD`.
2. Go to **Settings**:
   - Enter the model endpoint, model name and key. The key is encrypted with `ATLAS_SECRET_KEY` and never shown again.
   - Select **Test connection**; the page shows the model's real reply and latency.
   - Under the model list, tick the models people may use.

## 9. Add people and set their permissions

1. **Users, Add user:** create each person with a username, a temporary password, and a platform role. Roles: `qe_lead`, `ba`, `developer`, `viewer`. A viewer can read but not run agents or change anything.
2. Open a project, then **Members**, and add the people who may see it. People see only the projects they are members of. The administrator sees all.
3. **Settings, Gate roles:** choose which roles may sign each gate G0 to G5. Agents never sign gates.
4. **Token Budget & Usage:** set each person's token limit.

Each person then signs in at the UI address with their username and changes their password on the Account page.

## 10. Prove it locally before Azure

Run the same zips through the same startup scripts on your machine, in the `web` profile:

```bash
python scripts/dev.py azure-local
```

This unzips both packages into a temporary folder, starts `startup.py` and `startup.js` with `ATLAS_PROFILE=web`, and runs the Playwright web-profile stories against them:
- sign-in;
- projects;
- members and permissions;
- documents;
- governance;
- the harness page saying it is desktop-only.

The evidence report is written to `docs/evidence/runs/`. (`azure-local` is added in M6; until then, use the `azure-backend` and `azure-frontend` launch configurations.)

## 11. Updates, backups and logs

- **Update.** Build new zips, deploy them through ZipDeployUI, and restart each app. Data in `/home/atlas/data` stays.
- **Backup.**
  - In each app, open **Backups** and check what your tier offers.
  - Also copy the database yourself: open Kudu's **Debug console**, go to `/home/atlas/data/`, and download `atlas.sqlite3` while no workflow is running.
- **Logs.**
  - Live output is in **Log stream**.
  - The application's own logs are in `/home/atlas/data/logs/`: `app-DAY.jsonl` holds requests, and `errors-DAY.jsonl` holds errors with stack traces.
  - An administrator can download both from **Settings, Application log**.
- **Stop paying.** Delete the resource group when the proof of concept ends. That removes both apps and the plan.

## Not in this proof of concept

| Missing | Reason | Where it comes from |
|---|---|---|
| Harness on the web | It needs a dedicated workspace per person | Desktop app (M7) |
| Company single sign-on (Entra ID) | Not required for a small team; built-in accounts are used | Target architecture |
| More than one instance | SQLite on one share supports one writer | PostgreSQL in the target architecture |
| Isolated repository runs | Repository code would share the web server | Container Apps Jobs in the target architecture; until then, admit only trusted users (CLAUDE.md) |

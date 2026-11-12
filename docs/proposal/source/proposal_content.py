"""The proposal workbook's text tables (split from build_proposal.py to keep both files short)."""

EVIDENCE = [  # key, retail key, sku, meter, tier, product
    ("APP_B1", "app_service", "B1", "B1", 0.0, "Azure App Service Basic Plan - Linux"),
    ("APP_B2", "app_service", "B2", "B2", 0.0, "Azure App Service Basic Plan - Linux"),
    ("APP_B3", "app_service", "B3", "B3", 0.0, "Azure App Service Basic Plan - Linux"),
    ("APP_P0V3", "app_service", "P0v3", "P0v3 App", 0.0, "Azure App Service Premium v3 Plan - Linux"),
    ("PG_B1MS", "pg_compute", "B1MS", "B1MS", 0.0, None),
    ("PG_B2S", "pg_compute", "B2S", "B2S", 0.0, None),
    ("PG_STORAGE", "pg_storage", "Storage", "Storage Data Stored", 0.0, None),
    ("PG_BACKUP", "pg_storage", "Backup Storage LRS", "Backup Storage LRS Data Stored", 0.0, None),
    ("BLOB_STORED", "blob", "Hot LRS", "Hot LRS Data Stored", 0.0, None),
    ("BLOB_WRITE", "blob", "Hot LRS", "Hot LRS Write Operations", 0.0, None),
    ("BLOB_READ", "blob", "Hot LRS", "Hot Read Operations", 0.0, None),
    ("KV_OPS", "key_vault", "Standard", "Operations", 0.0, None),
    ("AUTO_FREE", "automation", "Basic", "Basic Runtime", 0.0, None),
    ("AUTO_PAID", "automation", "Basic", "Basic Runtime", 500.0, None),
    ("EGRESS_FREE", "bandwidth", "Standard", "Standard Data Transfer Out", 0.0, None),
    ("EGRESS_PAID", "bandwidth", "Standard", "Standard Data Transfer Out", 100.0, None),
    ("LOGS_FREE", "log_analytics", "Analytics Logs", "Analytics Logs Data Ingestion", 0.0, None),
    ("LOGS_PAID", "log_analytics", "Analytics Logs", "Analytics Logs Data Ingestion", 5.0, None),
]

ASSUME = [
    ("HOURS_MONTH", "Hours in a billing month", 730, "hours", "Azure pricing convention (365 x 24 / 12)."),
    ("PG_HOURS", "PostgreSQL running hours, standard schedule", 264, "hours", "12 hours a day on 22 weekdays, started and stopped by Azure Automation (deployment step 13)."),
    ("PG_HOURS_8H", "PostgreSQL running hours, 8-hour weekdays", 176, "hours", "8 hours a day on 22 weekdays."),
    ("PG_GB", "PostgreSQL provisioned storage", 32, "GB", "Smallest Flexible Server size; billed while the server is stopped."),
    ("PG_BACKUP_EXTRA_GB", "Backup storage above provisioned size", 0, "GB", "7-day retention; backup up to the provisioned size is included at no charge."),
    ("BLOB_GB", "Blob data stored (installers, versions kept)", 2, "GB", "One release is about 0.93 GB (2 DMGs, 2 zips, 1 MSI); versioning keeps the previous one."),
    ("BLOB_WRITES_10K", "Blob write operations", 0.01, "x 10,000", "About 100 uploads a month."),
    ("BLOB_READS_10K", "Blob read operations", 0.1, "x 10,000", "About 1,000 downloads and latest.json reads a month."),
    ("KV_OPS_10K", "Key Vault operations", 0.01, "x 10,000", "3 secret reads per API start, about 30 starts a month, plus portal use."),
    ("AUTO_MIN", "Automation runbook minutes", 44, "minutes", "2 jobs a weekday x 22 days, about 1 minute each."),
    ("EGRESS_GB", "Outbound data to the internet", 20, "GB", "About 100 installer downloads of 0.19 GB plus web traffic."),
    ("LOGS_GB", "Application Insights / Log Analytics ingestion", 0, "GB", "Optional; 0 means not enabled. First 5 GB a month are free."),
    ("USERS", "People using the web app", 5, "people", "Small trusted team (repository code shares the API machine)."),
]

ARCH = [
    ("UI web app", "App Service (Linux), Node 20 LTS", "Shares plan B1", "Serves the Next.js app and the CopilotKit runtime route; the landing page lists desktop downloads.", "Static Web Apps (cannot run the server-side runtime route)."),
    ("API web app", "App Service (Linux), Python 3.12", "Shares plan B1", "Runs FastAPI and Microsoft Agent Framework: agents, harness, workflows, gates and ledger.", "Container Apps (more moving parts; owner chose App Service, 2026-11-11)."),
    ("App Service plan", "App Service plan", "Basic B1, Linux", "Cheapest plan that runs both apps with Always On and a /home share.", "B2 or P0v3 when more memory or CPU is needed (see Cost Estimate)."),
    ("Database", "Azure Database for PostgreSQL Flexible Server", "Burstable B1ms, 32 GB, PostgreSQL 17", "The only database the app supports. Point-in-time restore for 7 days, many writers, and it can be stopped to save cost.", "SQLite (removed: one writer, no managed backup)."),
    ("Secrets", "Key Vault", "Standard", "Holds the admin password, secret key and database URL; the API reads them with its managed identity, so no secret sits in app settings.", "App settings (secrets visible to anyone with portal access)."),
    ("Files", "Storage account, Blob", "Standard LRS, Hot", "Public-read 'downloads' container for the desktop installers and latest.json, with versioning and soft delete.", "GitHub Release only (no link from the app's own landing page)."),
    ("Workspaces", "App Service /home share", "Included with the plan", "Repository workspaces, documents and evidence until the Blob storage layer is built.", "Blob containers (planned)."),
    ("Start/stop schedule", "Azure Automation", "Basic, within free minutes", "Starts PostgreSQL at 08:00 and stops it at 20:00 on weekdays to stay under the USD 25 cap.", "Leave it always on (about USD 28.60, above the cap)."),
    ("Monitoring (optional)", "Application Insights / Log Analytics", "Pay per GB after 5 GB free", "OpenTelemetry traces from the API; the app also has its own /traces page and log downloads.", "In-app traces and logs only."),
    ("Desktop app", "GitHub Actions build, Blob download", "macOS DMG (Apple silicon, Intel), Windows MSI", "Each person can run the full platform locally, including stdio MCP and plugin installs, with a local PostgreSQL.", "Web app only."),
]

STEPS = [
    ("Prepare", "Your computer", "Install the repository (python scripts/dev.py setup) and PostgreSQL 16 or newer. Make two random values: python -c \"import secrets; print(secrets.token_urlsafe(48))\".", "Two values saved safely."),
    ("Package", "Terminal / PowerShell", "Run python scripts/package_azure_kudu.py. Never zip with Explorer or Finder.", "dist/azure_backend.zip and dist/azure_frontend.zip exist."),
    ("Package", "Terminal / PowerShell", "Set ATLAS_ADMIN_USERNAME and ATLAS_ADMIN_PASSWORD, then run python scripts/dev.py azure-local --check.", "Prints 'API health: 200; UI /login: 200'."),
    ("Resource group", "Resource groups > Create", "Name rg-agentic-qe, Region East US 2. Review + create, Create.", "Listed in East US 2."),
    ("Key Vault", "Key vaults > Create", "Name kv-agentic-qe-<unique>, East US 2, Pricing tier Standard, Permission model: Azure role-based access control.", "Vault created."),
    ("Key Vault", "Vault > Access control (IAM) > Add role assignment", "Role Key Vault Secrets Officer for your own account.", "You can add secrets."),
    ("Key Vault", "Vault > Objects > Secrets > Generate/Import", "Add atlas-admin-password (12+ characters) and atlas-secret-key (the random value).", "Both secrets Enabled."),
    ("PostgreSQL", "Azure Database for PostgreSQL flexible servers > Create", "Name pg-agentic-qe-<unique>, East US 2, version 17, Workload Development, Configure server: Burstable, Standard_B1ms, 32 GiB, backup 7 days. PostgreSQL authentication only. Networking: Public access (allowed IP addresses), Azure services access off.", "Status Ready."),
    ("PostgreSQL", "Server > Settings > Databases > + Add", "Name agentic_qe.", "Database listed."),
    ("PostgreSQL", "Vault > Secrets > Generate/Import", "atlas-database-url = postgresql://<user>:<password>@pg-agentic-qe-<unique>.postgres.database.azure.com:5432/agentic_qe?sslmode=require (percent-encode @ : / ? # in the password).", "Secret Enabled."),
    ("Storage", "Storage accounts > Create", "Name stagenticqe<unique>, East US 2, Standard, LRS. Data protection: blob versioning on, soft delete 7 days.", "Account created."),
    ("Storage", "Account > Settings > Configuration", "Allow Blob anonymous access: Enabled. Save.", "Setting saved."),
    ("Storage", "Account > Data storage > Containers > + Container", "Name downloads, Anonymous access level: Blob (never Container).", "Container listed."),
    ("Storage", "Container > Upload", "Upload the DMGs, zips, MSI and latest.json from GitHub Release v0.1.0 with Overwrite on. Set latest.json Cache-Control to no-cache. Copy the container URL.", "<container URL>/latest.json opens in a private window."),
    ("App Service plan", "App Service plans > Create", "Name plan-agentic-qe, Linux, East US 2, Pricing plan Basic B1.", "Overview shows Basic (B1), Linux."),
    ("API app", "App Services > Create > Web App", "Name aqe-api-<unique>, Publish Code, Python 3.12, Linux, East US 2, plan plan-agentic-qe.", "App created."),
    ("API app", "App > Settings > Identity", "System assigned: On. Then on the vault, role Key Vault Secrets User for this managed identity.", "Role assignment listed on the vault."),
    ("API app", "App > Settings > Configuration > General settings", "Startup Command python /home/site/wwwroot/startup.py; Always on On; HTTPS Only On.", "Saved."),
    ("API app", "App > Settings > Environment variables", "ATLAS_KEY_VAULT_URL, ATLAS_PROFILE=web, ATLAS_DATA_DIR=/home/atlas/data, ATLAS_ADMIN_USERNAME, ATLAS_ALLOWED_HOSTS, ATLAS_ALLOWED_ORIGINS, ATLAS_MAX_SANDBOXES=5, WEBSITES_ENABLE_APP_SERVICE_STORAGE=true, WEBSITES_PORT=8000, SCM_DO_BUILD_DURING_DEPLOYMENT=false, ENABLE_ORYX_BUILD=false.", "Applied."),
    ("API app", "https://aqe-api-<unique>.scm.azurewebsites.net/ZipDeployUI", "Drag dist/azure_backend.zip onto the page, then Restart the app.", "Log stream: 'Environment built', then 'Starting API on port 8000'."),
    ("Database firewall", "API app > Settings > Properties", "Copy all outbound and additional outbound IP addresses.", "Address list copied."),
    ("Database firewall", "PostgreSQL > Settings > Networking", "Add one firewall rule per address (start = end), Save, restart the API app.", "/api/health returns status ok."),
    ("UI app", "App Services > Create > Web App", "Name aqe-ui-<unique>, Node 20 LTS, Linux, East US 2, plan plan-agentic-qe. Startup Command node /home/site/wwwroot/startup.js; Always on and HTTPS Only On.", "App created."),
    ("UI app", "App > Settings > Environment variables", "ATLAS_BACKEND_URL, ATLAS_DOWNLOADS_URL (container URL, no trailing slash), WEBSITES_ENABLE_APP_SERVICE_STORAGE=true, WEBSITES_PORT=3000, SCM_DO_BUILD_DURING_DEPLOYMENT=false, ENABLE_ORYX_BUILD=false.", "Applied."),
    ("UI app", "https://aqe-ui-<unique>.scm.azurewebsites.net/ZipDeployUI", "Drag dist/azure_frontend.zip onto the page, then Restart.", "Log stream ends with 'Starting UI on port 3000'; landing page shows downloads."),
    ("Lock the API", "API app > Settings > Networking > Access restriction", "Unmatched rule action Deny; one Allow rule per UI outbound address; Advanced tool site: allow only your IP.", "API health answers 403 in your browser; the UI still works."),
    ("Cost schedule", "Automation Accounts > Create", "Name aa-agentic-qe, East US 2, system-assigned identity on.", "Account created."),
    ("Cost schedule", "PostgreSQL > Access control (IAM)", "Role Contributor (scoped to this server) for the Automation account's managed identity.", "Role assignment listed."),
    ("Cost schedule", "Automation > Runbooks > Create a runbook", "pg-start-stop, PowerShell 7.2, code from the guide section 13 (Invoke-AzRestMethod start/stop). Save, Publish. Test with ACTION=stop then start.", "Job output 'HTTP 202'; server Stopped, then Ready."),
    ("Cost schedule", "Runbook > Schedules > Add a schedule", "pg-start-weekdays 08:00 Mon-Fri ACTION=start; pg-stop-weekdays 20:00 Mon-Fri ACTION=stop.", "Two schedules linked."),
    ("Check", "API app > Development Tools > SSH", "python /home/site/wwwroot/scripts/env_check.py --env azure", "Prints 'azure: OK'."),
    ("First sign-in", "https://aqe-ui-<unique>.azurewebsites.net", "Sign in as the admin; set the model on Settings and Test connection; add users.", "Harness answers a message in a project."),
]

UI = [
    ("Landing page /", "Everyone", "Open the UI address. Read what the platform does; download the desktop app for macOS or Windows if you want it; select Sign in.", "Login page opens."),
    ("Login /login", "Everyone", "Enter the username and password the admin gave you, then sign in. Change the temporary password on /account.", "Projects list opens."),
    ("Settings /settings", "Admin", "Enter the model endpoint, model name and key; select Test connection; tick the models people may use; grant plugins to roles.", "Test connection succeeds."),
    ("Users /users", "Admin", "Add user: username, temporary password, email and role (qe_lead, ba, developer or viewer).", "User appears in the list."),
    ("Settings, Gate roles", "Admin", "Choose who may sign gates G0 to G5. Agents never sign.", "Roles saved."),
    ("Projects /projects", "Members", "Create a project, then attach a repository: upload a zip or paste a GitHub URL. Add Members who may see it.", "Repository files and facts appear."),
    ("Project, Harness", "Members", "Type a request, or '/' to pick a command or skill (for example /agentic-qe:qe-start <app>). Watch the status lines; approve or reject each file write and shell command on its card. A plugin command stays active until you send another; to resume it, send the same command again.", "Answer, todos and written files appear; each write shows the command's check result."),
    ("Project, BA", "BA, QE lead", "Write or generate requirements documents (BRD) and Gherkin; every save is a new version with history. Sign gate G1 when ready.", "Version history lists each save."),
    ("Project, QE", "QE lead", "Run the QE cycle gate by gate (G0 to G5). Each gate needs its check to pass and a named person to sign.", "Gate shows signed with name, role and time."),
    ("Project, Bugs and Feature", "Developers", "Run a bug scan and review findings; generated changes land on a separate branch, shown as a diff.", "Findings list and diff."),
    ("Project, Approvals and Governance", "Approvers", "Approve or reject pending items; review the hash-chained ledger.", "Ledger verifies."),
    ("Skill Studio /skills/studio", "Admin, QE lead", "Choose source and kind, write the request, review the plan, approve, generate, test (Repair from test failures if needed), evaluate, publish.", "Skill listed on /skills with a version."),
    ("MCP /mcp", "Admin", "Add a remote (HTTP) MCP server, Connect, then grant each tool to roles. stdio servers run only in the desktop app.", "Tools listed as granted."),
    ("Agents /agents", "Everyone", "See the governed agents and their evaluation scores (n and judge, or why blank).", "Agent list."),
    ("Traces /traces", "Admin: all; member: own", "Open a run to see its span tree and timings.", "Trace detail."),
    ("Usage", "Admin", "Check token use per person and model; set allowances.", "Usage table."),
    ("Account /account", "Each person", "Change your own password and email.", "Saved."),
    ("Desktop app", "Each person", "Install PostgreSQL 16+ first; install the DMG (right-click, Open the first time) or the MSI (SmartScreen: More info, Run anyway). It runs its own API, UI and local database.", "Same pages as the web app, plus stdio MCP and plugin installs."),
]

GAPS = [
    (1, "No INR prices; the team is billed in India.", "Every unit price retrieved in USD and INR from the API (Price Evidence); Cost Estimate shows both; INR column added to the guide.", "Fixed"),
    (2, "Guide said installers are 160 to 760 MB.", "Measured release v0.1.0: 164 to 195 MB per file; guide corrected.", "Fixed"),
    (3, "Taxes not mentioned.", "Proposal and guide state prices exclude taxes (for example 18% GST in India).", "Fixed"),
    (4, "PostgreSQL storage price was from 2026-11-11 only.", "Re-read live: USD 0.115 / INR 10.9513 per GB a month, the 'Storage Data Stored' meter.", "Fixed"),
    (5, "Not stated that storage is billed while PostgreSQL is stopped.", "Stated in Cost Estimate and the guide.", "Fixed"),
    (6, "Free allowances were stated without proof.", "API tiers confirm: egress free to 100 GB, Automation free to 500 min, Log Analytics free to 5 GB.", "Fixed"),
    (7, "Installer names with spaces did not match latest.json on GitHub Release.", "Installers now named agentic-qe-<version>-<os>-<arch>; old dotted files removed from v0.1.0.", "Fixed"),
    (8, "No screenshots of the Azure portal steps.", "Needs a real subscription (owner decision D5).", "Open"),
    (9, "No 'database stopped (outside working hours)' page.", "Planned in the platform; until then the app shows a database error naming PostgreSQL.", "Open"),
    (10, "Not yet deployed to a real Azure subscription.", "First test deployment with evidence (health, sign-in, harness turn, QE run) is the next plan item.", "Open"),
]


def lines(A):
    return [
        ("App Service plan B1, Linux (API + UI)", "B1", "APP_B1", A["HOURS_MONTH"], "hours", "Billed while the plan exists, even if both apps are stopped."),
        ("PostgreSQL Flexible Server B1ms compute", "B1MS", "PG_B1MS", A["PG_HOURS"], "hours", "Billed only while the server runs."),
        ("PostgreSQL storage", "Storage Data Stored", "PG_STORAGE", A["PG_GB"], "GB", "Billed while stopped too."),
        ("PostgreSQL backup above provisioned size", "Backup Storage LRS", "PG_BACKUP", A["PG_BACKUP_EXTRA_GB"], "GB", "Usually 0."),
        ("Blob Storage Hot LRS, data", "Hot LRS Data Stored", "BLOB_STORED", A["BLOB_GB"], "GB", "downloads container (desktop installers)."),
        ("Blob Storage writes", "Hot LRS Write Operations", "BLOB_WRITE", A["BLOB_WRITES_10K"], "x 10,000", ""),
        ("Blob Storage reads", "Hot Read Operations", "BLOB_READ", A["BLOB_READS_10K"], "x 10,000", ""),
        ("Key Vault Standard", "Operations", "KV_OPS", A["KV_OPS_10K"], "x 10,000", "Secrets read at API start."),
        ("Azure Automation (start/stop schedule)", "Basic Runtime, above 500 min", "AUTO_PAID", f"MAX(0,{A['AUTO_MIN']}-500)", "minutes", "First 500 minutes a month free."),
        ("Outbound data (internet egress)", "Data Transfer Out, above 100 GB", "EGRESS_PAID", f"MAX(0,{A['EGRESS_GB']}-100)", "GB", "First 100 GB a month free."),
        ("Application Insights (optional)", "Log ingestion, above 5 GB", "LOGS_PAID", f"MAX(0,{A['LOGS_GB']}-5)", "GB", "First 5 GB a month free."),
    ]


def options(A):
    return [
        ("Standard: B1 + PostgreSQL 12 h weekdays (recommended)", "B1 / B1ms", "APP_B1", A["HOURS_MONTH"], "PG_B1MS", A["PG_HOURS"]),
        ("Lower: B1 + PostgreSQL 8 h weekdays", "B1 / B1ms", "APP_B1", A["HOURS_MONTH"], "PG_B1MS", A["PG_HOURS_8H"]),
        ("Always on: B1 + PostgreSQL 24 x 7", "B1 / B1ms", "APP_B1", A["HOURS_MONTH"], "PG_B1MS", A["HOURS_MONTH"]),
        ("Upgrade: B2 plan + PostgreSQL 12 h weekdays", "B2 / B1ms", "APP_B2", A["HOURS_MONTH"], "PG_B1MS", A["PG_HOURS"]),
        ("Upgrade: P0v3 plan + PostgreSQL B2s 24 x 7", "P0v3 / B2s", "APP_P0V3", A["HOURS_MONTH"], "PG_B2S", A["HOURS_MONTH"]),
    ]


def proposal_rows(FETCHED, tot, header_row, USD_CAP=25):
    return [
        ("Purpose", "Host the Agentic QE Platform for a small trusted team as a browser app on Azure, with a desktop app for each person, at no more than USD 25 a month."),
        ("What the platform does", "BAs and developers run governed AI agents (Microsoft Agent Framework) over real repositories: requirements and Gherkin, test plans, test design, generated tests, execution with Playwright evidence, healing, traceability and gate sign-off (G0 to G5) by named people. Every change is versioned and recorded in a hash-chained ledger."),
        ("Recommendation", "One Linux App Service plan B1 running two web apps (API and UI), Azure Database for PostgreSQL Flexible Server B1ms stopped outside working hours, Blob Storage for desktop installers, and Key Vault for secrets, all in East US 2, deployed by uploading zip packages through Kudu."),
        ("Monthly cost (USD)", f"='Cost Estimate'!G{tot}"),
        ("Monthly cost (INR)", f"='Cost Estimate'!H{tot}"),
        ("Yearly cost (USD)", f"='Cost Estimate'!G{tot + 1}"),
        ("Yearly cost (INR)", f"='Cost Estimate'!H{tot + 1}"),
        ("Within the USD 25 cap", f"='Cost Estimate'!G{tot + 2}"),
        ("Always-on alternative (USD)", f"='Cost Estimate'!G{header_row + 3}"),
        ("Region", "East US 2 (owner decision, 2026-11-11)."),
        ("Not included", "Taxes (for example 18% GST when billed in India), model tokens from the model provider, support plans, and Azure reservations or credits."),
        ("Deployment model", "Zip packages built and checked on a laptop (python scripts/package_azure_kudu.py, then azure-local --check), uploaded through Kudu ZipDeployUI. GitHub never connects to Azure."),
        ("Security", "Secrets only in Key Vault, read by the API's managed identity. The API accepts traffic only from the UI. PostgreSQL accepts only the API's outbound addresses. Everyone signs in; every API path is denied by default."),
        ("Known limits", "Repository code runs on the API machine until isolated sandbox jobs exist, so admit only trusted people. stdio MCP servers, npx and plugin installs are desktop-only. While PostgreSQL is stopped the app shows a database error (a friendly 'outside working hours' page is planned)."),
        ("Status", "Packages verified locally (API health 200, UI login 200) and the full test suite passes on PostgreSQL. Desktop installers are published as GitHub Release v0.1.0. Not yet deployed to a real Azure subscription."),
        ("Workbook contents", "Proposal; Cost Estimate; Assumptions; Price Evidence (live API rows, USD and INR); Architecture (what and why); Deployment Steps (portal, step by step); UI Guide (step by step); Gaps and Fixes (review findings)."),
    ]


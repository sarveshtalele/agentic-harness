import type { DocGroup } from "./types";
import { evaluationsPage } from "./evaluations";

export const reference: DocGroup = {
    title: "Reference",
    pages: [
      evaluationsPage,
      {
        slug: "models",
        title: "Models and limits",
        summary: "Several models on one endpoint, who may use each, and token limits that reset on a schedule.",
        body: `## One endpoint, several models

Every model uses the endpoint and key set on **Settings**. The admin manages the list under **Settings > Models**.

1. Choose **Load from proxy**. Each name the endpoint lists is added, switched off.
2. Choose **Test** beside a model. It sends a real short request and reports the result.
3. Switch the model on once its test works, and pick the default with the radio button.

A name added by hand starts switched on. A loaded name never does, because a listed name may not work. A model that is switched off cannot be used by anyone, but its ticks are kept, so switching it on again restores access. A model can be removed only when no one has it ticked.

## Who may use which

The admin ticks the models each person may use on **Users**, and picks their default from those. A person with no model ticked cannot start a run or send a chat message, and the refusal says so (AQE-ALLOW-001). Every use is checked, including the account default and an agent's model. An attempt to use a model that is not allowed is refused, and the attempt is logged against the account.

## Which model a call uses

The first match wins.

| Order | Source |
|---|---|
| 1 | The model picked for the run or chat. The picker sits on each run form and in Copilot. Leave it on Default to go on to the next row |
| 2 | The agent's model, if an admin has set one |
| 3 | The account's default |
| 4 | The system default, set on **Settings** |

Each call records the model it really used.

## Token limits

Each person can have limits on total tokens, in these periods.

| Limit | Resets |
|---|---|
| Allocation | Never. The admin raises it |
| Daily | Midnight |
| Weekly | Monday at midnight |
| Monthly | The 1st, at midnight |
| Per model | Its own daily, weekly, or monthly figure, for one model |

Periods follow the time zone set on **Settings**, which is Asia/Kolkata by default. Tokens count for the account that started each call, and a run is charged to the person who started it.

When a limit is reached, the run or chat stops at its next model call. The error (AQE-ALLOW-002) names the limit and the time it resets. Finished batches are kept. After the reset, **Retry failed stage** continues the work. Admin work, including agent evaluations, is never counted against a user.

## Seeing usage

- The header shows the tokens left today or in the allocation, whichever is tighter. It turns amber at 80 percent used.
- **Account** shows your own models, limits, and usage.
- **Usage** (admin only) shows tokens by day, user, model, and agent, for the last 7, 30, 90, or 365 days, with a CSV download.`,
      },
      {
        slug: "settings",
        title: "Environment settings",
        summary: "Settings you can change without touching code.",
        body: `## Settings

Put these in \`.env\`, or in Azure's environment variables. They keep the \`ATLAS_\` prefix so existing installs continue to work.

| Name | Default | Purpose |
|---|---|---|
| \`OPENAI_BASE_URL\`, \`OPENAI_API_KEY\`, \`DEFAULT_MODEL\` | None | Model, unless set on the Settings page |
| \`ATLAS_DATA_DIR\` | \`data\` | Runtime data |
| \`ATLAS_RUN_TOKEN_LIMIT\` | 600000 | Token budget for one run |
| \`ATLAS_MODEL_TIMEOUT\` | 180 | Seconds before one model call fails |
| \`ATLAS_MODEL_CONCURRENCY\` | 4 | Model calls at once |
| \`ATLAS_DATABASE_URL\` | None | PostgreSQL connection. Locally \`python scripts/dev.py db\` fills it in; on Azure it comes from Key Vault |
| \`ATLAS_KEY_VAULT_URL\` | None | Azure: read the secrets from this Key Vault at startup with the app's managed identity |
| \`ATLAS_PORT\`, \`ATLAS_UI_PORT\` | 8000, 3000 | Local ports |
| \`ATLAS_ALLOWED_ORIGINS\`, \`ATLAS_ALLOWED_HOSTS\` | Local addresses | Who may call the API |
| \`ATLAS_ADMIN_USERNAME\`, \`ATLAS_ADMIN_PASSWORD\` | None | The administrator's sign-in. Nobody can sign in until both are set |
| \`ATLAS_SESSION_HOURS\` | 12 | Hours before a session ends |
| \`ATLAS_SESSION_IDLE_MINUTES\` | 480 | Minutes without activity before a session ends |
| \`ATLAS_LOG_RETENTION_DAYS\` | 30 | Days of daily log files to keep |
| \`ATLAS_MODEL_NO_CACHE\` | 1 | Asks the model proxy not to answer from its cache, so a retry is a real retry. Set 0 only if the endpoint rejects the field |`,
      },
      {
        slug: "azure",
        title: "Deploy to Azure",
        summary: "Run on App Service, PostgreSQL, Blob and Key Vault for about $20.62 (₹1,963) a month.",
        body: `## Cost (East US 2, under the $25 cap)

One Linux App Service plan B1 holds both web apps ($12.41 a month). PostgreSQL Flexible Server B1ms runs 12 hours on weekdays ($4.49 compute, $3.68 for 32 GiB storage). Blob Storage and Key Vault cost under $0.11. The total is about $20.62 (₹1,963) a month before taxes; always on, it is about $28.54 (₹2,718). Prices are pay-as-you-go from Azure's retail prices on 12 November 2026. Model tokens are extra.

## Steps

1. Run \`python scripts/package_azure_kudu.py\`, then \`python scripts/dev.py azure-local --check\`. It must print \`API health: 200; UI /login: 200\`.
2. In the Azure portal, create the resource group, Key Vault (three secrets), PostgreSQL, the storage account with the \`downloads\` container, the B1 plan and the two web apps.
3. Give the API's managed identity the role Key Vault Secrets User, and add the app settings and startup commands.
4. Upload each zip through Kudu's ZipDeployUI. The server builds its own environment on first start.
5. Open the PostgreSQL firewall to the API, lock the API to the UI, and schedule PostgreSQL to stop outside working hours.

The complete click-by-click guide is in \`docs/AZURE_DEPLOYMENT_GUIDE.md\`.

Azure has not been deployed for real yet, so treat the steps as untested until you try them.`,
      },
      {
        slug: "troubleshooting",
        title: "Troubleshooting",
        summary: "Common problems and what to do.",
        body: `## Common problems

| Symptom | Do this |
|---|---|
| Model shows missing | Set it in **Settings**, then choose **Test connection** |
| Run stopped for token use | Raise \`ATLAS_RUN_TOKEN_LIMIT\`, or use a smaller repository |
| Scan says some files were not reviewed | The token budget ran out. Raise the limit and scan again |
| Test verdict is INCONCLUSIVE | No test ran. Tick install dependencies, and check that a test runner is detected |
| Run shows interrupted | The app restarted during the run. Choose **Retry failed stage** to resume from the last saved checkpoint |
| Start refused, naming a run already in progress | Only one run of each kind can be active in a project. Open the run it names, and finish or cancel it |
| Limit reached (AQE-ALLOW-002) | Wait for the reset time in the message, or ask an administrator to raise the limit |
| Model not allowed for this account | Ask an administrator to tick that model for you on the Users page |
| Private clone fails | Check the token's repository access in **Settings** |
| Port is in use | Set \`ATLAS_PORT\` and \`ATLAS_UI_PORT\` |

## Find the cause

Open **Observability**, choose the run, and select the error line for details.`,
      },
      {
        slug: "error-codes",
        title: "Error codes",
        summary: "Every error code, what it means, whether a retry can help, and what to do.",
        body: `## Codes

Each failed stage records one code. The run page shows it with the message and the action to take. Failures are grouped by code and agent on **Observability**, under **Errors**.

| Code | Meaning | Retry can help | What to do |
|---|---|---|---|
| AQE-MODEL-001 | The model reply was empty or was not valid JSON | Yes | Retry the stage. The saved reply shows the exact character that broke. |
| AQE-MODEL-002 | The model reply was cut off at the agent's token limit | No | Raise the agent's token limit on the Agents page, then retry the stage. |
| AQE-MODEL-003 | The model sent JSON with a missing or wrong field | Yes | Retry the stage. The message names the missing or wrong field. |
| AQE-MODEL-004 | The model did not reply in time. Message: The model did not reply in time. | Yes | Check the model endpoint, or raise ATLAS_MODEL_TIMEOUT, then retry the stage. |
| AQE-MODEL-005 | The model provider blocked the request under its content policy. Message starts: The model provider blocked this request | No | Remove the flagged text from the input or the repository, then retry the stage. |
| AQE-MODEL-006 | The model endpoint rejected the API key, refused the request, or cannot be reached. Messages: The model endpoint rejected the API key (HTTP {code}). The model endpoint is busy or failing (HTTP {code}). Cannot reach the model endpoint. | No, except when the endpoint is busy or failing (HTTP 429 or 5xx) or cannot be reached: then Yes | Open Settings and check the base URL, model, and API key, then retry the stage. For busy or failing endpoints the action is: Wait a moment and retry the stage. If it keeps happening, check the provider. |
| AQE-ALLOW-001 | The account has no time or tokens left, may not use the model chosen, or has no model ticked, or the run reached its token limit | No | Ask your administrator to raise the allocation or tick the model, then retry the stage. |
| AQE-ALLOW-002 | A daily, weekly, monthly, or per-model token limit is reached. The message names the limit and when it resets | No, until the reset time | Wait for the reset, or ask your administrator to raise the limit, then use Retry failed stage. A run keeps its finished batches. |
| AQE-REPO-001 | The repository address or access token did not work | No | Check the repository address and access token, then try again. |
| AQE-EVID-001 | No requirement passed evidence checks. No quote was found on disk at the stated file and line | No | Review the requirements and the repository, then retry the stage. |
| AQE-TEST-001 | Dependencies could not be installed, so the tests could not run | No | Tick install dependencies for this run, or fix the environment, then retry the stage. |
| AQE-INT-001 | An unexpected error. The message gives the exception type and a short description | No | Copy the diagnostics and report it. |

"Retry can help" means a plain retry may succeed without any change. The run page still offers Retry failed stage for every failed run, because the fix named in the action may already be done.

## Retry failed stage

A failed run shows **Retry failed stage**. It repeats the stage that failed, not the whole run. Use it after you have applied the fix named in the action. Design and generate keep the batches they finished, so only the unfinished part runs again. A retry counts against the same limits as the first attempt. An interrupted run can be retried the same way.

## Copy diagnostics

**Copy diagnostics** copies the run's error code, message, action, and technical details to the clipboard, so you can attach them to a report. Secrets are masked before the copy is made.

## Saved replies

Each failed stage keeps one diagnostic record, with a redacted stack trace. When the model's reply was the problem, the whole reply is saved with the run, with secrets masked, so you can see the exact text that broke.

## Partial results

A stage that keeps failing after its retries can end with a partial result. The run page then lists the missing requirements. A partial result is marked PARTIAL in its document, and it **cannot be approved**. Send it back, or fix the cause named in the error and run the stage again.`,
      },
    ],
};

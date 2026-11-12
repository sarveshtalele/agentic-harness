# Desktop release guide: build, publish to Blob, show on the login page

This guide puts a new version of the desktop app where users can download it from the web app's login page. It is phase H7 of `docs/MASTER_PLAN.md`. GitHub never connects to Azure: GitHub Actions builds the installers, and you upload them yourself.

| Step | Where | Result |
|---|---|---|
| 1. Build | GitHub Actions, workflow `desktop` (every push to the feature branch that touches the app, every tag) | three installer artifacts plus `desktop-latest-json`; a `v*` tag also makes a GitHub Release |
| 2. Check | Your computer | SHA-256 values match the manifests |
| 3. Publish | Azure portal, Storage account | DMG, zip, MSI and `latest.json` in the `downloads` container |
| 4. Point the UI at it | Azure portal, UI web app | `ATLAS_DOWNLOADS_URL` app setting |
| 5. Verify | Browser | Login page shows the links, version and SHA-256 |

## 1. Build the installers in GitHub Actions

1. On GitHub, open the repository, then **Actions**, then the **desktop** workflow.
2. It starts by itself on every push to `feature/maf-harness-platform` that changes `apps/desktop`, `src`, `scripts/desktop_build.py` or `requirements.txt`, and on every `v*` or `desktop-*` tag. To start it by hand, select **Run workflow** and choose the branch or tag.
3. Wait for the three build jobs to finish. Each builds for its own processor, because the bundled backend is built for the machine it runs on:
   - `macos-latest` / `arm64`: DMG and zip for Apple silicon;
   - `macos-15-intel` / `x64`: DMG and zip for Intel Macs;
   - `windows-latest` / `x64`: the MSI.

   Then the `manifest` job merges their manifests into one `latest.json`.
4. Open the finished run. Under **Artifacts**, download the three `desktop-…` artifacts and `desktop-latest-json`.
5. Unzip them. You now have:
   - macOS: `agentic-qe-<version>-mac-arm64.dmg`, `agentic-qe-<version>-mac-x64.dmg`, and the zips (`...-mac-arm64.zip`, `...-mac-x64.zip`). The names have no spaces, so GitHub Releases, Blob Storage and `latest.json` all use the same name;
   - Windows: `agentic-qe-<version>-win-x64.msi`;
   - `latest.json`, listing every installer with its size and SHA-256.

**A `v*` tag** (for example `git tag v0.2.0 && git push origin v0.2.0`) also runs the `release` job, which publishes the installers and `latest.json` as a GitHub Release with the same name.

**Building on a Mac without CI:** `python scripts/desktop_build.py` builds the UI, the PyInstaller backend and the DMG on this machine. The MSI can only be built on Windows.

## 2. Check the files

Every `latest-*.json` lists each installer's name, size and SHA-256. Compare them before you upload.

- **macOS or Linux:** `shasum -a 256 agentic-qe-0.1.0-mac-arm64.dmg`
- **Windows (PowerShell):** `Get-FileHash agentic-qe-0.1.0-win-x64.msi -Algorithm SHA256`

If a value differs, do not publish. Download the artifact again.

CI already merged the manifests into `latest.json`. To merge them yourself, put the per-runner `latest-*.json` files in one folder and run `python scripts/desktop_build.py --merge <folder>`. It refuses manifests of different versions, which means the jobs built different commits; run the workflow again.

## 3. Publish to the Blob `downloads` container (Azure portal, eastus2)

The Storage account comes from the Azure guide, `docs/AZURE_DEPLOYMENT_GUIDE.md` (section 8).

### Create the container once

1. Allow anonymous read on the account:
   - in the portal, open the **Storage account**, then **Settings, Configuration**;
   - set **Allow Blob anonymous access** to **Enabled** and select **Save**.

   This only allows it; each container still decides for itself. All other containers stay private.
2. Create the container:
   - **Data storage, Containers**, then **+ Container**;
   - Name: `downloads`;
   - **Anonymous access level: Blob (anonymous read access for blobs only)**. Never choose "Container"; that would let anyone list the files;
   - select **Create**.

### Upload a version

1. Open the `downloads` container and select **Upload**.
2. Add the DMG files, the macOS zips, the MSI and `latest.json`.
3. Tick **Overwrite if files already exist**, so `latest.json` is replaced.
4. Under **Advanced**, keep **Blob type: Block blob**.
5. Select **Upload**.
6. Open `latest.json` in the container, select **Properties**, and set **Cache-Control** to `no-cache`, then **Save**. Without this, browsers may keep showing the old version for a while.
7. Copy the container URL from **Properties**, for example `https://<account>.blob.core.windows.net/downloads`.

Older installers can stay in the container. The login page links only the files listed in `latest.json`.

## 4. Point the UI at the container

1. Open the **UI web app** (`aqe-ui-<yourname>`), then **Settings, Environment variables, App settings**.
2. Add `ATLAS_DOWNLOADS_URL` with the container URL from step 3.7, with no trailing slash.
3. Select **Apply**, then restart the app.

## 5. Verify

1. Open the web app's login page in a private browser window.
2. Under **Desktop app** it shows:
   - **Download for Windows (MSI)**;
   - **Download for macOS (DMG, Apple silicon)** and **(Intel)**;
   - the version, and each file's size and SHA-256.
3. Click each link. The download must start, and the file's SHA-256 must match.
4. If the section says "No desktop installer is published yet", check:
   - that `latest.json` exists in the container and opens in the browser at `<container URL>/latest.json`;
   - that the app setting has no typo.

The page never shows a link that `latest.json` does not list.

## 6. Publish without Azure: a GitHub Release

Anyone with the link can download from a GitHub Release, so this works with or without the Blob container.

- **Automatic.** Push a tag such as `v0.2.0`. The `release` job attaches the DMGs, the zips, the MSI and `latest.json` to a release of that name.
- **By hand.**
  1. On GitHub, open the repository, then **Releases**, then **Draft a new release**.
  2. Choose or create a tag (for example `v0.2.0`) on `feature/maf-harness-platform`.
  3. Drag in the files from the run's artifacts:
     - `agentic-qe-<version>-mac-arm64.dmg`;
     - `agentic-qe-<version>-mac-x64.dmg`;
     - `agentic-qe-<version>-win-x64.msi`;
     - `latest.json`.
  4. In the description, paste the SHA-256 values from `latest.json`.
  5. Select **Publish release**.
- **The repository is private?** Then only people with access can download. To share wider, use the Blob container (section 3) or make a public releases repository.

## 7. Install the desktop app (for everyone)

**1. Get the installer.** Use one of:
- the web app's home page or sign-in page, **Download** section;
- the GitHub Release page;
- a link the admin sends.

| Your computer | File |
|---|---|
| Mac with Apple silicon (Apple menu, **About This Mac**, Chip: Apple M1 or later) | `agentic-qe-<version>-mac-arm64.dmg` |
| Mac with an Intel processor (Processor: Intel) | `agentic-qe-<version>-mac-x64.dmg` |
| Windows 10 or 11, 64-bit | `agentic-qe-<version>-win-x64.msi` |

**2. Check the file** (recommended). Its SHA-256 must equal the value on the download page or in `latest.json`:
- macOS: `shasum -a 256 ~/Downloads/agentic-qe-<version>-mac-arm64.dmg`;
- Windows PowerShell: `Get-FileHash "$env:USERPROFILE\Downloads\agentic-qe-<version>-win-x64.msi" -Algorithm SHA256`.

**3. Install PostgreSQL once** (version 16 or newer). The app keeps its data in its own local PostgreSQL cluster and starts it by itself. It needs the PostgreSQL programs on the computer:
- macOS: `brew install postgresql@17` (with Homebrew), or the installer from postgresql.org;
- Windows: the installer from postgresql.org. Keep the default folder; you do not need to create a database.

**4. Install the app.**
- **Windows.** Double-click the MSI and follow the steps. The installers are not signed yet: if SmartScreen shows "Windows protected your PC", select **More info**, then **Run anyway**.
- **macOS.** Open the DMG and drag **Agentic QE Platform** into **Applications**. On first launch, right-click the app, select **Open**, then **Open** again. If macOS says the app "is damaged", run this once in Terminal, then open it again:
  ```bash
  xattr -dr com.apple.quarantine "/Applications/Agentic QE Platform.app"
  ```

**5. First run.** The app asks for a local admin username and a password of at least 12 characters, stored with the operating system's keychain encryption. Then the home page opens; select **Sign in**. The model is set on **Settings**.

**Where the app keeps things** (`<data>` is `~/Library/Application Support/Agentic QE Platform/data` on macOS, `%APPDATA%\Agentic QE Platform\data` on Windows):

| What | Where |
|---|---|
| Database (local PostgreSQL cluster) | `<data>/postgres` |
| Projects, repository clones, workspaces | `<data>/projects` |
| Harness conversations: one JSONL file per chat session, one message per line, written by MAF's file history | `<data>/harness/<project id>/history/~session-<id>.jsonl` |
| Harness todos and per-user memory | `<data>/harness/<project id>/todos`, `<data>/harness/<project id>/memory/<user id>` |
| Plugins' own state (for example agentic-qe's validator environment) | `<data>/harness/plugin-home` |
| Logs | `<data>/logs/app-DAY.jsonl`, `errors-DAY.jsonl`, and `../logs/backend.log` |

**Uninstall.**
- Windows: **Settings**, **Apps**, then **Agentic QE Platform**, **Uninstall**.
- macOS: drag the app to the Bin.

The data folder above stays until you delete it.

## 8. What the desktop app can do that the web app cannot

The desktop app runs on the user's own computer, so it allows what a shared server must not:

- **MCP servers started by a command** (stdio).
  - To add one, an admin opens **MCP**, **Add server**, and sets:
    - **Transport:** stdio;
    - **Command:** `npx` (or `node`, `uvx`, `python`, `python3`, or a full path to a program);
    - **Arguments:** select **Add argument** for each, for example `-y`, then `@modelcontextprotocol/server-filesystem@<version>`, then the folder it may read;
    - **Environment:** secret values, stored encrypted and never shown again.
  - Then select **Connect**: the tools come from the server's own `list_tools`.
  - Then **grant** each tool to the roles that may use it.

  Pin the package version (`@<version>`), because `npx -y` runs whatever version it downloads.
- **Plugins.**
  1. **Settings**, **Plugins**, **Upload** takes a plugin zip (Claude Code format).
  2. Enable it, and grant it to roles.
  3. Its skills, commands (`/plugin:command` in the harness), hooks and agents load on the next harness turn.
  4. MCP servers its `.mcp.json` declares appear on **MCP**, not connected, until an admin connects them.
- **Scope today.** MCP servers and plugins are **platform-wide**, one list per installation. **Per role:** tools and plugins are granted to roles. **Per project:** only members see a project. **Per chat session:** a session gets the tools its user's role was granted, plus the ones it loads with `load_tools`; nothing is configured per session. Project-level and session-level MCP configuration (as in Claude Code's project `.mcp.json`) is not built. A repository's own `.mcp.json` is never started by itself, because repository content is untrusted.
- **Terminal harness.** `bin/harness` (macOS and Linux), `bin\harness.bat` or `bin\harness.ps1` (Windows) runs the same harness in a terminal against the same data.

## 9. Releasing a new version

1. Raise `version` in `apps/desktop/package.json`, for example `0.2.0`, and commit.
2. Push a tag `desktop-0.2.0`, or run the workflow by hand.
3. Repeat steps 2 to 5. Upload the new installers and the new `latest.json`. The login page switches to the new version on its next load.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| The workflow fails at `npm ci` | The lock file is out of date | Run `npm install` in `src/frontend` or `apps/desktop` locally, commit the lock file |
| The macOS job fails in PyInstaller | A missing hidden import | Read the job log for `ModuleNotFoundError` and add the module to `--collect-all` in `scripts/desktop_build.py` |
| The download link returns 404 or `PublicAccessNotPermitted` | Anonymous access is off on the account or the container | Repeat "Create the container once" |
| The app opens and shows "Port 18765 is already in use" | Another program, or an earlier copy of the app, holds the port | Quit it. Or rebuild with `AQE_DESKTOP_API_PORT` set to another port |
| The app starts but the window never opens | The backend failed to start | Read `backend.log` in the app's data folder: macOS `~/Library/Application Support/Agentic QE Platform/logs/`, Windows `%APPDATA%\Agentic QE Platform\logs\` |

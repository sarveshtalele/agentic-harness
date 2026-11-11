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
   - macOS: `Agentic QE Platform-<version>-arm64.dmg`, `...-x64.dmg`, and the zips;
   - Windows: `Agentic QE Platform <version>.msi`;
   - `latest.json`, listing every installer with its size and SHA-256.

**A `v*` tag** (for example `git tag v0.2.0 && git push origin v0.2.0`) also runs the `release` job, which publishes the installers and `latest.json` as a GitHub Release with the same name.

**Building on a Mac without CI:** `python scripts/desktop_build.py` builds the UI, the PyInstaller backend and the DMG on this machine. The MSI can only be built on Windows.

## 2. Check the files

Every `latest-*.json` lists each installer's name, size and SHA-256. Compare them before you upload.

- **macOS or Linux:** `shasum -a 256 "Agentic QE Platform-0.1.0-arm64.dmg"`
- **Windows (PowerShell):** `Get-FileHash "Agentic QE Platform 0.1.0.msi" -Algorithm SHA256`

If a value differs, do not publish. Download the artifact again.

CI already merged the manifests into `latest.json`. To merge them yourself, put the per-runner `latest-*.json` files in one folder and run `python scripts/desktop_build.py --merge <folder>`. It refuses manifests of different versions, which means the jobs built different commits; run the workflow again.

## 3. Publish to the Blob `downloads` container (Azure portal, eastus2)

The Storage account comes from the Azure guide, `docs/AZURE_POSTGRES_BLOB_PORTAL_GUIDE.md`.

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

## 6. How users open the app (it is not signed yet)

The installers are unsigned until the owner provides signing certificates (`CSC_LINK` for Windows, an Apple Developer ID for macOS). Until then:

- **Windows.** Run the MSI. If SmartScreen shows "Windows protected your PC", select **More info**, then **Run anyway**.
- **macOS.** Open the DMG and drag the app into Applications. On first launch, right-click the app, select **Open**, then **Open** again. If macOS says the app "is damaged", run this once in Terminal:
  ```bash
  xattr -dr com.apple.quarantine "/Applications/Agentic QE Platform.app"
  ```

**First run.** The app asks for a local admin username and a password of at least 12 characters. They are stored with the operating system's keychain encryption and never leave the machine.

The desktop app runs everything locally, data included: the harness, plugin installs, npx commands, local and remote MCP servers. Nothing is shared with the web app unless the user exports it.

## 7. Releasing a new version

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

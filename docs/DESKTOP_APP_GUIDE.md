# Desktop App Guide

Status: written 2026-11-10. The code is in place and syntax-checked. The Electron download was refused in the build sandbox, so no installer and no dev-mode run has been verified yet.

## What it is

`apps/desktop` is an Electron shell. On start it launches two loopback-only children and opens a window on the UI:

| Child | Packaged | Dev |
|---|---|---|
| Backend, port 18765 | PyInstaller one-folder `resources/backend/atlas-backend` | `python -m uvicorn backend.app:app` with `PYTHONPATH=src:.` |
| UI, port 18766 | Next.js standalone `resources/ui/server.js`, run by the Electron binary with `ELECTRON_RUN_AS_NODE=1` | the same, from `apps/desktop/build/ui` |

The backend runs with `ATLAS_PROFILE=desktop`, data in `<userData>/data`, and `ATLAS_ALLOWED_ORIGINS` set to the UI origin. Logs go to `<userData>/logs/backend.log` and `ui.log`. Closing the app stops both children (`taskkill /T` on Windows).

Ports are fixed because Next.js bakes the backend URL in at build time. Override the API port with `AQE_DESKTOP_API_PORT` at build and run time, the UI port with `AQE_DESKTOP_UI_PORT`. A busy port shows an error dialog naming it.

## First run and security

A setup window asks for a local admin username and a password of at least 12 characters. They are stored with Electron `safeStorage` in `<userData>/admin.bin`; a random `ATLAS_SECRET_KEY` is made once in `secret.bin`. All three reach the backend by environment, never argv. If the OS keychain is unavailable the app refuses to store them. Windows use `contextIsolation`, `sandbox`, no `nodeIntegration`; navigation stays on the UI origin and other http(s) links open in the system browser.

## Build

```
npm ci            # in src/frontend and apps/desktop
python -m pip install -r requirements.txt pyinstaller
python scripts/desktop_build.py          # UI + backend + installers for this OS
python scripts/desktop_build.py --ui     # UI only (enough for dev mode)
```

Output goes to `apps/desktop/dist/`: DMG and zip (arm64, x64) on macOS, MSI (x64) on Windows. The MSI must be built on Windows; CI does it on `windows-latest` (`.github/workflows/desktop.yml`, manual run or a `v*` / `desktop-*` tag). Builds are unsigned unless `CSC_LINK` is set.

## Run in dev mode

```
python scripts/desktop_build.py --ui
cd apps/desktop && npm install && npx electron .
```
Set `AQE_DESKTOP_USER_DATA` to use a throwaway data folder. Test: `AQE_DESKTOP_TEST=1 pytest tests/desktop -m desktop`.

## Opening an unsigned app

- **macOS:** open the DMG, drag the app to Applications. On first launch right-click the app, choose Open, then Open again. If macOS says it is damaged, run `xattr -dr com.apple.quarantine "/Applications/Agentic QE Platform.app"`.
- **Windows:** run the MSI. On the SmartScreen prompt choose More info, then Run anyway.

## Limits

No auto-update, no Linux build, no signing. The packaged backend is not yet proven to start: PyInstaller hidden imports for `agent_framework` and `chromadb` may need adjusting after the first real build.

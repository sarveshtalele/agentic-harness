#!/usr/bin/env python3
"""
package_azure_kudu.py - Packaging automation for Azure App Service & Kudu ZipDeploy

Generates production-ready, clean deployment zip archives for:
  1. dist/azure_backend.zip  (FastAPI, Uvicorn, prompts, templates, skills, evals, startup.sh, Kudu Oryx .deployment, web.config)
  2. dist/azure_frontend.zip (Next.js 16 app, package.json, next.config.ts, startup.sh, startup.js, Kudu Oryx .deployment, web.config)

Designed specifically for environments with NO GitHub Actions / CI/CD pipeline,
enabling direct upload via Azure Portal Kudu ZipDeploy or REST API.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # run directly, only scripts/ is on sys.path
    sys.path.insert(0, str(ROOT))

from scripts.azure.archive import create_zip, verify_kudu  # noqa: E402
from scripts.azure.files import backend_entries, collect_folder, frontend_source_entries, git_tracked  # noqa: E402
from scripts.azure.logs import make_logger  # noqa: E402
from scripts.azure.preflight import kudu_preflight  # noqa: E402

DIST = ROOT / "dist"
DEPLOY_DIR = ROOT / "deploy/azure"
log, _warn, error = make_logger("package_kudu")
# New, uncommitted files are shipped; .gitignore keeps .env, data/ and builds out.
TRACKED = git_tracked(ROOT)
create_zip_archive = create_zip


def run_preflight_checks() -> bool:
    return kudu_preflight(ROOT, log, error)


def collect_folder_files(folder: Path, base_dir: Path) -> dict[str, Path]:
    return collect_folder(folder, base_dir, TRACKED)


def gather_backend_entries() -> dict[str, Path]:
    """Backend files: startup scripts, src/backend plus a backend/ alias, prompts, templates, skills and evals."""
    entries = backend_entries(ROOT, DEPLOY_DIR, TRACKED)
    entries["toolchains.py"] = DEPLOY_DIR / "toolchains.py"  # startup.py downloads Node, JDK, Maven, .NET, Go and Chromium into /home/tools
    entries.update(collect_folder_files(ROOT / "plugins" / "agentic-qe", ROOT))  # read at runtime by qe/plugin_bridge.py
    return entries


def gather_frontend_entries() -> dict[str, Path]:
    """Frontend sources plus startup.sh, startup.js, .deployment, web.config and staticwebapp.config.json."""
    return frontend_source_entries(ROOT, DEPLOY_DIR, TRACKED)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package Azure Kudu ZipDeploy bundles for Agentic QE Platform")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip pre-flight syntax and integrity checks")
    args = parser.parse_args()

    log("==================================================================")
    log(" Azure App Service / Kudu ZipDeploy Packaging Automation")
    log(" Target Region: eastus2")
    log("==================================================================")

    if not args.skip_preflight:
        if not run_preflight_checks():
            error("Pre-flight checks failed. Aborting packaging.")
            return 1

    DIST.mkdir(parents=True, exist_ok=True)

    # 1. Package Backend
    log("\n[1/2] Building Backend Zip: dist/azure_backend.zip...")
    backend_entries = gather_backend_entries()
    backend_meta = create_zip(DIST / "azure_backend.zip", backend_entries)

    # Verify Backend Zip
    backend_critical = ["startup.sh", "startup.py", "toolchains.py", ".deployment", "web.config", "requirements.txt", "src/backend/app.py", "backend/app.py", "plugins/agentic-qe/plugin.json", "templates/stacks/go/stack.json"]
    if not verify_kudu(backend_meta, backend_critical, log, error):
        error("Backend zip verification failed!")
        return 1

    # Also duplicate/link as agentic-qe-backend.zip for backward compatibility
    shutil.copy2(DIST / "azure_backend.zip", DIST / "agentic-qe-backend.zip")

    # 2. Package Frontend
    log("\n[2/2] Building Frontend Zip: dist/azure_frontend.zip...")
    frontend_entries = gather_frontend_entries()
    frontend_meta = create_zip(DIST / "azure_frontend.zip", frontend_entries)

    # Verify Frontend Zip
    frontend_critical = ["startup.sh", "startup.js", ".deployment", "web.config", "package.json", "next.config.ts"]
    if not verify_kudu(frontend_meta, frontend_critical, log, error):
        error("Frontend zip verification failed!")
        return 1

    # Also duplicate/link as agentic-qe-frontend.zip for backward compatibility
    shutil.copy2(DIST / "azure_frontend.zip", DIST / "agentic-qe-frontend.zip")

    # Summary Report
    log("\n==================================================================")
    log(" Packaging Completed Successfully!")
    log("==================================================================")
    for meta, title in [(backend_meta, "Backend Bundle"), (frontend_meta, "Frontend Bundle")]:
        log(f"--- {title} ---")
        log(f"  File:              {meta['path'].relative_to(ROOT)}")
        log(f"  Total Files:       {meta['count']}")
        log(f"  Uncompressed Size: {meta['uncompressed_bytes'] / (1024 * 1024):.2f} MB")
        log(f"  Compressed Size:   {meta['compressed_bytes'] / (1024 * 1024):.2f} MB")
        log(f"  SHA256:            {meta['sha256']}")

    log("\nKudu ZipDeploy Instructions:")
    log("  Backend deploy URL:  https://<backend-app-name>.scm.azurewebsites.net/api/zipdeploy")
    log("  Frontend deploy URL: https://<frontend-app-name>.scm.azurewebsites.net/api/zipdeploy")
    log("  (Linux apps: use the zipdeploy API above or `az webapp deploy --type zip`; Microsoft documents the Kudu drag-and-drop ZipDeploy page as not working on Linux.)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

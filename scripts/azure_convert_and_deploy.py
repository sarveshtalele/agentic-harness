#!/usr/bin/env python3
"""
azure_convert_and_deploy.py - End-to-End Azure App Service / Kudu Conversion & Deployment Automation

This script converts the Agentic QE Platform repository into production-ready Azure App Service
deployment packages (ZIP archives) and optionally deploys them directly to Azure Kudu.

Capabilities:
  1. CONVERT / PACKAGE:
     - Backend: Builds dist/azure_backend.zip with FastAPI app, MAF 2.0 workflows, skills, prompts,
       templates, evals, requirements.txt, startup.sh, startup.py, .deployment, and web.config.
     - Frontend: Builds dist/azure_frontend.zip with Next.js 16 app, startup.sh, startup.js,
       .deployment, web.config, and staticwebapp.config.json.
     - Optional --build-frontend flag to pre-compile Next.js standalone bundle for instant B1 startup.
  2. DEPLOY TO KUDU:
     - Directly deploys generated ZIPs to Azure App Service via Azure CLI (`az webapp deploy`)
       or Kudu REST API (`/api/zipdeploy`).
  3. INFRASTRUCTURE SETUP GENERATOR:
     - Emits Azure CLI scripts for 1-time setup of Resource Group, App Service Plan, WebApps, and DBs.

Usage:
  python scripts/azure_convert_and_deploy.py --convert
  python scripts/azure_convert_and_deploy.py --convert --build-frontend
  python scripts/azure_convert_and_deploy.py --deploy --resource-group rg-agentic-eastus2 --backend-app app-backend --frontend-app app-frontend
  python scripts/azure_convert_and_deploy.py --print-setup
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # run directly, only scripts/ is on sys.path
    sys.path.insert(0, str(ROOT))

from scripts.azure.archive import create_zip, verify_convert  # noqa: E402
from scripts.azure.deploy import build_frontend_standalone, deploy_to_azure as _deploy_to_azure  # noqa: E402
from scripts.azure.files import backend_entries, collect_folder, frontend_source_entries, frontend_standalone_entries  # noqa: E402
from scripts.azure.logs import make_logger  # noqa: E402
from scripts.azure.preflight import convert_preflight  # noqa: E402
from scripts.azure.setup_script import generate_setup_script  # noqa: E402

DIST = ROOT / "dist"
DEPLOY_DIR = ROOT / "deploy/azure"
log, warn, error = make_logger("Azure-Kudu")
create_archive = create_zip


def run_preflight_checks() -> bool:
    """Validates source syntax, required assets, and configuration files."""
    return convert_preflight(ROOT, DEPLOY_DIR, log, error)


def collect_folder_files(folder: Path, base_dir: Path) -> Dict[str, Path]:
    return collect_folder(folder, base_dir)


def gather_backend_files() -> Dict[str, Path]:
    """Collects complete backend files mapped for Azure App Service execution."""
    return backend_entries(ROOT, DEPLOY_DIR)


def gather_frontend_files(prebuilt_standalone: bool = False) -> Dict[str, Path]:
    """Collects frontend files for either source-based or prebuilt-standalone deployment."""
    if prebuilt_standalone:
        return frontend_standalone_entries(ROOT, DEPLOY_DIR, log)
    return frontend_source_entries(ROOT, DEPLOY_DIR)  # source-based package for Oryx to build


def verify_archive(meta: Dict[str, Any], required_files: List[str], allowed_dirs: Optional[Set[str]] = None) -> bool:
    return verify_convert(meta, required_files, error, allowed_dirs)


def deploy_to_azure(*args, **kwargs) -> bool:
    return _deploy_to_azure(*args, log=log, error=error, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert, Package, and Deploy Agentic QE Platform to Azure App Service / Kudu"
    )
    parser.add_argument("--convert", action="store_true", default=True, help="Convert and package code into deployable zip archives (default: True)")
    parser.add_argument("--build-frontend", action="store_true", help="Pre-build Next.js standalone bundle locally before packaging")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip pre-flight syntax and verification checks")
    parser.add_argument("--deploy", action="store_true", help="Deploy generated zip archives directly to Azure Kudu")
    parser.add_argument("--resource-group", default=os.environ.get("AZURE_RESOURCE_GROUP", "rg-agentic-harness-eastus2"), help="Azure Resource Group")
    parser.add_argument("--backend-app", default=os.environ.get("AZURE_BACKEND_APP", ""), help="Azure Backend App Service name")
    parser.add_argument("--frontend-app", default=os.environ.get("AZURE_FRONTEND_APP", ""), help="Azure Frontend App Service name")
    parser.add_argument("--print-setup", action="store_true", help="Print authoritative 1-time Azure infrastructure setup script")
    parser.add_argument("--write-setup-script", action="store_true", help="Write 1-time setup script to deploy/azure/setup_azure_infrastructure.sh")

    args = parser.parse_args()

    if args.print_setup:
        print(generate_setup_script(args.resource_group, backend_app=args.backend_app or "agentic-backend", frontend_app=args.frontend_app or "agentic-frontend"))
        return 0

    if args.write_setup_script:
        out_script = DEPLOY_DIR / "setup_azure_infrastructure.sh"
        out_script.write_text(generate_setup_script(args.resource_group, backend_app=args.backend_app or "agentic-backend", frontend_app=args.frontend_app or "agentic-frontend"), encoding="utf-8")
        out_script.chmod(0o755)
        log(f"Setup script written to: {out_script.relative_to(ROOT)}")
        return 0

    log("==================================================================")
    log(" Agentic QE Platform - Azure App Service & Kudu Automation")
    log(" Target Architecture: Azure Linux App Service (B1/P1v3)")
    log("==================================================================")

    if not args.skip_preflight:
        if not run_preflight_checks():
            error("Pre-flight checks failed. Aborting packaging.")
            return 1

    DIST.mkdir(parents=True, exist_ok=True)

    # Pre-build frontend if requested
    if args.build_frontend:
        if not build_frontend_standalone(ROOT, log, error):
            error("Frontend build failed. Aborting packaging.")
            return 1

    # 1. Package Backend
    log("\n[1/2] Converting & Packaging Backend -> dist/azure_backend.zip...")
    backend_entries = gather_backend_files()
    backend_meta = create_zip(DIST / "azure_backend.zip", backend_entries)

    backend_reqs = ["startup.sh", "startup.py", ".deployment", "web.config", "requirements.txt", "src/backend/app.py", "backend/app.py"]
    if not verify_convert(backend_meta, backend_reqs, error):
        error("Backend archive verification failed!")
        return 1
    shutil.copy2(DIST / "azure_backend.zip", DIST / "agentic-qe-backend.zip")

    # 2. Package Frontend
    log("\n[2/2] Converting & Packaging Frontend -> dist/azure_frontend.zip...")
    frontend_entries = gather_frontend_files(prebuilt_standalone=args.build_frontend)
    frontend_meta = create_zip(DIST / "azure_frontend.zip", frontend_entries)

    frontend_reqs = ["startup.sh", "startup.js", ".deployment", "web.config", "package.json", "next.config.ts"]
    allowed_fe_dirs = {"node_modules", ".next"} if args.build_frontend else None
    if not verify_convert(frontend_meta, frontend_reqs, error, allowed_dirs=allowed_fe_dirs):
        error("Frontend archive verification failed!")
        return 1
    shutil.copy2(DIST / "azure_frontend.zip", DIST / "agentic-qe-frontend.zip")

    # Print Summary Report
    log("\n==================================================================")
    log(" Packaging Completed Successfully!")
    log("==================================================================")
    for meta, title in [(backend_meta, "Backend App Service (Python 3.12)"), (frontend_meta, "Frontend App Service (Node 20)")]:
        log(f"--- {title} ---")
        log(f"  Archive:           {meta['path'].relative_to(ROOT)}")
        log(f"  Total Files:       {meta['count']}")
        log(f"  Uncompressed Size: {meta['uncompressed_bytes'] / (1024 * 1024):.2f} MB")
        log(f"  Compressed Size:   {meta['compressed_bytes'] / (1024 * 1024):.2f} MB")
        log(f"  SHA256:            {meta['sha256']}")

    log("\nDirect Kudu ZipDeploy Target Endpoints:")
    log("  Backend:  https://<backend-app>.scm.azurewebsites.net/api/zipdeploy")
    log("  Frontend: https://<frontend-app>.scm.azurewebsites.net/api/zipdeploy")
    log("  Web UI:   https://<app-name>.scm.azurewebsites.net/ZipDeploy")

    # Direct Deployment if --deploy specified
    if args.deploy:
        if not args.backend_app and not args.frontend_app:
            error("--deploy specified but neither --backend-app nor --frontend-app was provided!")
            return 1
        ok = deploy_to_azure(
            resource_group=args.resource_group,
            backend_app=args.backend_app or None,
            frontend_app=args.frontend_app or None,
            backend_zip=DIST / "azure_backend.zip",
            frontend_zip=DIST / "azure_frontend.zip",
        )
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

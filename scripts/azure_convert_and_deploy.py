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
import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
DEPLOY_DIR = ROOT / "deploy/azure"

SKIP_DIRS: Set[str] = {
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "test-results",
    ".git",
    ".github",
    ".sessions",
}

SKIP_FILES: Set[str] = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".DS_Store",
    "Thumbs.db",
    "agent-framework.pdf",
}


def log(msg: str) -> None:
    print(f"[Azure-Kudu] {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"[Azure-Kudu WARNING] {msg}", flush=True)


def error(msg: str) -> None:
    print(f"[Azure-Kudu ERROR] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Pre-Flight Validation Checks
# ---------------------------------------------------------------------------

def run_preflight_checks() -> bool:
    """Validates source syntax, required assets, and configuration files."""
    log("Running pre-flight verification...")
    passed = True

    # 1. Compile backend Python files
    py_files = list((ROOT / "src/backend").rglob("*.py"))
    if not py_files:
        error("No Python source files found under src/backend!")
        passed = False
    else:
        log(f"  Validating syntax of {len(py_files)} Python source files...")
        for p in py_files:
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as exc:
                error(f"  Python syntax error in {p.relative_to(ROOT)}: {exc}")
                passed = False

    # 2. Check requirements.txt
    req_file = ROOT / "requirements.txt"
    if not req_file.is_file() or req_file.stat().st_size == 0:
        error("  requirements.txt is missing or empty!")
        passed = False
    else:
        req_text = req_file.read_text(encoding="utf-8")
        for pkg in ("fastapi", "uvicorn", "pydantic"):
            if pkg not in req_text.lower():
                error(f"  Critical dependency '{pkg}' missing from requirements.txt!")
                passed = False

    # 3. Check assets: prompts, templates, skills, evals
    for folder in ("prompts", "templates", "skills", "evals"):
        fpath = ROOT / folder
        if not fpath.is_dir() or not any(fpath.iterdir()):
            error(f"  Required asset directory '{folder}/' is missing or empty!")
            passed = False

    # 4. Check Frontend package.json
    fe_pkg = ROOT / "src/frontend/package.json"
    if not fe_pkg.is_file():
        error("  src/frontend/package.json is missing!")
        passed = False
    else:
        try:
            pkg = json.loads(fe_pkg.read_text(encoding="utf-8"))
            if "next" not in pkg.get("dependencies", {}):
                error("  'next' dependency missing in frontend package.json!")
                passed = False
        except Exception as exc:
            error(f"  Invalid JSON in frontend package.json: {exc}")
            passed = False

    # 5. Check deployment runner templates
    deploy_templates = [
        DEPLOY_DIR / "backend_startup.sh",
        DEPLOY_DIR / "backend_startup.py",
        DEPLOY_DIR / "frontend_startup.sh",
        DEPLOY_DIR / "frontend_startup.js",
        DEPLOY_DIR / "kudu.deployment",
        DEPLOY_DIR / "backend_web.config",
        DEPLOY_DIR / "frontend_web.config",
    ]
    for dt in deploy_templates:
        if not dt.is_file():
            error(f"  Deployment template missing: {dt.relative_to(ROOT)}")
            passed = False

    if passed:
        log("  Pre-flight verification completed successfully.")
    return passed


# ---------------------------------------------------------------------------
# File Filtering & Gathering
# ---------------------------------------------------------------------------

def should_skip(path: Path, base_dir: Path) -> bool:
    rel_parts = path.relative_to(base_dir).parts
    if path.name in SKIP_FILES:
        return True
    if any(p in SKIP_DIRS for p in rel_parts):
        return True
    if any(p.startswith(".next") for p in rel_parts):
        return True
    if path.suffix in (".pyc", ".pyo"):
        return True
    return False


def collect_folder(folder: Path, base_dir: Path) -> Dict[str, Path]:
    entries: Dict[str, Path] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not path.is_symlink() and not should_skip(path, base_dir):
            rel_name = path.relative_to(base_dir).as_posix()
            entries[rel_name] = path
    return entries


def gather_backend_files() -> Dict[str, Path]:
    """Collects complete backend files mapped for Azure App Service execution."""
    entries: Dict[str, Path] = {
        "requirements.txt": ROOT / "requirements.txt",
        "startup.sh": DEPLOY_DIR / "backend_startup.sh",
        "startup.py": DEPLOY_DIR / "backend_startup.py",
        ".deployment": DEPLOY_DIR / "kudu.deployment",
        "web.config": DEPLOY_DIR / "backend_web.config",
    }

    # Gather src/backend
    src_backend_files = collect_folder(ROOT / "src/backend", ROOT)
    entries.update(src_backend_files)

    # Provide direct top-level backend/ alias so `from backend.app import app`
    # succeeds whether PYTHONPATH points to /home/site/wwwroot or /home/site/wwwroot/src
    for rel_path, abs_path in src_backend_files.items():
        if rel_path.startswith("src/backend/"):
            direct_alias = rel_path[len("src/"):]
            entries[direct_alias] = abs_path

    # Gather core asset directories
    for folder in ("prompts", "templates", "skills", "evals"):
        fdir = ROOT / folder
        if fdir.is_dir():
            entries.update(collect_folder(fdir, ROOT))

    return entries


def gather_frontend_files(prebuilt_standalone: bool = False) -> Dict[str, Path]:
    """Collects frontend files for either source-based or prebuilt-standalone deployment."""
    fe_root = ROOT / "src/frontend"
    entries: Dict[str, Path] = {
        "startup.sh": DEPLOY_DIR / "frontend_startup.sh",
        "startup.js": DEPLOY_DIR / "frontend_startup.js",
        ".deployment": DEPLOY_DIR / "kudu.deployment",
        "web.config": DEPLOY_DIR / "frontend_web.config",
        "staticwebapp.config.json": DEPLOY_DIR / "staticwebapp.config.json",
    }

    if prebuilt_standalone:
        log("  Packaging pre-built Next.js standalone bundle...")
        standalone_dir = fe_root / ".next/standalone"
        static_dir = fe_root / ".next/static"
        public_dir = fe_root / "public"

        if not standalone_dir.is_dir():
            raise RuntimeError("Next.js standalone directory .next/standalone does not exist! Run build first.")

        # Collect standalone server and dependencies
        for p in standalone_dir.rglob("*"):
            if p.is_file() and not p.is_symlink():
                rel = p.relative_to(standalone_dir).as_posix()
                entries[rel] = p

        # Collect static assets into .next/static
        if static_dir.is_dir():
            for p in static_dir.rglob("*"):
                if p.is_file():
                    rel = f".next/static/{p.relative_to(static_dir).as_posix()}"
                    entries[rel] = p
                    # Also map nested if Next.js nested the standalone app under src/frontend
                    entries[f"src/frontend/{rel}"] = p

        # Collect public assets
        if public_dir.is_dir():
            for p in public_dir.rglob("*"):
                if p.is_file():
                    rel = f"public/{p.relative_to(public_dir).as_posix()}"
                    entries[rel] = p
                    entries[f"src/frontend/{rel}"] = p

        # Include package.json and next.config.ts for reference
        entries["package.json"] = fe_root / "package.json"
        entries["next.config.ts"] = fe_root / "next.config.ts"
    else:
        # Source-based package for Oryx to build
        frontend_sources = collect_folder(fe_root, fe_root)
        entries.update(frontend_sources)

    return entries


# ---------------------------------------------------------------------------
# ZIP Creation and Verification
# ---------------------------------------------------------------------------

def create_archive(zip_path: Path, entries: Dict[str, Path]) -> Dict[str, Any]:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    uncompressed_bytes = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name, src in sorted(entries.items()):
            file_bytes = src.read_bytes()
            uncompressed_bytes += len(file_bytes)

            zinfo = zipfile.ZipInfo(name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            is_executable = src.suffix == ".sh" or os.access(src, os.X_OK)
            mode = 0o755 if is_executable else 0o644
            zinfo.external_attr = (mode & 0xFFFF) << 16
            zf.writestr(zinfo, file_bytes)

    compressed_bytes = zip_path.stat().st_size
    sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    return {
        "path": zip_path,
        "count": len(entries),
        "uncompressed_bytes": uncompressed_bytes,
        "compressed_bytes": compressed_bytes,
        "sha256": sha256,
    }


def verify_archive(
    meta: Dict[str, Any],
    required_files: List[str],
    allowed_dirs: Optional[Set[str]] = None,
) -> bool:
    zip_path: Path = meta["path"]
    valid = True
    effective_skip = SKIP_DIRS - (allowed_dirs or set())

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            corrupt = zf.testzip()
            if corrupt:
                error(f"  CRC check failed on file: {corrupt} in {zip_path.name}")
                return False

            names = set(zf.namelist())
            for req in required_files:
                if req not in names:
                    error(f"  Required file '{req}' missing from {zip_path.name}!")
                    valid = False

            for name in names:
                parts = Path(name).parts
                if any(p in effective_skip for p in parts):
                    error(f"  Forbidden directory leaked into {zip_path.name}: {name}")
                    valid = False
                if Path(name).name in SKIP_FILES:
                    error(f"  Forbidden file leaked into {zip_path.name}: {name}")
                    valid = False
    except Exception as exc:
        error(f"  Failed reading archive {zip_path.name}: {exc}")
        return False

    return valid


# ---------------------------------------------------------------------------
# Pre-build Next.js Standalone
# ---------------------------------------------------------------------------

def build_frontend_standalone() -> bool:
    log("Building Next.js 16 frontend in standalone mode (ATLAS_STANDALONE=1)...")
    fe_dir = ROOT / "src/frontend"
    env = {
        **os.environ,
        "ATLAS_STANDALONE": "1",
        "NEXT_TELEMETRY_DISABLED": "1",
        "NODE_ENV": "production",
    }

    try:
        # Auto-install frontend dependencies in src/frontend if missing
        if not (fe_dir / "node_modules").is_dir():
            log("  Installing frontend dependencies in src/frontend...")
            install_cmd = ["npm", "ci"] if (fe_dir / "package-lock.json").is_file() else ["npm", "install"]
            subprocess.run(install_cmd, cwd=fe_dir, check=True)

        log("  Running Next.js build...")
        subprocess.run(["npm", "run", "build"], cwd=fe_dir, env=env, check=True)
        log("  Next.js standalone build completed successfully.")
        return True
    except subprocess.CalledProcessError as exc:
        error(f"  Next.js build failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Direct Azure Kudu Deploy
# ---------------------------------------------------------------------------

def deploy_to_azure(
    resource_group: str,
    backend_app: Optional[str] = None,
    frontend_app: Optional[str] = None,
    backend_zip: Optional[Path] = None,
    frontend_zip: Optional[Path] = None,
) -> bool:
    """Deploys zip archives to Azure App Service via Azure CLI or Kudu ZipDeploy API."""
    log("==================================================================")
    log(" Deploying Packages to Azure App Service / Kudu")
    log("==================================================================")

    # Check for Azure CLI
    has_az = shutil.which("az") is not None
    if not has_az:
        error("Azure CLI ('az') is not installed or not in PATH!")
        log("You can manually deploy by uploading the ZIP files to:")
        log("  https://<app-name>.scm.azurewebsites.net/ZipDeploy")
        return False

    success = True

    if backend_app and backend_zip and backend_zip.exists():
        log(f"\n[Deploy 1/2] Deploying Backend ({backend_zip.name}) to {backend_app}...")
        cmd = [
            "az", "webapp", "deploy",
            "--resource-group", resource_group,
            "--name", backend_app,
            "--src-path", str(backend_zip),
            "--type", "zip",
            "--async", "false",
        ]
        try:
            subprocess.run(cmd, check=True)
            log(f"  Backend successfully deployed to: https://{backend_app}.azurewebsites.net")
        except subprocess.CalledProcessError as exc:
            error(f"  Backend deployment failed: {exc}")
            success = False

    if frontend_app and frontend_zip and frontend_zip.exists():
        log(f"\n[Deploy 2/2] Deploying Frontend ({frontend_zip.name}) to {frontend_app}...")
        cmd = [
            "az", "webapp", "deploy",
            "--resource-group", resource_group,
            "--name", frontend_app,
            "--src-path", str(frontend_zip),
            "--type", "zip",
            "--async", "false",
        ]
        try:
            subprocess.run(cmd, check=True)
            log(f"  Frontend successfully deployed to: https://{frontend_app}.azurewebsites.net")
        except subprocess.CalledProcessError as exc:
            error(f"  Frontend deployment failed: {exc}")
            success = False

    return success


# ---------------------------------------------------------------------------
# Infrastructure 1-Time Setup Generator
# ---------------------------------------------------------------------------

def generate_setup_script(
    resource_group: str = "rg-agentic-harness-eastus2",
    location: str = "eastus2",
    plan_name: str = "asp-agentic-harness-b1",
    backend_app: str = "agentic-harness-backend-prod",
    frontend_app: str = "agentic-harness-frontend-prod",
    sku: str = "B1",
) -> str:
    """Generates the authoritative Azure CLI bash script for 1-time setup."""
    return f"""#!/usr/bin/env bash
# ==============================================================================
# 1-TIME AZURE INFRASTRUCTURE SETUP SCRIPT FOR AGENTIC QE PLATFORM
# Region: {location} | Tier: Basic {sku} | OS: Linux
# ==============================================================================
set -euo pipefail

RESOURCE_GROUP="{resource_group}"
LOCATION="{location}"
APP_PLAN="{plan_name}"
BACKEND_APP="{backend_app}"
FRONTEND_APP="{frontend_app}"
SKU="{sku}"

echo "=================================================================="
echo " 1-Time Azure Infrastructure Setup"
echo " Resource Group: $RESOURCE_GROUP"
echo " Location:       $LOCATION"
echo " Plan:           $APP_PLAN (Linux $SKU)"
echo " Backend App:    $BACKEND_APP (Python 3.12)"
echo " Frontend App:   $FRONTEND_APP (Node.js 20)"
echo "=================================================================="

# 1. Create Resource Group
echo "\\n[1/6] Creating Resource Group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# 2. Create Shared Linux App Service Plan (Hosts both Backend & Frontend)
echo "\\n[2/6] Creating App Service Plan ($SKU Linux)..."
az appservice plan create \\
  --name "$APP_PLAN" \\
  --resource-group "$RESOURCE_GROUP" \\
  --location "$LOCATION" \\
  --is-linux \\
  --sku "$SKU"

# 3. Create Backend WebApp (Python 3.12)
echo "\\n[3/6] Creating Backend WebApp..."
az webapp create \\
  --name "$BACKEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --plan "$APP_PLAN" \\
  --runtime "PYTHON:3.12" \\
  --startup-file "/home/site/wwwroot/startup.sh"

# 4. Configure Backend App Settings & Persistent Storage
echo "\\n[4/6] Configuring Backend Environment & Persistent Storage..."
az webapp config appsettings set \\
  --name "$BACKEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --settings \\
    WEBSITES_PORT="8000" \\
    PORT="8000" \\
    WEBSITES_ENABLE_APP_SERVICE_STORAGE="true" \\
    ATLAS_HOME="/home/atlas" \\
    ATLAS_DATA_DIR="/home/atlas/data" \\
    ATLAS_SQLITE_JOURNAL="WAL" \\
    SCM_DO_BUILD_DURING_DEPLOYMENT="true" \\
    ENABLE_ORYX_BUILD="true"

# 5. Create Frontend WebApp (Node 20)
echo "\\n[5/6] Creating Frontend WebApp..."
az webapp create \\
  --name "$FRONTEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --plan "$APP_PLAN" \\
  --runtime "NODE:20-lts" \\
  --startup-file "/home/site/wwwroot/startup.sh"

# 6. Configure Frontend App Settings & Backend Proxy Binding
echo "\\n[6/6] Binding Frontend to Backend URL..."
az webapp config appsettings set \\
  --name "$FRONTEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --settings \\
    WEBSITES_PORT="3000" \\
    PORT="3000" \\
    WEBSITES_ENABLE_APP_SERVICE_STORAGE="true" \\
    ATLAS_BACKEND_URL="https://$BACKEND_APP.azurewebsites.net" \\
    NEXT_TELEMETRY_DISABLED="1" \\
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# Enable CORS on Backend for Frontend Origin
az webapp cors add \\
  --name "$BACKEND_APP" \\
  --resource-group "$RESOURCE_GROUP" \\
  --allowed-origins "https://$FRONTEND_APP.azurewebsites.net"

echo "\\n=================================================================="
echo " 1-Time Azure Setup Complete!"
echo " Backend URL:  https://$BACKEND_APP.azurewebsites.net"
echo " Frontend URL: https://$FRONTEND_APP.azurewebsites.net"
echo " Next Step: Run python scripts/azure_convert_and_deploy.py --convert"
echo "=================================================================="
"""


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

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
        if not build_frontend_standalone():
            error("Frontend build failed. Aborting packaging.")
            return 1

    # 1. Package Backend
    log("\n[1/2] Converting & Packaging Backend -> dist/azure_backend.zip...")
    backend_entries = gather_backend_files()
    backend_meta = create_archive(DIST / "azure_backend.zip", backend_entries)

    backend_reqs = ["startup.sh", "startup.py", ".deployment", "web.config", "requirements.txt", "src/backend/app.py", "backend/app.py"]
    if not verify_archive(backend_meta, backend_reqs):
        error("Backend archive verification failed!")
        return 1
    shutil.copy2(DIST / "azure_backend.zip", DIST / "agentic-qe-backend.zip")

    # 2. Package Frontend
    log("\n[2/2] Converting & Packaging Frontend -> dist/azure_frontend.zip...")
    frontend_entries = gather_frontend_files(prebuilt_standalone=args.build_frontend)
    frontend_meta = create_archive(DIST / "azure_frontend.zip", frontend_entries)

    frontend_reqs = ["startup.sh", "startup.js", ".deployment", "web.config", "package.json", "next.config.ts"]
    allowed_fe_dirs = {"node_modules", ".next"} if args.build_frontend else None
    if not verify_archive(frontend_meta, frontend_reqs, allowed_dirs=allowed_fe_dirs):
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

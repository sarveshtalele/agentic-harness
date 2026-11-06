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
import hashlib
import json
import os
import py_compile
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

SKIP_DIRS = {
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
SKIP_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".DS_Store",
    "Thumbs.db",
    "agent-framework.pdf",
}


def log(msg: str) -> None:
    print(f"[package_kudu] {msg}", flush=True)


def error(msg: str) -> None:
    print(f"[package_kudu ERROR] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Pre-flight Checks
# ---------------------------------------------------------------------------

def run_preflight_checks() -> bool:
    log("Running pre-flight validation checks...")
    ok = True

    # 1. Check Python syntax of all backend files
    backend_py_files = list((ROOT / "src/backend").rglob("*.py"))
    if not backend_py_files:
        error("No Python files found in src/backend!")
        ok = False
    else:
        log(f"Compiling {len(backend_py_files)} Python files in src/backend...")
        for py_path in backend_py_files:
            try:
                py_compile.compile(str(py_path), doraise=True)
            except py_compile.PyCompileError as exc:
                error(f"Syntax error in {py_path}: {exc}")
                ok = False

    # 2. Check requirements.txt
    req_file = ROOT / "requirements.txt"
    if not req_file.is_file() or req_file.stat().st_size == 0:
        error("requirements.txt is missing or empty!")
        ok = False
    else:
        req_content = req_file.read_text(encoding="utf-8")
        if "fastapi" not in req_content or "uvicorn" not in req_content:
            error("requirements.txt missing core FastAPI / Uvicorn dependencies!")
            ok = False

    # 3. Check assets: prompts, templates, skills, evals
    for folder in ("prompts", "templates", "skills", "evals"):
        fpath = ROOT / folder
        if not fpath.is_dir() or not any(fpath.iterdir()):
            error(f"Required backend asset directory '{folder}' is missing or empty!")
            ok = False

    # 4. Check Frontend package.json and next.config.ts
    fe_pkg = ROOT / "src/frontend/package.json"
    if not fe_pkg.is_file():
        error("src/frontend/package.json is missing!")
        ok = False
    else:
        try:
            pkg_data = json.loads(fe_pkg.read_text(encoding="utf-8"))
            if "next" not in pkg_data.get("dependencies", {}):
                error("Next.js dependency not found in frontend package.json!")
                ok = False
        except Exception as exc:
            error(f"Frontend package.json invalid JSON: {exc}")
            ok = False

    fe_config = ROOT / "src/frontend/next.config.ts"
    if not fe_config.is_file():
        error("src/frontend/next.config.ts is missing!")
        ok = False

    # 5. Check startup scripts in deploy/azure
    required_deploy_files = [
        ROOT / "deploy/azure/backend_startup.sh",
        ROOT / "deploy/azure/backend_startup.py",
        ROOT / "deploy/azure/frontend_startup.sh",
        ROOT / "deploy/azure/frontend_startup.js",
        ROOT / "deploy/azure/kudu.deployment",
        ROOT / "deploy/azure/backend_web.config",
        ROOT / "deploy/azure/frontend_web.config",
    ]
    for dep_file in required_deploy_files:
        if not dep_file.is_file():
            error(f"Deployment file missing: {dep_file.relative_to(ROOT)}")
            ok = False

    if ok:
        log("Pre-flight validation passed successfully!")
    return ok


# ---------------------------------------------------------------------------
# File Filtering
# ---------------------------------------------------------------------------

def should_skip(path: Path, base_dir: Path) -> bool:
    rel_parts = path.relative_to(base_dir).parts
    if path.name in SKIP_FILES:
        return True
    if any(part in SKIP_DIRS for part in rel_parts):
        return True
    if any(part.startswith(".next") for part in rel_parts):
        return True
    if path.suffix in (".pyc", ".pyo"):
        return True
    return False


def collect_folder_files(folder: Path, base_dir: Path) -> dict[str, Path]:
    entries: dict[str, Path] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not path.is_symlink() and not should_skip(path, base_dir):
            rel_name = path.relative_to(base_dir).as_posix()
            entries[rel_name] = path
    return entries


# ---------------------------------------------------------------------------
# Backend Entries Gathering
# ---------------------------------------------------------------------------

def gather_backend_entries() -> dict[str, Path]:
    """
    Collects all files for the Azure App Service Python Backend.
    Includes:
      - requirements.txt
      - startup.sh (bash entrypoint for Azure App Service)
      - startup.py (python entrypoint)
      - .deployment (Kudu Oryx config)
      - web.config (IIS/Kudu config)
      - src/backend/... (full source tree)
      - backend/... (direct root import alias for resilience)
      - prompts/, templates/, skills/, evals/
    """
    entries: dict[str, Path] = {
        "requirements.txt": ROOT / "requirements.txt",
        "startup.sh": ROOT / "deploy/azure/backend_startup.sh",
        "startup.py": ROOT / "deploy/azure/backend_startup.py",
        ".deployment": ROOT / "deploy/azure/kudu.deployment",
        "web.config": ROOT / "deploy/azure/backend_web.config",
    }

    # Include src/backend as src/backend/...
    src_backend_files = collect_folder_files(ROOT / "src/backend", ROOT)
    entries.update(src_backend_files)

    # Also map src/backend/... to backend/... so `from backend.app import app`
    # works whether PYTHONPATH is set to /home/site/wwwroot or /home/site/wwwroot/src
    for rel_path, abs_path in src_backend_files.items():
        if rel_path.startswith("src/backend/"):
            direct_alias = rel_path[len("src/"):]
            entries[direct_alias] = abs_path

    # Include assets: prompts, templates, skills, evals
    for folder in ("prompts", "templates", "skills", "evals"):
        target_dir = ROOT / folder
        if target_dir.is_dir():
            entries.update(collect_folder_files(target_dir, ROOT))

    return entries


# ---------------------------------------------------------------------------
# Frontend Entries Gathering
# ---------------------------------------------------------------------------

def gather_frontend_entries() -> dict[str, Path]:
    """
    Collects all files for the Next.js Frontend.
    Includes:
      - package.json, package-lock.json, next.config.ts, tsconfig.json
      - app/, components/, lib/, content/, etc.
      - startup.sh (bash entrypoint)
      - startup.js (Node builder & standalone runner)
      - .deployment (Kudu Oryx config)
      - web.config (IIS/Kudu config)
      - staticwebapp.config.json (Azure Static Web Apps config)
    """
    base = ROOT / "src/frontend"
    entries: dict[str, Path] = {
        "startup.sh": ROOT / "deploy/azure/frontend_startup.sh",
        "startup.js": ROOT / "deploy/azure/frontend_startup.js",
        ".deployment": ROOT / "deploy/azure/kudu.deployment",
        "web.config": ROOT / "deploy/azure/frontend_web.config",
        "staticwebapp.config.json": ROOT / "deploy/azure/staticwebapp.config.json",
    }

    frontend_files = collect_folder_files(base, base)
    entries.update(frontend_files)
    return entries


# ---------------------------------------------------------------------------
# Archive Creation & Verification
# ---------------------------------------------------------------------------

def create_zip_archive(target_path: Path, entries: dict[str, Path]) -> dict[str, any]:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    uncompressed_size = 0

    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, src in sorted(entries.items()):
            # Read file bytes to calculate uncompressed size
            file_bytes = src.read_bytes()
            uncompressed_size += len(file_bytes)

            # Preserve unix permissions (especially executable bit for .sh scripts)
            zinfo = zipfile.ZipInfo(name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            is_executable = src.suffix == ".sh" or os.access(src, os.X_OK)
            mode = 0o755 if is_executable else 0o644
            zinfo.external_attr = (mode & 0xFFFF) << 16
            archive.writestr(zinfo, file_bytes)

    compressed_size = target_path.stat().st_size
    sha256_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()

    return {
        "path": target_path,
        "count": len(entries),
        "uncompressed_bytes": uncompressed_size,
        "compressed_bytes": compressed_size,
        "sha256": sha256_hash,
    }


def verify_zip_archive(meta: dict[str, any], expected_critical_files: list[str]) -> bool:
    zip_path: Path = meta["path"]
    log(f"Verifying {zip_path.name}...")
    valid = True

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            # Test integrity
            bad_file = archive.testzip()
            if bad_file:
                error(f"CRC check failed on file: {bad_file} in {zip_path.name}")
                return False

            names = set(archive.namelist())

            # Check critical files
            for req in expected_critical_files:
                if req not in names:
                    error(f"Missing required file '{req}' in {zip_path.name}!")
                    valid = False

            # Check for forbidden artifacts
            for name in names:
                parts = Path(name).parts
                if any(p in SKIP_DIRS for p in parts) or any(p.startswith(".next") for p in parts):
                    error(f"Forbidden directory '{name}' leaked into {zip_path.name}!")
                    valid = False
                if Path(name).name in SKIP_FILES:
                    error(f"Forbidden file '{name}' leaked into {zip_path.name}!")
                    valid = False

    except Exception as exc:
        error(f"Failed to read {zip_path.name}: {exc}")
        return False

    return valid


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

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
    backend_meta = create_zip_archive(DIST / "azure_backend.zip", backend_entries)

    # Verify Backend Zip
    backend_critical = ["startup.sh", "startup.py", ".deployment", "web.config", "requirements.txt", "src/backend/app.py", "backend/app.py"]
    if not verify_zip_archive(backend_meta, backend_critical):
        error("Backend zip verification failed!")
        return 1

    # Also duplicate/link as agentic-qe-backend.zip for backward compatibility
    shutil.copy2(DIST / "azure_backend.zip", DIST / "agentic-qe-backend.zip")

    # 2. Package Frontend
    log("\n[2/2] Building Frontend Zip: dist/azure_frontend.zip...")
    frontend_entries = gather_frontend_entries()
    frontend_meta = create_zip_archive(DIST / "azure_frontend.zip", frontend_entries)

    # Verify Frontend Zip
    frontend_critical = ["startup.sh", "startup.js", ".deployment", "web.config", "package.json", "next.config.ts"]
    if not verify_zip_archive(frontend_meta, frontend_critical):
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
    log("  Or drag & drop zip files into Kudu Zip Deploy UI: https://<app-name>.scm.azurewebsites.net/ZipDeploy")

    return 0


if __name__ == "__main__":
    sys.exit(main())

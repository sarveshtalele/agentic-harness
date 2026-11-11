"""Pre-build the Next.js standalone bundle and deploy the zips with the Azure CLI."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def build_frontend_standalone(root: Path, log, error) -> bool:
    log("Building Next.js 16 frontend in standalone mode (ATLAS_STANDALONE=1)...")
    fe_dir = root / "src/frontend"
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


def deploy_to_azure(
    resource_group: str,
    backend_app: Optional[str] = None,
    frontend_app: Optional[str] = None,
    backend_zip: Optional[Path] = None,
    frontend_zip: Optional[Path] = None,
    *,
    log,
    error,
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

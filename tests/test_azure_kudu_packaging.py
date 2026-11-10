"""Tests for Azure App Service & Kudu packaging and conversion script."""
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile
import pytest

from scripts.azure_convert_and_deploy import (
    run_preflight_checks,
    gather_backend_files,
    gather_frontend_files,
    create_archive,
    verify_archive,
    generate_setup_script,
    ROOT,
)


def test_preflight_checks_pass_on_current_codebase():
    """Verify that current codebase satisfies all Azure pre-flight checks."""
    assert run_preflight_checks() is True


def test_gather_backend_files_contains_essential_azure_artifacts():
    """Verify that backend packaging gathers all critical files and aliases."""
    entries = gather_backend_files()
    assert "startup.sh" in entries
    assert "startup.py" in entries
    assert ".deployment" in entries
    assert "web.config" in entries
    assert "requirements.txt" in entries
    assert "backend/app.py" in entries
    assert "src/backend/app.py" in entries
    # Check that skills and prompts are gathered
    has_skills = any(k.startswith("skills/") for k in entries)
    assert has_skills, "Expected skills to be gathered in backend package"


def test_gather_frontend_files_contains_essential_azure_artifacts():
    """Verify that frontend packaging gathers all critical files."""
    entries = gather_frontend_files(prebuilt_standalone=False)
    assert "startup.sh" in entries
    assert "startup.js" in entries
    assert ".deployment" in entries
    assert "web.config" in entries
    assert "package.json" in entries
    assert "next.config.ts" in entries


def test_create_and_verify_archive(tmp_path):
    """Verify archive creation and verification logic."""
    dummy_file = tmp_path / "app.py"
    dummy_file.write_text("print('hello')", encoding="utf-8")
    startup_sh = tmp_path / "startup.sh"
    startup_sh.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    entries = {
        "startup.sh": startup_sh,
        "backend/app.py": dummy_file,
    }

    target_zip = tmp_path / "test_package.zip"
    meta = create_archive(target_zip, entries)

    assert meta["path"].exists()
    assert meta["count"] == 2
    assert meta["compressed_bytes"] > 0
    assert meta["sha256"]

    # Verify integrity
    valid = verify_archive(meta, ["startup.sh", "backend/app.py"])
    assert valid is True

    # Test that forbidden leak is detected
    forbidden_file = tmp_path / ".env"
    forbidden_file.write_text("SECRET=123", encoding="utf-8")
    entries[".env"] = forbidden_file
    leaked_zip = tmp_path / "leaked_package.zip"
    leaked_meta = create_archive(leaked_zip, entries)
    assert verify_archive(leaked_meta, ["startup.sh"]) is False

    # Test allowed_dirs in standalone mode
    sa_entries = {
        "startup.sh": startup_sh,
        "node_modules/fake-dep/index.js": dummy_file,
    }
    sa_zip = tmp_path / "standalone_package.zip"
    sa_meta = create_archive(sa_zip, sa_entries)
    # Without allowed_dirs, node_modules is flagged
    assert verify_archive(sa_meta, ["startup.sh"]) is False
    # With allowed_dirs={"node_modules"}, it passes
    assert verify_archive(sa_meta, ["startup.sh"], allowed_dirs={"node_modules"}) is True


def test_generate_setup_script():
    """Verify 1-time setup script generator contains expected Azure CLI commands."""
    script = generate_setup_script(
        resource_group="rg-test-eastus2",
        location="eastus2",
        plan_name="asp-test-b1",
        backend_app="app-backend-test",
        frontend_app="app-frontend-test",
        sku="B1",
    )
    assert 'RESOURCE_GROUP="rg-test-eastus2"' in script
    assert 'APP_PLAN="asp-test-b1"' in script
    assert 'BACKEND_APP="app-backend-test"' in script
    assert 'FRONTEND_APP="app-frontend-test"' in script
    assert 'az group create --name "$RESOURCE_GROUP"' in script
    assert "az appservice plan create" in script
    assert "--is-linux" in script
    assert '--sku "$SKU"' in script
    assert "az webapp create" in script
    assert '--runtime "PYTHON:3.12"' in script
    assert '--runtime "NODE:20-lts"' in script
    assert 'WEBSITES_PORT="8000"' in script
    assert 'WEBSITES_PORT="3000"' in script
    assert 'ATLAS_BACKEND_URL="https://$BACKEND_APP.azurewebsites.net"' in script
    assert "az webapp cors add" in script


def test_branch_isolation_policy():
    """Verify that branch isolation script correctly blocks merging feature/azure-kudu-deployment into main."""
    verify_script = ROOT / "scripts/verify_branch_isolation.sh"
    assert verify_script.is_file()
    assert os.access(verify_script, os.X_OK)

    # The script reads the current branch, so run it in a scratch repository checked out at the locked branch;
    # otherwise the result depends on whichever branch this checkout happens to be on.
    scratch = Path(tempfile.mkdtemp())
    git = ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=test"]
    subprocess.run(git + ["init", "-q", "-b", "feature/azure-kudu-deployment"], cwd=scratch, check=True, timeout=30)
    subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "init"], cwd=scratch, check=True, timeout=30)

    # Locked branch targeting main must fail with exit code 1
    res = subprocess.run([str(verify_script), "main"], capture_output=True, text=True, cwd=scratch, timeout=30)
    assert res.returncode == 1
    assert "strictly protected" in res.stderr
    assert "cannot merge" in res.stderr

    # Calling targeting itself must succeed
    res_self = subprocess.run([str(verify_script), "feature/azure-kudu-deployment"], capture_output=True, text=True, cwd=scratch, timeout=30)
    assert res_self.returncode == 0


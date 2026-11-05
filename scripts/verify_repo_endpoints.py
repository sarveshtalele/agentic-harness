"""Verification script testing GET /api/projects/{id}/repo and GET /api/projects/{id}/repo/tree
for all 4 seeded projects against the actual SQLite database and workspaces.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backend.app import app
from backend.config import repo_dir, sandbox_dir
from backend.repos import ingest

PROJECTS = [
    "prj_agentic_qe",
    "prj_fintech_gateway",
    "prj_ecommerce_core",
    "prj_mcp_market"
]

REQUIRED_ANALYSIS_KEYS = [
    "mode", "total_files", "source_files", "test_file_count", "test_files",
    "languages", "lines_of_code", "frameworks", "test_runners", "routes",
    "ci", "entrypoints", "manifests", "docs", "top_imports"
]


def run_verification():
    print("=" * 70)
    print("AGENTIC QE PLATFORM: REPO BACKEND ENDPOINTS & INGESTION VERIFICATION")
    print("=" * 70)

    with TestClient(app) as client:
        # Authenticate
        admin_user = os.environ.get("ATLAS_ADMIN_USERNAME", "admin")
        admin_pass = os.environ.get("ATLAS_ADMIN_PASSWORD", "admin")
        login_res = client.post("/api/auth/login", json={"username": admin_user, "password": admin_pass})
        if login_res.status_code != 200:
            print(f"[FAIL] Login failed: status {login_res.status_code}, response: {login_res.text}")
            sys.exit(1)
        print(f"[PASS] Successfully authenticated as admin user: '{admin_user}'")

        all_passed = True

        for pid in PROJECTS:
            print("-" * 70)
            print(f"Testing Project: {pid}")

            # 1. GET /api/projects/{pid}/repo
            repo_res = client.get(f"/api/projects/{pid}/repo")
            if repo_res.status_code != 200:
                print(f"  [FAIL] GET /api/projects/{pid}/repo returned status {repo_res.status_code}")
                print(f"         Detail: {repo_res.text}")
                all_passed = False
                continue

            repo_data = repo_res.json()
            if not repo_data:
                print(f"  [FAIL] GET /api/projects/{pid}/repo returned empty response (None)")
                all_passed = False
                continue

            print(f"  [PASS] GET /api/projects/{pid}/repo returned 200 OK")
            print(f"         Kind: {repo_data.get('kind')}, Commit: {repo_data.get('commit_sha', '')[:8]}")

            # Check analysis keys
            analysis = repo_data.get("analysis", {})
            missing_keys = [k for k in REQUIRED_ANALYSIS_KEYS if k not in analysis]
            if missing_keys:
                print(f"  [FAIL] Missing required analysis keys: {missing_keys}")
                all_passed = False
            else:
                print(f"  [PASS] All {len(REQUIRED_ANALYSIS_KEYS)} expected analysis keys present")

            print(f"         Mode: {analysis.get('mode')}")
            print(f"         Files: total={analysis.get('total_files')}, source={analysis.get('source_files')}, test={analysis.get('test_file_count')}")
            print(f"         Languages: {analysis.get('languages')}")
            print(f"         Lines of Code: {analysis.get('lines_of_code')}")
            print(f"         Frameworks: {analysis.get('frameworks')}")
            print(f"         Test Runners: {analysis.get('test_runners')}")
            print(f"         Routes: {len(analysis.get('routes', []))} routes detected")
            print(f"         CI Workflows: {analysis.get('ci')}")
            print(f"         Top Imports ({len(analysis.get('top_imports', []))}): {analysis.get('top_imports', [])[:5]}")

            # 2. GET /api/projects/{pid}/repo/tree
            tree_res = client.get(f"/api/projects/{pid}/repo/tree")
            if tree_res.status_code != 200:
                print(f"  [FAIL] GET /api/projects/{pid}/repo/tree returned status {tree_res.status_code}")
                all_passed = False
                continue

            tree_data = tree_res.json()
            files = tree_data.get("files", [])
            if not files:
                print(f"  [FAIL] GET /api/projects/{pid}/repo/tree returned 0 files")
                all_passed = False
            else:
                print(f"  [PASS] GET /api/projects/{pid}/repo/tree returned 200 OK with {len(files)} files")

            # 3. GET /api/projects/{pid}/repo/file
            if files:
                first_file = files[0]
                file_res = client.get(f"/api/projects/{pid}/repo/file?path={first_file}")
                if file_res.status_code != 200:
                    print(f"  [FAIL] GET /api/projects/{pid}/repo/file for '{first_file}' returned status {file_res.status_code}")
                    all_passed = False
                else:
                    print(f"  [PASS] GET /api/projects/{pid}/repo/file for '{first_file}' returned 200 OK ({len(file_res.text)} bytes)")

            # 4. GET /api/projects/{pid}/repo/file with non-existent file
            missing_res = client.get(f"/api/projects/{pid}/repo/file?path=non_existent_file.xyz")
            if missing_res.status_code != 404:
                print(f"  [FAIL] Expected 404 for missing file, got {missing_res.status_code}")
                all_passed = False
            else:
                detail = missing_res.json().get("detail", "")
                if "File not found" in detail:
                    print(f"  [PASS] Missing file returned clean 404 with JSON detail: '{detail}'")
                else:
                    print(f"  [WARN] Missing file returned 404 but detail was: '{detail}'")

        print("=" * 70)
        if all_passed:
            print("ALL 4 SEEDED PROJECTS VERIFIED SUCCESSFULLY! NO 500 OR FILENOTFOUND ERRORS.")
            print("=" * 70)
            sys.exit(0)
        else:
            print("VERIFICATION FAILED: One or more checks encountered errors.")
            print("=" * 70)
            sys.exit(1)


if __name__ == "__main__":
    run_verification()

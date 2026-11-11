"""Project export zip and agent metrics with no eval run. Kept from the retired legacy suite, now on fresh projects."""
import io
import os
import zipfile

from fastapi.testclient import TestClient

from backend.app import app
from backend.db import db
from backend.maf.evals.store import detail


def test_project_export_zip_has_setup_scripts_for_each_os():
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": os.environ["ATLAS_ADMIN_USERNAME"], "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        project = client.post("/api/projects", json={"name": "Export shop", "description": "export"}).json()["id"]
        got = client.get(f"/api/projects/{project}/export-zip")
        assert got.status_code == 200 and got.headers["content-type"] == "application/zip"
        assert f"{project}_sdlc_export.zip" in got.headers["content-disposition"]
        bundle = zipfile.ZipFile(io.BytesIO(got.content))
        assert {"setup_mac_linux.sh", "setup_windows.bat", "README_SETUP.md"} <= set(bundle.namelist())
        assert "python3 -m venv" in bundle.read("setup_mac_linux.sh").decode() and "call .venv\\Scripts\\activate.bat" in bundle.read("setup_windows.bat").decode()


def test_agent_metrics_are_not_measured_without_an_eval_run():
    with db() as con:
        con.execute("DELETE FROM evaluation_metrics")
    for agent in ("project-copilot", "business-analyst", "repo-intelligence-analyst", "confidence-reviewer"):
        for metric in detail(agent)["metrics"]:
            assert metric["state"] in ("n/a", "not_measured") and metric.get("value") is None, metric

"""Failed design batches and retry from the failed stage."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from backend import config
from backend.app import app

from backend.db import db
from backend.maf import llm

from tests.scripted_client import ScriptedClient
from tests.helpers_api import make_user, pending, sign_in, unique, wait_run
from tests.helpers_errors import Designer, IDS, run_to_design


def test_one_failed_design_batch_keeps_the_other_three_and_retry_repeats_only_it(client, project):
    designer = Designer()
    run = run_to_design(client, project, designer)
    assert run["status"] == "failed" and run["failure"]["code"] == "AQE-MODEL-001" and run["failure"]["stage"] == "design"
    kept = list((config.RUNS / run["id"] / "parts" / "design").glob("*.json"))
    assert len(kept) == 3, "three finished batches were saved as they completed"
    first_pass = len(designer.batches)
    designer.healed = True
    assert client.post(f"/api/runs/{run['id']}/retry").status_code == 200
    run = wait_run(client, run["id"])
    assert run["status"] == "waiting_approval" and pending(run)["gate"] == 3 and "PARTIAL" not in pending(run)["title"]
    repeated = {r for batch in designer.batches[first_pass:] for r in batch}
    assert repeated == set(IDS[12:]), "only the failed batch is asked again"
    doc = next(d for d in client.get(f"/api/projects/{project['id']}/documents").json() if d["kind"] == "test_cases")
    assert len(client.get(f"/api/documents/{doc['id']}").json()["data"]) == 64 and "partial" not in pending(run)["payload"]
    assert not (config.RUNS / run["id"] / "parts" / "design").exists(), "kept batches are cleared once the stage finishes"


def test_batches_that_keep_failing_end_as_a_partial_result_that_cannot_be_approved(client, project):
    designer = Designer()
    run = run_to_design(client, project, designer)
    for _ in range(2):  # the third run of the stage may end partial
        assert run["status"] == "failed"
        assert client.post(f"/api/runs/{run['id']}/retry").status_code == 200
        run = wait_run(client, run["id"], ("waiting_approval", "failed"))
    assert run["status"] == "waiting_approval"
    gate = pending(run)
    assert "PARTIAL" in gate["title"] and "REQ-013" in gate["summary"] and gate["payload"]["partial"]["missing"] == IDS[12:]
    doc = next(d for d in client.get(f"/api/projects/{project['id']}/documents").json() if d["kind"] == "test_cases")
    assert "PARTIAL" in doc["title"] and len(client.get(f"/api/documents/{doc['id']}").json()["data"]) == 48
    refused = client.post(f"/api/approvals/{gate['id']}/decide", json={"approved": True})
    assert refused.status_code == 400 and "partial" in refused.json()["message"] and refused.json()["error_id"]
    assert pending(client.get(f"/api/runs/{run['id']}").json())["status"] == "pending", "a refused approval changes nothing"


def test_only_one_retry_can_run_at_a_time(client, project):
    designer = Designer()
    run = run_to_design(client, project, designer)
    designer.healed = True
    with ThreadPoolExecutor(2) as pool:
        codes = sorted(f.result().status_code for f in [pool.submit(client.post, f"/api/runs/{run['id']}/retry") for _ in range(2)])
    assert codes == [200, 409]
    assert wait_run(client, run["id"])["status"] == "waiting_approval"
    assert client.post(f"/api/runs/{run['id']}/retry").status_code == 409, "a run that is not failed cannot be retried"


def test_a_retry_counts_against_the_run_token_limit(client, project, monkeypatch):
    from backend.maf import engine

    run = run_to_design(client, project, Designer())
    monkeypatch.setattr(engine, "RUN_TOKEN_LIMIT", 1)
    refused = client.post(f"/api/runs/{run['id']}/retry")
    assert refused.status_code == 403 and refused.json()["code"] == "AQE-ALLOW-001" and "ATLAS_RUN_TOKEN_LIMIT" in refused.json()["action"]
    assert client.get(f"/api/runs/{run['id']}").json()["status"] == "failed"


def test_retry_belongs_to_the_projects_owner(client):
    first, second = unique("owner"), unique("other")
    make_user(client, first)
    make_user(client, second)
    mine, _ = sign_in(first)
    theirs, _ = sign_in(second)
    project = mine.post("/api/projects", json={"name": "Mine", "description": ""}).json()
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, started_at) VALUES ('run_owned', ?, 'qe', 'failed', '{}', '2026-01-01T00:00:00+00:00')", (project["id"],))
    refused = theirs.post("/api/runs/run_owned/retry")
    assert refused.status_code == 404 and refused.json()["message"] == "Not found", "another user is told nothing about the run"
    assert TestClient(app).post("/api/runs/run_owned/retry").status_code == 401
    llm.set_client_override(ScriptedClient([("x", "ok")]))
    assert mine.post("/api/runs/run_owned/retry").status_code != 404, "the owner reaches the route"
    assert client.post("/api/runs/run_missing/retry").status_code == 404

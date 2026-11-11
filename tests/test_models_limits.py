"""Token limits per period, per model and per run."""

import pytest

from backend import config

from backend.core import auth, models

from backend.maf import llm
from tests.reviewing import reviewer
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import GOOD_REVIEW, pending, rules, upload_repo, wait_run
from tests.helpers_errors import IDS, Designer
from tests.helpers_models import account, at, spend, start_ba


STOP_AT = 4  # each design batch of 16 cases is reviewed in two requests of 8


# ---- limits --------------------------------------------------------------------------------

@pytest.mark.parametrize("period,row_at,still_blocked,free_at,word", [
    ("day", "2026-11-04T09:00:00+00:00", "2026-11-04T18:00:00+00:00", "2026-11-04T19:00:00+00:00", "daily"),     # Kolkata midnight is 18:30 UTC
    ("week", "2026-11-04T09:00:00+00:00", "2026-11-08T10:00:00+00:00", "2026-11-09T10:00:00+00:00", "weekly"),  # Monday 9 November, local
    ("month", "2026-11-04T09:00:00+00:00", "2026-11-30T10:00:00+00:00", "2026-12-01T10:00:00+00:00", "monthly"),
])
def test_each_limit_stops_a_start_with_its_reset_time_then_allows_it_after_the_reset(client, monkeypatch, period, row_at, still_blocked, free_at, word):
    llm.set_client_override(ScriptedClient(rules()))
    user, mine, project = account(client)
    client.patch(f"/api/users/{user['id']}", json={"limits": {period: 100}})
    spend(user["id"], 100, created_at=row_at)
    at(monkeypatch, "2026-11-04T10:00:00+00:00")
    stopped = start_ba(mine, project)
    body = stopped.json()
    assert stopped.status_code == 429 and body["code"] == "AQE-ALLOW-002" and word in body["message"] and "resets at" in body["message"] and "IST" in body["message"]
    at(monkeypatch, still_blocked)
    assert start_ba(mine, project).status_code == 429, "not reset yet"
    at(monkeypatch, free_at)
    assert start_ba(mine, project).status_code == 201, "reset: works again"


def test_the_overall_allocation_and_the_period_limits_apply_together(client, monkeypatch):
    user, mine, project = account(client, token_limit=10_000)
    at(monkeypatch, "2026-11-04T10:00:00+00:00")
    client.patch(f"/api/users/{user['id']}", json={"limits": {"day": 50, "month": 10_000}})
    spend(user["id"], 60, created_at="2026-11-04T09:00:00+00:00")
    with pytest.raises(auth.AllowanceError) as stopped:
        auth.check_allowance(project["id"], user["id"])
    assert stopped.value.code == "AQE-ALLOW-002" and "daily" in stopped.value.message
    client.patch(f"/api/users/{user['id']}", json={"limits": {"day": None}})
    auth.check_allowance(project["id"], user["id"])
    spend(user["id"], 10_000, created_at="2026-11-04T09:30:00+00:00")
    with pytest.raises(auth.AllowanceError) as stopped:
        auth.check_allowance(project["id"], user["id"])
    assert stopped.value.code == "AQE-ALLOW-001" and "allocation" in stopped.value.message


def test_a_per_model_limit_stops_only_that_model(client, monkeypatch):
    user, mine, project = account(client, ("m-a", "m-pricey"))
    at(monkeypatch, "2026-11-04T10:00:00+00:00")
    client.patch(f"/api/users/{user['id']}", json={"model_limits": [{"model": "m-pricey", "period": "day", "tokens": 100}]})
    spend(user["id"], 100, model="m-pricey", created_at="2026-11-04T09:00:00+00:00")
    auth.check_allowance(project["id"], user["id"], "m-a")
    with pytest.raises(auth.AllowanceError) as stopped:
        auth.check_allowance(project["id"], user["id"], "m-pricey")
    assert stopped.value.code == "AQE-ALLOW-002" and "m-pricey" in stopped.value.message
    assert client.patch(f"/api/users/{user['id']}", json={"model_limits": [{"model": "m-unticked", "period": "day", "tokens": 5}]}).status_code == 400
    assert mine.get("/api/auth/me").json()["model_usage"] == {"m-pricey": 100}


def test_the_time_zone_decides_where_a_day_starts(client, monkeypatch):
    user, mine, project = account(client)
    client.patch(f"/api/users/{user['id']}", json={"limits": {"day": 100}})
    spend(user["id"], 100, created_at="2026-11-04T19:00:00+00:00")  # 00:30 on 5 November in Kolkata, 19:00 on 4 November in UTC
    at(monkeypatch, "2026-11-05T00:30:00+00:00")
    assert models.timezone_name() == "Asia/Kolkata", "the default zone"
    assert models.limit_problem(user["id"]) is not None
    assert client.put("/api/settings/timezone", json={"timezone": "UTC"}).json() == {"timezone": "UTC"}
    try:
        assert models.limit_problem(user["id"]) is None, "in UTC that spending belongs to the day before"
    finally:
        client.put("/api/settings/timezone", json={"timezone": "Asia/Kolkata"})
    assert client.put("/api/settings/timezone", json={"timezone": "Mars/Base"}).status_code == 400
    assert mine.put("/api/settings/timezone", json={"timezone": "UTC"}).status_code == 403


def test_a_limit_during_a_qe_run_stops_it_keeps_finished_batches_and_retry_continues_after_the_reset(client, monkeypatch):
    user, mine, project = account(client)
    client.patch(f"/api/users/{user['id']}", json={"limits": {"day": 100_000}})
    at(monkeypatch, "2026-11-04T10:00:00+00:00")
    monkeypatch.setattr("backend.maf.runtime.gate.MODEL_CONCURRENCY", 1)
    designer, reviews = Designer(), []
    designer.healed = True

    perfect = reviewer()

    def review(text):
        reviews.append(1)
        if len(reviews) == STOP_AT:  # other work by the same account uses up the day while the second batch is being reviewed
            spend(user["id"], 1_000_000, created_at="2026-11-04T10:00:00+00:00")
        return perfect(text)

    upload_repo(mine, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    from tests.helpers_errors import PLAN, REQUIREMENTS

    llm.set_client_override(ScriptedClient([("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", REQUIREMENTS), ("You are a principal test architect", PLAN),
                                            ("Review type: design cases.", review), *case_rules(), ("You are an independent reviewer", GOOD_REVIEW), ("You are a test design architect", designer)]))
    run = mine.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(4):
        run = wait_run(mine, run["id"])
        if run["status"] != "waiting_approval":
            break
        mine.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    run = wait_run(mine, run["id"], ("failed", "waiting_approval", "completed"))
    assert run["status"] == "failed" and run["failure"]["code"] == "AQE-ALLOW-002" and run["failure"]["stage"] == "design"
    assert "partial" not in run["state"] and not any(a["status"] == "pending" for a in run["approvals"]), "a limit never becomes an approvable partial result"
    kept = list((config.RUNS / run["id"] / "parts" / "design").glob("*.json"))
    assert len(kept) == 2, "the batches that finished before the limit are saved"
    refused = mine.post(f"/api/runs/{run['id']}/retry")
    assert refused.status_code == 429 and refused.json()["code"] == "AQE-ALLOW-002", "retry waits for the reset"
    assert mine.get(f"/api/runs/{run['id']}").json()["status"] == "failed"
    asked = len(designer.batches)
    at(monkeypatch, "2026-11-05T10:00:00+00:00")
    assert mine.post(f"/api/runs/{run['id']}/retry").status_code == 200
    run = wait_run(mine, run["id"])
    assert run["status"] == "waiting_approval" and pending(run)["gate"] == 3 and "PARTIAL" not in pending(run)["title"]
    assert {r for batch in designer.batches[asked:] for r in batch} == set(IDS[8:]), "only the batches that had not finished are asked again"
    doc = next(d for d in mine.get(f"/api/projects/{project['id']}/documents").json() if d["kind"] == "test_cases")
    assert len(mine.get(f"/api/documents/{doc['id']}").json()["data"]) == 64

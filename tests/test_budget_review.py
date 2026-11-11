"""Review evidence size, review retries and token limits between batches."""

import asyncio
import json
import re

from backend.maf import llm
from backend.maf import runtime

from tests import reviewing
from tests.scripted_client import ScriptedClient
from tests.helpers_api import pending, upload_repo, wait_run
from tests.helpers_confidence import CALC, base_rules, go_to_gate


# NOT RUN, retries, and matching


def counts_of(run):
    return pending(run)["payload"]["confidence"]["counts"]


def test_an_item_the_reviewer_left_out_is_asked_for_once_more(client, project):
    state = {"first": True}

    def grade(kind, key):
        if kind == "design" and key == "C3" and state["first"]:
            state["first"] = False
            return {"skip": True}

    run, _ = go_to_gate(client, project, 3, base_rules(grade=grade))
    assert counts_of(run)["not_run"] == 0


def test_a_reviewer_that_names_the_case_id_instead_of_the_item_key_is_still_matched(client, project):
    def by_own_id(text):
        out = json.loads(reviewing.reviewer()(text))
        kind, items = reviewing.asked(text)
        own = {key: re.search(r'"id":\s*"([^"]+)"', body).group(1) for key, body in items}
        for record in out["items"]:
            record["tc_id"] = own[record["tc_id"]]
        return json.dumps(out)

    run, _ = go_to_gate(client, project, 3, base_rules(extra=[("Review type: design cases.", by_own_id)]))
    assert counts_of(run)["not_run"] == 0


def test_an_unusable_reply_splits_the_batch_in_half_once(client, project):
    sizes = []

    def flaky(text):
        kind, items = reviewing.asked(text)
        sizes.append(len(items))
        return "I cannot answer in JSON" if len(items) > 2 else reviewing.reviewer()(text)

    run, _ = go_to_gate(client, project, 3, base_rules(extra=[("Review type: design cases.", flaky)]))
    assert counts_of(run)["not_run"] == 0, "nothing was lost"
    assert sizes.count(4) >= 1 and sizes.count(2) == 2, sizes


def test_a_half_that_fails_again_is_not_run_and_the_other_half_is_kept(client, project):
    def flaky(text):
        kind, items = reviewing.asked(text)
        return "I cannot answer in JSON" if "C3" in [key for key, _ in items] else reviewing.reviewer()(text)

    run, _ = go_to_gate(client, project, 3, base_rules(extra=[("Review type: design cases.", flaky)]))
    counts = counts_of(run)
    assert counts["not_run"] == 2 and counts["cases"] == 4
    assert [r["status"] for r in pending(run)["payload"]["confidence"]["records"]] == ["reviewed", "reviewed", "NOT RUN", "NOT RUN"]


# the token limit


def test_a_call_queued_at_the_model_gate_stops_when_an_earlier_call_used_the_limit(client, project, monkeypatch):
    from backend.db import db, now

    upload_repo(client, project, {"calc.py": CALC})
    llm.set_client_override(ScriptedClient(base_rules()))  # every scripted call reports 15 tokens
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, state, started_at) VALUES ('run_gate', ?, 'qe', 'running', '{}', '{}', ?)", (project["id"], now()))
    monkeypatch.setattr(runtime, "RUN_TOKEN_LIMIT", 10)
    gate = {}
    monkeypatch.setattr(runtime, "_model_gate", lambda: gate.setdefault("one", asyncio.Semaphore(1)))

    async def both():
        calls = [runtime.AgentCall("run_gate", project["id"], "confidence-reviewer", skills=()) for _ in range(3)]
        text = "Review type: design cases.\nITEMS:\n[C1]\n{}\n\nEVIDENCE:\n"
        return await asyncio.gather(*(c.text(text) for c in calls), return_exceptions=True)

    results = client.portal.call(both)
    assert isinstance(results[0], str)
    assert all(type(r).__name__ == "AllowanceError" and r.code == "AQE-ALLOW-001" for r in results[1:]), results
    with db() as con:
        assert con.execute("SELECT tokens_in+tokens_out FROM runs WHERE id='run_gate'").fetchone()[0] == 15, "the queued calls never reached the model"


def test_a_run_stops_at_the_limit_between_batches_keeps_its_work_and_the_gate_shows_tokens(client, project, monkeypatch):
    from backend.db import db

    run, _ = go_to_gate(client, project, 2, base_rules())
    tokens = pending(run)["payload"]["tokens"]
    assert tokens["used"] > 0 and tokens["used"] + tokens["left"] == tokens["limit"] and f"{tokens['left']:,} left" in pending(run)["summary"]
    monkeypatch.setattr(runtime, "RUN_TOKEN_LIMIT", tokens["used"] + 10)
    assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True, "feedback": ""}).status_code == 200
    run = wait_run(client, run["id"], ("failed", "completed", "waiting_approval"), timeout=20)
    if run["status"] == "waiting_approval":  # reviews stop first, so the design that fitted reaches its gate unreviewed, and the next model call stops the run
        assert run["state"]["cases_review"]["counts"]["not_run"] > 0
        assert client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True, "feedback": "Unreviewed, accepted for this test"}).status_code == 200
        run = wait_run(client, run["id"], ("failed", "completed"), timeout=20)
    with db() as con:
        code = con.execute("SELECT code FROM run_failures WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (run["id"],)).fetchone()[0]
        used = con.execute("SELECT tokens_in+tokens_out FROM runs WHERE id=?", (run["id"],)).fetchone()[0]
    assert code == "AQE-ALLOW-001"
    assert used <= tokens["used"] + 10 + 15 * 4, "only calls already in flight can pass the limit"
    kinds = {d["kind"] for d in client.get(f"/api/projects/{project['id']}/documents").json()}
    assert {"requirements", "test_plan"} <= kinds, "work finished before the stop is kept"


def test_reviews_stop_first_so_the_run_can_finish(client):
    """Past two thirds of the limit, no review or send-back runs: items say why, with no score and no pass, and no model call is made."""
    import asyncio

    from backend.db import db
    from backend.maf.engine import RunContext
    from backend.maf import runtime
    from backend.maf.workflows import shared

    project_id = client.post("/api/projects", json={"name": "Budget"}).json()["id"]
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, started_at, tokens_in, tokens_out) VALUES ('run_budget', ?, 'qe', 'running', '{}', '2026-11-02', ?, 0)", (project_id, runtime.RUN_TOKEN_LIMIT * 2 // 3))
    records, spent = asyncio.run(shared.review_cases(RunContext("run_budget", project_id), "design", "design cases", [("C1", "case one")], "evidence", None))
    assert spent == 0 and records[0]["verdict"] == "NOT RUN" and shared.NOT_REVIEWED in str(records[0])

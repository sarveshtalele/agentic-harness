"""Daily logs, retention, run folders and error groups."""

import json
import logging
import os

from datetime import timedelta

from fastapi.testclient import TestClient

from backend import config
from backend.app import app
from backend.core import logs
from backend.db import db, new_id

from tests.helpers_api import make_user, sign_in, unique
from tests.helpers_ops import insert_run


# ---- structured log files ------------------------------------------------------

def read_lines():
    path = logs.file_for(logs.today())
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_requests_and_errors_are_logged_without_secrets_bodies_queries_or_usernames(client, project):
    secret = "sk-" + "Qx7" * 12
    password = "Pw-" + unique("p")
    name = unique("someone")
    client.post("/api/auth/login", json={"username": name, "password": password})  # a failed sign-in with a body
    client.get(f"/api/projects/{project['id']}?token={secret}&password={password}")
    client.post(f"/api/projects/{project['id']}/documents", json={"kind": "brd", "title": f"password={password} key {secret}", "content": "# T\n"})
    logging.getLogger("aqe.engine").error("run failed with api_key=%s and password=%s", secret, password, extra={"fields": {"run_id": "run_1", "stage": "design", "agent": "qa", "error_id": "err_1"}})
    text = logs.file_for(logs.today()).read_text(encoding="utf-8")
    assert secret not in text and password not in text and name not in text
    lines = read_lines()
    request = next(line for line in lines if line.get("path") == f"/api/projects/{project['id']}")
    assert request["method"] == "GET" and request["status"] == 200 and request["user_id"] == "admin" and request["request_id"].startswith("req_") and request["duration_ms"] >= 0
    assert "token" not in json.dumps(request) and "query" not in request
    failure = next(line for line in lines if line["level"] == "ERROR" and line.get("run_id") == "run_1")
    assert failure["stage"] == "design" and failure["agent"] == "qa" and failure["error_id"] == "err_1"
    assert all(line["logger"] == "aqe.request" or line["level"] in {"WARNING", "ERROR", "CRITICAL"} for line in lines), "other loggers write only warnings and errors"


def test_errors_file_keeps_each_warning_and_error_with_its_stack_and_no_secret(client):
    secret = "sk-" + "Zk9" * 12
    try:
        raise ValueError(f"bad key {secret}")
    except ValueError:
        logging.getLogger("aqe.chat").exception("chat failed")
    logging.getLogger("aqe.chat").info("not an error")
    path = logs.file_for(logs.today(), "errors")
    text = path.read_text(encoding="utf-8")
    assert secret not in text
    lines = [json.loads(line) for line in text.splitlines()]
    failure = [line for line in lines if line["message"] == "chat failed"][-1]
    assert "ValueError" in failure["stack"] and "test_ops_logs.py" in failure["where"]
    assert all(line["level"] in {"WARNING", "ERROR", "CRITICAL"} for line in lines)
    got = client.get(f"/api/logs?date={logs.today().isoformat()}&kind=errors")
    assert got.status_code == 200 and "errors-" in got.headers["content-disposition"]
    assert client.get("/api/logs?kind=../app").status_code == 422


def test_retention_removes_only_old_log_files_by_the_date_in_their_name():
    config.LOGS.mkdir(parents=True, exist_ok=True)
    today = logs.today()
    old, edge, fresh = (config.LOGS / f"app-{(today - timedelta(days=d)).isoformat()}.jsonl" for d in (31, 30, 1))
    old_errors = config.LOGS / f"errors-{(today - timedelta(days=31)).isoformat()}.jsonl"
    old_errors.write_text("x")
    other = [config.LOGS / "notes.txt", config.LOGS / "app-2020-01-01.jsonl.bak", config.LOGS / "keep-2020-01-01.jsonl"]
    for path in (old, edge, fresh, *other):
        path.write_text("x")
    os.utime(fresh, (0, 0))  # modification time is ignored: only the name counts
    assert sorted(logs.prune(30, today)) == sorted([old.name, old_errors.name])
    assert not old.exists() and edge.exists() and fresh.exists() and all(p.exists() for p in other)


def test_only_an_admin_downloads_logs_and_only_for_a_real_date(client):
    client.get("/api/projects")
    name = unique()
    make_user(client, name)
    other, _ = sign_in(name)
    day = logs.today().isoformat()
    assert other.get("/api/logs").status_code == 403 and other.get(f"/api/logs?date={day}").status_code == 403
    assert TestClient(app).get(f"/api/logs?date={day}").status_code == 401
    got = client.get(f"/api/logs?date={day}")
    assert got.status_code == 200 and "attachment" in got.headers["content-disposition"] and json.loads(got.text.splitlines()[0])["level"]
    for bad in ("../../etc/passwd", "2026-13-01", "2026-02-30", "20261101", "yesterday", "2026-1-1"):
        assert client.get("/api/logs", params={"date": bad}).status_code == 422, bad
    assert client.get("/api/logs?date=1999-01-01").status_code == 404


# ---- run files go with the project ---------------------------------------------

def test_deleting_a_project_removes_its_run_folders_and_nothing_else(client, project):
    keep = client.post("/api/projects", json={"name": "Keep", "description": ""}).json()
    gone, kept = insert_run(project["id"], "qe", "failed"), insert_run(keep["id"], "qe", "failed")
    for run_id in (gone, kept):
        folder = config.RUNS / run_id / "failures"
        folder.mkdir(parents=True)
        (folder / "err-reply.txt").write_text("reply")
    stranger = config.RUNS / "run_not_in_any_project"
    stranger.mkdir()
    assert client.delete(f"/api/projects/{project['id']}").status_code == 204
    assert not (config.RUNS / gone).exists()
    assert (config.RUNS / kept / "failures" / "err-reply.txt").exists() and stranger.exists()


# ---- error groups on the Observability Errors tab ------------------------------

def insert_failure(run_id, code, agent, message, created_at, stack=""):
    with db() as con:
        con.execute("INSERT INTO run_failures (id, run_id, code, message, action, retryable, agent, stack, created_at) VALUES (?,?,?,?,'Retry the stage.',0,?,?,?)",
                    (new_id("fail"), run_id, code, message, agent, stack, created_at))


def test_error_groups_count_by_code_and_agent_show_latest_message_and_never_the_stack(client, project):
    run = insert_run(project["id"], "qe", "failed")
    insert_failure(run, "AQE-MODEL-001", "qa", "first", "2030-01-01T00:00:01+00:00", stack="SECRET-STACK-TRACE")
    insert_failure(run, "AQE-MODEL-001", "qa", "second", "2030-01-01T00:00:02+00:00", stack="SECRET-STACK-TRACE")
    insert_failure(run, "AQE-MODEL-001", "designer", "other agent", "2030-01-01T00:00:03+00:00")
    insert_failure(run, "AQE-REPO-001", "", "clone failed", "2030-01-01T00:00:00+00:00")
    got = client.get(f"/api/observability/errors?project_id={project['id']}")
    assert got.status_code == 200 and "SECRET-STACK-TRACE" not in got.text
    body = got.json()
    assert body["total"] == 4 and all("stack" not in g for g in body["groups"])
    assert [(g["code"], g["agent"], g["count"], g["latest_message"]) for g in body["groups"]] == [
        ("AQE-MODEL-001", "designer", 1, "other agent"),
        ("AQE-MODEL-001", "qa", 2, "second"),
        ("AQE-REPO-001", "", 1, "clone failed"),
    ]
    assert client.get(f"/api/observability/errors?project_id={project['id']}&q=x").status_code == 200


def test_error_groups_are_empty_for_a_project_with_no_failures_and_for_other_users(client, project):
    name = unique()
    make_user(client, name)
    other, _ = sign_in(name)
    theirs = other.post("/api/projects", json={"name": "Theirs", "description": ""}).json()
    assert other.get(f"/api/observability/errors?project_id={project['id']}").json() == {"total": 0, "groups": []}
    insert_failure(insert_run(project["id"], "qe", "failed"), "AQE-TEST-001", "", "mine", "2030-01-02T00:00:00+00:00")
    assert other.get("/api/observability/errors").json() == {"total": 0, "groups": []}, "another user's failure is not shown"
    insert_failure(insert_run(theirs["id"], "qe", "failed"), "AQE-TEST-001", "", "theirs", "2030-01-02T00:00:00+00:00")
    seen = other.get("/api/observability/errors").json()
    assert seen["total"] == 1 and seen["groups"][0]["latest_message"] == "theirs"
    assert other.get(f"/api/observability/errors?project_id={project['id']}").json()["total"] == 0
    assert client.get(f"/api/observability/errors?project_id={project['id']}").json()["total"] >= 1

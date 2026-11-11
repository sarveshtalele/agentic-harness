"""Full agentic-qe cycle (Gates 0 to 5) through the harness over AG-UI on the real model passed in through env.
Throwaway store and admin (tests.conftest). The script stands in for the human: it approves every card, types each gate
phrase, and says "continue" when a turn stops at its budget or the active command's files are still missing on disk.
A gate counts only when the plugin's own ledger (.qe/ledger.jsonl) records it APPROVED."""
import json
import os
import shutil
import sys
import time

root, out = sys.argv[1], sys.argv[2]
sys.path[:0] = [os.path.join(root, "src"), root]
os.chdir(root)
import tests.conftest  # noqa: E402,F401  throwaway ATLAS_DATA_DIR, admin, migrations, prompts
from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402
from backend.config import sandbox_dir  # noqa: E402
from backend.db import db  # noqa: E402
from backend.maf import harness  # noqa: E402
from backend.maf.harness_kit import active_command  # noqa: E402

APP = os.environ.get("CYCLE_APP", "personal-finance-mcp")
REPO = os.environ.get("CYCLE_REPO", "https://github.com/sarveshtalele/personal-finance-mcp")
LAST_GATE = int(os.environ.get("CYCLE_LAST_GATE", "5"))
STEPS = [  # (what the human types, the gate it ends at or None)
    (f"/agentic-qe:qe-start {APP} --mode brownfield", 0),
    ("/agentic-qe:qe-doctor", None),
    ("Set up the pandas/numpy validator that qe-doctor reports as not set up: run its validator command with --yes, then run qe-doctor's check again.", None),
    (f"/agentic-qe:qe-discover {APP}", None),
    (f"/agentic-qe:qe-requirements {APP}", 1),
    (f"/agentic-qe:qe-plan {APP}", 2),
    (f"/agentic-qe:qe-design {APP}", 3),
    (f"/agentic-qe:qe-data {APP}", None),
    (f"/agentic-qe:qe-generate {APP}", 4),
    (f"/agentic-qe:qe-execute {APP}", None),
    (f"/agentic-qe:qe-heal {APP}", None),
    (f"/agentic-qe:qe-trace {APP}", None),
    (f"/agentic-qe:qe-sign {APP} --signer qa-admin --role \"QE Lead\"", 5),
]
CONTINUES, GATE_TRIES = int(os.environ.get("CYCLE_CONTINUES", "4")), 3
os.makedirs(out, exist_ok=True)
log = open(os.path.join(out, "transcript.jsonl"), "a", encoding="utf-8")


def note(kind, **data):
    log.write(json.dumps({"t": time.strftime("%H:%M:%S"), "kind": kind, **data}, default=str) + "\n")
    log.flush()
    print(kind, json.dumps(data, default=str)[:300], flush=True)


def send(client, thread_id, text, run, resume=None):
    body = {"threadId": thread_id, "runId": run, "messages": [{"id": f"m_{run}", "role": "user", "content": text}] if text else [],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    if resume:
        body["resume"] = resume
    with client.stream("POST", "/agui/harness", json=body, timeout=3600) as response:
        raw = "".join(response.iter_text())
    events = [json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")]
    calls = {}
    for e in events:
        if e["type"] == "TOOL_CALL_START":
            calls[e["toolCallId"]] = {"name": e["toolCallName"], "args": ""}
        elif e["type"] == "TOOL_CALL_ARGS" and e["toolCallId"] in calls:
            calls[e["toolCallId"]]["args"] += e.get("delta", "")
        elif e["type"] == "TOOL_CALL_RESULT":
            note("tool_result", id=e.get("toolCallId"), name=calls.get(e.get("toolCallId"), {}).get("name"), content=str(e.get("content"))[:4000])
        elif e["type"] == "RUN_ERROR":
            note("run_error", message=e.get("message"), code=e.get("code"))
    for cid, c in calls.items():
        note("tool_call", id=cid, name=c["name"], args=c["args"][:4000])
    return events


def turn(client, thread_id, text, tag):
    note("user", text=text)
    events, approvals = send(client, thread_id, text, tag), 0
    while events and events[-1]["type"] == "RUN_FINISHED" and (events[-1].get("outcome") or {}).get("type") == "interrupt" and approvals < 80:
        answers = []
        for i in events[-1]["outcome"]["interrupts"]:
            note("approval_card", id=i["id"], approved=True, card=json.dumps(i, default=str)[:3000])
            answers.append({"interruptId": i["id"], "status": "resolved", "payload": {"approved": True}})
        approvals += 1
        events = send(client, thread_id, None, f"{tag}a{approvals}", resume=answers)
    stored = client.get(f"/api/chats/{thread_id}").json()["messages"]
    reply = stored[-1]["content"] if stored and stored[-1]["role"] == "assistant" else ""
    note("assistant_reply", step=text, approvals=approvals, reply=reply)
    return reply


def gates(ws):
    path = ws / ".qe" / "ledger.jsonl"
    entries = [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []
    return {e["gate"] for e in entries if e.get("type") == "gate_decision" and e.get("decision") == "APPROVED"}


def missing(project_id, user_id, thread_id, ws):
    command = active_command.current(harness.state_dirs(project_id, user_id)["tools"], thread_id)
    return [p for p in (command or {}).get("paths", []) if not (ws / p).is_file()]


with TestClient(app) as client:
    assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
    me = client.get("/api/auth/me").json()
    project = client.post("/api/projects", json={"name": APP, "description": "agentic-qe brownfield cycle through the harness"}).json()
    ingest = client.post(f"/api/projects/{project['id']}/repo/git", json={"url": REPO})
    note("ingest", status=ingest.status_code)
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
    ws, n = sandbox_dir(project["id"]), 0
    for text, gate in STEPS:
        if gate is not None and gate > LAST_GATE:
            break
        n += 1
        if text.startswith("/agentic-qe:qe-start"):
            reply = turn(client, thread["id"], text, f"s{n}")
        else:
            reply = turn(client, thread["id"], text, f"s{n}")
            for k in range(CONTINUES):
                gaps = missing(project["id"], me["id"], thread["id"], ws)
                if 'Reply "continue"' not in reply and not gaps:
                    break
                note("continue_because", budget='Reply "continue"' in reply, missing=gaps)
                reply = turn(client, thread["id"], "continue", f"s{n}c{k}")
        if gate is None:
            continue
        for attempt in range(GATE_TRIES):
            turn(client, thread["id"], f"approve gate {gate} for {APP}", f"s{n}g{attempt}")
            if gate in gates(ws):
                note("gate_approved", gate=gate, attempt=attempt)
                break
            note("gate_refused", gate=gate, attempt=attempt)
            turn(client, thread["id"], f"The plugin refused gate {gate}. Fix exactly what its check reports, run the check again, and tell me when it passes.", f"s{n}f{attempt}")
        else:
            note("stopped", reason=f"gate {gate} still refused after {GATE_TRIES} tries")
            break
    with db() as con:
        led = [dict(r) for r in con.execute("SELECT seq, ts, actor, action, target, data FROM ledger WHERE project_id=? ORDER BY seq", (project["id"],))]
        tools = [dict(r) for r in con.execute("SELECT agent, tool, status, error, latency_ms, arguments FROM tool_calls WHERE project_id=? ORDER BY id", (project["id"],))]
    json.dump(led, open(os.path.join(out, "platform-ledger.json"), "w"), indent=1)
    json.dump(tools, open(os.path.join(out, "tool-calls.json"), "w"), indent=1)
    json.dump([r for r in led if r["action"] == "plugin.hook"], open(os.path.join(out, "hook-decisions.json"), "w"), indent=1)
    if (ws / "docs" / "qe").exists():
        shutil.copytree(ws / "docs" / "qe", os.path.join(out, "docs-qe"), dirs_exist_ok=True)
    for name in ("ledger.jsonl", "run.json"):
        if (ws / ".qe" / name).exists():
            shutil.copy2(ws / ".qe" / name, os.path.join(out, f"qe-{name}"))
    note("done", gates_approved=sorted(gates(ws)), workspace=str(ws))

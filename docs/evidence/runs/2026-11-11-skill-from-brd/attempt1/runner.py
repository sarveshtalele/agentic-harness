"""Live: a skill made from a BRD, end to end, on the real model passed in through env. Throwaway store (tests.conftest).
Path A, Skill Studio: BRD document -> plan -> approve -> generate -> test (repair up to 2 rounds) -> evaluate -> publish.
Path B, harness: the harness is asked to use the published skill on a sample, then to create a skill from the same BRD
with create_skill (the human approves the card). Every request and response is written to transcript.jsonl."""
import json
import os
import sys
import time

root, out = sys.argv[1], sys.argv[2]
sys.path[:0] = [os.path.join(root, "src"), root]
os.chdir(root)
import tests.conftest  # noqa: E402,F401
from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402

os.makedirs(out, exist_ok=True)
log = open(os.path.join(out, "transcript.jsonl"), "a", encoding="utf-8")
BRD = """# BRD: Invoice total calculator

## Purpose
Finance staff need the payable total of an invoice computed the same way every time.

## Requirements
- FR-1: The input is a JSON object with `lines` (each with `description`, `quantity`, `unit_price`), `discount_percent` (0 to 100) and `tax_percent` (0 to 50).
- FR-2: The subtotal is the sum of quantity times unit_price over all lines.
- FR-3: The discount applies to the subtotal; tax applies to the discounted amount.
- FR-4: Every money value is rounded half up to 2 decimals.
- FR-5: The output is JSON with `subtotal`, `discount`, `tax` and `total`.
- FR-6: A negative quantity or unit_price, or a percent out of range, is an error naming the field; no total is produced.

## Acceptance
- Two lines (2 x 10.00 and 1 x 5.50), discount 10, tax 20: subtotal 25.50, discount 2.55, tax 4.59, total 27.54.
- A line with quantity -1 returns an error naming `quantity`.
"""


def note(kind, **data):
    log.write(json.dumps({"t": time.strftime("%H:%M:%S"), "kind": kind, **data}, default=str) + "\n")
    log.flush()
    print(kind, json.dumps(data, default=str)[:400], flush=True)


def call(c, method, path, **kw):
    got = c.request(method, path, timeout=1800, **kw)
    body = got.json() if got.headers.get("content-type", "").startswith("application/json") else got.text
    note("api", method=method, path=path, status=got.status_code, body=body if len(json.dumps(body, default=str)) < 20000 else str(body)[:20000])
    return got.status_code, body


def harness_turn(c, thread_id, text, tag):
    note("user", text=text)
    body = {"threadId": thread_id, "runId": tag, "messages": [{"id": f"m_{tag}", "role": "user", "content": text}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    for n in range(20):
        with c.stream("POST", "/agui/harness", json=body, timeout=3600) as r:
            events = [json.loads(line[6:]) for line in "".join(r.iter_text()).splitlines() if line.startswith("data: ")]
        for e in events:
            if e["type"] in ("TOOL_CALL_START", "TOOL_CALL_RESULT", "RUN_ERROR"):
                note("event", type=e["type"], name=e.get("toolCallName"), content=str(e.get("content") or e.get("message") or "")[:3000])
        last = events[-1] if events else {}
        if last.get("type") == "RUN_FINISHED" and (last.get("outcome") or {}).get("type") == "interrupt":
            answers = [{"interruptId": i["id"], "status": "resolved", "payload": {"approved": True}} for i in last["outcome"]["interrupts"]]
            note("approval_card", cards=[json.dumps(i)[:1500] for i in last["outcome"]["interrupts"]])
            body = {"threadId": thread_id, "runId": f"{tag}a{n}", "messages": [], "resume": answers, "state": {}, "tools": [], "context": [], "forwardedProps": {}}
            continue
        break
    reply = c.get(f"/api/chats/{thread_id}").json()["messages"][-1]["content"]
    note("assistant_reply", text=reply)
    return reply


with TestClient(app) as c:
    assert c.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
    project = c.post("/api/projects", json={"name": "Invoice skills", "description": "skill from a BRD"}).json()["id"]
    _, doc = call(c, "POST", f"/api/projects/{project}/documents", json={"kind": "brd", "title": "BRD: Invoice total calculator", "content": BRD})
    # Path A: Skill Studio
    status, plan = call(c, "POST", "/api/skill-studio/plans", json={"project_id": project, "kind": "scripts", "source": {"type": "document", "document_id": doc["id"]},
                                                                    "request": "Create a skill that computes invoice totals exactly as this BRD says, with a scripts/run.py that reads the JSON input on stdin and prints the JSON output."})
    summary = {"plan_status": status}
    if status == 201:
        pid = plan["id"]
        summary["approve"] = call(c, "POST", f"/api/skill-studio/plans/{pid}/approve")[0]
        summary["generate"] = call(c, "POST", f"/api/skill-studio/plans/{pid}/generate")[0]
        status, tested = call(c, "POST", f"/api/skill-studio/plans/{pid}/test", json={"mode": "scripts"})
        summary["test"] = tested.get("summary") if isinstance(tested, dict) else tested
        for _ in range(2):
            if isinstance(tested, dict) and (tested.get("summary") or {}).get("all_passed"):
                break
            call(c, "POST", f"/api/skill-studio/plans/{pid}/repair")
            status, tested = call(c, "POST", f"/api/skill-studio/plans/{pid}/test", json={"mode": "scripts"})
            summary["test_after_repair"] = tested.get("summary") if isinstance(tested, dict) else tested
        summary["evaluate"] = call(c, "POST", f"/api/skill-studio/plans/{pid}/evaluate")[1]
        status, published = call(c, "POST", f"/api/skill-studio/plans/{pid}/publish")
        summary["publish"] = {"status": status, "body": published}
    note("studio_summary", **summary)
    # Path B: the harness uses the published skill, then makes its own from the same BRD
    thread = c.post(f"/api/projects/{project}/chats", json={"agent": "harness"}).json()["id"]
    name = (summary.get("publish") or {}).get("body", {}).get("name") if isinstance((summary.get("publish") or {}).get("body"), dict) else None
    if name:
        harness_turn(c, thread, f"Use the {name} skill on this invoice and show the totals: two lines (2 x 10.00 and 1 x 5.50), discount 10, tax 20.", "h1")
    harness_turn(c, thread, f"Create a new skill from the BRD document '{doc['title']}' in this project: it should check an invoice JSON against FR-6 and list every invalid field. Use create_skill.", "h2")
    note("done")

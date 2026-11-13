"""Live: the agentic-qe cycle to Gate 5 on a real repository with the real model (docs/PHASE2_PLAN.md R5, FINAL_PLAN item 2).

    python scripts/dev.py live tests/test_qe_cycle_live.py

The harness runs the plugin's own phase commands on sarveshtalele/personal-finance-mcp (cloned from GitHub). This test is
the human: it answers the harness's approval cards and types each gate approval in the plugin's own grammar, and a gate
counts only when the plugin's hook recorded it in the workspace's .qe/ledger.jsonl. A refused gate gets at most three
"fix what the check reports" turns. Everything is kept in docs/evidence/runs/<date>-qe-cycle-g5/: the session as JSON
lines, the approval cards, the plugin's docs/qe tree and ledger, and the traceability view.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import app as platform
from backend.config import sandbox_dir

pytestmark = pytest.mark.live
REPO, APP = "sarveshtalele/personal-finance-mcp", "personal-finance-mcp"
OUT = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "runs" / f"{date.today().isoformat()}-qe-cycle-g5-{os.environ.get('DEFAULT_MODEL', 'model')}"
FIX = "/agentic-qe:qe-{phase} {app} the plugin refused gate {gate}: run check_gate({gate}, \"{app}\") and describe_contract on each file it names, fix exactly the gaps it reports, run check_gate again, and tell me when it passes."
# (command, gate it ends with or None, phase name for a fix turn)
STEPS = [("/agentic-qe:qe-start {app} --mode brownfield", 0, "start"), ("/agentic-qe:qe-doctor", None, "doctor"),
         ("/agentic-qe:qe-discover {app}", None, "discover"), ("/agentic-qe:qe-requirements {app}", 1, "requirements"),
         ("/agentic-qe:qe-plan {app}", 2, "plan"), ("/agentic-qe:qe-design {app}", None, "design"), ("/agentic-qe:qe-data {app}", 3, "data"),
         ("/agentic-qe:qe-generate {app}", 4, "generate"), ("/agentic-qe:qe-execute {app}", None, "execute"), ("/agentic-qe:qe-heal {app}", None, "heal"),
         ("/agentic-qe:qe-trace {app}", None, "trace"), ("/agentic-qe:qe-sign {app}", 5, "sign")]


def approved(root: Path, gate: int) -> bool:
    ledger = root / ".qe" / "ledger.jsonl"
    state = None
    for line in ledger.read_text(encoding="utf-8").splitlines() if ledger.is_file() else []:
        r = json.loads(line)
        if r.get("type") == "gate_decision" and r.get("source") == "user_prompt" and r.get("gate") == gate:
            state = r.get("decision")
    return state == "APPROVED"


def test_the_agentic_qe_cycle_reaches_gate_5_on_a_real_repository(monkeypatch):
    assert os.environ.get("DEFAULT_MODEL") and os.environ.get("OPENAI_API_KEY"), "live test needs a real model in the environment"
    OUT.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AQH_HOME", str(OUT / "aqh"))  # the session's JSON lines land in the evidence folder
    from aqh.client import Session

    log = (OUT / "steps.jsonl").open("a", encoding="utf-8")
    note = lambda **kw: (log.write(json.dumps({"t": time.strftime("%H:%M:%S"), **kw}) + "\n"), log.flush())  # noqa: E731
    with TestClient(platform) as http:
        session = Session(http, local=False)
        session.login("qa-admin", os.environ["ATLAS_ADMIN_PASSWORD"])
        project = http.post("/api/projects", json={"name": APP, "description": "Live agentic-qe cycle to Gate 5"}).json()
        clone = http.post(f"/api/projects/{project['id']}/repo/git", json={"url": REPO})
        assert clone.status_code == 200, clone.text
        thread = session.new_thread(project["id"])
        root = sandbox_dir(project["id"])
        cards = []

        def turn(text: str) -> str:
            reply = []
            started = time.monotonic()
            session.turn(thread, text, lambda card: cards.append(card.get("message", "")) or True,
                         lambda e: reply.append(e.get("delta", "")) if e.get("type") == "TEXT_MESSAGE_CONTENT" else None, OUT)
            said = "".join(reply)
            note(kind="turn", text=text, seconds=int(time.monotonic() - started), reply=said[-3000:])
            return said

        reached = -1
        for command, gate, phase in STEPS:
            said = turn(command.format(app=APP))
            if phase == "doctor" and "not set up" in said.lower():
                turn("Set up the pandas/numpy validator that qe-doctor reports as not set up: run its validator command with --yes, then run qe-doctor's check again.")
            if gate is None:
                continue
            phrase = f"approve gate 0 for {APP} mode brownfield" if gate == 0 else f"approve gate {gate} for {APP}"
            for attempt in range(3):  # at most two fix turns: a third repeat of the same failure is a harness defect to fix, not to retry
                turn(phrase)
                if approved(root, gate):
                    break
                note(kind="refused", gate=gate, attempt=attempt + 1)
                if attempt < 2:
                    turn(FIX.format(phase=phase, app=APP, gate=gate))
            note(kind="gate", gate=gate, approved=approved(root, gate))
            if not approved(root, gate):
                break
            reached = gate
        trace = http.get(f"/api/projects/{project['id']}/qe/trace").json()
        (OUT / "trace.json").write_text(json.dumps(trace, indent=1), encoding="utf-8")
        (OUT / "cards.json").write_text(json.dumps(cards, indent=1), encoding="utf-8")
        for name in ("docs/qe", ".qe"):
            if (root / name).exists():
                shutil.copytree(root / name, OUT / "workspace" / name, dirs_exist_ok=True)
        note(kind="end", reached=reached)
        log.close()
    assert reached == 5, f"the cycle stopped after gate {reached}; see {OUT}"

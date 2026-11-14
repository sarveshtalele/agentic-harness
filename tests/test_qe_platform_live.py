"""Live: the platform's QE Cycle (Gates 0 to 5) on a real repository with the real model, through the API.

    python scripts/dev.py live tests/test_qe_platform_live.py

AQE_LIVE_REPO picks the repository (default: personal-finance-mcp on GitHub). The test signs in as the test admin, who
approves each gate as the named person; every gate's summary, the agentic-qe plugin's verdicts and the seconds per gate
go to docs/evidence/runs/<date>-qe-platform-<repo>-<model>/summary.json, written before any assertion can fail.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from pathlib import Path

import pytest

from tests.helpers_api import client, pending, wait_run  # noqa: F401 - fixtures

pytestmark = pytest.mark.live

REPO = os.environ.get("AQE_LIVE_REPO", "https://github.com/sarveshtalele/personal-finance-mcp.git")
REASON = ("Live test approver: approved with the REJECT items still listed after one send-back, to measure the later "
          "stages end to end. Not a release decision.")
STAGE_LIMIT = 600 # seconds one gate segment may take before the run counts as stuck; the 180 s goal is reported, not hidden


def _evidence_dir() -> Path:
    name = re.sub(r"[^a-z0-9-]+", "-", f"{Path(REPO).stem}-{os.environ.get('DEFAULT_MODEL', 'model')}".lower()).strip("-")
    folder = Path(__file__).resolve().parent.parent / "docs" / "evidence" / "runs" / f"{dt.datetime.now():%Y-%m-%d-%H%M}-qe-platform-{name}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def test_qe_cycle_to_gate5_on_a_real_repository(client):
    project = client.post("/api/projects", json={"name": Path(REPO).stem, "description": "live QE cycle"}).json()
    connected = client.post(f"/api/projects/{project['id']}/repo/git", json={"url": REPO})
    assert connected.status_code == 200, connected.text
    started = time.time()
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    record = {"repo": REPO, "model": os.environ.get("DEFAULT_MODEL"), "run_id": run["id"], "gates": [], "started": dt.datetime.now().isoformat()}
    folder = _evidence_dir()
    try:
        mark = time.time()
        sent_back: set[int] = set()
        for _ in range(9):
            run = wait_run(client, run["id"], timeout=STAGE_LIMIT)
            if run["status"] != "waiting_approval":
                break
            approval = pending(run)
            entry = {"gate": approval["gate"], "seconds": round(time.time() - mark, 1), "title": approval["title"],
                     "summary": approval["summary"], "plugin_check": approval["payload"].get("plugin_check"),
                     "design_audit": approval["payload"].get("design_audit")}
            record["gates"].append(entry)
            decided = client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True})
            if decided.status_code == 400 and approval["gate"] not in sent_back and approval["gate"] < 5:  # sending Gate 5 back ends the run
                # the engine refuses to approve REJECT items without a reason; as a person would, send the gate back once with it
                entry["refused"] = decided.json().get("detail")
                sent_back.add(approval["gate"])
                decided = client.post(f"/api/approvals/{approval['id']}/decide",
                                      json={"approved": False, "feedback": f"Revise the items the review judged REJECT and fix their flaws. {entry['refused']}"})
                entry["sent_back"] = True
            elif decided.status_code == 400:
                # owner decision 2026-11-14: after one send-back, the test admin approves what is left with a written reason,
                # so Gates 4 and 5 are measured; the reason is in the gate record and this evidence, never hidden
                entry["refused"] = decided.json().get("detail")
                entry["approved_with_reason"] = REASON
                decided = client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True, "feedback": REASON})
            assert decided.status_code == 200, decided.text
            mark = time.time()
        run = wait_run(client, run["id"], ("completed", "failed", "rejected"), timeout=STAGE_LIMIT)
    finally:
        record |= {"status": run.get("status"), "error": run.get("error"), "total_seconds": round(time.time() - started, 1),
                   "summary": (run.get("state") or {}).get("summary"),
                   "requirements": len((run.get("state") or {}).get("requirements") or [])}
        (folder / "summary.json").write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
        print(f"\nevidence: {folder / 'summary.json'}", flush=True)
        for g in record["gates"]:
            print(f"G{g['gate']} after {g['seconds']} s: {g['summary'][:300]}", flush=True)
    assert run["status"] == "completed", run.get("error")
    assert [g["gate"] for g in record["gates"] if not g.get("sent_back")] == [0, 1, 2, 3, 4, 5]
    assert record["gates"][1]["plugin_check"]["error"] is None, record["gates"][1]["plugin_check"]

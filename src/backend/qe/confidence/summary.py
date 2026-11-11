"""Summarising reviews, capping failed tests, reject ids."""
from __future__ import annotations

from backend.qe.confidence.rubric import TEST_FAIL_CAP, verdict_for, worst


def summarise(records: list[dict], tokens: dict | None = None) -> dict:
    """The roll-up kept under `cases_review`, `tests_review` and `plan_review`. Verdict by the worst rule; a case that did not run counts as REVISE, never APPROVED."""
    done = [r for r in records if r.get("status") == "reviewed"]
    verdicts = [r["verdict"] for r in records]
    if not done:
        verdict = "NOT RUN"
    elif "REJECT" in verdicts:
        verdict = "REJECT"
    elif "REVISE" in verdicts or len(done) < len(records):
        verdict = "REVISE"
    else:
        verdict = "APPROVED"
    issues = [f"{r['tc_id']}: {f.get('dimension') or 'flaw'} at {f['evidence']}. Fix: {f['fix']}" for r in records for f in r.get("flaws", [])][:30]
    issues += [f"{r['tc_id']}: NOT RUN. {r['problems'][0] if r.get('problems') else ''}" for r in records if r.get("status") == "NOT RUN"][:10]
    return {"score": round(sum(r["total"] for r in done) / len(done)) if done else None, "verdict": verdict, "issues": issues[:40],
            "counts": {"cases": len(records), "approved": verdicts.count("APPROVED"), "revise": verdicts.count("REVISE"), "reject": verdicts.count("REJECT"), "not_run": len(records) - len(done),
                       "low": sum(1 for r in records if r.get("low")), "evidence_missing": sum(1 for r in records if r.get("evidence") == "missing")},
            "tokens": tokens or {}, "records": records}


def cap_failed(records: list[dict], executed: dict[str, str]) -> dict:
    """After execution: a reviewed test that FAILED shows at most TEST_FAIL_CAP. `executed` maps a case id to passed, failed, skipped or not run."""
    capped = []
    for record in records:
        if record.get("status") == "reviewed" and executed.get(record["tc_id"]) == "failed":
            total = min(record["total"], TEST_FAIL_CAP)
            capped.append({**record, "total_before": record["total"], "total": total, "capped": True, "verdict": worst(record["verdict"], verdict_for(total)),
                           "low": True, "low_reason": f"the test failed when it ran, so its score is capped at {TEST_FAIL_CAP}"})
        else:
            capped.append({**record, "capped": False})
    before = summarise(records)
    summary = summarise(capped)
    return {**summary, "score_before": before["score"], "capped": sum(1 for r in capped if r["capped"]), "failed": sum(1 for r in records if executed.get(r["tc_id"]) == "failed"),
            "executed": sum(1 for r in records if executed.get(r["tc_id"]) in {"passed", "failed"})}


def reject_ids(payload: dict) -> list[str]:
    """Ids of the records on a gate that code judged REJECT, for the rule that a person approving them must give a reason."""
    review = payload.get("confidence") or {}
    return [r.get("tc_id", "?") for r in review.get("records", []) if r.get("verdict") == "REJECT"]


def flaw_lines(record: dict) -> str:
    """The flaws and fixes of one record, as the text an agent receives when its item is sent back."""
    return "\n".join(f"- {f.get('dimension') or 'flaw'} at {f['evidence']}. Fix: {f['fix']}" for f in record.get("flaws", [])) or "- " + "; ".join(record.get("problems", [])[:3])

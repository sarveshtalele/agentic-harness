"""QE Sign Stage: Release readiness review and Gate 5 sign-off."""
from __future__ import annotations

import json
from backend.core import documents
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.trace import _defect_body
from backend.qe import model


async def qe_sign(rc: RunContext, state: dict) -> dict:
    s = state["summary"]
    call = AgentCall(rc.run_id, rc.project_id, "confidence-reviewer")
    review = await call.typed(f"Independently review release readiness from this evidence only.\nSUMMARY:\n{json.dumps(s)}\nDEFECTS:\n{json.dumps(state.get('defects', []))[:6000]}\nHEALER LOG:\n{json.dumps(state.get('healer_log', []))}\nPLAN REVIEW:\n{json.dumps(state.get('plan_review'))}", model.ConfidenceReview)
    body = (f"## Verdict: {s['verdict']}\n\n| Metric | Value |\n|---|---|\n| Tests executed | {s['executed']} |\n| Passed | {s['passed']} |\n| Failed | {s['failed']} |\n| Pass rate | {s['pass_rate']}% |\n"
            f"| Requirements covered | {s['requirements_covered']}/{s['requirements']} ({s['coverage']}%) |\n| Application defects | {s['defects']} |\n| Independent review | {review.score} ({review.verdict}) |\n\n"
            f"## Coverage gaps\n\n{', '.join(s['gaps']) or 'None'}\n\n## Review issues\n\n" + ("\n".join(f"- {i}" for i in review.issues) or "None") + "\n\n## Defect records\n\n" + _defect_body(state.get("defect_records", [])) + "\n\n## Execution summary\n\n" + (state.get("execution_summary") or {}).get("text", "No summary.") + "\n\n## Defects\n\n" + ("\n".join(f"- **{d['name']}**: {d['message'][:300]}" for d in state.get("defects", [])) or "None") + f"\n\nBranch with generated tests: `{state.get('branch', '')}`\n")
    doc = documents.create(rc.project_id, "release", "Production Release Readiness & Sign-Off", body, "agent:confidence-reviewer", data={"summary": s, "review": review.model_dump()}, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    return {"release_doc": doc["id"], "release_review": review.model_dump()}

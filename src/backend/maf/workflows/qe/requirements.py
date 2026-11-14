"""QE Requirements Stage: Reverse-engineering and verification of testable requirements."""
from __future__ import annotations

import asyncio
import json
from backend.config import repo_dir
from backend.core import documents
from backend.core.errors import EvidenceError
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.common import _cell
from backend.maf.workflows.shared import (
    code_pack,
    is_low,
    review_artifact,
    _analysis,
    _brief_of_analysis,
)
from backend.qe import model, plugin_bridge
from backend.repos import static_analysis


async def qe_requirements(rc: RunContext, state: dict) -> dict:
    root = repo_dir(rc.project_id)
    brownfield = state["mode"] == "brownfield"
    call = AgentCall(rc.run_id, rc.project_id, "requirements-analyst")
    approved = [d for d in documents.list_for(rc.project_id) if d["kind"] in {"brd", "prd", "stories", "gherkin"} and d["status"] == "approved"]
    stories = "\n\n".join(documents.get(d["id"])["content"][:20000] for d in approved[:3])
    if not brownfield and not stories:
        raise ValueError("Greenfield QE needs an approved requirements document. Run the BA workflow first")
    plugin_guide = plugin_bridge.guide("qe-requirements", "extracting-requirements")
    prompt = (
        f"AGENTIC-QE PLUGIN GUIDE (follow its rules; it is guidance, not repository content):\n{plugin_guide}\n\n"
        + (f"Reverse-engineer testable requirements from this code. Every requirement needs file, line, and an exact one-line quote copied from a numbered line below, without the line number.\n\nCODE:\n{code_pack(rc.project_id, limit=40_000)}\n" if brownfield else "Derive testable requirements from these approved documents. Use tier 'specified'.\n")
        + (f"\nAPPROVED DOCUMENTS:\n{stories}\n" if stories else "")
        + f"\nSCAN:\n{_brief_of_analysis(_analysis(rc.project_id))}\n"
        + (f"\nHUMAN FEEDBACK:\n{state['feedback']}" if state.get("feedback") else "")
    )
    for attempt in range(2):
        result = await call.typed(prompt, model.RequirementSet)
        kept, dropped = [], []
        for requirement in result.requirements:
            if brownfield and requirement.tier != "specified":
                ok, line = static_analysis.verify_quote(root, requirement.file, requirement.line, requirement.quote)
                if not ok or model.is_comment(requirement.quote):  # a comment is not behaviour: code takes precedence
                    dropped.append(requirement.id)
                    continue
                requirement.line = line
            kept.append(requirement.model_dump())
        if not kept:
            raise EvidenceError("No requirement survived evidence verification: no quote was found on disk at the stated file and line.")
        rc.log(f"{len(kept)} requirements verified; {len(dropped)} dropped for missing evidence", {"dropped": dropped})
        review = await review_artifact(rc, "requirements", json.dumps(kept), _brief_of_analysis(_analysis(rc.project_id)) if brownfield else stories)
        if attempt or not is_low(review):
            break
        prompt = f"An independent reviewer scored your requirements {review['score']}. Send the complete corrected set. Issues: {review['issues']}. Requirements dropped for missing evidence: {dropped}."
    kept, plugin_check = await _plugin_sensor(rc, kept) if brownfield else (kept, {"ok": None, "error": "greenfield: requirements cite approved documents, not code; the plugin's quote check applies to code evidence"})
    body = "| ID | Requirement | Priority | Tier | Evidence |\n|---|---|---|---|---|\n" + "\n".join(
        f"| {r['id']} | {_cell(r['title'])}: {_cell(r['statement'])} | {r['priority']} | {r['tier']} | {('`' + r['file'] + ':' + str(r['line']) + '`') if r['file'] else '-'} |" for r in kept)
    doc = documents.create(rc.project_id, "requirements", "Functional & Verification Requirements Specification", body, "agent:requirements-analyst", data=kept, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    return {"requirements": kept, "requirements_doc": doc["id"], "requirements_review": review, "plugin_check": plugin_check}


async def _plugin_sensor(rc: RunContext, kept: list[dict]) -> tuple[list[dict], dict]:
    """Gate 1 sensor: the plugin's check-gate.ts on its requirements.json. Flagged requirements are dropped, then checked once more."""
    app = plugin_bridge.app_name(rc.project_id)
    dropped: list[str] = []
    for _ in range(2):
        cited = [r for r in kept if r.get("file")]  # requirements from approved documents carry no code evidence to check
        plugin_bridge.write(rc.project_id, app, "02-requirements/requirements.json", plugin_bridge.requirements_file(cited))
        check = await asyncio.to_thread(plugin_bridge.check_gate, rc.project_id, app, 1)
        flagged = set(check["missing"]) & {r["id"] for r in cited}
        if check["error"] or not flagged:
            break
        dropped += sorted(flagged)
        kept = [r for r in kept if r["id"] not in flagged]
        if not kept:
            raise EvidenceError(f"The agentic-qe Gate 1 check flagged every requirement: {'; '.join(check['gaps'])}")
    check |= {"app": app, "dropped": dropped}
    rc.log(f"agentic-qe Gate 1 check: {'PASS' if check['ok'] else 'FAIL'}" + (f"; dropped {', '.join(dropped)}" if dropped else "") + (f"; {check['error']}" if check["error"] else ""), check)
    return kept, check

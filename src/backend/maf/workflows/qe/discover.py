"""QE Discovery Stage: AST repository analysis and architecture mapping."""
from __future__ import annotations

from backend.config import repo_dir
from backend.core import doc_checks, documents
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.ba import _strip_preamble
from backend.maf.workflows.shared import (
    discovery_pack,
    is_low,
    review_artifact,
    _analysis,
    _brief_of_analysis,
)
from backend.repos import scan, static_analysis


async def qe_discover(rc: RunContext, state: dict) -> dict:
    a = _analysis(rc.project_id)
    root = repo_dir(rc.project_id)
    call = AgentCall(rc.run_id, rc.project_id, "repo-intelligence-analyst")
    evidence = f"SCAN:\n{_brief_of_analysis(a)}\n\nCODE:\n{discovery_pack(rc.project_id)}"
    text = _strip_preamble(await call.text(f"Write the discovery summary from these scan facts and this code.\n\n{evidence}"))
    tree = scan.tree(root, limit=100_000) if root.exists() else []
    sources = static_analysis.review_targets(root) if root.exists() else []
    issues = doc_checks.discovery_issues(text, tree, sources, evidence)
    review = await review_artifact(rc, "discovery summary", text, evidence)
    if issues or is_low(review):
        rc.log(f"Discovery sent back: {issues or review['issues']}", kind="warning")
        text = _strip_preamble(await call.text(f"Rewrite the complete discovery summary and fix these problems: {issues + review['issues']}. Use only paths that appear in the evidence."))
        issues = doc_checks.discovery_issues(text, tree, sources, evidence)
        review = await review_artifact(rc, "discovery summary", text, evidence)
    if issues:
        rc.log(f"Discovery still has gaps: {issues}", kind="warning")
    doc = documents.create(rc.project_id, "discovery", "Repository AST Architecture & Stack Discovery", text, "agent:repo-intelligence-analyst", data=a, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    rc.log("Discovery saved", {"document_id": doc["id"]}, "artifact")
    return {"discovery_id": doc["id"], "discovery_review": review, "discovery_issues": issues}

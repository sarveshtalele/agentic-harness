"""Gate 0 intake and the token lines a gate shows."""
from __future__ import annotations

from backend.config import RUN_TOKEN_LIMIT
from backend.core import gates
from backend.db import db
from backend.maf.engine import RunContext
from backend.maf.workflows.shared.pack import _analysis
from backend.rag import retrieve, store
from backend.repos import ingest


async def intake(rc: RunContext, state: dict) -> dict:
    a = _analysis(rc.project_id)
    rc.log(f"Mode {a['mode']}: {a['total_files']} files, runners {a['test_runners'] or 'none'}")
    return {"mode": a["mode"]}


def documents_note(project_id: str) -> tuple[str, list[dict]]:
    """Gate 0's line on the uploaded requirement documents and what search can do with them; ("", []) when none are indexed."""
    found = store.sources(project_id)
    if not found:
        return "", []
    how = retrieve.mode(project_id)
    search = "hybrid (keyword and vector)" if how["vector"] else f"keyword only. {how['note']}".strip()
    names = ", ".join(f"{s['filename']} v{s['version']}" for s in found)
    return f" Requirement documents ({len(found)}): {names}. Search: {search}", [{k: s[k] for k in ("doc_id", "filename", "version", "chunk_count", "sha256")} for s in found]


def intake_gate(rc: RunContext, state: dict):
    if gates.is_approved(rc.project_id, 0):
        return None
    a = _analysis(rc.project_id)
    repo = ingest.get(rc.project_id)
    source = f"{repo['kind']} {repo['url']} at {repo['commit_sha'][:10]}" if repo else "no repository"
    note, docs = documents_note(rc.project_id)
    return {"gate": 0, "title": "Gate 0: confirm intake scope",
            "summary": f"Mode: {a['mode']}. Source: {source}. Files: {a['total_files']}. Languages: {', '.join(a['languages']) or 'none'}. "
                       "Agents read this project's repository and documents only. Generated code lands on a separate branch." + note
                       + (" Approving Gate 0 lets the platform run this repository's dependency installers (pip, npm) in the sandbox, only to collect and compile the generated tests. No test body is run; "
                          "you download the tests and run them on your own systems." if a["mode"] == "brownfield" else ""),
            "payload": {"analysis": {k: a.get(k) for k in ("mode", "languages", "frameworks", "test_runners", "total_files", "test_file_count")}, "sources": docs, "search": retrieve.mode(rc.project_id)}}


def token_line(run_id: str) -> dict:
    """Tokens this run has used against its limit, for the gate."""
    with db() as con:
        row = con.execute("SELECT tokens_in+tokens_out FROM runs WHERE id=?", (run_id,)).fetchone()
    used = row[0] if row else 0
    return {"used": used, "limit": RUN_TOKEN_LIMIT, "left": max(RUN_TOKEN_LIMIT - used, 0), "text": f"Tokens: {used:,} used of {RUN_TOKEN_LIMIT:,}, {max(RUN_TOKEN_LIMIT - used, 0):,} left."}


def token_estimate(run_id: str, agent: str | None, calls: int, next_step: str, basis: str) -> dict:
    """What the next step will probably cost, from model calls this run has already made. Nothing is invented: with no recorded call to average, the estimate is null and says why.

    `agent` limits the average to one agent's calls; None averages every call in the run.
    """
    with db() as con:
        used = con.execute("SELECT tokens_in+tokens_out FROM runs WHERE id=?", (run_id,)).fetchone()
        count, total = con.execute(f"SELECT COUNT(*), COALESCE(SUM(tokens_in+tokens_out), 0) FROM agent_calls WHERE run_id=? AND status='ok' AND tokens_in+tokens_out>0{' AND agent=?' if agent else ''}",
                                   (run_id, agent) if agent else (run_id,)).fetchone()
    average = round(total / count) if count else None
    return {"used_so_far": used[0] if used else 0, "run_limit": RUN_TOKEN_LIMIT, "next_step": next_step, "average_agent": agent or "all agents", "recorded_calls": count,
            "average_tokens_per_call": average, "expected_calls": calls, "estimated_tokens": average * calls if average is not None else None,
            "basis": basis if average is not None else f"No call by {agent or 'any agent'} is recorded in this run yet, so there is nothing to base an estimate on."}

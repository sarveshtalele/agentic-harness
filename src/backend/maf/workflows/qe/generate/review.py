"""Independent review of the generated tests with one send-back, and the saved test-code document."""
from __future__ import annotations

import json

from backend.core import documents
from backend.maf.runtime import AgentCall
from backend.maf.workflows.edits import Edit, apply_edits
from backend.maf.workflows.qe.common import CODE_REVIEW_BATCH
from backend.maf.workflows.qe.generate.env import Env
from backend.maf.workflows.qe.generate.files import GeneratedFile, GeneratedSuite, _generated_file_problems
from backend.maf.workflows.shared import review_evidence, review_with_send_back
from backend.qe import confidence, emit


async def review_and_save(env: Env, suite: GeneratedSuite, unresolved: list[dict], case_of: dict, call: AgentCall, missing: list[str], partial: dict | None) -> dict:
    rc, state, worktree, known, async_ok, facts = env.rc, env.state, env.worktree, env.known, env.async_ok, env.facts
    static_findings = env.static_findings
    marked = {u["path"] for u in unresolved}
    tests = [{"case_id": cid, "path": f.path, **({"unresolved": True} if f.path in marked else {})} for f in suite.files for cid in f.case_ids]

    def test_text(item: GeneratedFile) -> str:
        numbered = "\n".join(f"{n}: {line}" for n, line in enumerate(item.content.splitlines(), 1))
        return f"TEST FILE {item.path}\n{numbered[:8_000]}\nCASE:\n{json.dumps(case_of.get(item.case_ids[0], {}))}"

    def test_evidence(indexes: list[int]) -> str:
        chosen = {case_of[suite.files[i].case_ids[0]]["requirement_id"] for i in indexes if suite.files[i].case_ids[0] in case_of}
        return review_evidence(rc.project_id, [r for r in state["requirements"] if r["id"] in chosen], worktree)

    async def revise_test(i: int, record: dict, calls: list) -> str:
        old = suite.files[i]
        again = AgentCall(rc.run_id, rc.project_id, "test-automation-engineer")
        calls.append(again)
        result = await again.typed(f"Rewrite only this generated test file and fix every flaw the independent reviewer found. Send a suite with exactly this one file, with the same path and case id.\nCASE:\n{json.dumps(case_of.get(old.case_ids[0], {}))}\n"
                                   f"CURRENT FILE {old.path}:\n{old.content}\nFLAWS AND FIXES:\n{confidence.flaw_lines(record)}\n\n{test_evidence([i])}", GeneratedSuite, attempts=2)
        new = next((f for f in result.files if f.path == old.path), None)
        if new is None or new.case_ids != old.case_ids:
            raise ValueError("The agent did not send back the same file for the same case")
        if problems := [*_generated_file_problems(new, known, worktree, async_ok), *(found if len(found := static_findings(new)) > len(static_findings(old)) else [])]:
            raise ValueError("; ".join(problems[:3]))
        if refused := apply_edits(worktree, [Edit(path=new.path, action="create", content=new.content)]):
            raise ValueError("; ".join(refused[:3]))
        suite.files[i] = new
        return test_text(new)

    records, tokens = await review_with_send_back(rc, "code", "generated tests", [(f.case_ids[0], test_text(f)) for f in suite.files], test_evidence, worktree, revise_test, CODE_REVIEW_BATCH)
    for record, item in zip(records, suite.files):
        record["file"] = record.get("file") or item.path
    tests_review = confidence.summarise(records, tokens)
    flagged_text = {u["path"]: "> STATIC CHECK FINDINGS, still open after one round trip to the agent:\n" + "\n".join(f"> - {x}" for x in u["findings"]) + "\n\n" for u in unresolved}
    body = "\n\n".join(f"## {f.path}\n\nCases: {', '.join(f.case_ids)}\n\n{flagged_text.get(f.path, '')}```\n{f.content}\n```" for f in suite.files)
    if partial:
        body = f"> PARTIAL RESULT. No tests yet for: {', '.join(partial['missing'])}\n\n" + body
    doc = documents.create(rc.project_id, "test_code", "Autonomous End-to-End Test Suite (PARTIAL)" if partial else "Autonomous End-to-End Test Suite", body, "agent:test-automation-engineer", data=tests, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    rc.log(f"[TEST_SYNTHESIS_COMPLETED] {len(suite.files)} deterministic test files written to sandbox branch {state['branch']}", kind="artifact")
    return {"worktree": state["worktree"], "branch": state["branch"], "tests": tests, "framework": suite.framework, "test_doc": doc["id"], "heal_attempts": state.get("heal_attempts", 0), "tests_review": tests_review, "tests_missing": missing, "emit_unresolved": unresolved, "env_facts": facts, "partial": partial,
            "missing_deps": [] if state.get("install_deps") else emit.missing_dependencies(worktree, env.inventory)}
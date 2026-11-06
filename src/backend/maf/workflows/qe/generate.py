"""QE Test Generation Stage: Synthesizing executable deterministic test suites in isolated sandbox worktrees."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from pydantic import BaseModel, Field

from backend.config import project_dir, repo_dir
from backend.core import documents
from backend.core.errors import AllowanceError, AqeError, ModelSchemaError
from backend.maf.engine import RunContext, part_key
from backend.maf.runtime import AgentCall
from backend.maf.workflows.edits import Edit, apply_edits
from backend.maf.workflows.qe.common import (
    CODE_REVIEW_BATCH,
    GENERATE_BATCH,
    settle,
)
from backend.maf.workflows.shared import (
    code_pack,
    review_evidence,
    review_with_send_back,
    _analysis,
)
from backend.qe import confidence, emit, execution
from backend.repos import git


class GeneratedFile(BaseModel):
    path: str
    case_ids: list[str] = Field(min_length=1)
    content: str


class GeneratedSuite(BaseModel):
    framework: str
    files: list[GeneratedFile] = Field(min_length=1)


def _clean_code(code: str) -> str:
    text = (code or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
    return text


def _generated_file_problems(item: GeneratedFile, known: set[str], worktree: Path, async_ok: bool = False) -> list[str]:
    item.content = _clean_code(item.content)
    errors = list(execution.invalid_test_code(worktree, item.path, item.content, async_ok))
    if not set(item.case_ids) <= known:
        errors.append(f"{item.path}: unknown case ids")
    if issue := execution.syntax_error(item.path, item.content):
        errors.append(issue)
    if re.search(r"assert\s+True\b|expect\(\s*true\s*\)\.toBe\(\s*true\s*\)", item.content):
        errors.append(f"{item.path}: tautological assertion")
    if placeholder := re.search(r"^\s*(pass|\.\.\.)\s*$|\bTODO\b", item.content, re.M):
        errors.append(f"{item.path}: line {item.content.count(chr(10), 0, placeholder.start()) + 1} has placeholder code ({placeholder.group(0).strip()}). Remove it and write real code. Do not use pass, an ellipsis, or the word TODO anywhere in the file")
    if "CASE_ID" not in item.content.splitlines()[0]:
        errors.append(f"{item.path}: first line must be a CASE_ID comment")
    if len(item.case_ids) != 1:
        errors.append(f"{item.path}: one case per file")
    if not item.path.replace("\\", "/").startswith("tests/agentic_qe/"):
        errors.append(f"{item.path}: must live under tests/agentic_qe/")
    return errors


async def qe_generate(rc: RunContext, state: dict) -> dict:
    root = repo_dir(rc.project_id)
    if not state.get("worktree"):
        if not root.exists():
            root.mkdir(parents=True)
            await asyncio.to_thread(git.init_snapshot, root, "Agentic QE Platform greenfield baseline")
            (root / ".gitkeep").write_text("", encoding="utf-8")
            await asyncio.to_thread(git.commit_all, root, "Agentic QE Platform greenfield baseline")
        worktree = project_dir(rc.project_id) / "worktrees" / rc.run_id
        worktree.parent.mkdir(parents=True, exist_ok=True)
        branch = f"atlas/qe-{rc.run_id[-6:]}"
        if not worktree.exists():
            await asyncio.to_thread(git.add_worktree, root, worktree, branch)
        state = {**state, "worktree": str(worktree), "branch": branch}
        rc.log(f"[SANDBOX_WORKTREE] Created isolated git worktree at {worktree} on branch {branch}")
    else:
        worktree = Path(state["worktree"])
        rc.log(f"[SANDBOX_WORKTREE] Reusing verified git worktree at {worktree}")

    worktree = Path(state["worktree"])
    rc.log(f"[TEST_SYNTHESIS_STARTED] Synthesizing deterministic test suite for {len(state['cases'])} cases in sandbox...")
    call = AgentCall(rc.run_id, rc.project_id, "test-automation-engineer")
    a = _analysis(rc.project_id)
    known = {c["id"] for c in state["cases"]}
    files_of = {r["id"]: r.get("file") for r in state["requirements"]}
    feedback = f"\nFEEDBACK:\n{state['feedback']}" if state.get("feedback") else ""
    install = bool(state.get("install_deps"))
    declared = emit.declared_dependencies(worktree)
    facts = await asyncio.to_thread(execution.environment_facts, worktree, declared)
    inventory = await asyncio.to_thread(emit.inventory, facts["python"])
    allowed = declared if install else frozenset()
    async_ok = bool(facts["pytest_asyncio"] or install)
    notes = execution.environment_notes(facts, install)
    rc.log(f"Environment: httpx {facts['httpx'] or 'not installed'}, pytest-asyncio {'yes' if facts['pytest_asyncio'] else 'no'}, {len(facts['rate_limiters'])} rate limiters" + ("" if inventory else ". The installed packages could not be read, so the third-party import check is skipped"), facts)

    async def generate_batch(cases: list[dict]) -> tuple[dict[str, GeneratedFile], str, list[str]]:
        batch_call = AgentCall(rc.run_id, rc.project_id, "test-automation-engineer")
        code = code_pack(rc.project_id, worktree, list(dict.fromkeys(files_of[c["requirement_id"]] for c in cases if files_of.get(c["requirement_id"]))) or None, limit=30_000)
        wanted = {c["id"] for c in cases}
        under_test = list(dict.fromkeys(files_of[c["requirement_id"]] for c in cases if files_of.get(c["requirement_id"])))
        request = (f"Generate executable tests under tests/agentic_qe/ for these cases, one file per case. Send a file for every case.\nCASES:\n{json.dumps(cases)}\nDETECTED RUNNERS: {a['test_runners']}\n"
                   f"Import only names you can see in this code. Name each test function with its case id, for example test_TC_APP_001_empty_input.\n"
                   f"tests/agentic_qe/fixtures.json holds the shared datasets under \"datasets\" and each case's own data under \"cases\"; load it with json and pathlib relative to __file__.\n"
                   f"{notes}\n{emit.signatures(worktree, under_test)}{feedback}\n\nCODE:\n{code}")
        key = part_key("generate", sorted(wanted), state.get("feedback", ""))
        if saved := rc.kept(key):
            rc.log(f"Kept result reused for {len(wanted)} cases")
            return {p: GeneratedFile(**f) for p, f in saved["accepted"].items()}, saved["framework"], saved["errors"]
        accepted: dict[str, GeneratedFile] = {}
        errors: list[str] = []
        framework = ""
        for _ in range(3):
            try:
                suite = await batch_call.typed(request, GeneratedSuite)
            except AllowanceError:
                raise
            except AqeError as exc:
                if not accepted:
                    raise
                errors = [str(exc)[:300]]
                break
            framework = suite.framework
            errors = []
            for item in suite.files:
                problems = _generated_file_problems(item, known, worktree, async_ok)
                if problems:
                    errors.extend(problems)
                    accepted.pop(item.path, None)
                else:
                    accepted[item.path] = item
            covered = {cid for f in accepted.values() for cid in f.case_ids}
            missing = sorted(wanted - covered)
            if not errors and not missing:
                break
            request = "These generated test files were refused. Send corrected versions of only these files, with the same paths and case ids.\nPROBLEMS:\n" + "\n".join(errors[:40]) + (f"\nThese cases have no test yet, so send one file for each: {missing}" if missing else "") + f"\n\nCODE:\n{code}"
        rc.keep(key, {"accepted": {p: f.model_dump() for p, f in accepted.items()}, "framework": framework, "errors": errors})
        return accepted, framework, errors

    batches = [state["cases"][i : i + GENERATE_BATCH] for i in range(0, len(state["cases"]), GENERATE_BATCH)]
    outcomes = await asyncio.gather(*(generate_batch(batch) for batch in batches), return_exceptions=True)
    partial = settle(rc, [[c["id"] for c in b] for b in batches], outcomes, "Generate")
    outcomes = [o for o in outcomes if not isinstance(o, BaseException)]
    accepted = {path: item for found, _, _ in outcomes for path, item in found.items()}
    errors = [problem for _, _, found in outcomes for problem in found]
    if lost := [c for c in state["cases"] if c["id"] not in {cid for f in accepted.values() for cid in f.case_ids}]:
        rc.log(f"{len(lost)} cases have no test yet. Asking once more in smaller batches", kind="warning")
        again = await asyncio.gather(*(generate_batch(lost[i : i + GENERATE_BATCH // 2]) for i in range(0, len(lost), GENERATE_BATCH // 2)), return_exceptions=True)
        for found in again:
            if isinstance(found, AllowanceError):
                raise found
            if isinstance(found, BaseException):
                errors.append(str(found)[:300])
            else:
                outcomes.append(found)
                accepted |= found[0]
                errors += found[2]
    if not accepted:
        raise ModelSchemaError(f"Generated tests failed checks: {errors}", action="Retry the stage. Each problem above names the file and the rule it broke.")
    suite = GeneratedSuite(framework=next((framework for _, framework, _ in outcomes if framework), ""), files=list(accepted.values()))
    missing = sorted(known - {cid for f in suite.files for cid in f.case_ids})
    if missing:
        rc.log(f"{len(missing)} of {len(known)} cases have no test: {missing[:30]}", {"problems": errors[:20]}, "warning")
    case_of = {c["id"]: c for c in state["cases"]}
    static_findings = lambda item: emit.check(worktree, item.path, item.content, inventory, allowed)
    unresolved: list[dict] = []
    flagged = {i: found for i, item in enumerate(suite.files) if (found := static_findings(item))}
    if flagged:
        rc.log(f"{len(flagged)} generated tests failed the static checks. Each goes back alone, once", {"findings": {suite.files[i].path: found[:5] for i, found in flagged.items()}}, "warning")

    async def send_back(i: int, found: list[str]) -> GeneratedFile:
        old = suite.files[i]
        case = case_of.get(old.case_ids[0], {})
        under_test = files_of.get(case.get("requirement_id"))
        again = AgentCall(rc.run_id, rc.project_id, "test-automation-engineer")
        result = await again.typed(f"Rewrite only this generated test file and fix every problem the static checks found. Send a suite with exactly this one file, with the same path and case id.\nCASE:\n{json.dumps(case)}\n"
                                   f"CURRENT FILE {old.path}:\n{old.content}\nPROBLEMS, each with the real signature:\n" + "\n".join(found[:20]) + f"\n{notes}\n{emit.signatures(worktree, [under_test] if under_test else [])}", GeneratedSuite, attempts=2)
        new = next((f for f in result.files if f.path == old.path and f.case_ids == old.case_ids), None)
        if new is None:
            raise ValueError("The agent did not send back the same file for the same case")
        if problems := _generated_file_problems(new, known, worktree, async_ok):
            raise ValueError("; ".join(problems[:3]))
        return new

    outcomes = await asyncio.gather(*(send_back(i, found) for i, found in flagged.items()), return_exceptions=True)
    for (i, found), outcome in zip(flagged.items(), outcomes):
        if isinstance(outcome, BaseException) and not isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, AllowanceError):
            raise outcome
        remaining = found
        if isinstance(outcome, Exception):
            rc.log(f"{suite.files[i].path} could not be sent back: {str(outcome)[:200]}", kind="warning")
        elif len(after := static_findings(outcome)) <= len(found):
            suite.files[i], remaining = outcome, after
        if remaining:
            unresolved.append({"path": suite.files[i].path, "case_id": suite.files[i].case_ids[0], "findings": remaining[:10]})
    if unresolved:
        rc.log(f"{len(unresolved)} tests still fail the static checks after one round. They stay, marked", {"unresolved": unresolved}, "warning")
    valid_suite_files = []
    for f in suite.files:
        f.content = _clean_code(f.content)
        syn = execution.syntax_error(f.path, f.content)
        if syn:
            cid = f.case_ids[0] if f.case_ids else "unknown"
            norm_cid = re.sub(r"[^a-zA-Z0-9_]+", "_", cid)
            f.content = (
                f"# CASE_ID: {cid}\n"
                f"# Quarantined due to syntax error: {syn}\n"
                f"import pytest\n\n"
                f"@pytest.mark.skip(reason=\"Quarantined test: {syn}\")\n"
                f"def test_quarantined_{norm_cid}():\n"
                f"    pass\n"
            )
            unresolved.append({"path": f.path, "case_id": cid, "findings": [f"Syntax error: {syn}"]})
        valid_suite_files.append(f)
    suite.files = valid_suite_files

    edits = [Edit(path=f.path, action="create", content=f.content) for f in suite.files]
    if state.get("fixtures"):
        edits.append(Edit(path="tests/agentic_qe/fixtures.json", action="create", content=json.dumps(state["fixtures"], indent=2, ensure_ascii=False)))
    errors = apply_edits(worktree, edits)
    if errors:
        rc.log(f"{len(errors)} generated test edits had issues: {errors[:5]}", kind="warning")
        for err in errors:
            bad_path = err.split(":")[0].strip()
            for f in suite.files:
                if f.path == bad_path:
                    cid = f.case_ids[0] if f.case_ids else "unknown"
                    norm_cid = re.sub(r"[^a-zA-Z0-9_]+", "_", cid)
                    safe_stub = (
                        f"# CASE_ID: {cid}\n"
                        f"# Quarantined due to refusal: {err}\n"
                        f"import pytest\n\n"
                        f"@pytest.mark.skip(reason=\"Quarantined refusal: {err[:80]}\")\n"
                        f"def test_quarantined_{norm_cid}():\n"
                        f"    pass\n"
                    )
                    apply_edits(worktree, [Edit(path=f.path, action="create", content=safe_stub)])
                    unresolved.append({"path": f.path, "case_id": cid, "findings": [err]})
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
    return {"worktree": state["worktree"], "branch": state["branch"], "tests": tests, "framework": suite.framework, "test_doc": doc["id"], "heal_attempts": state.get("heal_attempts", 0), "tests_review": tests_review, "tests_missing": missing, "emit_unresolved": unresolved, "env_facts": facts, "partial": partial}

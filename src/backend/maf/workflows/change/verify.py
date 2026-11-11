"""Change workflow, verify stage: tests and the independent review run together, and a failure goes back for a repair."""
from __future__ import annotations

import asyncio
from pathlib import Path

from backend.maf.engine import RunContext
from backend.maf.workflows.change.prepare import _rescan
from backend.maf.workflows.change.scope import spec_gaps
from backend.maf.workflows.shared import review_artifact
from backend.qe import execution
from backend.repos import git, scan


def cap_for_failed_tests(confidence: dict, verdict: str) -> dict:
    """The review runs before the tests finish, so code keeps a high score from sitting beside a failing verdict."""
    if verdict != "FAIL" or confidence["score"] is None or confidence["score"] <= 60:
        return confidence
    return {**confidence, "score": 60, "verdict": "REVISE",  # fabrication-ok: documented cap beside a failing test verdict
            "model_score": confidence["score"], "issues": ["Tests fail with this change", *confidence.get("issues", [])]}


async def change_verify(rc: RunContext, state: dict) -> dict:
    worktree = Path(state["worktree"])
    analysis = await asyncio.to_thread(_rescan, worktree)
    results = []

    async def run_tests() -> None:
        for runner in execution.choose_runners(analysis):
            result = await asyncio.to_thread(execution.run_suite, runner, worktree, state.get("test_target") or ("." if runner == "pytest" else ""), worktree.parent / f"{rc.run_id}-results")
            results.append(result)
            rc.log(f"{runner}: {result['passed']} passed, {result['failed']} failed", {k: result[k] for k in ("exit_code", "reason")}, "test")

    # the confidence review runs beside the tests, so a person sees both before approving
    _, confidence = await asyncio.gather(run_tests(), review_artifact(rc, "code change", git.diff(worktree), state["spec"]))
    outcome = execution.compare_to_baseline(results, state.get("baseline", {}))
    rc.log(f"Verdict {outcome['verdict']}. {outcome['reason']}".strip(), {"new_failures": [c["name"] for c in outcome["new_failures"]][:20]}, "test")
    suites = [{k: r.get(k) for k in ("runner", "verdict", "passed", "failed", "skipped", "exit_code", "reason")} for r in results]
    gaps = spec_gaps(worktree, state)
    if gaps and outcome["verdict"] in {"PASS", "NO NEW FAILURES"}:
        outcome |= {"verdict": "INCOMPLETE", "reason": "; ".join(gaps)}
    update = {"verification": {"confidence": cap_for_failed_tests(confidence, outcome["verdict"]), "changed_assertions": _changed_assertions(worktree), "verdict": outcome["verdict"], "reason": outcome["reason"], "new_failures": len(outcome["new_failures"]), "existing_failures": outcome["existing_failures"], "suites": suites}, "failure": ""}
    # retry only what the change broke; environment failures are not the agent's to fix
    # failing test files go first in paths, because code_pack drops whatever is over its limit
    if outcome["verdict"] == "FAIL" and state["attempt"] < (2 if len(state.get("finding_files", [])) > 1 else 3):
        update |= {"failure": "\n".join(f"{c['classname']}::{c['name']}: {c['message'][:800]}" for c in outcome["new_failures"][:10]), "_next": "implement", "paths": list(dict.fromkeys([*_failing_files(worktree, outcome["new_failures"]), *state["paths"]]))}
    return update


def _changed_assertions(worktree: Path) -> list[str]:
    """Existing assertions this change removed or altered. Editing a test can hide a bug, so the reviewer must see these."""
    return [line[1:].strip() for line in git.diff(worktree).splitlines() if line.startswith("-") and not line.startswith("---") and execution.ASSERTION.search(line)][:20]


def _failing_files(worktree: Path, cases: list[dict]) -> list[str]:
    """Test files behind failures, so a retry can read them. ponytail: pytest class names only; other runners keep the files already chosen."""
    return [f for f in scan.tree(worktree) if f.endswith(".py") and any(c["classname"].startswith(f[:-3].replace("/", ".")) for c in cases)][:4]

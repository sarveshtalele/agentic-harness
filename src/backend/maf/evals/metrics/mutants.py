"""Mutation score: plant each bug in a temporary copy of a repository and see whether the generated tests notice."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from backend.core.security import safe_path
from backend.maf.evals.metrics.ratios import ratio
from backend.qe import execution

SKIP_COPY = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".venv", ".pytest_cache")


def mutation_score(repo: Path, tests: dict[str, str], mutants: list[dict], *, runner: str = "pytest", target: str = "tests", timeout: int = 120) -> dict:
    """Plant each bug in a temporary copy of the repository and run the generated tests with `execution.run_suite`.

    A mutant is killed when a test fails. Zero executed tests, or tests that already fail on the unchanged code, give INCONCLUSIVE and no score.
    A mutant whose text is not found exactly once is "not applied" and is left out of the score.
    """
    with tempfile.TemporaryDirectory(prefix="atlas-mutation-") as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(repo, work, ignore=SKIP_COPY)
        for name, body in tests.items():
            path = safe_path(work, name, for_write=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        results = Path(tmp) / "results"
        base = execution.run_suite(runner, work, target, results, timeout)
        if base["verdict"] != "PASS":
            reason = "No test was executed" if base["verdict"] == "INCONCLUSIVE" else "The tests already fail on the unchanged code, so a failure would prove nothing"
            return {"verdict": "INCONCLUSIVE", "score": None, "reason": reason, "baseline": base["verdict"], "executed": base["passed"] + base["failed"], "killed": 0, "survived": 0, "not_applied": 0, "mutants": []}
        report, killed, survived, skipped = [], 0, 0, 0
        for mutant in mutants:
            path = safe_path(work, mutant["file"])
            original = path.read_text(encoding="utf-8") if path.is_file() else ""
            if original.count(mutant["find"]) != 1:
                skipped += 1
                report.append({"id": mutant["id"], "status": "not_applied"})
                continue
            path.write_text(original.replace(mutant["find"], mutant["replace"]), encoding="utf-8")
            try:
                done = execution.run_suite(runner, work, target, results, timeout)
            finally:
                path.write_text(original, encoding="utf-8")
            status = "killed" if done["failed"] else "survived"
            killed, survived = killed + (status == "killed"), survived + (status == "survived")
            report.append({"id": mutant["id"], "status": status, "failed_tests": [c["name"] for c in done["cases"] if c["status"] == "failed"][:5]})
        score = ratio(killed, killed + survived)
        return {"verdict": "INCONCLUSIVE" if score is None else "MEASURED", "score": score, "reason": "No mutant could be applied" if score is None else "", "baseline": "PASS",
                "executed": base["passed"], "killed": killed, "survived": survived, "not_applied": skipped, "mutants": report}

"""The discovery eval's scoring is deterministic: same trace, same numbers (docs/PHASE2_PLAN.md step 1)."""
import json
from pathlib import Path

from backend.maf.evals.discovery import aggregate, score

TASKS = json.loads((Path(__file__).resolve().parent.parent / "evals" / "harness" / "discovery.json").read_text(encoding="utf-8"))


def test_the_task_file_has_twenty_tasks_with_checks_and_a_fixture_repository():
    ids = [t["id"] for t in TASKS["tasks"]]
    assert len(ids) == 20 and len(set(ids)) == 20
    assert all(t["prompt"] and t["check"] for t in TASKS["tasks"])
    repo = TASKS["repo"]
    assert ".claude/skills/release-notes/SKILL.md" in repo and ".agents/skills/changelog-lint/scripts/lint.ts" in repo
    assert repo["app/pricing.py"].count("\n") == 14  # what count_lines.sh prints, the run-bash check


def test_a_good_run_scores_selected_first_try_and_passed(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "pricing.py").write_text("return total * 0.5\n", encoding="utf-8")
    task = {"id": "fix-bug", "tools": ["file_access_replace"], "check": {"file_contains": {"app/pricing.py": "0.5"}, "file_lacks": {"app/pricing.py": "0.6"}}}
    calls = [{"name": "file_access_ls", "args": "{}", "result": "app"},
             {"name": "file_access_replace", "args": "{}", "result": "ok"}]
    s = score(task, calls, "done", tmp_path)
    assert s["selected"] and s["first_ok"] and s["passed"] and s["invalid_args"] == 0


def test_invented_names_bad_arguments_and_refusals_are_counted(tmp_path):
    task = {"id": "run-bash", "tools": ["bash"], "check": {"answer_any": ["14"]}}
    calls = [{"name": "shell_exec", "args": "{}", "result": 'Error: Requested function "shell_exec" not found.'},
             {"name": "run_shell", "args": "{}", "result": "Error [invalid_arguments]: {\"code\": \"invalid_arguments\"}"},
             {"name": "run_shell", "args": "{}", "result": "Refused: bash is not an allowed program"}]
    s = score(task, calls, "I could not run it", tmp_path)
    assert (s["invented"], s["invalid_args"], s["refused"]) == (1, 1, 1)
    assert not s["selected"] and not s["first_ok"] and not s["passed"]
    totals = aggregate([s])
    assert totals["pass_rate"] == 0 and totals["arg_validity"] == round(1 - 1 / 3, 3) and totals["invented_names"] == 1

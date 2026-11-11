"""Review targets, replies, discovery checks and test-file isolation."""

import pytest

from backend.core import doc_checks

from backend.qe import execution
from backend.repos import static_analysis


def test_review_targets_cover_all_source_files_but_not_tests(tmp_path):
    (tmp_path / "tests").mkdir()
    for name in ("a.py", "b.ts", "style.css", "README.md", "tests/test_a.py"):
        (tmp_path / name).write_text("x = 1\n")
    assert static_analysis.review_targets(tmp_path) == ["a.py", "b.ts"]


def test_large_files_keep_their_real_line_numbers_when_split():
    from backend.maf.workflows.bug_scan import PART_CHARS, file_parts

    text = "\n".join("x" * 50 for _ in range(1000))
    parts = file_parts("big.py", text)
    assert len(parts) > 1 and all(len(p) < PART_CHARS + 100 for p in parts)
    assert parts[1].splitlines()[1].split(":")[0] != "1" and parts[-1].splitlines()[-1].startswith("1000: ")


def test_bare_list_replies_fit_a_single_list_schema():
    from pydantic import BaseModel

    from backend.maf.runtime import _fit_schema, extract_json

    class Item(BaseModel):
        id: str

    class Items(BaseModel):
        items: list[Item]

    class Two(BaseModel):
        a: list[Item]
        b: str

    reply = 'Here you go:\n```json\n[{"id": "1"}, {"id": "2"}]\n```'
    assert len(Items.model_validate(_fit_schema(extract_json(reply), Items)).items) == 2
    with pytest.raises(ValueError):
        _fit_schema(extract_json(reply), Two)
    assert extract_json('See [FR-001] and [1, 2]. {"a": 1}') == {"a": 1}


def test_test_runs_leave_no_bytecode_in_the_worktree(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_calc.py").write_text("from calc import add\n\n\ndef test_add():\n    assert add(1, 1) == 2\n")
    result = execution.run_suite("pytest", tmp_path, ".", tmp_path.parent / "results")
    assert result["passed"] == 1 and not list(tmp_path.rglob("__pycache__"))


def test_ruff_skips_test_files_but_not_folders_named_like_tests(tmp_path):
    inner = tmp_path / "test_project"
    inner.mkdir()
    bad = "import subprocess\n\n\ndef f(x):\n    subprocess.call(x, shell=True)\n"
    (inner / "app.py").write_text(bad)
    (inner / "test_app.py").write_text(bad)
    files = {f["file"] for f in static_analysis.run_ruff(inner)}
    assert files == {"app.py"}


def test_malformed_reply_is_reported_and_never_replaced_by_a_fragment():
    from backend.maf.runtime import extract_json

    broken = '{"cases": [{"id": "A", "x": 1}, {"id": "B", "x": '
    with pytest.raises(ValueError, match="not valid JSON"):
        extract_json(broken, ("cases",))
    assert extract_json('{"cases": [{"id": "A"}], "extra": oops', ("cases",)) == [{"id": "A"}], "a complete list inside a broken object is usable"
    assert extract_json('{"a": "line one\nline two"}'.replace("\\n", "\n"), ("a",))["a"].startswith("line one")
    assert extract_json(r'{"pattern": "\d+ items"}', ("pattern",))["pattern"] == r"\d+ items"


def test_discovery_checks_find_gaps_and_invented_paths():
    good = "\n".join(f"## {h}\ntext" for h in doc_checks.DISCOVERY_HEADINGS) + "\nSee `src/app.py:3` and `src/`, and `web/page.js`."
    tree = ["src/app.py", "web/page.js", "README.md"]
    assert doc_checks.discovery_issues(good, tree, ["src/app.py", "web/page.js"]) == []
    issues = " ".join(doc_checks.discovery_issues("## Purpose and Users\nSee `src/gone.py`.", tree, ["src/app.py", "web/page.js"]))
    assert "missing section: Risks" in issues and "src/gone.py" in issues and "web" in issues


def test_test_extras_install_and_async_needs_are_environment(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1"\n[project.optional-dependencies]\ndev = ["pytest-asyncio"]\ndocs = ["sphinx"]\n')
    assert execution._test_extras(tmp_path) == "[dev]"
    assert execution.classify_failure("Failed: async def functions are not natively supported.") == "ENVIRONMENT"


def test_discovery_check_reads_real_headings_and_ignores_module_names():
    text = "\n".join(f"## {h}: with a description" for h in doc_checks.DISCOVERY_HEADINGS) + "\n`src.server`, `127.0.0.1`, `ci.yml`, `app.py`, `made_up.py`."
    assert doc_checks.discovery_issues(text, [".github/workflows/ci.yml", "src/app.py"], []) == ["cited paths that do not exist: ['made_up.py']"]


def test_discovery_accepts_a_path_the_repository_mentions_but_not_an_invented_one():
    text = "\n".join(f"## {h}" for h in doc_checks.DISCOVERY_HEADINGS) + "\nSee `web/out/` and `made/up/`."
    assert doc_checks.discovery_issues(text, ["src/app.py"], [], "Dockerfile: COPY web/out/ /site") == ["cited paths that do not exist: ['made/up/']"]


def test_failing_tests_cap_a_high_change_review():
    from backend.maf.workflows.change import cap_for_failed_tests
    review = {"score": 100, "verdict": "APPROVED", "issues": []}
    capped = cap_for_failed_tests(review, "FAIL")
    assert (capped["score"], capped["verdict"], capped["model_score"]) == (60, "REVISE", 100) and "Tests fail" in capped["issues"][0]
    assert cap_for_failed_tests(review, "PASS") == review
    not_run = {"score": None, "verdict": "NOT RUN", "issues": []}
    assert cap_for_failed_tests(not_run, "FAIL") == not_run


def test_one_test_file_that_cannot_import_does_not_stop_the_others(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_good.py").write_text("def test_runs():\n    assert 1 + 1 == 2\n")
    (tests / "test_bad.py").write_text("import module_that_does_not_exist\n\ndef test_never():\n    assert 1 + 1 == 2\n")
    result = execution.run_suite("pytest", tmp_path, "tests", tmp_path / "results")
    assert result["passed"] == 1 and result["failed"] == 1 and result["verdict"] == "FAIL"

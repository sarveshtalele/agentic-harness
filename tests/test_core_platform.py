"""Measures, baselines, layout, packaging, launchers and generated-test checks."""

import os

import subprocess

from pathlib import Path


from backend.qe import execution
from backend.repos import git


def test_invented_measures_are_caught_unless_proposed():
    from backend.core import doc_checks

    sources = "Links expire in 30 minutes."
    doc = "## Non-Functional Requirements\nResponses in 200 ms.\nUptime 99.9%.\nLinks expire in 30 minutes.\nHandle 100 users (proposed).\nFR-001 applies.\n"
    assert doc_checks.invented_measures(doc, sources) == ["200 ms", "99.9%"]
    result = doc_checks.apply({"score": 100, "verdict": "APPROVED", "issues": []}, doc, sources=sources)
    assert result["score"] <= 70 and any("200 ms" in i for i in result["issues"])
    assert doc_checks.invented_measures("Links expire in 30 minutes.", sources) == []


def test_tool_markup_is_not_shown_as_text():
    from backend.maf.runtime import _strip_tool_markup

    assert _strip_tool_markup("Done.\n<\uff5cDSML\uff5ctool_calls>\n<\uff5cDSML\uff5cinvoke name='x'>") == "Done."


def test_compare_to_baseline_verdicts():
    case = lambda n, s="failed", m="assert 1 == 2": {"classname": "t", "name": n, "status": s, "message": m}
    run = lambda *cases: [{"runner": "pytest", "passed": sum(c["status"] == "passed" for c in cases), "failed": sum(c["status"] == "failed" for c in cases), "cases": list(cases)}]
    assert execution.compare_to_baseline(run(case("a", "passed")), {})["verdict"] == "PASS"
    assert execution.compare_to_baseline(run(case("a")), {})["verdict"] == "FAIL"
    assert execution.compare_to_baseline(run(case("a")), {"pytest": ["t::a"]})["verdict"] == "NO NEW FAILURES"
    assert execution.compare_to_baseline(run(case("a", m="ModuleNotFoundError: x")), {})["verdict"] == "INCONCLUSIVE"
    assert execution.compare_to_baseline([], {})["verdict"] == "INCONCLUSIVE"


def test_model_calls_have_a_bounded_timeout():
    from backend.config import MODEL_RETRIES, MODEL_TIMEOUT
    from backend.maf import llm

    llm.update("https://models.example/v1", "m", "k" * 12)
    sdk = llm.client().client
    assert sdk.timeout == MODEL_TIMEOUT and sdk.max_retries == MODEL_RETRIES == 3  # bounded retries with the client's backoff


def test_each_agent_tool_and_workflow_lives_in_its_own_file():
    from backend.maf import tools, workflows  # noqa: F401
    from backend.maf.agents import POLICIES
    from backend.maf.engine import REGISTRY

    root = Path(__file__).resolve().parent.parent
    assert {p.stem for p in (root / "prompts").glob("*.md")} == set(POLICIES) == {p.stem for p in (root / "evals").glob("*.json")}
    assert next(iter(POLICIES)) == "project-copilot", "the chat offers the first agent by default"
    assert set(REGISTRY) == {"ba", "brainstorm", "bug_scan", "change", "qe"}
    assert all((root / "src/backend/maf/workflows" / f"{name}.py").is_file() or (root / "src/backend/maf/workflows" / name / "__init__.py").is_file() for name in REGISTRY)
    names = [t.name for t in tools.repo_tools("p", root) + tools.document_tools("p") + tools.chat_tools("p", "t", None)]
    assert len(names) == 12 and all((root / "src/backend/maf/tools" / f"{name}.py").is_file() for name in names)


def test_packages_exclude_secrets_and_tests():
    import importlib.util

    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("package_azure", root / "scripts/package_azure.py")
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    backend, frontend = package.backend_entries(), package.frontend_entries()
    for needed in ("startup.py", "requirements.txt", "src/backend/app.py", "prompts/project-copilot.md", "templates/brd.md", "evals/project-copilot.json"):
        assert needed in backend
    assert {"startup.js", "package.json", "package-lock.json", "next.config.ts"} <= set(frontend)
    for name in [*backend, *frontend]:
        assert not name.startswith(("tests/", "data/")) and "node_modules" not in name and ".next/" not in name and not name.endswith(".env")


def test_launchers_exist_and_call_the_same_command():
    root = Path(__file__).resolve().parent.parent
    assert "scripts\\dev.py up" in (root / "start-windows.bat").read_text() and b"\r\n" in (root / "start-windows.bat").read_bytes()
    assert "scripts/dev.py up" in (root / "start-mac.command").read_text() and b"\r\n" not in (root / "start-mac.command").read_bytes()


def test_dependency_date_ignores_commits_made_by_this_app(tmp_path):
    env = {**os.environ, "GIT_COMMITTER_DATE": "2024-01-02T00:00:00+00:00"}
    run = lambda *args, **kw: subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, **kw)
    run("init", "-q")
    (tmp_path / "a").write_text("1")
    run("add", "-A")
    run("-c", "user.name=Owner", "-c", "user.email=o@x", "commit", "-qm", "owner", env=env)
    (tmp_path / "b").write_text("2")
    run("add", "-A")
    run("-c", f"user.name={execution.GIT_AUTHOR}", "-c", "user.email=a@x", "commit", "-qm", "generated")
    assert execution._commit_date(tmp_path).startswith("2024-01-02")


def test_generated_tests_must_import_real_names_and_real_plugins(tmp_path):
    (tmp_path / "src" / "tools").mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("")
    (tmp_path / "src" / "tools" / "__init__.py").write_text("")
    (tmp_path / "src" / "tools" / "calc.py").write_text("from math import pi\nLIMIT = 3\n\n\ndef add(a, b):\n    return a + b\n")
    good = "from src.tools.calc import add, LIMIT, pi\nfrom src.tools import calc\nimport pytest\n\n\ndef test_a():\n    assert add(1, 1) == 2\n"
    assert execution.invalid_test_code(tmp_path, "t.py", good) == []
    assert "has no invented" in execution.invalid_test_code(tmp_path, "t.py", "from src.tools.calc import invented\n")[0]
    assert "does not exist" in execution.invalid_test_code(tmp_path, "t.py", "from src.tools.gone import x\n")[0]
    assert execution.invalid_test_code(tmp_path, "t.py", "from third_party import anything\n") == []
    assert "pytest-asyncio" in execution.invalid_test_code(tmp_path, "t.py", "import pytest\n\n\nasync def test_a():\n    assert 1\n")[0]
    (tmp_path / "requirements.txt").write_text("pytest-asyncio\n")
    assert execution.invalid_test_code(tmp_path, "t.py", "async def test_a():\n    assert 1\n") == []
    assert execution.invalid_test_code(tmp_path, "t.js", "import x from 'y'") == []
    assert execution.classify_failure("ImportError: cannot import name 'x' from 'src.a'") == "FIXTURE_DRIFT"
    assert execution.classify_failure("ModuleNotFoundError: No module named 'requests'") == "ENVIRONMENT"


def test_shallow_clones_are_detected_and_clones_are_full(tmp_path, monkeypatch):
    origin = tmp_path / "origin"
    origin.mkdir()
    run = lambda *args, cwd=origin: subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@x", *args], cwd=cwd, check=True, capture_output=True)
    run("init", "-q")
    for n in range(3):
        (origin / "a").write_text(str(n))
        run("add", "-A")
        run("commit", "-qm", str(n))
    shallow = tmp_path / "shallow"
    run("clone", "-q", "--depth", "1", origin.as_uri(), str(shallow), cwd=tmp_path)
    assert git.is_shallow(shallow) and not git.is_shallow(origin)
    calls = []
    monkeypatch.setattr(git, "run", lambda args, **kw: calls.append(args))
    git.clone("https://github.com/o/r", tmp_path / "x")
    assert "--depth" not in calls[0]

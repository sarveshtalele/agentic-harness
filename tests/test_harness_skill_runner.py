"""The harness runs a Studio skill's scripts/run.py (found live 2026-11-11: MAF answered "requires a runner")."""
import asyncio
from types import SimpleNamespace

from backend import config
from backend.maf.harness_kit.skill_runner import run_skill_script


def _skill(tmp_path):
    folder = tmp_path / "computing-invoice-totals"
    (folder / "scripts").mkdir(parents=True)
    (folder / "scripts" / "run.py").write_text("import json, sys\ndata = json.load(sys.stdin)\nprint(json.dumps({'total': sum(l['q'] * l['p'] for l in data['lines'])}))\n")
    (folder / "scripts" / "other.py").write_text("print('not me')\n")
    return SimpleNamespace(path=str(folder)), folder


def test_run_py_gets_the_input_on_stdin_and_its_output_comes_back(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE", "desktop")
    skill, folder = _skill(tmp_path)
    entry = SimpleNamespace(full_path=str(folder / "scripts" / "run.py"))
    assert asyncio.run(run_skill_script(skill, entry, {"input": '{"lines": [{"q": 2, "p": 10}, {"q": 1, "p": 5.5}]}'})).strip() == '{"total": 25.5}'
    failed = asyncio.run(run_skill_script(skill, entry, {"input": "not json"}))
    assert "failed (exit code 1)" in failed and "JSONDecodeError" in failed  # a crash is reported with its error, never hidden


def test_other_scripts_and_the_web_profile_are_refused(tmp_path, monkeypatch):
    skill, folder = _skill(tmp_path)
    monkeypatch.setattr(config, "PROFILE", "desktop")
    assert "Only scripts/run.py runs here" in asyncio.run(run_skill_script(skill, SimpleNamespace(full_path=str(folder / "scripts" / "other.py")), None))
    monkeypatch.setattr(config, "PROFILE", "web")
    assert "off on the shared web server" in asyncio.run(run_skill_script(skill, SimpleNamespace(full_path=str(folder / "scripts" / "run.py")), {"input": "{}"}))


def test_sandbox_commands_find_chromium_and_windows_basics(tmp_path, monkeypatch):
    import os

    from backend.repos.sandbox.env import clean_sandbox_env

    browsers = tmp_path / "ms-playwright"
    browsers.mkdir()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
    monkeypatch.setenv("PATHEXT", ".COM;.EXE;.CMD")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-pass")
    env = clean_sandbox_env({"HOME": str(tmp_path / "harness-home")})  # the harness gives commands another HOME
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(browsers) and env["HOME"] == str(tmp_path / "harness-home")
    assert env["PATHEXT"] == ".COM;.EXE;.CMD" and "OPENAI_API_KEY" not in env
    from backend.config import ROOT

    if (ROOT / "node_modules").is_dir():  # the project's own .bin comes first, joined with the OS separator (";" on Windows)
        assert env["PATH"].split(os.pathsep)[0] == str(ROOT / "node_modules" / ".bin")

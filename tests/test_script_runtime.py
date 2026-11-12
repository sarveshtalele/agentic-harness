"""Skill scripts in every common language, with health checks and flags (docs/PHASE2_PLAN.md section 7.3 and 7.4)."""
import asyncio
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.core import script_health
from backend.core import script_runtime as rt
from backend.maf.harness_kit import skill_runner

NODE = rt.node_version()
HAS_TS = bool(NODE and (NODE >= (22, 6) or NODE[0] >= 23))


def skill(root: Path, name: str, md_body: str, files: dict) -> Path:
    folder = root / name
    (folder / "scripts").mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test skill\n---\n{md_body}\n", encoding="utf-8")
    for rel, text in files.items():
        (folder / rel).write_text(text, encoding="utf-8")
    return folder


def test_language_detection_order(tmp_path):
    folder = skill(tmp_path, "langs", "Run `node ${CLAUDE_SKILL_DIR}/scripts/report.ts` and `python3 scripts/tool`.",
                   {"scripts/report.ts": "console.log(1)\n", "scripts/tool": "print(1)\n", "scripts/run_me": "#!/usr/bin/env bash\necho hi\n",
                    "scripts/x.ps1": "Write-Output 1\n", "scripts/y.xyz": "?\n"})
    md = (folder / "SKILL.md").read_text()
    assert rt.declared(md, "scripts/report.ts") == "typescript"  # node runs it; the extension says TypeScript
    assert rt.declared(md, "scripts/tool") == "python"  # the run command SKILL.md shows
    assert rt.declared("metadata:\n  runtime: pwsh\n", "scripts/anything") == "powershell"
    assert rt.shebang(folder / "scripts" / "run_me") == "bash"
    assert rt.plan(folder / "scripts" / "y.xyz", folder, md).argv is None


def test_python_uses_the_skills_own_virtual_environment(tmp_path):
    folder = skill(tmp_path, "venv-skill", "", {"scripts/a.py": "print(1)\n"})
    python = folder / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    assert rt.plan(folder / "scripts" / "a.py", folder).argv[0] == str(python)


def test_health_flags_what_cannot_run_and_explains_why(tmp_path):
    bad = skill(tmp_path, "bad", "", {"scripts/syntax.py": "def (:\n", "scripts/missing.py": "import not_a_real_module_xyz\n",
                                      "scripts/odd.xyz": "#!/usr/bin/env not-an-interpreter-xyz\n?\n"})
    static = script_health.check_skill(bad, refresh=True)
    by = {r["script"]: r for r in static["scripts"]}
    assert static["verdict"] == "flagged"
    assert by["scripts/syntax.py"]["verdict"] == "flagged" and "SyntaxError" in by["scripts/syntax.py"]["reason"]
    assert by["scripts/missing.py"]["verdict"] == "ok"  # a static check executes nothing, so it cannot see imports
    assert by["scripts/odd.xyz"]["verdict"] == "flagged" and "not-an-interpreter-xyz" in by["scripts/odd.xyz"]["reason"]
    smoked = {r["script"]: r for r in script_health.check_skill(bad, refresh=True, smoke=True)["scripts"]}
    assert smoked["scripts/missing.py"]["verdict"] == "flagged" and "not_a_real_module_xyz" in smoked["scripts/missing.py"]["reason"]


@pytest.mark.skipif(not HAS_TS, reason="Node 22.6+ is needed to run TypeScript")
def test_a_typescript_script_runs_with_arguments_through_the_harness_runner(tmp_path, monkeypatch):
    folder = skill(tmp_path, "ts-skill", "Run `node ${CLAUDE_SKILL_DIR}/scripts/sum.ts 2 3`.",
                   {"scripts/sum.ts": "const nums: number[] = process.argv.slice(2).map(Number);\nconsole.log(`sum ${nums.reduce((a, b) => a + b, 0)}`);\n"})
    monkeypatch.setattr(skill_runner.testing, "check_profile", lambda: None)
    run = skill_runner.runner(None)
    out = asyncio.run(run(SimpleNamespace(path=str(folder), name="ts-skill"), SimpleNamespace(full_path=str(folder / "scripts" / "sum.ts")), ["2", "3"]))
    assert "sum 5" in out and "typescript script scripts/sum.ts: exit code 0" in out


def test_a_flagged_script_is_refused_and_three_failures_flag_a_skill(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_runner.testing, "check_profile", lambda: None)
    run = skill_runner.runner(None)
    broken = skill(tmp_path, "broken", "", {"scripts/b.py": "def (:\n"})
    out = asyncio.run(run(SimpleNamespace(path=str(broken), name="broken"), SimpleNamespace(full_path=str(broken / "scripts" / "b.py")), []))
    assert out.startswith("Refused: the skill broken is flagged") and "SyntaxError" in out
    failing = skill(tmp_path, "failing", "", {"scripts/f.py": "import sys\nsys.exit(0 if '--help' in sys.argv else 3)\n"})
    for _ in range(skill_runner.FAILS_TO_FLAG):
        out = asyncio.run(run(SimpleNamespace(path=str(failing), name="failing"), SimpleNamespace(full_path=str(failing / "scripts" / "f.py")), []))
        assert "exit code 3" in out
    out = asyncio.run(run(SimpleNamespace(path=str(failing), name="failing"), SimpleNamespace(full_path=str(failing / "scripts" / "f.py")), []))
    assert "failed 3 runs in a row" in out and out.startswith("Refused")


@pytest.mark.skipif(not shutil.which("pwsh") and os.name != "nt", reason="no PowerShell on this machine")
def test_a_powershell_script_runs(tmp_path, monkeypatch):
    folder = skill(tmp_path, "ps-skill", "", {"scripts/hello.ps1": "param([string]$Name = 'x')\nWrite-Output \"hello $Name\"\n"})
    monkeypatch.setattr(skill_runner.testing, "check_profile", lambda: None)
    out = asyncio.run(skill_runner.runner(None)(SimpleNamespace(path=str(folder), name="ps-skill"),
                                                SimpleNamespace(full_path=str(folder / "scripts" / "hello.ps1")), ["-Name", "shop"]))
    assert "hello shop" in out


def test_the_skills_page_shows_each_skills_health():
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        listed = client.get("/api/skills").json()["skills"]
        assert listed and all(s["health"]["verdict"] in ("ok", "warning", "flagged") for s in listed)
        with_scripts = next((s for s in listed if s["health"]["reason"] != "no scripts"), None)
        if with_scripts:
            again = client.post(f"/api/skills/{with_scripts['name']}/health")
            assert again.status_code == 200 and again.json()["verdict"] in ("ok", "warning", "flagged")

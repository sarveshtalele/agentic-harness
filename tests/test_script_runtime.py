"""Skill scripts in every common language, with health checks and flags (docs/PHASE2_PLAN.md section 7.3 and 7.4)."""
import asyncio
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.core import script_health
from backend.core import script_runtime as rt

NODE = rt.node_version()
HAS_TS = bool(NODE and (NODE >= (22, 6) or NODE[0] >= 23))


def skill(root: Path, name: str, md_body: str, files: dict) -> Path:
    folder = root / name
    (folder / "scripts").mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test skill\n---\n{md_body}\n", encoding="utf-8")
    for rel, text in files.items():
        (folder / rel).write_text(text, encoding="utf-8")
    return folder


def real(folder, script: str):
    """MAF's own FileSkill and FileSkillScript for a folder: the runner must work with what MAF really hands it."""
    from agent_framework import FileSkillsSource

    skill = next(s for s in asyncio.run(FileSkillsSource([str(folder.parent)], script_runner=lambda *a: None,
                                                                                   script_extensions=rt.SCRIPT_EXTENSIONS).get_skills(None))
                 if Path(s.path).name == folder.name)
    found = skill.get_script(script)
    return skill, asyncio.run(found) if asyncio.iscoroutine(found) else found


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


def test_the_skills_page_shows_each_skills_health():
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        listed = client.get("/api/skills").json()["skills"]
        assert listed and all(s["health"]["verdict"] in ("ok", "warning", "flagged") for s in listed)
        with_scripts = next((s for s in listed if s["health"]["reason"] != "no scripts"), None)
        if with_scripts:
            again = client.post(f"/api/skills/{with_scripts['name']}/health")
            assert again.status_code == 200 and again.json()["verdict"] in ("ok", "warning", "flagged")

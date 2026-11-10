"""Each Azure backend package, extracted as App Service would, must import the app from the package and find its
prompts, skills, templates and evals. The Kudu packages ship a top-level backend/ copy that `python -m uvicorn` imports
first from wwwroot; before the fix, config.ROOT then pointed one level above wwwroot and no agent had a prompt.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import azure_convert_and_deploy, package_azure, package_azure_kudu

PACKAGERS = {
    "package_azure_kudu": package_azure_kudu.gather_backend_entries,
    "azure_convert_and_deploy": azure_convert_and_deploy.gather_backend_files,
    "package_azure": package_azure.backend_entries,
}
PROBE = (
    "import json, backend, backend.config as c; "
    "print(json.dumps({'module': backend.__file__, 'root': str(c.ROOT), 'prompts': str(c.PROMPTS_DIR), "
    "'skills': str(c.SKILLS_DIR), 'templates': str(c.TEMPLATES_DIR)}))"
)


@pytest.mark.parametrize("name", sorted(PACKAGERS))
def test_extracted_backend_package_finds_its_assets(name, tmp_path):
    wwwroot = tmp_path / "wwwroot"
    for rel, source in PACKAGERS[name]().items():
        target = wwwroot / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(source).read_bytes())
    env = {**os.environ, "PYTHONPATH": f"{wwwroot / 'src'}{os.pathsep}{wwwroot}", "ATLAS_DATA_DIR": str(tmp_path / "data")}
    env.pop("ATLAS_SKILLS_DIR", None)
    # cwd first on sys.path, as `python -m uvicorn` run from wwwroot does on App Service
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=wwwroot, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    found = json.loads(out.stdout.strip().splitlines()[-1])
    real = os.path.realpath(wwwroot)
    assert os.path.realpath(found["module"]).startswith(real), f"imported backend from outside the package: {found['module']}"
    assert os.path.realpath(found["root"]) == real, found
    for key in ("prompts", "skills", "templates"):
        assert Path(found[key]).is_dir(), f"{name}: {key} folder missing in the package at {found[key]}"
    assert (Path(found["prompts"]) / "harness.md").is_file() and (wwwroot / "evals" / "harness.json").is_file()


def test_every_azure_setup_script_sets_what_the_backend_needs():
    """Without these the deployed backend refuses every request (host guard), every write (origin guard), every
    sign-in (no admin), or locks SQLite on the /home share (WAL)."""
    root = Path(__file__).resolve().parents[1]
    scripts = {"sh": (root / "deploy/azure/setup_azure_infrastructure.sh").read_text(encoding="utf-8"),
               "ps1": (root / "deploy/azure/setup_azure_infrastructure.ps1").read_text(encoding="utf-8"),
               "generated": azure_convert_and_deploy.generate_setup_script()}
    for name, text in scripts.items():
        for needed in ("ATLAS_ALLOWED_HOSTS=", "ATLAS_ALLOWED_ORIGINS=", "ATLAS_ADMIN_USERNAME", "ATLAS_ADMIN_PASSWORD", 'ATLAS_SQLITE_JOURNAL="DELETE"'):
            assert needed in text, f"{name} setup script lacks {needed}"
        assert 'ATLAS_SQLITE_JOURNAL="WAL"' not in text, name


def test_frontend_startup_copies_standalone_with_real_files():
    """Turbopack links external packages (pino, shiki) as symlinks into the temporary build folder, which startup.js
    deletes; copying the links verbatim broke /api/copilotkit on the packaged app ("Cannot find module 'pino-<hash>'")."""
    text = (Path(__file__).resolve().parents[1] / "deploy/azure/frontend_startup.js").read_text(encoding="utf-8")
    assert 'materializeExternals(fs.realpathSync(path.join(work, ".next", "standalone")), output);' in text
    assert "fs.rmSync(link, { force: true });" in text and "fs.cpSync(real, link" in text

"""Build the desktop app: UI standalone, backend with PyInstaller, then installers with electron-builder.

    python scripts/desktop_build.py            # everything for this OS
    python scripts/desktop_build.py --ui        # only the UI (enough for the dev-mode app)
    python scripts/desktop_build.py --backend   # only the PyInstaller backend
    python scripts/desktop_build.py --package   # only electron-builder (needs the two above)
Unsigned unless signing variables exist (CSC_LINK on macOS and Windows).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "desktop"
BUILD = DESKTOP / "build"
FRONTEND = ROOT / "src" / "frontend"
API_PORT = os.environ.get("AQE_DESKTOP_API_PORT", "18765")
NPM = shutil.which("npm") or "npm"
NPX = shutil.which("npx") or "npx"
DATA = ["prompts", "templates", "skills", "evals", "plugins"]


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, check=True)


def materialize_externals(standalone: Path, out: Path) -> None:
    """Turbopack links external packages as symlinks into the build folder; replace each with a real copy (see deploy/azure/frontend_startup.js)."""
    for d in (out / ".next" / "node_modules", out / "src" / "frontend" / ".next" / "node_modules"):
        if not d.is_dir():
            continue
        for link in [p for p in d.iterdir() if p.is_symlink()]:
            target = (d / os.readlink(link)).resolve()
            real = out / target.relative_to(standalone) if standalone in target.parents else target
            link.unlink()
            shutil.copytree(real, link, symlinks=False)


def build_ui() -> None:
    env = {"ATLAS_STANDALONE": "1", "ATLAS_BACKEND_URL": f"http://127.0.0.1:{API_PORT}", "NEXT_TELEMETRY_DISABLED": "1"}
    run([NPM, "run", "build"], FRONTEND, env)
    standalone = (FRONTEND / ".next" / "standalone").resolve()
    out = BUILD / "ui"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(standalone, out, symlinks=True)
    materialize_externals(standalone, out)
    nested = out / "src" / "frontend"
    for base in ([out, nested] if nested.is_dir() else [out]):
        (base / ".next").mkdir(parents=True, exist_ok=True)
        shutil.copytree(FRONTEND / ".next" / "static", base / ".next" / "static", dirs_exist_ok=True)
        if (FRONTEND / "public").is_dir():
            shutil.copytree(FRONTEND / "public", base / "public", dirs_exist_ok=True)
    print(f"UI built: {out}")


def build_backend() -> None:
    work = BUILD / "pyinstaller"
    sep = os.pathsep
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--name", "atlas-backend", "--distpath", str(BUILD / "backend-dist"),
           "--workpath", str(work), "--specpath", str(work), "--paths", str(ROOT / "src"), "--hidden-import", "backend.app"]
    for name in DATA:
        if (ROOT / name).is_dir():
            cmd += ["--add-data", f"{ROOT / name}{sep}{name}"]
    cmd += ["--add-data", f"{ROOT / 'src' / 'backend' / 'migrations'}{sep}backend/migrations"]
    for pkg in ("agent_framework", "agent_framework_openai", "agent_framework_ag_ui", "chromadb", "gherkin", "tzdata"):
        cmd += ["--collect-all", pkg]
    cmd += ["--collect-submodules", "backend", str(DESKTOP / "backend_entry.py")]
    run(cmd, ROOT)
    out = BUILD / "backend"
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(BUILD / "backend-dist" / "atlas-backend", out, symlinks=True)
    print(f"Backend built: {out}")


def package() -> None:
    for need in (BUILD / "ui", BUILD / "backend"):
        if not need.is_dir():
            sys.exit(f"Missing {need}. Run this script without --package first.")
    env = {} if os.environ.get("CSC_LINK") else {"CSC_IDENTITY_AUTO_DISCOVERY": "false"}
    run([NPX, "electron-builder"], DESKTOP, env)
    for f in sorted((DESKTOP / "dist").glob("*.*")):
        if f.suffix in {".dmg", ".zip", ".msi"}:
            print(f"Artifact: {f} ({f.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    for flag in ("ui", "backend", "package"):
        ap.add_argument(f"--{flag}", action="store_true")
    a = ap.parse_args()
    everything = not (a.ui or a.backend or a.package)
    if everything or a.ui:
        build_ui()
    if everything or a.backend:
        build_backend()
    if everything or a.package:
        run([NPM, "ci", "--no-audit", "--no-fund"], DESKTOP) if not (DESKTOP / "node_modules").is_dir() else None
        package()


if __name__ == "__main__":
    main()

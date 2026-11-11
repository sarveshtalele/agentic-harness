"""Skip rules and the file sets for the backend and frontend packages."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SKIP_DIRS = {
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "test-results",
    ".git",
    ".github",
    ".sessions",
}
SKIP_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".DS_Store",
    "Thumbs.db",
    "agent-framework.pdf",
}
ASSET_FOLDERS = ("prompts", "templates", "skills", "evals")


def should_skip(path: Path, base_dir: Path) -> bool:
    rel_parts = path.relative_to(base_dir).parts
    if path.name in SKIP_FILES:
        return True
    if any(part in SKIP_DIRS for part in rel_parts):
        return True
    if any(part.startswith(".next") for part in rel_parts):
        return True
    if path.suffix in (".pyc", ".pyo"):
        return True
    return False


def git_tracked(root: Path) -> set[Path] | None:
    """Files git tracks plus new ones it would track (.gitignore keeps .env, data/ and builds out). None outside a checkout."""
    git = shutil.which("git")
    if not git or not (root / ".git").exists():
        return None
    result = subprocess.run([git, "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root, capture_output=True, timeout=60, check=False)
    if result.returncode != 0:
        return None
    return {(root / name).resolve() for name in result.stdout.decode("utf-8", "replace").split("\0") if name}


def collect_folder(folder: Path, base_dir: Path, tracked: set[Path] | None = None) -> dict[str, Path]:
    """Files under folder keyed by path relative to base_dir. With `tracked`, anything git does not list is never shipped."""
    entries: dict[str, Path] = {}
    for path in sorted(folder.rglob("*")):
        if tracked is not None and path.resolve() not in tracked:
            continue  # untracked or ignored locally: never shipped
        if path.is_file() and not path.is_symlink() and not should_skip(path, base_dir):
            entries[path.relative_to(base_dir).as_posix()] = path
    return entries


def backend_entries(root: Path, deploy_dir: Path, tracked: set[Path] | None = None) -> dict[str, Path]:
    """Backend package: startup files, src/backend, a top-level backend/ alias and the asset folders."""
    entries: dict[str, Path] = {
        "requirements.txt": root / "requirements.txt",
        "requirements-evals.txt": root / "requirements-evals.txt",  # installed only with ATLAS_INSTALL_EVALS=1 (RAGAS)
        "startup.sh": deploy_dir / "backend_startup.sh",
        "startup.py": deploy_dir / "backend_startup.py",
        ".deployment": deploy_dir / "kudu.deployment",
        "web.config": deploy_dir / "backend_web.config",
        "scripts/env_check.py": root / "scripts" / "env_check.py",  # run in Kudu SSH to check the App Service settings
    }
    src_backend_files = collect_folder(root / "src/backend", root, tracked)
    entries.update(src_backend_files)
    # Also map src/backend/... to backend/... so `from backend.app import app`
    # works whether PYTHONPATH is set to /home/site/wwwroot or /home/site/wwwroot/src
    for rel_path, abs_path in src_backend_files.items():
        if rel_path.startswith("src/backend/"):
            entries[rel_path[len("src/"):]] = abs_path
    for folder in ASSET_FOLDERS:
        if (root / folder).is_dir():
            entries.update(collect_folder(root / folder, root, tracked))
    return entries


def frontend_source_entries(root: Path, deploy_dir: Path, tracked: set[Path] | None = None) -> dict[str, Path]:
    """Frontend sources for Oryx to build on App Service."""
    base = root / "src/frontend"
    entries: dict[str, Path] = {
        "startup.sh": deploy_dir / "frontend_startup.sh",
        "startup.js": deploy_dir / "frontend_startup.js",
        ".deployment": deploy_dir / "kudu.deployment",
        "web.config": deploy_dir / "frontend_web.config",
        "staticwebapp.config.json": deploy_dir / "staticwebapp.config.json",
    }
    entries.update(collect_folder(base, base, tracked))
    return entries


def frontend_standalone_entries(root: Path, deploy_dir: Path, log) -> dict[str, Path]:
    """Frontend with the pre-built Next.js standalone bundle (needs `npm run build` with ATLAS_STANDALONE=1 first)."""
    fe_root = root / "src/frontend"
    entries: dict[str, Path] = {
        "startup.sh": deploy_dir / "frontend_startup.sh",
        "startup.js": deploy_dir / "frontend_startup.js",
        ".deployment": deploy_dir / "kudu.deployment",
        "web.config": deploy_dir / "frontend_web.config",
        "staticwebapp.config.json": deploy_dir / "staticwebapp.config.json",
    }
    log("  Packaging pre-built Next.js standalone bundle...")
    standalone_dir = fe_root / ".next/standalone"
    static_dir = fe_root / ".next/static"
    public_dir = fe_root / "public"

    if not standalone_dir.is_dir():
        raise RuntimeError("Next.js standalone directory .next/standalone does not exist! Run build first.")

    # Collect standalone server and dependencies
    for p in standalone_dir.rglob("*"):
        if p.is_file() and not p.is_symlink():
            rel = p.relative_to(standalone_dir).as_posix()
            entries[rel] = p

    # Collect static assets into .next/static
    if static_dir.is_dir():
        for p in static_dir.rglob("*"):
            if p.is_file():
                rel = f".next/static/{p.relative_to(static_dir).as_posix()}"
                entries[rel] = p
                # Also map nested if Next.js nested the standalone app under src/frontend
                entries[f"src/frontend/{rel}"] = p

    # Collect public assets
    if public_dir.is_dir():
        for p in public_dir.rglob("*"):
            if p.is_file():
                rel = f"public/{p.relative_to(public_dir).as_posix()}"
                entries[rel] = p
                entries[f"src/frontend/{rel}"] = p

    # Include package.json and next.config.ts for reference
    entries["package.json"] = fe_root / "package.json"
    entries["next.config.ts"] = fe_root / "next.config.ts"
    return entries

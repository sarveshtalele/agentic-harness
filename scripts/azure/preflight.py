"""Pre-flight checks. The two scripts check slightly different things and word their errors differently."""
from __future__ import annotations

import json
import py_compile
from pathlib import Path


def kudu_preflight(root: Path, log, error) -> bool:
    log("Running pre-flight validation checks...")
    ok = True

    # 1. Check Python syntax of all backend files
    backend_py_files = list((root / "src/backend").rglob("*.py"))
    if not backend_py_files:
        error("No Python files found in src/backend!")
        ok = False
    else:
        log(f"Compiling {len(backend_py_files)} Python files in src/backend...")
        for py_path in backend_py_files:
            try:
                py_compile.compile(str(py_path), doraise=True)
            except py_compile.PyCompileError as exc:
                error(f"Syntax error in {py_path}: {exc}")
                ok = False

    # 2. Check requirements.txt
    req_file = root / "requirements.txt"
    if not req_file.is_file() or req_file.stat().st_size == 0:
        error("requirements.txt is missing or empty!")
        ok = False
    else:
        req_content = req_file.read_text(encoding="utf-8")
        if "fastapi" not in req_content or "uvicorn" not in req_content:
            error("requirements.txt missing core FastAPI / Uvicorn dependencies!")
            ok = False

    # 3. Check assets: prompts, templates, skills, evals
    for folder in ("prompts", "templates", "skills", "evals"):
        fpath = root / folder
        if not fpath.is_dir() or not any(fpath.iterdir()):
            error(f"Required backend asset directory '{folder}' is missing or empty!")
            ok = False

    # 4. Check Frontend package.json and next.config.ts
    fe_pkg = root / "src/frontend/package.json"
    if not fe_pkg.is_file():
        error("src/frontend/package.json is missing!")
        ok = False
    else:
        try:
            pkg_data = json.loads(fe_pkg.read_text(encoding="utf-8"))
            if "next" not in pkg_data.get("dependencies", {}):
                error("Next.js dependency not found in frontend package.json!")
                ok = False
        except Exception as exc:
            error(f"Frontend package.json invalid JSON: {exc}")
            ok = False

    fe_config = root / "src/frontend/next.config.ts"
    if not fe_config.is_file():
        error("src/frontend/next.config.ts is missing!")
        ok = False

    # 5. Check startup scripts in deploy/azure
    required_deploy_files = [
        root / "deploy/azure/backend_startup.sh",
        root / "deploy/azure/backend_startup.py",
        root / "deploy/azure/frontend_startup.sh",
        root / "deploy/azure/frontend_startup.js",
        root / "deploy/azure/kudu.deployment",
        root / "deploy/azure/backend_web.config",
        root / "deploy/azure/frontend_web.config",
    ]
    for dep_file in required_deploy_files:
        if not dep_file.is_file():
            error(f"Deployment file missing: {dep_file.relative_to(root)}")
            ok = False

    if ok:
        log("Pre-flight validation passed successfully!")
    return ok


def convert_preflight(root: Path, deploy_dir: Path, log, error) -> bool:
    """Validates source syntax, required assets, and configuration files."""
    log("Running pre-flight verification...")
    passed = True

    # 1. Compile backend Python files
    py_files = list((root / "src/backend").rglob("*.py"))
    if not py_files:
        error("No Python source files found under src/backend!")
        passed = False
    else:
        log(f"  Validating syntax of {len(py_files)} Python source files...")
        for p in py_files:
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as exc:
                error(f"  Python syntax error in {p.relative_to(root)}: {exc}")
                passed = False

    # 2. Check requirements.txt
    req_file = root / "requirements.txt"
    if not req_file.is_file() or req_file.stat().st_size == 0:
        error("  requirements.txt is missing or empty!")
        passed = False
    else:
        req_text = req_file.read_text(encoding="utf-8")
        for pkg in ("fastapi", "uvicorn", "pydantic"):
            if pkg not in req_text.lower():
                error(f"  Critical dependency '{pkg}' missing from requirements.txt!")
                passed = False

    # 3. Check assets: prompts, templates, skills, evals
    for folder in ("prompts", "templates", "skills", "evals"):
        fpath = root / folder
        if not fpath.is_dir() or not any(fpath.iterdir()):
            error(f"  Required asset directory '{folder}/' is missing or empty!")
            passed = False

    # 4. Check Frontend package.json
    fe_pkg = root / "src/frontend/package.json"
    if not fe_pkg.is_file():
        error("  src/frontend/package.json is missing!")
        passed = False
    else:
        try:
            pkg = json.loads(fe_pkg.read_text(encoding="utf-8"))
            if "next" not in pkg.get("dependencies", {}):
                error("  'next' dependency missing in frontend package.json!")
                passed = False
        except Exception as exc:
            error(f"  Invalid JSON in frontend package.json: {exc}")
            passed = False

    # 5. Check deployment runner templates
    deploy_templates = [
        deploy_dir / "backend_startup.sh",
        deploy_dir / "backend_startup.py",
        deploy_dir / "frontend_startup.sh",
        deploy_dir / "frontend_startup.js",
        deploy_dir / "kudu.deployment",
        deploy_dir / "backend_web.config",
        deploy_dir / "frontend_web.config",
    ]
    for dt in deploy_templates:
        if not dt.is_file():
            error(f"  Deployment template missing: {dt.relative_to(root)}")
            passed = False

    if passed:
        log("  Pre-flight verification completed successfully.")
    return passed

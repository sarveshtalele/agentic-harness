"""Health of a skill's scripts (docs/PHASE2_PLAN.md section 7.4): can each script run here? Flag the skill when not.

Per script: (1) language supported and interpreter found (`script_runtime.plan`); (2) syntax: `python -m py_compile`,
`node --check`, `bash -n`, the PowerShell parser, `ruby -c`; (3) outside the web profile, a smoke run with `--help` and
empty standard input in a temporary copy of the skill, 20 seconds at most. Verdicts:
- `flagged`: cannot run here (no interpreter, unsupported language, syntax error, a missing module or package);
- `warning`: runs, but the smoke run timed out or exited non-zero (it may need arguments); usable, shown to the person;
- `ok`.
A skill takes its worst script's verdict. Results are cached by a hash of the skill's files and the interpreters' paths,
so a changed script is checked again and an unchanged one is not.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from backend.config import DATA_DIR, PROFILE
from backend.core import script_runtime as rt
from backend.repos.sandbox import clean_sandbox_env

CACHE = DATA_DIR / "skill-health"
SMOKE_S = 20
MISSING = re.compile(r"ModuleNotFoundError|No module named|ImportError|Cannot find module|ERR_MODULE_NOT_FOUND|cannot load such file|"
                     r"command not found|is not recognized as (?:the name of )?a cmdlet|ERR_UNKNOWN_FILE_EXTENSION|"
                     r"ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING|SyntaxError", re.I)
SKIP_DIRS = frozenset({".venv", "node_modules", "__pycache__", ".git"})
RANK = {"ok": 0, "warning": 1, "flagged": 2}


def scripts_of(skill_dir: Path) -> list[Path]:
    folder = skill_dir / "scripts"
    if not folder.is_dir():
        return []
    # a known extension, or any file with a shebang line (`#!/usr/bin/env ruby`, an extensionless tool)
    return sorted(p for p in folder.rglob("*") if p.is_file() and not SKIP_DIRS & set(p.parts)
                  and (p.suffix.lower() in rt.EXTENSIONS or rt.shebang(p)))


_digests: dict[tuple, str] = {}  # (folder, file sizes and times) -> content hash, so an unchanged folder is not re-read


def digest(skill_dir: Path) -> str:
    files = [p for p in sorted(skill_dir.rglob("*")) if p.is_file() and not SKIP_DIRS & set(p.relative_to(skill_dir).parts)]
    stamp = (str(skill_dir), tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in files))
    if stamp in _digests:
        return _digests[stamp]
    _digests[stamp] = _content_digest(skill_dir)
    return _digests[stamp]


def _content_digest(skill_dir: Path) -> str:
    h = hashlib.sha256(f"{PROFILE}|{rt.find_bash()}|{rt.find_powershell()}|{shutil.which('node')}".encode())
    for p in sorted(skill_dir.rglob("*")):
        if p.is_file() and not SKIP_DIRS & set(p.relative_to(skill_dir).parts):
            h.update(p.relative_to(skill_dir).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _syntax(language: str, argv: list[str], script: Path) -> list[str] | None:
    s = str(script)
    if language == "python":
        return [argv[0], "-c", "import ast, sys; ast.parse(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1])", s]
    if language == "typescript" and os.path.basename(argv[0]).startswith("node"):  # `node --check` does not strip types
        strip = ("const m = require('node:module'); if (m.stripTypeScriptTypes) "
                 "m.stripTypeScriptTypes(require('node:fs').readFileSync(process.argv[1], 'utf8'));")
        return [argv[0], "-e", strip, s]
    if language == "javascript" and os.path.basename(argv[0]).startswith("node"):
        return [argv[0], "--check", s]
    if language == "bash":
        return [argv[0], "-n", s]
    if language == "powershell":
        quoted = "'" + s.replace("'", "''") + "'"  # -Command joins extra arguments into the text, so the path goes inside it
        parse = (f"$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile({quoted}, [ref]$null, [ref]$e); "
                 "if ($e) { $e | ForEach-Object { $_.ToString() }; exit 1 }")
        return [argv[0], "-NoProfile", "-NonInteractive", "-Command", parse]
    if language == "ruby":
        return [argv[0], "-c", s]
    return None


def gist(text: str, name: str = "") -> str:
    """The line that explains a failure: the last one naming an error, with a line number when one is given."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    errors = [line for line in lines if re.search(r"error|cannot|not found|unexpected|missing", line, re.I)]
    near = re.findall(rf"{re.escape(name)}\"?,? (?:line )?:?(\d+)|{re.escape(name)}:(\d+)", text) if name else []
    where = near or re.findall(r"line (\d+)()", text)
    at = next((a or b for a, b in where if a or b), "")
    return ((errors or lines or ["no output"])[-1][:200]) + (f" (line {at})" if at else "")


def check_script(script: Path, skill_dir: Path, skill_md: str, smoke: bool = False) -> dict:
    p = rt.plan(script, skill_dir, skill_md)
    result = {"script": script.relative_to(skill_dir).as_posix(), "language": p.language, "interpreter": p.reason}
    if p.argv is None:
        return {**result, "verdict": "flagged", "reason": p.reason}
    env = clean_sandbox_env()
    if syntax := _syntax(p.language, p.argv, script):
        done = rt.run(syntax, cwd=skill_dir, env=env, timeout=30)
        if done["exit_code"] != 0:
            return {**result, "verdict": "flagged", "reason": f"syntax error: {gist(done['stderr'] or done['stdout'], script.name)}"}
    if not smoke or PROFILE == "web":  # a smoke run executes the script: only right before its first approved run, never on web
        return {**result, "verdict": "ok", "reason": "interpreter found and syntax checked"}
    with tempfile.TemporaryDirectory(prefix="skill-health-") as scratch:
        copy = Path(scratch) / skill_dir.name
        shutil.copytree(skill_dir, copy, symlinks=False, ignore=shutil.ignore_patterns(*SKIP_DIRS - {".venv", "node_modules"}))
        argv = [a.replace(str(skill_dir), str(copy)) for a in p.argv]
        done = rt.run([*argv, "--help"], cwd=copy, env=env, stdin="", timeout=SMOKE_S)
    text = (done["stderr"] or "") + (done["stdout"] or "")
    if done["exit_code"] is not None and done["exit_code"] != 0 and MISSING.search(text):
        return {**result, "verdict": "flagged", "reason": f"cannot start: {gist(text, script.name)}"}
    if done["exit_code"] is None:
        return {**result, "verdict": "warning", "reason": f"smoke run with --help did not finish in {SMOKE_S} s"}
    if done["exit_code"] != 0:
        return {**result, "verdict": "warning", "reason": f"smoke run with --help exited {done['exit_code']} (it may need arguments)"}
    return {**result, "verdict": "ok", "reason": "ran with --help"}


def check_skill(skill_dir: Path, *, refresh: bool = False, smoke: bool = False) -> dict:
    """{"verdict", "scripts": [...], "hash"} for one skill folder, cached by content. `smoke` also runs each script with --help."""
    skill_dir = Path(skill_dir).resolve()
    key = digest(skill_dir)
    cached = CACHE / f"{key}-{'smoke' if smoke else 'static'}.json"
    if cached.is_file() and not refresh:
        return json.loads(cached.read_text(encoding="utf-8"))
    md = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace") if (skill_dir / "SKILL.md").is_file() else ""
    results = [check_script(s, skill_dir, md, smoke) for s in scripts_of(skill_dir)]
    verdict = max((r["verdict"] for r in results), key=RANK.get, default="ok")
    report = {"skill": skill_dir.name, "verdict": verdict, "scripts": results, "hash": key}
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def reason(report: dict) -> str:
    bad = [r for r in report["scripts"] if r["verdict"] == report["verdict"] and r["verdict"] != "ok"]
    return "; ".join(f"{r['script']}: {r['reason']}" for r in bad)


def flag_runtime(skill_dir: Path, report: dict, why: str) -> None:
    """Flag a skill whose scripts keep failing at run time; stays until its files change (a new hash) or `refresh`."""
    for kind in ("static", "smoke"):
        cached = CACHE / f"{report['hash']}-{kind}.json"
        if cached.is_file():
            data = json.loads(cached.read_text(encoding="utf-8"))
            data.update({"verdict": "flagged", "runtime_flag": why})
            cached.write_text(json.dumps(data, indent=1), encoding="utf-8")


def cached_report(skill_dir: Path) -> dict | None:
    """The newest known report for a folder without running anything (smoke first, then static)."""
    key = digest(Path(skill_dir).resolve())
    for kind in ("smoke", "static"):
        cached = CACHE / f"{key}-{kind}.json"
        if cached.is_file():
            return json.loads(cached.read_text(encoding="utf-8"))
    return None


_running: set[str] = set()


def refresh_in_background(skill_dirs: list[Path]) -> None:
    """Static checks for every skill not checked yet, in one background thread (nothing is executed)."""
    import threading

    todo = [d for d in skill_dirs if scripts_of(d) and cached_report(d) is None and str(d) not in _running]
    if not todo:
        return
    _running.update(str(d) for d in todo)

    def work():
        for d in todo:
            try:
                check_skill(d)
            except OSError:
                pass
            finally:
                _running.discard(str(d))

    threading.Thread(target=work, daemon=True).start()


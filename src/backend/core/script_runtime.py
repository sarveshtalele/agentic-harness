"""Skill scripts in every common language (docs/PHASE2_PLAN.md section 7.3): detect the language, find the interpreter, run.

Detection, first match wins:
1. declared in SKILL.md: frontmatter `metadata.runtime`, or a run command its body shows (`node ${CLAUDE_SKILL_DIR}/scripts/x.ts`);
2. the shebang line (`#!/usr/bin/env python3`, `node`, `tsx`, `bash`, `pwsh`, ...);
3. the extension: .py Python; .ts .mts .cts TypeScript; .js .mjs .cjs JavaScript; .sh .bash Bash; .ps1 PowerShell; .rb Ruby;
   .go Go (`go run`);
4. otherwise unknown.
Interpreters: Python is the skill's own `.venv` or this platform's Python; TypeScript is Node 22.18+ (type stripping; 22.6
to 22.17 with `--experimental-strip-types`) or the skill's `tsx`; JavaScript is Node; Bash is /bin/bash or Git for Windows'
bash; PowerShell is pwsh or Windows PowerShell; anything else is the program the shebang or declaration names, when it is
on PATH. A missing interpreter is a reason, never a guess. Runs use an argument list, no shell, a timeout and a clean env.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EXTENSIONS = {".py": "python", ".ts": "typescript", ".mts": "typescript", ".cts": "typescript", ".js": "javascript",
              ".mjs": "javascript", ".cjs": "javascript", ".sh": "bash", ".bash": "bash", ".ps1": "powershell", ".rb": "ruby", ".go": "go"}
SCRIPT_EXTENSIONS = tuple(EXTENSIONS)
PROGRAM_LANGUAGE = {"python": "python", "python3": "python", "node": "javascript", "tsx": "typescript", "bash": "bash", "sh": "bash",
                    "pwsh": "powershell", "powershell": "powershell", "ruby": "ruby", "go": "go", "deno": "typescript", "bun": "javascript"}
RUN_LINE = re.compile(r"(?:^|[\s`(])(python3?|node|tsx|npx\s+tsx|bash|sh|pwsh|powershell|ruby|go\s+run)\s+"
                      r"(?:\"?\$\{(?:CLAUDE|AQH)_SKILL_DIR\}/)?(scripts/[\w./-]+)", re.M)
TIMEOUT = 120


@dataclass
class Plan:
    language: str  # python, typescript, javascript, bash, powershell, ruby, go, or unknown
    argv: list[str] | None  # the interpreter command for this script, None when it cannot run here
    reason: str  # why argv is None, or how the language was found


def declared(skill_md: str, relative: str) -> str | None:
    """The language SKILL.md states for `relative` (scripts/x.ext): a metadata runtime, or a run command in the body."""
    runtime = re.search(r"^\s*runtime:\s*['\"]?([\w-]+)", skill_md, re.M)
    if runtime and runtime[1].lower() in PROGRAM_LANGUAGE:
        return PROGRAM_LANGUAGE[runtime[1].lower()]
    for program, path in RUN_LINE.findall(skill_md):
        if path.rstrip("`\"'") == relative:
            if "tsx" in program:
                return "typescript"
            if program == "node":  # node runs .js and, with type stripping, .ts: the extension says which
                return EXTENSIONS.get(Path(relative).suffix.lower(), "javascript")
            return PROGRAM_LANGUAGE.get(program.split()[0])
    return None


def shebang(path: Path) -> str | None:
    try:
        first = path.open("rb").readline(200).decode("utf-8", errors="replace").strip()
    except OSError:
        return None
    if not first.startswith("#!"):
        return None
    words = first[2:].split()
    program = os.path.basename(words[1] if words and os.path.basename(words[0]) == "env" and len(words) > 1 else (words[0] if words else ""))
    return program or None


def find_bash() -> str | None:
    if os.name != "nt":
        return next((p for p in ("/bin/bash", "/usr/bin/bash") if Path(p).exists()), None) or shutil.which("bash")
    git = shutil.which("git")
    roots = [Path(git).resolve().parent.parent] if git else []
    roots += [Path(os.environ[v]) / "Git" for v in ("ProgramFiles", "ProgramFiles(x86)") if os.environ.get(v)]
    roots += [Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Git"] if os.environ.get("LOCALAPPDATA") else []
    return next((str(r / "bin" / "bash.exe") for r in roots if (r / "bin" / "bash.exe").is_file()), None)


def find_powershell() -> str | None:
    return shutil.which("pwsh") or (shutil.which("powershell") if os.name == "nt" else None)


def node_version() -> tuple[int, int] | None:
    node = shutil.which("node")
    if not node:
        return None
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10, check=False, stdin=subprocess.DEVNULL).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    found = re.match(r"v(\d+)\.(\d+)", out.strip())
    return (int(found[1]), int(found[2])) if found else None


def _venv_python(skill_dir: Path) -> str | None:
    candidate = skill_dir / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(candidate) if candidate.is_file() else None


def _tsx(skill_dir: Path) -> str | None:
    local = skill_dir / "node_modules" / ".bin" / ("tsx.cmd" if os.name == "nt" else "tsx")
    return str(local) if local.is_file() else shutil.which("tsx")


def plan(script: Path, skill_dir: Path, skill_md: str = "") -> Plan:
    """How to run `script`, or why it cannot run on this machine."""
    relative = script.relative_to(skill_dir).as_posix()
    bang = shebang(script)
    language = declared(skill_md, relative) or (PROGRAM_LANGUAGE.get(bang) if bang else None) or EXTENSIONS.get(script.suffix.lower(), "unknown")
    s = str(script)
    if language == "python":
        return Plan(language, [_venv_python(skill_dir) or sys.executable, s], "python")
    if language in ("typescript", "javascript"):
        version = node_version()
        tsx = _tsx(skill_dir) if language == "typescript" else None
        if language == "typescript" and tsx and ("tsx" in skill_md or bang == "tsx"):
            return Plan(language, [tsx, s], "tsx")
        if version is None:
            return Plan(language, None, "Node.js is not installed here")
        if language == "javascript" or version >= (22, 18) or version[0] >= 23:
            return Plan(language, [shutil.which("node"), s], f"node {version[0]}.{version[1]}")
        if version >= (22, 6):
            return Plan(language, [shutil.which("node"), "--experimental-strip-types", s], f"node {version[0]}.{version[1]}")
        return Plan(language, [tsx, s], "tsx") if tsx else Plan(language, None, f"TypeScript needs Node 22.6 or newer (found {version[0]}.{version[1]}) or tsx")
    if language == "bash":
        bash = find_bash()
        return Plan(language, [bash, s], "bash") if bash else Plan(language, None, "bash is not installed here (on Windows, install Git for Windows)")
    if language == "powershell":
        ps = find_powershell()
        flags = ["-NoLogo", "-NoProfile", "-NonInteractive"] + (["-ExecutionPolicy", "Bypass"] if os.name == "nt" else [])
        return Plan(language, [ps, *flags, "-File", s], "powershell") if ps else Plan(language, None, "PowerShell is not installed here")
    if language == "go":
        go = shutil.which("go")
        return Plan(language, [go, "run", s], "go") if go else Plan(language, None, "Go is not installed here")
    program = bang or {"ruby": "ruby"}.get(language)  # whatever the shebang names, found on PATH
    found = shutil.which(program) if program else None
    if found:
        return Plan(language, [found, s], program)
    return Plan(language, None, f"no interpreter for {script.name}" + (f" ({program} is not installed here)" if program else ""))


def run(argv: list[str], *, cwd: Path, env: dict[str, str], stdin: str = "", timeout: int = TIMEOUT) -> dict:
    try:
        done = subprocess.run(argv, cwd=cwd, input=stdin, env=env, capture_output=True, text=True, timeout=timeout, shell=False,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"exit_code": None, "stdout": "", "stderr": f"timed out after {timeout} s"}
    except OSError as exc:
        return {"exit_code": None, "stdout": "", "stderr": f"could not start: {exc}"}
    return {"exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr}

"""Greenfield stack templates (docs/QE_V2_PLAN.md section 4): list, validate stack.json, copy into a workspace, check the toolchains.

A template is a folder in templates/stacks/ holding a runnable skeleton and its stack.json manifest. Running one is in stack_run.py.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from backend.core.security import safe_path
from backend.qe.execution.runners import clean_env

ROOT = Path(__file__).resolve().parents[3] / "templates" / "stacks"
TOOLS = ("python", "node", "java", "mvn", "dotnet", "go")
# argv[0] may only be one of these, or a placeholder the runner fills ({python} this platform's Python, {venv_python} the workspace's .venv)
PROGRAMS = {"{python}", "{venv_python}", "npm", "npx", "node", "mvn", "java", "dotnet", "go"}
VERSION_COMMAND = {"python": ["{python}", "--version"], "node": ["node", "--version"], "java": ["java", "-version"], "mvn": ["mvn", "-v"],
                   "dotnet": ["dotnet", "--version"], "go": ["go", "version"]}
SKIP_COPY = {".venv", "node_modules", "__pycache__", ".next", "target", "bin", "obj"}


class StackError(ValueError):
    """A template or stack id that cannot be used; the message says why."""


class Toolchain(BaseModel):
    name: Literal["python", "node", "java", "mvn", "dotnet", "go"]
    min: str = Field(pattern=r"^\d+(\.\d+)*$")


class Tests(BaseModel):
    unit: list[str] = Field(min_length=1)
    integration: list[str] = Field(min_length=1)
    e2e: list[str] | None = None


class Stack(BaseModel):
    id: str
    name: str
    language: str
    ui: bool
    toolchains: list[Toolchain] = Field(min_length=1)
    install: list[list[str]]
    build: list[list[str]] = Field(min_length=1)
    test: Tests
    start: list[str] = Field(min_length=1)
    health: str
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("install", "build")
    @classmethod
    def _steps(cls, steps):
        for argv in steps:
            _program(argv)
        return steps

    @field_validator("start")
    @classmethod
    def _start(cls, argv):
        _program(argv)
        if not any("{port}" in a for a in argv):
            raise ValueError("the start command needs a {port} placeholder")
        return argv

    @model_validator(mode="after")
    def _whole(self):
        for argv in (self.test.unit, self.test.integration, self.test.e2e):
            if argv:
                _program(argv)
        if "{port}" not in self.health or not self.health.startswith("http://127.0.0.1:"):
            raise ValueError("health must be a http://127.0.0.1:{port}/... URL")
        if self.ui and not self.test.e2e:
            raise ValueError("a stack with a web page needs an e2e (Playwright) command")
        return self


def _program(argv: list[str]) -> None:
    if not argv or argv[0] not in PROGRAMS:
        raise ValueError(f"command {argv[:1]} is not an allowed program ({sorted(PROGRAMS)})")


def load(stack_id: str) -> Stack:
    """The validated manifest of one template. An unknown id is refused."""
    if stack_id not in ids():
        raise StackError(f"Unknown stack '{stack_id}'. The templates are: {', '.join(ids())}.")
    path = ROOT / stack_id / "stack.json"
    try:
        stack = Stack.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise StackError(f"Template {stack_id} has an invalid stack.json: {str(exc)[:600]}") from exc
    if stack.id != stack_id:
        raise StackError(f"Template folder {stack_id} declares id {stack.id}")
    return stack


def ids() -> list[str]:
    return sorted(p.name for p in ROOT.iterdir() if (p / "stack.json").is_file()) if ROOT.is_dir() else []


def list_templates() -> list[Stack]:
    return [load(i) for i in ids()]


def copy_template(stack_id: str, workspace: Path, folder: str = "app") -> Path:
    """Copy the skeleton into workspace/folder (through safe_path). Refuses a folder that already holds files."""
    load(stack_id)
    target = safe_path(workspace, folder, for_write=True)
    if target.exists() and any(target.iterdir()):
        raise StackError(f"{folder} in the workspace is not empty; the template is not copied over existing files")
    shutil.copytree(ROOT / stack_id, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*SKIP_COPY))
    return target


def _version(tool: str) -> tuple[str, str]:
    """(version, reason): the version found, or '' and why not."""
    argv = [sys.executable if a == "{python}" else a for a in VERSION_COMMAND[tool]]
    exe = argv[0] if argv[0] == sys.executable else shutil.which(argv[0])
    if not exe:
        return "", f"{argv[0]} is not on PATH"
    try:
        done = subprocess.run([exe, *argv[1:]], capture_output=True, text=True, errors="replace", timeout=30, env=clean_env())
    except (OSError, subprocess.SubprocessError) as exc:
        return "", f"{argv[0]} did not run: {exc}"
    found = re.search(r"\d+(?:\.\d+)+", done.stdout + done.stderr)
    return (found[0], "") if found else ("", f"{argv[0]} printed no version (exit {done.returncode}): a stub, not a toolchain")


def _tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def toolchain_status(stack: Stack) -> dict:
    """{ok, missing: [reason], found: {tool: version}} for the toolchains this machine has against the template's minimums."""
    found, missing = {}, []
    for t in stack.toolchains:
        version, reason = _version(t.name)
        if not version:
            missing.append(f"{t.name} {t.min}+: {reason}")
        elif _tuple(version) < _tuple(t.min):
            missing.append(f"{t.name} {t.min}+ needed, {version} found")
        else:
            found[t.name] = version
    return {"ok": not missing, "missing": missing, "found": found}

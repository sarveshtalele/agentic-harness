"""Run a template's manifest commands inside a workspace folder: argument lists, no shell, a timeout, clean_env, the app always stopped."""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from backend.qe.execution.runners import TAIL, clean_env
from backend.qe.stacks import Stack, StackError

STEP_TIMEOUT = 900
START_TIMEOUT = 90
POLL = 1  # seconds between health probes while the app starts


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _argv(argv: list[str], cwd: Path, port: int = 0) -> list[str]:
    venv = cwd / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    fill = {"{python}": sys.executable, "{venv_python}": str(venv)}
    out = [fill.get(argv[0]) or shutil.which(argv[0]) or "", *(a.replace("{port}", str(port)) for a in argv[1:])]
    if not out[0]:
        raise StackError(f"{argv[0]} is not on PATH")
    return out


def run_step(stack: Stack, argv: list[str], cwd: Path, timeout: int = STEP_TIMEOUT) -> dict:
    """One command to completion. {argv, exit, tail}; exit is None when it timed out."""
    real = _argv(argv, cwd)
    try:
        done = subprocess.run(real, cwd=cwd, env=clean_env(stack.env), capture_output=True, text=True, errors="replace", timeout=timeout)
        return {"argv": argv, "exit": done.returncode, "tail": (done.stdout + done.stderr)[-TAIL:]}
    except subprocess.TimeoutExpired as exc:
        return {"argv": argv, "exit": None, "tail": f"timed out after {timeout}s " + str(exc.stdout or "")[-500:]}


def _stop(proc: subprocess.Popen) -> None:
    """Kill the app and everything it started (npm, go run and dotnet run start a child)."""
    if proc.poll() is None:
        if os.name == "nt":
            subprocess.run([shutil.which("taskkill") or "taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=30)
        else:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                proc.kill()
        proc.wait(timeout=10)


def start_and_probe(stack: Stack, cwd: Path, timeout: int = START_TIMEOUT) -> dict:
    """Start the app on a free 127.0.0.1 port, poll the health URL, stop it. {ok, port, status, tail}."""
    port = free_port()
    log = cwd / ".start.log"
    with log.open("wb") as out:
        flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        proc = subprocess.Popen(_argv(stack.start, cwd, port), cwd=cwd, env=clean_env(stack.env), stdout=out, stderr=subprocess.STDOUT, **flags)
        status, deadline = None, time.monotonic() + timeout
        try:
            while time.monotonic() < deadline and proc.poll() is None:
                try:
                    with urllib.request.urlopen(stack.health.replace("{port}", str(port)), timeout=3) as reply:
                        status = reply.status
                        break
                except OSError:
                    time.sleep(POLL)
        finally:
            _stop(proc)
    return {"ok": status == 200, "port": port, "status": status, "tail": log.read_text(encoding="utf-8", errors="replace")[-TAIL:]}


def run_stack(stack: Stack, cwd: Path, levels: tuple[str, ...] = ("unit",)) -> dict:
    """install -> build -> the named test levels -> start and probe. Stops at the first failing step; ok only when all passed."""
    steps = []
    for phase, argvs in (("install", stack.install), ("build", stack.build), *((lvl, [getattr(stack.test, lvl)]) for lvl in levels)):
        for argv in argvs:
            result = {"phase": phase, **run_step(stack, argv, cwd)}
            steps.append(result)
            if result["exit"] != 0:
                return {"ok": False, "steps": steps, "start": None}
    start = start_and_probe(stack, cwd)
    return {"ok": start["ok"], "steps": steps, "start": start}

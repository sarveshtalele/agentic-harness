"""Toolchains for greenfield runs on the built-in App Service Python image (no Docker).

Downloads pinned Node, JDK (Temurin), Maven, .NET SDK and Go once into /home/tools (the App Service /home share survives
restarts), each verified against the SHA the vendor publishes (pinned below), plus Playwright's Chromium and, when it is
missing and we are root, its system libraries. Idempotent: a tool that is already installed is skipped. Nothing is skipped
silently: every step logs, and /home/tools/status.json says what is ready and what is not.

  python toolchains.py                  install everything (Linux x64 only), print the status, exit 1 if anything failed
  python toolchains.py --only node,go   just those
  python toolchains.py --root DIR       install under DIR instead of ATLAS_TOOLS_DIR or /home/tools

backend_startup.py imports tool_env() for the PATH and *_HOME variables of the API process and runs this in the background.
Standard library only. ponytail: Linux x64 only (App Service B1); other platforms log a skip and use what is on PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("ATLAS_TOOLS_DIR", "/home/tools"))
from toolchain_pins import ALL, FIXED_ENV, TOOLS  # noqa: E402 - pinned versions and vendor hashes
from toolchain_fetch import download, extract  # noqa: E402 - verified download and atomic extraction


def log(message: str) -> None:
    print(f"[agentic-qe toolchains] {message}", flush=True)


def supported() -> bool:
    return sys.platform.startswith("linux") and platform.machine().lower() in ("x86_64", "amd64")


def wanted(value: str | None) -> list[str]:
    """ATLAS_INSTALL_TOOLCHAINS: unset or 'all' = every tool, 'none' = nothing, else a comma list."""
    if value is None or value.strip().lower() in ("", "all"):
        return list(ALL)
    if value.strip().lower() == "none":
        return []
    names = [n.strip().lower() for n in value.split(",") if n.strip()]
    bad = [n for n in names if n not in ALL]
    if bad:
        raise SystemExit(f"ATLAS_INSTALL_TOOLCHAINS: unknown tool {', '.join(bad)}. Valid: {', '.join(ALL)}, all, none")
    return names


def tool_env(root: Path = ROOT, base_path: str | None = None) -> dict[str, str]:
    """PATH and *_HOME variables for the API process. Directories that are not installed yet are harmless on PATH."""
    paths, env = [], dict(FIXED_ENV)
    for spec in TOOLS.values():
        home = root / spec["dir"]
        paths += [str((home / b).resolve(strict=False)) for b in spec["bins"]]
        env.update({k: str(home) for k in spec.get("env", {})})
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(root / "ms-playwright")
    env["PATH"] = os.pathsep.join(paths + [base_path if base_path is not None else os.environ.get("PATH", "")])
    return env


def install(name: str, root: Path) -> str:
    """Install one pinned tool. Returns 'present' or 'installed'; raises with the reason otherwise."""
    spec = TOOLS[name]
    final = root / spec["dir"]
    if (final / spec["check"]).exists():
        return "present"
    for stale in root.glob(f".{spec['dir']}.*"):  # an interrupted earlier run
        shutil.rmtree(stale, ignore_errors=True) if stale.is_dir() else stale.unlink(missing_ok=True)
    part, work = root / f".{spec['dir']}.part", root / f".{spec['dir']}.tmp"
    log(f"{name}: downloading {spec['url']}")
    download(spec["url"], spec["algo"], spec["digest"], part)
    log(f"{name}: {spec['algo']} verified; extracting")
    try:
        extract(part, work, spec["strip"])
        if not (work / spec["check"]).exists():
            raise RuntimeError(f"{spec['check']} not found after extraction")
        if final.exists():
            shutil.rmtree(final)  # only our own half-installed folder (no check file)
        work.rename(final)
    finally:
        part.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)
    return "installed"


def chrome_binaries(browsers: Path) -> list[Path]:
    return [p for pattern in ("chromium-*/chrome-linux*/chrome", "chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell") for p in browsers.glob(pattern)]


def missing_libraries(binary: Path) -> list[str]:
    ldd = shutil.which("ldd")
    if not ldd:
        return []
    out = subprocess.run([ldd, str(binary)], capture_output=True, text=True, timeout=60, check=False).stdout
    return [line.split("=>")[0].strip() for line in out.splitlines() if "not found" in line]


def install_chromium(root: Path, python: str) -> str:
    browsers = root / "ms-playwright"
    env = {**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(browsers)}
    note = "present"
    if not chrome_binaries(browsers):
        log("chromium: playwright install chromium")
        subprocess.run([python, "-m", "playwright", "install", "chromium"], env=env, check=True, timeout=1200)
        note = "installed"
    binaries = chrome_binaries(browsers)
    if not binaries:
        raise RuntimeError("playwright install finished but no chromium binary was found")
    missing = sorted({lib for b in binaries for lib in missing_libraries(b)})
    if missing:
        # system libraries live outside /home, so they are gone after each restart and this repeats
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            raise RuntimeError(f"chromium is missing system libraries ({', '.join(missing[:4])}...) and this process is not root, so apt cannot install them")
        log(f"chromium: missing {', '.join(missing[:4])}{'...' if len(missing) > 4 else ''}; playwright install-deps chromium (apt)")
        subprocess.run([python, "-m", "playwright", "install-deps", "chromium"], env=env, check=True, timeout=1200)
        still = sorted({lib for b in binaries for lib in missing_libraries(b)})
        if still:
            raise RuntimeError(f"chromium still misses {', '.join(still[:4])} after install-deps")
        note += " + system libraries installed"
    return note


def run(names: list[str], root: Path, python: str) -> dict[str, dict]:
    root.mkdir(parents=True, exist_ok=True)
    status_file = root / "status.json"
    status: dict[str, dict] = {n: {"ok": False, "detail": "not attempted yet"} for n in names}
    for name in names:
        try:
            detail = install_chromium(root, python) if name == "chromium" else install(name, root)
            status[name] = {"ok": True, "detail": detail, **({"version": TOOLS[name]["dir"]} if name in TOOLS else {})}
            log(f"{name}: {detail}")
        except Exception as exc:  # noqa: BLE001 - one failing tool must not stop the others; the reason is logged and saved
            status[name] = {"ok": False, "detail": str(exc)[:500]}
            log(f"{name}: FAILED: {exc}")
        status_file.write_text(json.dumps({"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tools": status}, indent=2))
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--only", help="comma list; default ATLAS_INSTALL_TOOLCHAINS or all")
    parser.add_argument("--python", default=os.environ.get("ATLAS_PYTHON", sys.executable), help="Python with playwright installed")
    args = parser.parse_args()
    if not supported():
        log(f"skipped: {sys.platform}/{platform.machine()} is not Linux x64. Greenfield toolchains must come from this machine's PATH")
        return 0
    names = wanted(args.only if args.only is not None else os.environ.get("ATLAS_INSTALL_TOOLCHAINS"))
    if not names:
        log("skipped: ATLAS_INSTALL_TOOLCHAINS=none")
        return 0
    args.root.mkdir(parents=True, exist_ok=True)
    import fcntl  # Linux only, and supported() has said we are on Linux

    with (args.root / ".lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log("another installer is already running; leaving it to finish")
            return 0
        status = run(names, args.root, args.python)
    failed = [n for n, s in status.items() if not s["ok"]]
    log("ready: " + ", ".join(n for n in names if n not in failed) + ("" if not failed else f"; NOT ready: {', '.join(failed)} (see status.json)"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

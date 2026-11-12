"""OS sandbox for harness shell commands (docs/PHASE2_PLAN.md section 5.3, tier T1), as Claude Code does it.

- macOS: Seatbelt (`sandbox-exec`) with a profile that allows reading, allows writing only in the workspace, the
  conversation's scratch folder and the temp folder, and blocks outbound network except to this machine;
- Linux: bubblewrap (`bwrap`): the system read-only, the workspace and temp folders writable, and its own empty network
  namespace (`--unshare-net`) unless network is allowed;
- Windows: no OS sandbox exists (Claude Code has the same limit), so commands keep asking for approval there.
It covers the shell and every process it starts. It is on when the conversation is in `auto` mode or a trusted settings
file sets `"sandbox": {"enabled": true}`; `"sandbox": {"network": true}` lets sandboxed commands use the network.
In `auto` mode a sandboxed command runs without an approval card (`permissions.decide`); deny rules and hooks still apply.
ponytail: network is all or nothing; Claude Code's per-domain proxy allowlist comes when a team asks for it.
"""
from __future__ import annotations

import functools
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from backend.core import settings_files


@functools.cache
def kind() -> str | None:
    """"seatbelt", "bubblewrap", or None when this machine has no usable OS sandbox."""
    if sys.platform == "darwin" and (exe := shutil.which("sandbox-exec")):
        probe = [exe, "-p", "(version 1)(allow default)", "/usr/bin/true"]
    elif sys.platform.startswith("linux") and (exe := shutil.which("bwrap")):
        probe = [exe, "--ro-bind", "/", "/", "--dev", "/dev", "--unshare-net", "--die-with-parent", "--", "/bin/true"]
    else:
        return None
    try:
        ok = subprocess.run(probe, capture_output=True, timeout=10, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    return ("seatbelt" if sys.platform == "darwin" else "bubblewrap") if ok else None


def settings(root=None) -> dict:
    found = {"enabled": False, "network": False}
    for layer in reversed(settings_files.layers(root)):  # lowest first, so higher layers win
        block = layer.data.get("sandbox") if layer.trusted and isinstance(layer.data.get("sandbox"), dict) else None
        if block:
            found.update({k: bool(block[k]) for k in ("enabled", "network") if k in block})
    return found


def active(mode: str, root=None) -> bool:
    return kind() is not None and (mode == "auto" or settings(root)["enabled"])


def _quote(path: Path) -> str:
    return '"' + str(Path(path).resolve()).replace("\\", "\\\\").replace('"', '\\"') + '"'


def seatbelt_profile(writable: list[Path], network: bool) -> str:
    places = " ".join(f"(subpath {_quote(p)})" for p in writable)
    net = "" if network else '(deny network-outbound)(allow network-outbound (remote ip "localhost:*") (remote unix-socket))'
    return ("(version 1)(allow default)(deny file-write*)"
            f'(allow file-write* {places} (literal "/dev/null") (literal "/dev/tty") (regex #"^/dev/fd/"))' + net)


def writable(ws) -> list[Path]:
    return [Path(ws.root), Path(ws.scratch), Path(tempfile.gettempdir())]


def wrap(argv: list[str], ws, network: bool = False) -> list[str]:
    """`argv` run inside the OS sandbox, or unchanged when there is none."""
    sandbox = kind()
    if sandbox == "seatbelt":
        return [shutil.which("sandbox-exec"), "-p", seatbelt_profile(writable(ws), network), *argv]
    if sandbox == "bubblewrap":
        binds = [arg for p in writable(ws) for arg in ("--bind", str(Path(p).resolve()), str(Path(p).resolve()))]
        return [shutil.which("bwrap"), "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", *binds,
                *([] if network else ["--unshare-net"]), "--die-with-parent", "--", *argv]
    return argv

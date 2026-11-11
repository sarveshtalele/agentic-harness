"""Installed and declared dependency inventory."""
from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path
from backend.qe import execution


SIGNATURE_BUDGET = 6000  # characters of real signatures added to one generation request


ALIASES = {"yaml": "pyyaml", "pil": "pillow", "cv2": "opencv-python", "sklearn": "scikit-learn", "bs4": "beautifulsoup4", "dateutil": "python-dateutil", "jwt": "pyjwt", "dotenv": "python-dotenv", "jose": "python-jose"}


INVENTORY = (
    "import json, sys\nfrom importlib import metadata as m\n"
    "versions = {}\nfor d in m.distributions():\n    n = d.metadata['Name']\n    if n:\n        versions[n.lower().replace('_', '-')] = d.version\n"
    "print(json.dumps({'modules': sorted(m.packages_distributions()), 'versions': versions, 'stdlib': sorted(sys.stdlib_module_names), 'python': sys.version.split()[0]}))\n"
)


def inventory(python: str) -> dict | None:
    """What the sandbox Python really has, read by that Python itself. None when it cannot be read, and then the third-party check is skipped.

    ponytail: one subprocess per call, no cache, because an install between two calls changes the answer.
    """
    try:
        done = subprocess.run([python, "-I", "-c", INVENTORY], capture_output=True, text=True, timeout=30, env=execution.clean_env(), errors="replace")
        data = json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if not isinstance(data, dict) or not {"modules", "versions", "stdlib"} <= set(data):
        return None
    return {"modules": set(data["modules"]), "versions": data["versions"], "stdlib": set(data["stdlib"]), "python": data.get("python", "")}


def _normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def declared_dependencies(worktree: Path) -> set[str]:
    """Distribution names the repository declares, for runs that will install them. Normalized, without versions or extras."""
    found: set[str] = set()
    take = lambda spec: found.add(_normal(m.group(0))) if (m := re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", spec.strip())) else None
    for path in worktree.glob("requirements*.txt"):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip() and not line.lstrip().startswith(("#", "-")):
                take(line)
    try:
        data = tomllib.loads((worktree / "pyproject.toml").read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return found
    project = data.get("project", {})
    for spec in [*project.get("dependencies", []), *(s for group in project.get("optional-dependencies", {}).values() for s in group), *(s for group in data.get("dependency-groups", {}).values() for s in group if isinstance(s, str))]:
        take(spec)
    found |= {_normal(k) for k in data.get("tool", {}).get("poetry", {}).get("dependencies", {})}
    return found

"""`python scripts/dev.py evidence [--e2e]`: run each test level into JUnit XML (failures recorded, not raised), then
write the evidence report (scripts/evidence_report.py). Runs with the project's .venv Python."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)}


def evidence() -> None:
    """Run each level into JUnit XML (failures recorded, not raised), then write the evidence report."""
    out = ROOT / "data" / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    levels = [("unit-integration", ["tests", "-q", "-m", "not e2e and not live and not smoke"]),
              ("smoke", ["tests/e2e/test_smoke.py", "-v", "-m", "smoke"])]
    if "--e2e" in sys.argv:
        levels.append(("e2e", ["tests/e2e", "-v", "-m", "e2e"]))
    for name, args in levels:
        subprocess.run([str(PYTHON), "-m", "pytest", *args, f"--junitxml={out / (name + '.xml')}"], cwd=ROOT, env=ENV, check=False)
    report = [str(PYTHON), str(ROOT / "scripts" / "evidence_report.py"), "--screens", str(ROOT / "docs" / "evidence" / "screens")]
    for name, _ in levels:
        report += ["--level", f"{name}={out / (name + '.xml')}"]
    subprocess.run(report, cwd=ROOT, env=ENV, check=True)


if __name__ == "__main__":
    evidence()

#!/usr/bin/env python3
"""Skill evaluator: the platform's skill checks (backend/core/skill_studio/checks.py) on one folder.

Reports only what it measured: each check passed or failed, and the count. Scripts are parsed, never executed.
Quality on the model is the Skill Studio's evaluate step, which runs eval cases with and without the skill.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

try:
    from backend.core.skill_studio import checks
except ImportError:  # run straight from the repository: skills/evaluator/scripts/ is three levels under the root
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
    from backend.core.skill_studio import checks


def evaluate_skill(skill_dir: Path) -> dict:
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")
    found = checks.run(skill_dir)
    total = checks.summary(found)
    return {
        "skill": skill_dir.name,
        "evaluated_at": int(time.time() * 1000),
        "checksPassed": total["passed"],
        "checksTotal": total["total"],
        "verdict": "PASS" if total["all_passed"] else "FAIL",  # a check result, not an approval; a named human approves
        "checks": found,
        "issues": [f"{c['check']}: {c['detail']}" for c in found if not c["passed"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an Agent Skill")
    parser.add_argument("--skill-dir", required=True, help="Path to the skill folder")
    print(json.dumps(evaluate_skill(Path(parser.parse_args().skill_dir)), indent=2))


if __name__ == "__main__":
    sys.exit(main())

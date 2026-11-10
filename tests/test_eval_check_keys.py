"""Every check key used in evals/*.json must be implemented, or the case passes without testing anything."""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

from backend.maf import evals

EVALS = Path(__file__).resolve().parents[1] / "evals"


def test_every_eval_check_key_is_implemented():
    source = inspect.getsource(evals.build_checks)
    supported = set(re.findall(r'rules\.get\("([a-z_]+)"', source)) | set(re.findall(r'"([a-z_]+)" in rules', source))
    used = {(f.name, key) for f in EVALS.glob("*.json") for case in json.loads(f.read_text(encoding="utf-8")) for key in case.get("checks", {})}
    unknown = sorted(f"{name}: {key}" for name, key in used if key not in supported)
    assert supported >= {"contains", "not_contains", "matches"} and not unknown, f"Unsupported eval checks: {unknown}"

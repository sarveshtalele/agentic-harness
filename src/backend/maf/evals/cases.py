"""Where eval cases come from: the agent files, the plugin skills' cases, and the benchmarks with their labelled keys."""
from __future__ import annotations

import json
from pathlib import Path

from backend.config import ROOT
from backend.core import skills as skill_lib

EVALS_DIR = ROOT / "evals"
BENCH_DIR = EVALS_DIR / "benchmarks"


def available() -> list[str]:
    return sorted(p.stem for p in EVALS_DIR.glob("*.json"))


def skill_cases(agent_key: str) -> list[dict]:
    """The plugin eval cases of this agent's skills. A case gets code checks only where `evals/skill-checks.json` has them for that exact query.

    The plugin's expectations are sentences for a human or grader. A case without code checks is listed as needing a grader and is neither passed nor failed.
    """
    overlay = json.loads((EVALS_DIR / "skills" / "checks.json").read_text(encoding="utf-8")) if (EVALS_DIR / "skills" / "checks.json").is_file() else {}
    cases = []
    for name in skill_lib.for_agent(agent_key):
        for number, plugin_case in enumerate(skill_lib.eval_cases(name), 1):
            checks = overlay.get(name, {}).get(plugin_case["query"])
            cases.append({"name": f"{name} #{number}", "category": "skill", "skill": name, "query": plugin_case["query"], "checks": checks,
                          "expected_behavior": plugin_case.get("expected_behavior", [])})
    return cases


def benchmarks() -> list[str]:
    return sorted(p.name for p in BENCH_DIR.iterdir() if (p / "labels.json").is_file()) if BENCH_DIR.is_dir() else []


def _labels(name: str) -> dict:
    return json.loads((BENCH_DIR / name / "labels.json").read_text(encoding="utf-8"))


def _numbered(base: Path, names: list[str]) -> str:
    """Files as the agents receive code: a FILE header and numbered lines."""
    return "\n".join(f"--- FILE {n} ---\n" + "\n".join(f"{i}: {line}" for i, line in enumerate((base / n).read_text(encoding="utf-8").splitlines(), 1)) for n in names)


def bench_cases(agent_key: str, name: str) -> list[dict]:
    """Cases of one benchmark for an agent, with their context built from the benchmark's own files."""
    path = BENCH_DIR / name / "cases" / f"{agent_key}.json"
    if not path.is_file():
        return []
    base = BENCH_DIR / name / "repo"
    cases = []
    for case in json.loads(path.read_text(encoding="utf-8")):
        context = case.get("context") or (_numbered(base, case["context_files"]) if case.get("context_files") else "")
        cases.append({**case, "context": context, "benchmark": name})
    return cases

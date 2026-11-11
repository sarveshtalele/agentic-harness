"""Agent evals on MAF's evaluation API. Each case runs the real active prompt, so prompt versions can be compared."""
from __future__ import annotations

import asyncio
import json

from backend.core import prompts
from backend.db import db, new_id, now, rows
from backend.maf.evals import grader, metrics, ragas_evaluator, store
from backend.maf.evals.aggregate import _aggregate, _ragas
from backend.maf.evals.cases import BENCH_DIR, EVALS_DIR, _labels, _numbered, available, bench_cases, benchmarks, skill_cases
from backend.maf.evals.checks import _last_part, _schemas, _score, build_checks
from backend.maf.evals.runner import EVAL_PROJECT, KEY_METRICS, STORED_TEXT, _find_items, _graded_skill_case, _key_counts, _mutation, _run_case, _sandbox


async def run(agent_key: str, *, benchmark: str = "", repeats: int = 1, ragas: bool = True) -> dict:
    """Run an agent's eval cases, or a benchmark's cases for it. `repeats` runs the whole set again so the spread can be shown; `ragas` adds the model-graded metrics."""
    path = EVALS_DIR / f"{agent_key}.json"
    if not path.exists():
        raise KeyError(f"No eval cases for {agent_key}")
    if benchmark and benchmark not in benchmarks():
        raise KeyError(f"No benchmark {benchmark}")
    _sandbox()
    reviewed = bool(_labels(benchmark).get("reviewed", False)) if benchmark else None
    batch, runs = new_id("bat"), []
    for _ in range(max(1, repeats)):
        cases = bench_cases(agent_key, benchmark) if benchmark else [*json.loads(path.read_text(encoding="utf-8")), *skill_cases(agent_key)]
        results = [await _run_case(agent_key, case) for case in cases]
        scored = [r for r in results if r["passed"] is not None]  # a case that needs a grader is neither passed nor failed
        ref = prompts.ref(agent_key)
        shown = await _ragas(agent_key, results) if ragas else {}
        eval_id = new_id("evl")
        _aggregate(agent_key, ref, results, shown, eval_id=eval_id, batch=batch, benchmark=benchmark, reviewed=reviewed)
        for r in results:
            r.pop("_item", None)
        record = {"id": eval_id, "agent": agent_key, "prompt_ref": ref, "passed": sum(r["passed"] for r in scored), "total": len(scored), "results": json.dumps(results, default=str), "created_at": now()}
        with db() as con:
            con.execute("INSERT INTO evaluations (id, agent, prompt_ref, passed, total, results, created_at) VALUES (:id,:agent,:prompt_ref,:passed,:total,:results,:created_at)", record)
        runs.append({**record, "results": results, "needs_grader": len(results) - len(scored), "tokens": sum(r.get("tokens", 0) for r in results) + sum(v.get("tokens", 0) for v in shown.values())})
    return {**runs[-1], "batch": batch, "repeats": len(runs), "benchmark": benchmark, "labels_reviewed": reviewed, "tokens_total": sum(r["tokens"] for r in runs)}


async def run_all(concurrency: int = 4, ragas: bool = True) -> list[dict]:
    gate = asyncio.Semaphore(concurrency)

    async def one(agent_key: str) -> dict:
        async with gate:
            return await run(agent_key, ragas=ragas)

    return await asyncio.gather(*(one(a) for a in available()))


def history(agent_key: str) -> list[dict]:
    with db() as con:
        items = rows(con.execute("SELECT * FROM evaluations WHERE agent=? ORDER BY rowid DESC LIMIT 20", (agent_key,)))
    return [{**i, "results": json.loads(i["results"])} for i in items]


def cases_worst_first(agent_key: str) -> list[dict]:
    """The cases of the latest run: failed first, then by the lowest score any metric gave."""
    latest = history(agent_key)
    if not latest:
        return []

    def badness(r: dict) -> tuple:
        scores = [v for v in (r.get("ragas") or {}).values()]
        return (r["passed"] is not False, min(scores) if scores else 1.0)

    return sorted(latest[0]["results"], key=badness)


__all__ = ["BENCH_DIR", "EVALS_DIR", "EVAL_PROJECT", "KEY_METRICS", "STORED_TEXT", "_aggregate", "_find_items", "_graded_skill_case", "_key_counts", "_labels", "_last_part", "_mutation", "_numbered", "_ragas",
           "_run_case", "_sandbox", "_schemas", "_score", "available", "bench_cases", "benchmarks", "build_checks", "cases_worst_first", "grader", "history", "metrics", "ragas_evaluator", "run", "run_all", "skill_cases", "store"]

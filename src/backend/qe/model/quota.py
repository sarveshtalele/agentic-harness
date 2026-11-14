"""Coverage checks, plan confidence and case quotas."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from backend.qe.model.domain import states_error


def coverage_gaps(requirements: list[dict], cases: list[dict]) -> list[str]:
    """Each P0/P1 requirement gets 1 Positive and 2 Negative (boundary counts). An Exception case is required only when the requirement states error behaviour."""
    gaps = []
    for requirement in requirements:
        kinds = [c["type"] for c in cases if c["requirement_id"] == requirement["id"]]
        if requirement.get("priority") not in ("P0", "P1"):
            if not kinds:  # a lower priority asks for less, but a requirement with a budget needs at least one case
                gaps.append(f"{requirement['id']}: no case")
            continue
        if "Positive" not in kinds:
            gaps.append(f"{requirement['id']}: no Positive case")
        if sum(k.startswith("Negative") for k in kinds) < 2:
            gaps.append(f"{requirement['id']}: needs 2 Negative cases")
        if "Exception" not in kinds and states_error(requirement):
            gaps.append(f"{requirement['id']}: no Exception case, and the requirement states error behaviour")
    return gaps


def duplicate_scenarios(cases: list[dict]) -> list[str]:
    seen, dupes = set(), []
    for case in cases:
        key = (case["requirement_id"], case["scenario"].strip().lower())
        if key in seen:
            dupes.append(case["id"])
        seen.add(key)
    return dupes


def plan_confidence(requirements: list[dict], plan: dict) -> dict:
    """Deterministic plan score, port of calculate-risk.ts: 100 approved, 70+ revise, lower rejected."""
    mapped = {r for area in plan["areas"] for r in area["requirement_ids"]}
    must = [r["id"] for r in requirements if r.get("priority") in ("P0", "P1")]
    missing = [r for r in must if r not in mapped]
    unknown = [r for r in mapped if r not in {x["id"] for x in requirements}]
    levels = {a["level"] for a in plan["areas"]} | set(plan.get("skipped_levels", {}))
    missing_levels = sorted({"Unit", "Integration", "E2E"} - levels)
    score = 100 - 40 * (len(missing) > 0) - min(30, 5 * len(missing)) - 15 * len(missing_levels) - 10 * (len(unknown) > 0)
    score = max(score, 0)
    verdict = "APPROVED" if score == 100 else "REVISE" if score >= 70 else "REJECTED"
    issues = [f"Requirement not planned: {r}" for r in missing] + [f"Level without area or reason: {l}" for l in missing_levels] + [f"Unknown requirement: {r}" for r in unknown]
    return {"score": score, "verdict": verdict, "issues": issues}


class ExecutionSummary(BaseModel):
    """What the qa-execution-engineer says about a run. Code compares every number and the verdict with the JUnit counts before it is shown."""
    summary: str = Field(min_length=1, max_length=1500)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    verdict: Literal["PASS", "FAIL", "INCONCLUSIVE"]


PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}


def limit_cases(cases: list[dict], requirements: list[dict], limit: int) -> tuple[list[dict], dict]:
    """Keeps at most `limit` cases, by the priority of the requirement each covers: every P0 case, then P1, then the rest, each in its order.

    P0 cases are never cut, so the result can exceed the limit, and the report says so. Nothing is dropped without being named.
    """
    priority = {r["id"]: r.get("priority", "P1") for r in requirements}
    of = lambda c: priority.get(c["requirement_id"], "P2")
    order = sorted(range(len(cases)), key=lambda i: (PRIORITY_RANK.get(of(cases[i]), 2), cases[i].get("priority", "P2"), i))
    p0 = sum(of(c) == "P0" for c in cases)
    first = {}
    for i, c in enumerate(cases):
        first.setdefault(c["requirement_id"], i)
    # the limit never takes a requirement's last case: that would open a coverage gap the plan and the plugin check depend on
    keep = set(order[: max(limit, p0)]) | set(first.values())
    kept = [c for i, c in enumerate(cases) if i in keep]
    left = [c for i, c in enumerate(cases) if i not in keep]
    by_priority: dict[str, int] = {}
    for c in left:
        by_priority[of(c)] = by_priority.get(of(c), 0) + 1
    uncovered = [r["id"] for r in requirements if r["id"] not in {c["requirement_id"] for c in kept}]
    note = f"{len(left)} cases left out by the limit of {limit} (ATLAS_MAX_CASES)" if left else f"No cases left out (limit {limit})"
    return kept, {"limit": limit, "total": len(cases), "kept": len(kept), "left_out_count": len(left), "left_out": [c["id"] for c in left], "left_out_by_priority": by_priority,
                  "p0_over_limit": p0 > limit, "requirements_without_cases": uncovered, "message": note + ("; P0 cases are never cut, so the limit was exceeded" if p0 > limit else "")}


FULL_QUOTA = 4  # P0 and P1: 1 Positive, 2 Negative, and 1 Exception when the requirement states error behaviour, else a third Negative


def case_quota(requirements: list[dict], limit: int, planned_ids: set[str] | frozenset = frozenset()) -> dict:
    """The case budget, decided before any design call. Returns `quota` (requirement id to "at most N cases"), the requirements left out, and the message for the gate.

    P0 and P1 get 4 each and are designed even when that passes the limit. The remaining budget goes to the others: 2 each, else 1 each, else 1 for the first ones that fit.
    """
    high = [r["id"] for r in requirements if r.get("priority", "P1") in ("P0", "P1")]
    low = [r["id"] for r in requirements if r.get("priority", "P1") not in ("P0", "P1")]
    quota = {i: FULL_QUOTA for i in high}
    room = max(limit - FULL_QUOTA * len(high), 0)
    each = 2 if room >= 2 * len(low) else 1
    quota |= {i: each for i in low[:room // each]}
    # a requirement the plan gives a scenario gets at least one case: a planned scenario with no case fails the plugin's Gate 3
    quota |= {i: 1 for i in low if i not in quota and i in planned_ids}
    left = [i for i in low if i not in quota]
    planned = sum(quota.values())
    over = FULL_QUOTA * len(high) > limit
    message = f"Case budget {planned} of {limit} (ATLAS_MAX_CASES), decided before design" + ("; P0 and P1 need more than the limit, so the limit is exceeded for them" if over else "")
    if left:
        message += f"; {len(left)} lower-priority requirements get no cases: {', '.join(left)}"
    return {"limit": limit, "quota": quota, "planned": planned, "left_out_requirements": left, "p0_over_limit": over, "message": message}


def apply_quota(cases: list[dict], quota: dict[str, int], requirements: list[dict] = ()) -> tuple[list[dict], list[dict]]:
    """Keeps at most the quota of cases per requirement, in order. The required kinds are kept first, so a cut never opens a coverage gap:
    1 Positive, 2 Negative and 1 Exception for a requirement that states error behaviour, else 1 Positive and 3 Negative. Returns (kept, dropped)."""
    errors = {r["id"] for r in requirements if states_error(r)}
    kind = lambda c: "Negative" if c["type"].startswith("Negative") else c["type"]
    keep: set[int] = set()
    for req in {c["requirement_id"] for c in cases}:
        idx = [i for i, c in enumerate(cases) if c["requirement_id"] == req]
        left = {"Positive": 1, "Negative": 2, "Exception": 1} if req in errors else {"Positive": 1, "Negative": 3}
        chosen = []
        for i in idx:
            if left.get(kind(cases[i]), 0) > 0 and len(chosen) < quota.get(req, 0):
                left[kind(cases[i])] -= 1
                chosen.append(i)
        chosen += [i for i in idx if i not in chosen][: max(quota.get(req, 0) - len(chosen), 0)]
        keep |= set(chosen)
    return [c for i, c in enumerate(cases) if i in keep], [c for i, c in enumerate(cases) if i not in keep]

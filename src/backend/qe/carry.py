"""Carry-forward hook: pure checks that what an earlier stage produced reaches the next stage exactly, complete, and uninvented.

No model calls. `before` compares inputs with the snapshot taken at the last approved gate; `after` compares a stage's
output with its input. Messages say what is wrong, where, and how to fix it, because they are fed back to the model.
"""
from __future__ import annotations

import hashlib
import json

FIELDS = {
    "req": ("id", "statement", "priority", "file", "line", "quote"),
    "scn": ("id", "level", "requirement_ids"),
    "case": ("id", "requirement_id", "scenario", "level", "steps", "expected_result", "test_data"),
    "test": ("case_id", "path"),
}
NAMES = {"req": "requirement", "scn": "plan scenario", "case": "case", "test": "test"}
# the stage that fixed each kind (for messages), and the kinds a stage only reads (an approved item must not change under it)
GATE = {"req": 1, "scn": 2, "case": 3, "test": 4}
READS = {
    "plan": ("req",), "design": ("req", "scn"), "data": ("req", "scn", "case"), "generate": ("req", "scn", "case"),
    "prepare": ("req", "scn", "case", "test"), "execute": ("req", "scn", "case", "test"), "heal": ("req", "scn", "case", "test"),
    "trace": ("req", "scn", "case", "test"), "sign": ("req", "scn", "case", "test"),
}
# upstream kind, downstream kind a stage must cover; the stage's own reason fields excuse what it leaves out
COVERS = {"plan": ("req", "scn"), "design": ("req", "case"), "generate": ("case", "test")}


def _hash(kind: str, item: dict) -> str:
    return hashlib.sha256(json.dumps({f: item.get(f) for f in FIELDS[kind]}, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def items(state: dict) -> dict[str, dict[str, dict]]:
    """{kind: {id: item}} for whatever the state holds."""
    plan = state.get("plan") or {}
    found = {"req": {r["id"]: r for r in state.get("requirements") or []},
             "scn": {a["id"]: a for a in plan.get("areas") or []},
             "case": {c["id"]: c for c in state.get("cases") or []},
             "test": {t["case_id"]: t for t in state.get("tests") or []}}
    return {k: v for k, v in found.items() if v}


def snapshot(state: dict) -> dict[str, dict[str, str]]:
    return {k: {i: _hash(k, x) for i, x in v.items()} for k, v in items(state).items()}


def digest(snap: dict) -> dict[str, str]:
    return {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for k, v in snap.items()}


def _differ(kind: str, old: dict, new: dict) -> str:
    fields = [f for f in FIELDS[kind] if old.get(f) != new.get(f)]
    return ", ".join(fields) or "content"


def _changes(old: dict[str, dict], new: dict[str, dict], kinds, where: str) -> tuple[list[str], dict]:
    """Per-kind: ids that changed or vanished between two item maps."""
    bad, changed, dropped = [], 0, 0
    for kind in kinds:
        for i, was in old.get(kind, {}).items():
            now = new.get(kind, {}).get(i)
            if now is None:
                dropped += 1
                bad.append(f"{NAMES[kind]} {i} is missing {where}. Restore it exactly as approved at Gate {GATE[kind]}.")
            elif _hash(kind, was) != _hash(kind, now):
                changed += 1
                bad.append(f"{i} changed {where} ({_differ(kind, was, now)}). Keep every approved field exactly as at Gate {GATE[kind]}.")
    return bad, {"changed": changed, "dropped": dropped}


def before(stage: str, state: dict) -> list[str]:
    """Inputs must still equal the snapshot of the last approved gate."""
    approved = (state.get("trace") or {}).get("approved") or {}
    have = items(state)
    bad = []
    for kind in READS.get(stage, ()):
        for i, h in (approved.get(kind) or {}).items():
            item = have.get(kind, {}).get(i)
            if item is None:
                bad.append(f"{NAMES[kind]} {i} is missing before {stage} (approved at Gate {GATE[kind]}).")
            elif _hash(kind, item) != h:
                bad.append(f"{i} changed after Gate {GATE[kind]}: its fields no longer match the approved snapshot. Restore the approved text.")
    return bad


def _excused(stage: str, state: dict) -> set[str]:
    """Upstream ids the stage names with a reason of its own: case budget, partial result, tests it could not write."""
    missing = set((state.get("partial") or {}).get("missing") or [])
    if stage == "plan":  # the plugin's Gate 2 rule: P0 and P1 must be planned; a lower priority may be left out, and is counted as such
        missing |= {r["id"] for r in state.get("requirements") or [] if r.get("priority") not in ("P0", "P1")}
    if stage == "design":
        limit = state.get("case_limit") or {}
        if limit.get("notice"):
            missing |= set(limit.get("requirements_without_cases") or []) | set(limit.get("left_out_requirements") or [])
        missing |= {d.get("requirement_id") for d in limit.get("dropped_over_quota") or []}
    if stage == "generate":
        missing |= set(state.get("tests_missing") or [])
    return missing


def after(stage: str, old: dict, new: dict) -> tuple[list[str], dict]:
    """Carried exactly, complete, no invention. Returns (violations, report)."""
    was, now = items(old), items(new)
    regenerated = {"requirements": ("req",), "plan": ("scn",), "design": ("case",), "generate": ("test",)}.get(stage, ())
    upstream = [k for k in was if k not in regenerated]
    bad, counts = _changes(was, now, upstream, f"by {stage}")
    total = sum(len(was[k]) for k in upstream)
    report = {"stage": stage, "upstream": total, "carried": total - counts["changed"] - counts["dropped"], "changed": counts["changed"],
              "dropped_with_reason": 0, "dropped_without_reason": counts["dropped"], "new": 0}
    if stage in COVERS:
        up, down = COVERS[stage]
        have, excuse = now.get(up, {}), _excused(stage, new)
        link = {"plan": lambda i, a: a["requirement_ids"], "design": lambda i, c: [c["requirement_id"]], "generate": lambda i, t: [t["case_id"]]}[stage]
        covered = {x for i, d in now.get(down, {}).items() for x in link(i, d)}
        for i in have:
            if i in covered:
                continue
            if i in excuse:
                report["dropped_with_reason"] += 1
            else:
                report["dropped_without_reason"] += 1
                bad.append(f"{NAMES[up]} {i} has no {NAMES[down]} in {stage} and no written reason. Add one for it, or name it with a reason.")
        for i, d in now.get(down, {}).items():
            for x in link(i, d):
                if x not in have:
                    bad.append(f"{NAMES[down]} {i} names {NAMES[up]} {x}, which does not exist. Use only ids from the approved {NAMES[up]}s: {', '.join(sorted(have)) or 'none'}.")
        report["new"] = len([i for i in now.get(down, {}) if i not in was.get(down, {})])
    report["verdict"] = "BLOCKED" if bad else "PASS"
    return bad, report


def summary(report: dict) -> str:
    """One sentence for a gate card."""
    return (f"Trace: {report['upstream']} upstream items carried {report['carried']}, {report['changed']} changed, "
            f"{report['dropped_with_reason']} dropped with reason, {report['dropped_without_reason']} dropped without reason, {report['new']} new.")


def record(project_id: str, stage: str, report: dict, state: dict) -> None:
    from backend.core import ledger
    ledger.append(project_id, "engine", "trace.check", stage, {**report, "hashes": digest(snapshot(state))})


def approved(project_id: str, stage: str, state: dict) -> dict:
    """Snapshot at an approved gate: written to docs/qe/<app>/trace/<stage>.json and the ledger. Returns the snapshot."""
    from backend.core import ledger
    from backend.qe import plugin_bridge
    snap = snapshot(state)
    plugin_bridge.write(project_id, plugin_bridge.app_name(project_id), f"trace/{stage}.json", {"stage": stage, "snapshot": snap, "last_check": (state.get("trace") or {}).get("last")})
    ledger.append(project_id, "engine", "trace.approved", stage, {"hashes": digest(snap), "counts": {k: len(v) for k, v in snap.items()}})
    return snap

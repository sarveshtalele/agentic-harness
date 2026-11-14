"""Validity checks V3 to V6 at the end of Generate: check every test, send each failure back once, re-check, write the plugin manifest."""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from backend.config import project_dir
from backend.maf.workflows.edits import Edit, apply_edits
from backend.maf.workflows.qe.generate.env import Env
from backend.maf.workflows.qe.generate.files import GeneratedFile, GeneratedSuite
from backend.maf.workflows.qe.generate.repair import repair_static
from backend.qe import plugin_bridge, validity

PARALLEL = 4  # collect runs one Python process per file


def _key(item: GeneratedFile) -> str:
    return item.path + hashlib.sha256(item.content.encode("utf-8")).hexdigest()


def _check(env: Env, item: GeneratedFile, case_of: dict) -> dict:
    quotes = {r["id"]: r.get("quote") or "" for r in env.state["requirements"]}
    return validity.check_file(env.worktree, item.path, item.content, item.case_ids, case_of, inventory=env.inventory, allowed=env.allowed, async_ok=env.async_ok, quotes=quotes)


async def _check_all(env: Env, suite: GeneratedSuite, case_of: dict, cache: dict) -> None:
    """Fills the cache for every file whose content has not been checked. Files on disk must match the suite."""
    gate = asyncio.Semaphore(PARALLEL)

    async def one(item: GeneratedFile) -> None:
        async with gate:
            cache[_key(item)] = await asyncio.to_thread(_check, env, item, case_of)

    await asyncio.gather(*(one(f) for f in suite.files if _key(f) not in cache))


def _rows(suite: GeneratedSuite, cache: dict, v1: dict) -> dict:
    return validity.tally([{"path": f.path, "case_id": f.case_ids[0], "checks": {"V1": v1.get(f.path, {"status": "NOT CHECKED", "message": "not audited"}), **cache[_key(f)]}} for f in suite.files])


def _write(env: Env, items: list[GeneratedFile]) -> None:
    apply_edits(env.worktree, [Edit(path=f.path, action="create", content=f.content) for f in items])


async def validate(env: Env, suite: GeneratedSuite, case_of: dict) -> dict:
    """First pass: check, send each failing file back once, leave the best version of every file on disk. Returns the check cache."""
    cache: dict = {}
    await _check_all(env, suite, case_of, cache)
    failing = [f for f in suite.files if validity.problems(cache[_key(f)])]
    if failing:
        def check(item: GeneratedFile) -> list[str]:
            _write(env, [item])  # collect reads the file from disk
            return validity.problems(_check(env, item, case_of))

        await repair_static(env, suite, case_of, check, "validity checks (V3 to V6)")
        _write(env, suite.files)  # a rewrite the checks did not accept must not stay on disk
        await _check_all(env, suite, case_of, cache)
    return cache



def write_records(env: Env, suite: GeneratedSuite, records: list[dict], audit: dict) -> None:
    """The plugin's 05-generation/confidence.json and audit.json, stamped as recorded from the agents' own checked answers."""
    rc, app = env.rc, plugin_bridge.app_name(env.rc.project_id)
    reviewed = [r for r in records if r.get("verdict") != "NOT RUN"]
    given = [{**audit["verdicts"][c], "id": c} for f in suite.files for c in f.case_ids if c in audit["verdicts"]]
    plugin_bridge.write(rc.project_id, app, "05-generation/confidence.json", plugin_bridge.recorded("confidence-reviewer", f"{rc.run_id}:code", "code", "items", reviewed))
    plugin_bridge.write(rc.project_id, app, "05-generation/audit.json", plugin_bridge.recorded("coverage-auditor", f"{rc.run_id}:code", "code", "verdicts", given))


async def finish(env: Env, suite: GeneratedSuite, case_of: dict, cache: dict, audit: dict, records: list[dict]) -> dict:
    """After the review: re-check any file it rewrote, write the plugin's manifest, code review and code audit records, run the plugin's Gate 4 check, and return state["validation"]."""
    rc, worktree = env.rc, env.worktree
    await _check_all(env, suite, case_of, cache)
    validation = _rows(suite, cache, audit["v1"])
    validation["audit"] = {k: audit[k] for k in ("first", "now", "regenerated")}
    app = plugin_bridge.app_name(rc.project_id)
    base = worktree.relative_to(project_dir(rc.project_id)).as_posix() if worktree.is_relative_to(project_dir(rc.project_id)) else ""
    manifest = {"files": [{"path": f"{base}/{f.path}".lstrip("/"), "caseIds": f.case_ids} for f in suite.files]}
    plugin_bridge.write(rc.project_id, app, "05-generation/manifest.json", manifest)
    write_records(env, suite, records, audit)
    validation["plugin_check"] = await asyncio.to_thread(plugin_bridge.check_gate, rc.project_id, app, 4)
    rc.log(f"[VALIDITY] {validity.line(validation)}", {"counts": validation["counts"], "invalid": validation["invalid"][:20]}, "review" if validation["invalid"] else "log")
    return validation

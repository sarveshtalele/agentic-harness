"""Stored skill plans: a draft the user edits, then an approval that fixes its SHA-256, then a generated draft folder."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from backend import config
from backend.core import ledger
from backend.core.security import redact, safe_path, sha256
from backend.core.skill_studio.models import SkillPlan
from backend.db import db, new_id, now, row


class PlanStateError(ValueError):
    """The plan is not in the state this step needs. Answered 409."""


def canonical(plan: dict) -> str:
    return json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def drafts_root() -> Path:
    return config.DATA_DIR / "skill_drafts"


def draft_dir(plan: dict) -> Path:
    """DATA_DIR/skill_drafts/<plan_id>/<name>/: the folder is named after the skill, as MAF and the name check need."""
    return safe_path(drafts_root(), f"{plan['id']}/{plan['plan']['name']}")


def _public(found: dict) -> dict:
    out = {k: v for k, v in found.items() if k not in ("plan_json", "checks_json", "source_text")}
    return {**out, "plan": json.loads(found["plan_json"]), "checks": json.loads(found["checks_json"]) if found["checks_json"] else [],
            "source_chars": len(found["source_text"])}


def get(plan_id: str, *, with_source: bool = False) -> dict:
    with db() as con:
        found = row(con.execute("SELECT * FROM skill_plans WHERE id=?", (plan_id,)))
    if not found:
        raise KeyError(f"skill plan {plan_id}")
    return {**_public(found), **({"source_text": found["source_text"]} if with_source else {})}


def create(project_id: str, author: str, kind: str, request: str, source: dict, plan: SkillPlan, prompt_ref: str, revise: str = "") -> dict:
    plan_id = new_id("spl")
    with db() as con:
        con.execute("INSERT INTO skill_plans (id, project_id, author, kind, request, source_type, source_ref, source_text, source_sha256, revise, plan_json, prompt_ref, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (plan_id, project_id, author, kind, redact(request), source["type"], source.get("ref", ""), source["text"], source["sha256"], revise,
                     canonical(plan.model_dump()), prompt_ref, now()))
    ledger.append(project_id, author, "skill.plan.created", plan_id, {"kind": kind, "name": plan.name, "source_sha256": source["sha256"], "prompt_ref": prompt_ref})
    return get(plan_id)


def update(plan_id: str, plan: SkillPlan, by: str) -> dict:
    current = get(plan_id)
    if current["status"] != "draft":
        raise PlanStateError("Only a draft plan can be edited. This one is approved; start a new plan to change it.")
    with db() as con:
        con.execute("UPDATE skill_plans SET plan_json=? WHERE id=? AND status='draft'", (canonical(plan.model_dump()), plan_id))
    ledger.append(current["project_id"], by, "skill.plan.edited", plan_id, {"name": plan.name})
    return get(plan_id)


def approve(plan_id: str, by: str) -> dict:
    current = get(plan_id)
    if current["status"] != "draft":
        raise PlanStateError(f"This plan is already {current['status']}.")
    digest, stamp = sha256(canonical(current["plan"])), now()
    with db() as con:
        con.execute("UPDATE skill_plans SET status='approved', plan_sha256=?, approved_by=?, approved_at=? WHERE id=? AND status='draft'", (digest, by, stamp, plan_id))
    ledger.append(current["project_id"], by, "skill.plan.approved", plan_id, {"plan_sha256": digest, "name": current["plan"]["name"]})
    return get(plan_id)


def require_approved(plan_id: str) -> dict:
    """The approved plan, only while its stored JSON still hashes to the approved SHA-256."""
    current = get(plan_id, with_source=True)
    if current["status"] not in ("approved", "generated") or not current["plan_sha256"]:
        raise PlanStateError("Approve the plan before generating the skill.")
    with db() as con:
        stored = con.execute("SELECT plan_json FROM skill_plans WHERE id=?", (plan_id,)).fetchone()[0]
    if sha256(canonical(json.loads(stored))) != current["plan_sha256"]:
        raise PlanStateError("The stored plan no longer matches the approved SHA-256. Nothing was generated; approve a new plan.")
    return current


def write_draft(plan: dict, files: list[dict]) -> Path:
    """Replace the draft folder with exactly these files. Every path goes through safe_path."""
    folder = draft_dir(plan)
    if folder.exists():
        shutil.rmtree(folder)  # the app's own draft for this plan, rebuilt from the model's files
    folder.mkdir(parents=True)
    for item in files:
        target = safe_path(folder, item["path"], for_write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")
    return folder


def mark_generated(plan: dict, draft_sha: str, checks: list[dict], by: str) -> dict:
    with db() as con:
        con.execute("UPDATE skill_plans SET status='generated', draft_sha256=?, checks_json=?, generated_at=? WHERE id=?", (draft_sha, json.dumps(checks), now(), plan["id"]))
    ledger.append(plan["project_id"], by, "skill.generated", plan["id"], {"draft_sha256": draft_sha, "checks_passed": sum(c["passed"] for c in checks), "checks_total": len(checks)})
    return get(plan["id"])


def require_generated(plan_id: str) -> tuple[dict, Path]:
    """The generated plan and its draft folder, refused when the folder changed since generation."""
    from backend.core.skill_studio.checks import digest, read_files

    current = require_approved(plan_id)
    if current["status"] != "generated":
        raise PlanStateError("Generate the skill first.")
    folder = draft_dir(current)
    if not folder.is_dir() or digest(read_files(folder)) != current["draft_sha256"]:
        raise PlanStateError("The draft folder changed after generation. Generate the skill again.")
    return current, folder

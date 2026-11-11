"""The Studio steps that combine a model call with server checks: generate, try on a sample, and evaluate with and without the skill."""
from __future__ import annotations

from backend.core import ledger
from backend.core.skill_studio import access, author, checks, plans, testing, versions
from backend.core.skill_studio import source as sources


async def propose(project_id: str, kind: str, request: str, source: dict, revise: str = "") -> dict:
    """A draft plan as the signed-in user. POST /api/skill-studio/plans and the harness create_skill tool both call this.
    It never approves: a human approves the draft in the Studio."""
    user = access.author()
    access.project(project_id, write=True)
    if revise and (revise in versions.CORE_SYSTEM_SKILLS or revise not in author._skill_names()):
        raise plans.PlanStateError(f"{revise} is not a skill the Studio can revise")
    found = sources.resolve(source)  # an unseen document raises KeyError, answered 404
    plan, ref = await author.propose_plan(project_id, kind, request, found, revise)
    return plans.create(project_id, user["id"], kind, request, found, plan, ref, revise)


async def generate(plan_id: str, by: str) -> dict:
    plan = plans.require_approved(plan_id)
    files = await author.write_files(plan, by)
    folder = plans.write_draft(plan, files)
    found = checks.run(folder)
    stored = plans.mark_generated(plan, checks.digest(checks.read_files(folder)), found, by)
    return {"plan": stored, "files": files, "checks": found, "summary": checks.summary(found)}


async def try_sample(plan_id: str, sample: str) -> dict:
    plan, folder = plans.require_generated(plan_id)
    files = checks.read_files(folder)
    result = await author.apply(plan["project_id"], sample, skill=author.skill_text(files, plan["plan"]["name"]))
    return {**result, "draft_sha256": plan["draft_sha256"]}


async def evaluate(plan_id: str, by: str) -> dict:
    """Each eval case runs twice on the model. Deterministic assertions grade both outputs; no model grades anything."""
    from backend.maf.evals import store  # late: maf imports core

    plan, folder = plans.require_generated(plan_id)
    name, cases = plan["plan"]["name"], plan["plan"]["eval_cases"]
    skill = author.skill_text(checks.read_files(folder), name)
    details, with_skill, without_skill, tokens = [], [], [], 0
    for number, case in enumerate(cases, 1):
        used = await author.apply(plan["project_id"], case["input"], skill=skill)
        base = await author.apply(plan["project_id"], case["input"], description=plan["plan"]["description"])
        graded_with, graded_without = testing.grade(used["output"], case["assertions"]), testing.grade(base["output"], case["assertions"])
        with_skill.append(graded_with)
        without_skill.append(graded_without)
        tokens += sum(r["tokens_in"] + r["tokens_out"] for r in (used, base))
        details.append({"case": number, "input": case["input"], "with_skill": {"output": used["output"], "assertions": graded_with},
                        "without_skill": {"output": base["output"], "assertions": graded_without}})
    rates = {"assertion_pass_rate_with_skill": testing.rate(with_skill), "assertion_pass_rate_without_skill": testing.rate(without_skill)}
    rates["skill_uplift"] = rates["assertion_pass_rate_with_skill"] - rates["assertion_pass_rate_without_skill"]
    ref = f"{plan['prompt_ref']}+draft:{plan['draft_sha256'][:12]}"
    for metric, value in rates.items():
        store.record(f"skill:{name}", ref, metric, value=value, n=len(cases), judge_model="deterministic-assertions", source="skill-studio",
                     tokens=tokens, detail=details if metric == "skill_uplift" else None)
    ledger.append(plan["project_id"], by, "skill.evaluated", plan_id, {"prompt_ref": ref, **rates, "n": len(cases)})
    return {"prompt_ref": ref, "n": len(cases), "judge_model": "deterministic-assertions", "metrics": rates, "tokens": tokens, "cases": details}

"""QE Workflow Definition: Autonomous Quality Engineering & AI SDLC Lifecycle Definition."""
from __future__ import annotations

from backend.core.errors import RepoError
from backend.maf.engine import Definition, REGISTRY, RunContext, StageSpec
from backend.maf.workflows.qe.common import (
    _doc_gate,
    _gate3_extras,
    _gate4_extras,
    _gate5_extras,
    _gate5_text,
    qe_commit,
)
from backend.maf.workflows.qe.data import qe_data
from backend.maf.workflows.qe.design import qe_design
from backend.maf.workflows.qe.discover import qe_discover
from backend.maf.workflows.qe.execute import qe_execute
from backend.maf.workflows.qe.generate import qe_generate
from backend.maf.workflows.qe.heal import qe_heal
from backend.maf.workflows.qe.plan import qe_plan
from backend.maf.workflows.qe.prepare import qe_prepare
from backend.maf.workflows.qe.requirements import qe_requirements
from backend.maf.workflows.qe.sign import qe_sign
from backend.maf.workflows.qe.trace import qe_trace
from backend.maf.workflows.shared import intake, intake_gate
from backend.qe import carry, validity
from backend.rag import store


async def qe_intake(rc: RunContext, state: dict) -> dict:
    """Intake that stops before Gate 0, and before any model call, when there is no code to test. A spec-first run ({"spec_first": true}) keeps the greenfield path: requirements from approved documents and a RED baseline."""
    update = await intake(rc, state)
    if update["mode"] == "brownfield":
        update["install_deps"] = True  # Gate 0's card says approving it lets the installers run, to collect and compile the tests; no test body runs
    if update["mode"] == "greenfield" and not state.get("spec_first") and not store.sources(rc.project_id):  # uploaded documents are enough: the code does not exist yet
        rc.log("No code to test: the repository has no source files. The QE run stops before Gate 0", kind="warning")
        raise RepoError("No code to test: this project's repository has no source files, so there is nothing to design, generate or run tests against.",
                        action='Upload or connect the code, then start the QE run again. To write failing tests before the code exists, upload the requirement documents (BRD, PRD, stories) on the Documents page, or start it with input {"spec_first": true} to use approved BA documents.')
    return update


def _plugin_line(check: dict | None, gate: int = 1) -> str:
    if not check or check.get("ok") is None:
        return f"agentic-qe Gate {gate} check not applied ({check['error']})." if check else ""
    if check.get("error"):
        return f"agentic-qe Gate {gate} check could not run: {check['error']}."
    return f"agentic-qe Gate {gate} check: PASS." if check["ok"] else f"agentic-qe Gate {gate} check: FAIL ({'; '.join(check['gaps'][:3])})."


def _run_note(state: dict) -> str:
    """Greenfield tests run here after Gate 4. Brownfield tests never run here: the team downloads them at Gate 5."""
    return "" if state.get("mode") == "brownfield" else f" Approving also allows them to run on this machine.{_deps_line(state)}"


def _deps_line(state: dict) -> str:
    missing = state.get("missing_deps") or []
    if not missing:
        return ""
    return (f" WARNING: {len(missing)} packages the repository declares are not installed ({', '.join(missing[:8])}), and this run "
            "was started without installing dependencies, so tests that import them will fail as environment. Start a new run "
            "with Install dependencies on to execute them.")


def qe_definition() -> Definition:
    """End-to-end quality engineering lifecycle: requirements to signed release, with human gates G0 to G5."""
    return Definition("qe", [
        StageSpec("intake", qe_intake, "Intake", approval=intake_gate, next="discover"),
        StageSpec("discover", qe_discover, "Discovery", next="requirements"),
        StageSpec("requirements", qe_requirements, "Requirements", guard=carry, approval=_doc_gate(1, "requirements", "requirements_doc", lambda s: f"{len(s['requirements'])} requirements with verified evidence. {_plugin_line(s.get('plugin_check'))}", "requirements_review", lambda rc, s: {"plugin_check": s.get("plugin_check")}), on_rejected="requirements", next="plan"),
        StageSpec("plan", qe_plan, "Test plan", guard=carry, approval=_doc_gate(2, "test plan", "plan_doc", lambda s: f"Deterministic score {s['plan_score']['score']}, independent review {s['plan_review']['score'] if s['plan_review']['score'] is not None else 'not run'} ({s['plan_review']['verdict']}). {_plugin_line(s.get('plan_plugin_check'), 2)}", "plan_review", lambda rc, s: {"plugin_check": s.get("plan_plugin_check")}), on_rejected="plan", next="design"),
        StageSpec("design", qe_design, "Test design", guard=carry, next="data"),
        StageSpec("data", qe_data, "Test data", guard=carry, approval=_doc_gate(3, "test design and data", "cases_doc", lambda s: f"{len(s['cases'])} cases. {s['case_limit']['message']}. Remaining gaps: {s['design_gaps'] or 'none'}. {_plugin_line(s.get('design_plugin_check'), 3)}", "cases_review", lambda rc, s: _gate3_extras(rc, s) | {"plugin_check": s.get("design_plugin_check"), "design_audit": s.get("design_audit")}), on_rejected="design", next="generate"),
        StageSpec("generate", qe_generate, "Generate tests", guard=carry, approval=_doc_gate(4, "generated tests", "test_doc", lambda s: f"{len(s['tests'])} of {len(s['cases'])} cases have tests, on branch {s['branch']}. {validity.line(s.get('validation'))}{_run_note(s)}", "tests_review", _gate4_extras), on_approved=qe_commit, on_rejected="generate", next="prepare"),
        StageSpec("prepare", qe_prepare, "Prepare environment", guard=carry, next="execute"),
        StageSpec("execute", qe_execute, "Execute", guard=carry),
        StageSpec("heal", qe_heal, "Heal test drift", guard=carry),
        StageSpec("trace", qe_trace, "Traceability", guard=carry),
        StageSpec("sign", qe_sign, "Release sign-off", guard=carry, approval=_doc_gate(5, "release", "release_doc", _gate5_text, "tests_review_after", _gate5_extras), next="END"),
    ], routes={"generate": ["trace"], "execute": ["heal", "trace"], "heal": ["execute", "trace"], "trace": ["sign"]})


REGISTRY["qe"] = qe_definition

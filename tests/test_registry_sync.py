"""Phase R registry sync: every row comes from a real source, links are derived from code, and two syncs give one hash."""
import json

from backend.config import ROOT
from backend.core import registry
from backend.core.registry import store
from backend.core.registry.code_sources import TOOLS_DIR
from backend.maf.agents import POLICIES

QE_STAGES = {"discover": "repo-intelligence-analyst", "requirements": "requirements-analyst", "plan": "principal-test-architect",
             "design": "test-design-architect", "generate": "test-automation-engineer", "execute": "qa-execution-engineer",
             "heal": "defect-diagnostician", "sign": "confidence-reviewer"}


def _synced():
    registry.sync()
    caps = {c["id"]: c for c in store.capabilities()}
    by = {(c["kind"], c["qualified_name"]): c for c in caps.values()}
    links = {(caps[l["from_id"]]["qualified_name"], l["relation"], caps[l["to_id"]]["qualified_name"]) for l in store.links()}
    return caps, by, links


def test_sync_finds_every_tool_file_agent_and_workflow_with_its_stages():
    caps, by, links = _synced()
    sources = {c["source"] for c in caps.values() if c["kind"] == "tool"}
    tool_files = [p for p in sorted(TOOLS_DIR.glob("*.py")) if "@tool(" in p.read_text(encoding="utf-8")]
    assert tool_files and all(p.relative_to(ROOT).as_posix() in sources for p in tool_files)
    assert by[("tool", "run_tests")]["needs_approval"] and not by[("tool", "grep")]["needs_approval"]
    assert {"todos_add", "mode_set", "load_skill", "run_shell"} <= {c["name"] for c in caps.values() if c["kind"] == "tool"}
    assert all(("agent", key) in by for key in POLICIES)
    assert {c["name"] for c in caps.values() if c["kind"] == "workflow"} == {"ba", "qe", "bug_scan", "change"}
    for stage, agent in QE_STAGES.items():
        assert ("qe", "contains", f"qe.{stage}") in links
        assert (f"qe.{stage}", "performed_by", agent) in links
    assert ("qe.plan", "gates", "G2") in links and ("ba.gherkin", "gates", "G1") in links and ("qe.intake", "gates", "G0") in links
    assert ("principal-test-architect", "uses_tool", "grep") in links
    assert ("principal-test-architect", "applies_skill", "local-skills:planning-tests") in links
    assert ("harness", "delegates_to", "confidence-reviewer") in links


def test_sync_reads_the_agentic_qe_plugin_commands_agents_hooks_and_scripts():
    caps, by, links = _synced()
    plugin = ROOT / "plugins" / "agentic-qe"
    commands = {c["qualified_name"] for c in caps.values() if c["kind"] == "command" and c["plugin"] == "agentic-qe"}
    assert "agentic-qe:qe-plan" in commands and len(commands) == len(list((plugin / "skills").glob("qe-*/SKILL.md")))
    agents = {c["qualified_name"] for c in caps.values() if c["kind"] == "agent" and c["plugin"] == "agentic-qe"}
    assert agents == {f"agentic-qe:{p.stem}" for p in (plugin / "agents").glob("*.md")}
    declared = json.loads((plugin / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    hooks = [c for c in caps.values() if c["kind"] == "hook" and c["plugin"] == "agentic-qe"]
    assert len(hooks) == sum(len(groups) for groups in declared.values())
    assert ("agentic-qe", "contains", "agentic-qe:qe-plan") in links
    assert ("agentic-qe:qe-plan", "applies_skill", "agentic-qe:planning-tests") in links
    assert ("agentic-qe:planning-tests", "runs_script", "agentic-qe:skills/planning-tests/scripts/calculate-risk.ts") in links
    assert all((ROOT / c["source"]).is_file() for c in caps.values() if c["kind"] == "script")
    assert all(len(c["sha256"]) == 64 for c in caps.values())


def test_two_syncs_give_the_same_version_hash():
    first, second = registry.sync(), registry.sync()
    assert first["hash"] == second["hash"] and first["id"] < second["id"]
    assert registry.latest()["hash"] == first["hash"]

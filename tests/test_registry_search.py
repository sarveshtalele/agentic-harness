"""Phase R harness search: BM25 over the visible registry, describe with links, and the compact index."""
from backend.core import registry
from backend.core.registry.search import bm25, words


def test_bm25_ranks_the_matching_document_first():
    docs = {"a": words("plan the tests by risk"), "b": words("read a file"), "c": words("planning tests and plans " * 2)}
    ranked = [cid for _, cid in bm25("planning the tests", docs)]
    assert ranked[:2] == ["c", "a"] and "b" not in ranked
    assert bm25("", docs) == [] and bm25("tests", {}) == []


def test_plan_the_tests_ranks_qe_plan_and_planning_tests_above_unrelated_tools():
    registry.sync()
    found = [r["qualified_name"] for r in registry.find_capability("plan the tests", None, limit=40)]
    tools = [i for i, r in enumerate(registry.find_capability("plan the tests", None, limit=40)) if r["kind"] == "tool"]
    first_tool = tools[0] if tools else len(found)
    assert found.index("agentic-qe:qe-plan") < first_tool and found.index("agentic-qe:planning-tests") < first_tool
    assert registry.find_capability("zzzz-nothing", None) == []


def test_describe_and_index_text():
    registry.sync()
    described = registry.describe_capability("agentic-qe:qe-plan", None)
    assert described["kind"] == "command" and any(l["relation"] == "runs_script" for l in described["down"])
    assert registry.describe_capability("no-such-capability", None) is None
    text = registry.index_text(None)
    assert "## command" in text and "- agentic-qe:qe-plan:" in text
    assert "discover->repo-intelligence-analyst" in text and "delegates_to:" in text
    assert len(text.splitlines()) == len([l for l in text.splitlines() if l.startswith(("## ", "- "))])

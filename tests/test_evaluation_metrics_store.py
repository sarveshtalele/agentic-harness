"""Evaluation metrics: the n/a table, stored scores, the judge model, and benchmark labels."""
import asyncio
import json
from pathlib import Path

import pytest
from agent_framework import Content, EvalItem, Message

from backend.db import db, rows
from backend.maf import evals, governance, llm
from backend.maf.evals import ragas_evaluator, store
from tests.scripted_client import ScriptedClient
from tests.helpers_api import client, project  # noqa: F401 - fixtures

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "evals" / "benchmarks" / "shop"


# ---- the n/a table and the cards ---------------------------------------------------------------------------

def test_every_agent_is_in_the_applicability_table_and_na_has_no_number():
    assert set(store.METRICS_BY_AGENT) == set(governance.POLICIES)
    assert not store.applies("feature-engineer", "groundedness") and not store.applies("feature-engineer", "faithfulness")
    assert not store.applies("test-automation-engineer", "faithfulness") and store.applies("test-automation-engineer", "groundedness")
    assert all(store.applies(a, m) for a in store.METRICS_BY_AGENT for m in ("recall", "f1"))
    tile = store.tile("feature-engineer", "faithfulness")
    assert tile == {"metric": "faithfulness", "label": "Faithfulness", "state": "n/a"}
    assert "value" not in tile


def test_a_card_says_not_measured_until_something_ran():
    fresh = store.tile("confidence-reviewer", "recall")
    assert fresh["state"] in ("not_measured", "measured")
    if fresh["state"] == "not_measured":
        assert "Not measured" in fresh["reason"] and "value" not in fresh


def test_a_measured_row_needs_a_value_and_other_states_store_none():
    with pytest.raises(ValueError):
        store.record("bug-reviewer", "x@v1:aaa", "recall", status="measured")
    store.record("bug-reviewer", "x@v1:bbb", "faithfulness", value=0.9, status="failed", reason="the judge did not answer")
    with db() as con:
        stored = rows(con.execute("SELECT value, status FROM evaluation_metrics WHERE prompt_ref='x@v1:bbb'"))
    assert stored == [{"value": None, "status": "failed"}]


def test_scores_are_stored_and_trended_by_prompt_version():
    agent = "principal-test-architect"
    store.record(agent, "trend@v1:aaa", "recall", value=0.4, n=3, benchmark="shop", labels_reviewed=False)
    store.record(agent, "trend@v2:bbb", "recall", value=0.7, n=3, benchmark="shop", labels_reviewed=False)
    store.record(agent, "trend@v2:bbb", "recall", value=0.9, n=3, benchmark="shop", labels_reviewed=False)
    by = store.by_version(agent)
    assert by["trend@v1:aaa"]["recall"]["value"] == 0.4 and by["trend@v2:bbb"]["recall"] == {"value": pytest.approx(0.8), "runs": 2}
    points = {p["prompt_ref"]: p for t in store.detail(agent)["trend"] if t["metric"] == "recall" for p in t["points"]}
    assert points["trend@v2:bbb"]["min"] == 0.7 and points["trend@v2:bbb"]["max"] == 0.9 and points["trend@v2:bbb"]["runs"] == 2
    assert store.tile(agent, "recall")["labels"] == "not reviewed", "the tile warns while the labels are unchecked"


# ---- judge model and self grading --------------------------------------------------------------------------

def test_a_score_is_self_graded_unless_a_different_judge_is_set(monkeypatch):
    monkeypatch.delenv("ATLAS_EVAL_MODEL", raising=False)
    assert ragas_evaluator.self_graded("deepseek") is True
    monkeypatch.setenv("ATLAS_EVAL_MODEL", "deepseek")
    assert ragas_evaluator.self_graded("deepseek") is True
    monkeypatch.setenv("ATLAS_EVAL_MODEL", "kimi")
    assert ragas_evaluator.self_graded("deepseek") is False and ragas_evaluator.judge_model() == "kimi"


def test_ragas_missing_reads_not_measured_and_gives_no_number(monkeypatch, client):
    monkeypatch.setattr(ragas_evaluator, "installed", lambda: (False, ragas_evaluator.NOT_INSTALLED))
    done = asyncio.run(ragas_evaluator.RagasEvaluator("m").evaluate([EvalItem(conversation=[Message(role="user", contents=[Content.from_text("q")]), Message(role="assistant", contents=[Content.from_text("a")])], context="c")], eval_name="x"))
    assert done.status == "not_measured" and done.error == "Not measured: RAGAS is not installed" and not done.items
    llm.set_client_override(ScriptedClient([("Reverse-engineer the requirements", json.dumps({"requirements": [{"id": "R", "title": "t", "statement": "s", "file": "cart.py", "line": 25, "quote": "if discount_percent < 0 or discount_percent > 100:"}]}))]))
    result = asyncio.run(evals.run("requirements-analyst", benchmark="shop", ragas=True))
    with db() as con:
        faith = rows(con.execute("SELECT value, status, reason FROM evaluation_metrics WHERE eval_id=? AND metric='faithfulness'", (result["id"],)))
    assert faith == [{"value": None, "status": "not_measured", "reason": "Not measured: RAGAS is not installed"}]
    assert store.tile("requirements-analyst", "faithfulness")["state"] == "not_measured"


# ---- benchmark labels ------------------------------------------------------------------------------------------------

def test_benchmark_labels_are_marked_unreviewed_and_point_at_real_lines():
    shop = json.loads((SHOP / "labels.json").read_text(encoding="utf-8"))
    finance = json.loads((ROOT / "evals" / "benchmarks" / "finance" / "labels.json").read_text(encoding="utf-8"))
    assert shop["reviewed"] is False and finance["reviewed"] is False
    assert len(finance["commit"]) == 40 and finance["bugs"] and finance["requirements"]
    planted = {"BUG-1": "/ 10", "BUG-2": "quantity - 1", "BUG-3": "// 100", "BUG-4": "amount > FREE_SHIPPING_FROM", "BUG-5": "inventory.reserve"}
    for bug in shop["bugs"]:
        lines = (SHOP / "repo" / bug["file"]).read_text(encoding="utf-8").splitlines()
        assert planted[bug["id"]] in lines[bug["line"] - 1], bug["id"]
    assert not {b["file"] for b in shop["bugs"]} & set(shop["clean_files"])
    for item in [*shop["requirements"], *finance["requirements"]]:
        assert item["tolerance"] >= 0 and item["line"] >= 1
    for agent in ("bug-reviewer", "requirements-analyst", "business-analyst", "test-automation-engineer"):
        assert evals.bench_cases(agent, "shop"), agent

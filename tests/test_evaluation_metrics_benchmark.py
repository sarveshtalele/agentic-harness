"""Evaluation metrics: a benchmark run with known answers, the cards API, and live groundedness."""
import asyncio
import json

import pytest

from backend.core import auth, prompts
from backend.db import db, rows
from backend.maf import evals, governance, llm
from backend.maf.evals import store
from tests.scripted_client import ScriptedClient
from tests.helpers_api import client, project  # noqa: F401 - fixtures
from tests.helpers_models import account


# ---- a benchmark run with known answers --------------------------------------------------------------------------

def finding(file, line, quote):
    return {"title": "t", "severity": "high", "file": file, "line": line, "quote": quote, "explanation": "e"}


BUG_REPLY = json.dumps({"findings": [
    finding("cart.py", 27, "discount = self.subtotal() * discount_percent / 10"),
    finding("inventory.py", 14, "if self.available(sku) < quantity - 1:"),
    finding("pricing.py", 10, "return round_money(amount * TAX_RATE_PERCENT // 100)"),
    finding("money.py", 6, "return float(Decimal(str(value)).quantize(Decimal(\"0.01\"), rounding=ROUND_HALF_UP))"),  # false alarm in a clean file
    finding("cart.py", 5, "this line does not exist"),                                                               # invented quote
]})


def test_benchmark_run_computes_precision_recall_f1_and_groundedness_from_the_key(client, monkeypatch):
    monkeypatch.delenv("ATLAS_EVAL_MODEL", raising=False)
    llm.set_client_override(ScriptedClient([("Review these files for real defects", BUG_REPLY)]))
    result = asyncio.run(evals.run("bug-reviewer", benchmark="shop", repeats=2))
    assert result["repeats"] == 2 and result["labels_reviewed"] is False and result["benchmark"] == "shop"
    case = result["results"][0]
    assert case["measured"]["key"]["tp"] == 3 and case["measured"]["key"]["fp"] == 2 and case["measured"]["key"]["fn"] == 2
    got = {t["metric"]: t for t in store.card("bug-reviewer")["tiles"]}
    assert got["recall"]["value"] == pytest.approx(0.6) and got["f1"]["value"] == pytest.approx(0.6)
    assert got["groundedness"]["value"] == pytest.approx(0.8) and got["groundedness"]["n"] == 5
    assert got["recall"]["labels"] == "not reviewed" and got["faithfulness"]["state"] in ("not_measured", "measured", "failed")
    if got["faithfulness"]["state"] == "failed":  # RAGAS installed and its judge unreachable: an honest failure that says why, never a score
        assert got["faithfulness"]["value"] is None and got["faithfulness"].get("reason")
    spread = store.detail("bug-reviewer")["spread"]["recall"]
    assert spread["runs"] == 2 and spread["min"] == spread["max"] == pytest.approx(0.6)
    assert "does not exist" in case["reason"] or "not in" in case["reason"], "the reason names why a citation failed"


def test_cases_come_worst_first_with_question_context_answer_and_reason(client):
    llm.set_client_override(ScriptedClient([("Review these files for real defects", BUG_REPLY)]))
    asyncio.run(evals.run("bug-reviewer", benchmark="shop"))
    first = evals.cases_worst_first("bug-reviewer")[0]
    assert first["question"].startswith("Review these files") and "--- FILE cart.py ---" in first["context"] and "findings" in first["answer"] and first["reason"]
    assert "_item" not in first


def test_the_api_serves_cards_and_agent_metrics(client):
    cards = client.get("/api/evals/cards").json()
    assert set(cards["cards"]) == set(governance.POLICIES) and "shop" in cards["benchmarks"]
    assert [t["metric"] for t in cards["cards"]["bug-reviewer"]["tiles"]] == ["groundedness", "faithfulness", "recall", "f1"]
    assert cards["ragas"]["installed"] in (True, False) and cards["ragas"]["judge_model"] == ""
    detail = client.get("/api/agents/bug-reviewer/metrics").json()
    assert {m["metric"] for m in detail["metrics"]} >= {"groundedness", "mutation_score"} and "cases" in detail
    assert client.get("/api/agents/no-such/metrics").status_code == 404
    assert isinstance(client.get("/api/prompts/bug-reviewer/scores").json(), dict)
    assert client.post("/api/agents/bug-reviewer/evals", json={"benchmark": "nope"}).status_code == 404


def test_a_user_cannot_start_an_eval_and_an_admin_eval_is_not_theirs(client):
    user, mine, project = account(client)
    assert mine.post("/api/agents/bug-reviewer/evals", json={}).status_code == 403
    llm.set_client_override(ScriptedClient([("Review these files for real defects", BUG_REPLY)]))
    before = mine.get("/api/auth/me").json()["tokens_used"]
    with db() as con:
        last_id = con.execute("SELECT COALESCE(MAX(id),0) FROM agent_calls").fetchone()[0]

    async def as_admin():
        auth.current_user.set({"id": "admin", "role": "admin"})
        return await evals.run("bug-reviewer", benchmark="shop")

    asyncio.run(as_admin())
    with db() as con:
        owners = {r["user_id"] for r in rows(con.execute("SELECT user_id FROM agent_calls WHERE source='eval' AND id>?", (last_id,)))}
    assert owners == {"admin"} and mine.get("/api/auth/me").json()["tokens_used"] == before


# ---- live groundedness on a real reply ----------------------------------------------------------------------------

def live_count():
    with db() as con:
        return con.execute("SELECT COUNT(*) FROM evaluation_metrics WHERE source='live'").fetchone()[0]


def test_every_real_reply_records_free_groundedness_per_agent_call(client, project):
    from backend.config import repo_dir
    from backend.maf.runtime import AgentCall

    root = repo_dir(project["id"])
    root.mkdir(parents=True, exist_ok=True)
    (root / "calc.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
    reply = json.dumps({"findings": [finding("calc.py", 2, "return a / b"), finding("calc.py", 2, "return b / a")]})
    llm.set_client_override(ScriptedClient([("Review", reply)]))
    call = AgentCall(None, project["id"], "bug-reviewer", source="workflow")
    asyncio.run(call.text("Review calc.py"))
    with db() as con:
        live = rows(con.execute("SELECT value, n, source, agent_call_id, prompt_ref FROM evaluation_metrics WHERE source='live' AND agent='bug-reviewer' ORDER BY id DESC LIMIT 1"))[0]
        call_row = rows(con.execute("SELECT id FROM agent_calls WHERE project_id=? ORDER BY id DESC LIMIT 1", (project["id"],)))[0]
    assert live["value"] == 0.5 and live["n"] == 2 and live["agent_call_id"] == call_row["id"] and live["prompt_ref"] == prompts.ref("bug-reviewer")
    before = live_count()
    llm.set_client_override(ScriptedClient([("Review", "Nothing to report.")]))
    asyncio.run(AgentCall(None, project["id"], "bug-reviewer", source="workflow").text("Review calc.py"))
    assert live_count() == before, "a reply with no citations records nothing"

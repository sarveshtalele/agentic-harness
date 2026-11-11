"""Evaluation metrics: formulas, groundedness, and mutation score with real pytest."""
import asyncio
import json
from pathlib import Path

import pytest
from agent_framework import Content, EvalItem, LocalEvaluator, Message

from backend.maf.evals import metrics

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "evals" / "benchmarks" / "shop"


# ---- formulas, including division by zero ------------------------------------------------------

def test_formulas_on_known_inputs():
    assert metrics.precision(3, 1) == 0.75 and metrics.recall(3, 1) == 0.75
    assert metrics.f1(3, 1, 1) == pytest.approx(0.75) and metrics.f1(2, 2, 0) == pytest.approx(2 * 2 / (2 * 2 + 2))
    assert metrics.f1(1, 0, 0) == 1.0 and metrics.ratio(1, 4) == 0.25


def test_a_zero_denominator_has_no_value_never_0_or_1():
    assert metrics.precision(0, 0) is None and metrics.recall(0, 0) is None and metrics.f1(0, 0, 0) is None
    assert metrics.ratio(0, 0) is None
    assert metrics.precision(0, 3) == 0.0, "found things that were all wrong is a real zero"


def test_matching_is_one_to_one_and_reports_misses_and_extras():
    key = [{"file": "a.py", "line": 10, "tolerance": 1}, {"file": "a.py", "line": 20}, {"file": "b.py", "line": 5}]
    found = [{"file": "a.py", "line": 11}, {"file": "a.py", "line": 10}, {"file": "c.py", "line": 1}]
    got = metrics.match(found, key, metrics.at_location)
    assert (got["tp"], got["fp"], got["fn"]) == (1, 2, 2), "the second finding at line 10 cannot match the same key item again"
    assert got["precision"] == pytest.approx(1 / 3) and got["recall"] == pytest.approx(1 / 3)
    assert metrics.match([], [], metrics.at_location)["f1"] is None


def test_coverage_counts_labelled_facts_in_text_and_cannot_count_extras():
    got = metrics.coverage("Tax is 18 percent and shipping is free from 500.", [{"keywords": ["18"]}, {"keywords": ["500"]}, {"keywords": ["40"]}])
    assert (got["tp"], got["fn"], got["fp"]) == (2, 1, None) and got["recall"] == pytest.approx(2 / 3)
    assert got["precision"] is None and got["f1"] is None


# ---- groundedness -----------------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    (tmp_path / "calc.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")
    return tmp_path


def test_groundedness_checks_every_path_line_and_quote_on_disk(repo):
    reply = json.dumps({"findings": [
        {"file": "calc.py", "line": 2, "quote": "return a / b"},        # real
        {"file": "calc.py", "line": 9, "quote": "return a / b"},        # real quote, wrong line: the quote is found and the line corrected
        {"file": "calc.py", "line": 2, "quote": "return a // b"},       # invented quote
        {"file": "nope.py", "line": 1, "quote": "x = 1"},               # no such file
        {"file": "../outside.py", "line": 1, "quote": "x = 1"},         # escape
        {"file": "calc.py", "line": 50},                                # no such line
    ]})
    got = metrics.groundedness(reply, root=repo)
    assert got["n"] == 6 and got["value"] == pytest.approx(2 / 6)
    reasons = " | ".join(b["reason"] for b in got["bad"])
    assert "quote is not in calc.py" in reasons and "nope.py does not exist" in reasons and "outside" in reasons and "no line 50" in reasons


def test_groundedness_with_nothing_cited_has_no_value(repo):
    got = metrics.groundedness("This code is fine.", root=repo)
    assert got == {"value": None, "n": 0, "bad": []}


def test_groundedness_against_the_given_context_and_prose_citations(repo):
    context = "--- FILE a.py ---\n1: def f():\n2:     return 1\n"
    good = metrics.groundedness(json.dumps([{"file": "a.py", "line": 2, "quote": "return 1"}]), context=context)
    assert good["value"] == 1.0
    bad = metrics.groundedness(json.dumps([{"file": "b.py", "line": 1, "quote": "x"}, {"file": "a.py", "line": 1, "quote": "def g():"}]), context=context)
    assert bad["value"] == 0.0 and "not in the given context" in bad["bad"][0]["reason"]
    prose = metrics.groundedness("See calc.py:2 and calc.py:99 for the division.", root=repo)
    assert prose["n"] == 2 and prose["value"] == 0.5


def test_metric_checks_plug_into_maf_local_evaluator(repo):
    item = EvalItem(conversation=[Message(role="user", contents=[Content.from_text("q")]),
                                  Message(role="assistant", contents=[Content.from_text(json.dumps({"findings": [{"file": "calc.py", "line": 2, "quote": "return a / b"}]}))])])
    done = asyncio.run(LocalEvaluator(metrics.groundedness_check(root=repo)).evaluate([item]))
    assert done.items[0].scores[0].name == "groundedness" and done.items[0].scores[0].score == 1.0
    silent = EvalItem(conversation=[Message(role="user", contents=[Content.from_text("q")]), Message(role="assistant", contents=[Content.from_text("no citations")])])
    none = asyncio.run(LocalEvaluator(metrics.groundedness_check(root=repo)).evaluate([silent]))
    score = none.items[0].scores[0]
    assert score.passed is False and score.score == 0.0 and score.sample["reason"].startswith("Not measured"), "MAF checks are pass or fail, so the reason says it was not measured"


# ---- mutation score on a tiny real repository with real pytest -------------------------------------------

@pytest.fixture
def tiny(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\npythonpath = .\n", encoding="utf-8")
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n\n\ndef sign(n):\n    if n > 0:\n        return 1\n    return -1\n", encoding="utf-8")
    return tmp_path


MUTANTS = [{"id": "M-add", "file": "calc.py", "find": "return a + b", "replace": "return a - b"},
           {"id": "M-sign", "file": "calc.py", "find": "if n > 0:", "replace": "if n >= 0:"},
           {"id": "M-gone", "file": "calc.py", "find": "text that is not there", "replace": "x"}]


def test_mutation_score_counts_killed_and_surviving_bugs(tiny):
    tests = {"tests/test_calc.py": "from calc import add, sign\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\ndef test_sign_positive():\n    assert sign(4) == 1\n"}
    got = metrics.mutation_score(tiny, tests, MUTANTS)
    status = {m["id"]: m["status"] for m in got["mutants"]}
    assert status == {"M-add": "killed", "M-sign": "survived", "M-gone": "not_applied"}, "sign(0) is never tested, so the >= mutant survives"
    assert got["verdict"] == "MEASURED" and got["score"] == 0.5 and got["killed"] == 1 and got["survived"] == 1 and got["not_applied"] == 1
    assert "return a + b" in (tiny / "calc.py").read_text(encoding="utf-8"), "the real repository is never touched"
    assert not (tiny / "tests").exists(), "generated tests are written only in the temporary copy"
    better = dict(tests, **{"tests/test_calc.py": tests["tests/test_calc.py"] + "\n\ndef test_sign_zero():\n    assert sign(0) == -1\n"})
    assert metrics.mutation_score(tiny, better, MUTANTS)["score"] == 1.0


def test_mutation_score_with_zero_executed_tests_is_inconclusive_with_no_number(tiny):
    empty = metrics.mutation_score(tiny, {"tests/test_none.py": "def helper():\n    return 1\n"}, MUTANTS)
    assert empty["verdict"] == "INCONCLUSIVE" and empty["score"] is None and "No test was executed" in empty["reason"] and empty["executed"] == 0
    failing = metrics.mutation_score(tiny, {"tests/test_bad.py": "def test_bad():\n    assert 1 == 2\n"}, MUTANTS)
    assert failing["verdict"] == "INCONCLUSIVE" and failing["score"] is None and "already fail" in failing["reason"]
    nothing_applies = metrics.mutation_score(tiny, {"tests/test_ok.py": "def test_ok():\n    assert True\n"}, [MUTANTS[2]])
    assert nothing_applies["verdict"] == "INCONCLUSIVE" and nothing_applies["score"] is None


def test_the_shop_tests_pass_so_a_mutation_baseline_is_valid():
    got = metrics.mutation_score(SHOP / "repo", {"tests/test_x.py": "from money import round_money\n\n\ndef test_round():\n    assert round_money(2.675) == 2.68\n"}, [{"id": "M", "file": "money.py", "find": "ROUND_HALF_UP)", "replace": "ROUND_DOWN)"}])
    assert got["verdict"] == "MEASURED" and got["score"] == 1.0

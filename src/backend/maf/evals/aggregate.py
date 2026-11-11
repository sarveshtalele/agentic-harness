"""Turning case results into one stored row per metric, including the model-graded RAGAS metrics."""
from __future__ import annotations

from agent_framework import Content, EvalItem, Message

from backend.maf.evals import metrics, ragas_evaluator, store


def _aggregate(agent_key: str, prompt_ref: str, results: list[dict], ragas: dict, *, eval_id: str, batch: str, benchmark: str, reviewed: bool | None) -> None:
    """One stored row per metric for this run. A metric nothing measured is stored with its reason and no value."""
    base = {"eval_id": eval_id, "batch": batch, "benchmark": benchmark, "labels_reviewed": reviewed}
    cases = [r for r in results if r.get("measured") is not None]
    wanted = {m for r in cases for m in r.get("wanted", [])}
    if ragas:
        wanted |= {m for m in store.RAGAS if store.applies(agent_key, m)}
    for metric in ("groundedness", "faithfulness", "recall", "f1"):  # the four tiles always get a row, n/a where they do not apply
        if not store.applies(agent_key, metric):
            store.record(agent_key, prompt_ref, metric, status="n/a", reason="Does not apply to this agent", **base)
    g = [r["measured"]["groundedness"] for r in cases if "groundedness" in r["measured"]]
    if not g and store.applies(agent_key, "groundedness"):  # the tile says why instead of "no evaluation has run"
        store.record(agent_key, prompt_ref, "groundedness", status="not_measured", reason="No eval case gave the agent repository or document context to cite", **base)
    if g and store.applies(agent_key, "groundedness"):
        n = sum(x["n"] for x in g)
        if n:
            store.record(agent_key, prompt_ref, "groundedness", value=sum(x["value"] * x["n"] for x in g) / n, n=n, detail=[{"case": r["name"], "bad": r["measured"]["groundedness"]["bad"]} for r in cases if "groundedness" in r["measured"]], **base)
        else:
            store.record(agent_key, prompt_ref, "groundedness", status="not_measured", reason="No reply cited a file, line, or quote", **base)
    k = [r["measured"]["key"] for r in cases if "key" in r["measured"]]
    if not k:
        for metric in ("recall", "f1"):
            if store.applies(agent_key, metric):
                store.record(agent_key, prompt_ref, metric, status="not_measured", reason="No eval case has a labelled answer key to count against", **base)
    if k:
        tp, fn = sum(x["tp"] for x in k), sum(x["fn"] for x in k)
        fp = None if any(x["fp"] is None for x in k) else sum(x["fp"] for x in k)
        detail = {"tp": tp, "fp": fp, "fn": fn, "missed": [x["missed"] for x in k], "extra": [x["extra"] for x in k]}
        for metric, value in (("precision", None if fp is None else metrics.precision(tp, fp)), ("recall", metrics.recall(tp, fn)), ("f1", None if fp is None else metrics.f1(tp, fp, fn))):
            if value is None:
                store.record(agent_key, prompt_ref, metric, status="not_measured", reason="This key lists facts to find, so extras cannot be counted" if fp is None else "Nothing was labelled or found, so the ratio has no denominator", detail=detail, **base)
            else:
                store.record(agent_key, prompt_ref, metric, value=value, n=len(k), detail=detail, **base)
    for r in cases:
        if "mutation" in r["measured"]:
            m = r["measured"]["mutation"]
            if m["score"] is None:
                store.record(agent_key, prompt_ref, "mutation_score", status="inconclusive", reason=m["reason"], detail=m, **base)
            else:
                store.record(agent_key, prompt_ref, "mutation_score", value=m["score"], n=m["killed"] + m["survived"], detail=m, **base)
    for metric in wanted & set(store.RAGAS):
        if not store.applies(agent_key, metric):
            store.record(agent_key, prompt_ref, metric, status="n/a", reason="Does not apply to this agent", **base)
            continue
        info = ragas.get(metric, {"status": "not_measured", "reason": "Not measured: model-graded metrics were not requested for this run"})
        if info.get("values"):
            store.record(agent_key, prompt_ref, metric, value=sum(info["values"]) / len(info["values"]), n=len(info["values"]), judge_model=info["judge"], self_graded=info["self_graded"], tokens=info["tokens"], detail=info["cases"], **base)
        else:
            store.record(agent_key, prompt_ref, metric, status=info.get("status", "not_measured"), reason=info.get("reason", "No case could be scored"), judge_model=info.get("judge", ""), self_graded=info.get("self_graded", False), tokens=info.get("tokens", 0), **base)


async def _ragas(agent_key: str, results: list[dict]) -> dict:
    """Per metric: the values with their cases, or the status and reason there are none. One batch through MAF's Evaluator interface."""
    target_metrics = [m for m in store.RAGAS if store.applies(agent_key, m)]
    asked = [(r, [m for m in r.get("wanted", target_metrics) if m in store.RAGAS] or target_metrics) for r in results if r.get("_item")]
    if not asked:
        return {}
    model_name = next((r["model"] for r, _ in asked if r.get("model")), "")
    names = tuple(sorted({m for _, ms in asked for m in ms}))
    runner = ragas_evaluator.RagasEvaluator(model_name, names)
    items = []
    for r, _ in asked:
        question, answer, context, reference = r["_item"]
        items.append(EvalItem(conversation=[Message(role="user", contents=[Content.from_text(question)]), Message(role="assistant", contents=[Content.from_text(answer)])], context=context or None, expected_output=reference or None))
    runner.plan = [ms for _, ms in asked]
    try:
        done = await runner.evaluate(items, eval_name=f"{agent_key}:ragas")
    except Exception as exc:  # the judge failing is a result of its own, never a score
        return {m: {"status": "failed", "reason": f"RAGAS could not run: {type(exc).__name__}: {str(exc)[:300]}", "judge": runner.model, "self_graded": ragas_evaluator.self_graded(model_name), "tokens": runner.tokens} for m in names}
    if done.status != "completed":
        return {m: {"status": "not_measured", "reason": done.error or "RAGAS did not run"} for m in names}
    out: dict = {}
    for metric in names:
        values, cases = [], []
        why = ""
        for (r, _), item in zip(asked, done.items):
            found = next((s for s in item.scores if s.name == metric), None)
            if found:
                values.append(found.score)
                cases.append({"case": r["name"], "value": found.score, "reason": (found.sample or {}).get("reason", "")})
                r.setdefault("ragas", {})[metric] = found.score
            else:
                why = (item.metadata or {}).get("notes", {}).get(metric, why)
        status = "unavailable" if metric in runner.skipped else "failed" if why.startswith("failed") else "not_measured"
        out[metric] = {"values": values, "cases": cases, "judge": runner.model, "self_graded": ragas_evaluator.self_graded(model_name), "tokens": runner.by_metric.get(metric, 0),
                       "status": status, "reason": runner.skipped.get(metric) or why or "No case could be scored"}
    return out

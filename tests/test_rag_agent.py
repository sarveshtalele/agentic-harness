"""QE v2 step 4: the document-analyst agent. Rerank keeps only ids it was given; an answer keeps only quotes found verbatim in the saved source."""
from __future__ import annotations

import json

from backend.maf import llm
from backend.rag import retrieve
from tests.helpers_api import client, project  # noqa: F401 - fixtures
from tests.scripted_client import ScriptedClient
from tests.test_rag import BRD, source_of, upload


def test_rerank_drops_unknown_ids_and_answers_keep_only_verbatim_quotes(client, project):
    saved = upload(client, project, ("sample_brd.md", BRD, "text/markdown")).json()["indexed"][0]
    ids = [c["id"] for c in retrieve.retrieve(project["id"], "fine cap per loan", 20)]
    assert len(ids) > 8

    def answer(text):
        chunk_id = next(i for i in ids if f"[{i}]" in text and "never exceeds 20 euro" in text.split(f"[{i}]", 1)[1].split("\n\n[", 1)[0])
        return json.dumps({"found": True, "answer": "20 euro", "citations": [{"chunk": chunk_id, "quote": "never exceeds 20 euro"},
                                                                              {"chunk": chunk_id, "quote": "never exceeds 99 euro"}, {"chunk": "chk_unknown", "quote": "x"}]})

    scripted = ScriptedClient([("Pick the 8 chunks most useful", lambda text: json.dumps({"ids": ["chk_unknown", ids[3], ids[3]]})), ("TASK: ANSWER\nQuestion:", answer)])
    llm.set_client_override(scripted)
    ranked = client.post(f"/api/projects/{project['id']}/rag/retrieve", json={"question": "fine cap per loan", "k": 8, "rerank": True}).json()["chunks"]
    assert ranked[0]["id"] == ids[3] and len({c["id"] for c in ranked}) == len(ranked) <= 8, "the model's pick leads, unknown ids are dropped"
    got = client.post(f"/api/projects/{project['id']}/rag/ask", json={"question": "fine cap per loan", "k": 20}).json()
    assert got["found"] is True and [c["quote"] for c in got["citations"]] == ["never exceeds 20 euro"]
    cite = got["citations"][0]
    assert cite["quote"] in "\n".join(source_of(project, saved["source_path"]).splitlines()[cite["line_start"] - 1 : cite["line_end"]])

    llm.set_client_override(ScriptedClient([("TASK: ANSWER\nQuestion:", json.dumps({"found": True, "answer": "Invented.", "citations": [{"chunk": ids[0], "quote": "not in the text at all"}]}))]))
    refused = client.post(f"/api/projects/{project['id']}/rag/ask", json={"question": "fine cap per loan", "k": 20}).json()
    assert refused["found"] is False and refused["answer"] == "Not in the documents." and refused["citations"] == []


def test_ask_with_nothing_indexed_calls_no_model(client, project):
    scripted = ScriptedClient([])
    llm.set_client_override(scripted)
    got = client.post(f"/api/projects/{project['id']}/rag/ask", json={"question": "anything"}).json()
    assert got["found"] is False and got["answer"] == "Not in the documents." and scripted.calls == []


def test_another_project_cannot_see_the_chunks(client, project):
    upload(client, project, ("sample_brd.md", BRD, "text/markdown"))
    other = client.post("/api/projects", json={"name": "Other", "description": "x"}).json()
    assert client.post(f"/api/projects/{other['id']}/rag/retrieve", json={"question": "fine cap per loan"}).json()["chunks"] == []
    assert client.get("/api/projects/prj_nope/rag").status_code in {403, 404}

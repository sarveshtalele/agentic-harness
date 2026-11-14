"""QE v2 step 4: requirement documents, chunks that keep their place, hybrid retrieval, cited answers (docs/QE_V2_PLAN.md section 5)."""
from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest

from backend.config import sandbox_dir
from backend.maf import llm
from backend.rag import chunk, embed, retrieve
from tests.helpers_api import client, project  # noqa: F401 - fixtures
from tests.scripted_client import ScriptedClient

DATA = Path(__file__).parent / "data"
BRD = (DATA / "sample_brd.md").read_bytes()
QA = json.loads((DATA / "sample_brd_qa.json").read_text(encoding="utf-8"))


def upload(client, project, *files):
    return client.post(f"/api/projects/{project['id']}/rag/documents", files=[("files", f) for f in files])


def source_of(project, path: str) -> str:
    return (sandbox_dir(project["id"]) / path).read_text(encoding="utf-8")


def pdf_with(text: str) -> bytes:
    """A one-page PDF built by hand (objects, xref table, trailer), so the test needs no PDF writer."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
               b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
               b"<</Length %d>>\nstream\n" % len(stream) + stream + b"\nendstream", b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return out + b"trailer\n<</Root 1 0 R/Size %d>>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)


# ---- chunking ----

def test_chunks_are_exact_line_slices_with_heading_path():
    text = BRD.decode()
    lines = text.splitlines()
    chunks = chunk.chunk_text(text)
    assert chunks and all(c.text == "\n".join(lines[c.line_start - 1 : c.line_end]) for c in chunks)
    fine_cap = next(c for c in chunks if "never exceeds 20 euro" in c.text)
    assert fine_cap.section == "TEST FIXTURE: Business Requirements Document, Harbor Library Loans > 6. Fines > 6.2 Fine cap" and lines[fine_cap.line_start - 1] == "### 6.2 Fine cap"
    covered = {n for c in chunks for n in range(c.line_start, c.line_end + 1)}
    assert all(n in covered for n, line in enumerate(lines, 1) if line.strip()), "every non-blank line is in some chunk"


def test_long_sections_split_near_the_target_with_overlap_and_pages_are_kept():
    paragraphs = [f"Paragraph {i}. " + "word " * 120 for i in range(30)]  # about 150 tokens each
    chunks = chunk.chunk_text("# Big\n\n" + "\n\n".join(paragraphs))
    assert len(chunks) > 3 and all(chunk.tokens(c.text) <= chunk.TARGET_TOKENS * 1.2 for c in chunks)
    assert all(b.line_start <= a.line_end for a, b in zip(chunks, chunks[1:])), "the next chunk starts inside the previous one"
    assert all(b.line_start > a.line_start for a, b in zip(chunks, chunks[1:]))
    pages = chunk.chunk_text("## Page 1\nAlpha text.\n\n## Page 2\nBeta text.")
    assert [(c.page, c.text.splitlines()[-1]) for c in pages] == [(1, "Alpha text."), (2, "Beta text.")]


# ---- upload, parse, index ----

def test_several_files_are_parsed_saved_and_listed(client, project):
    from docx import Document

    word = Document()
    word.add_heading("Refund policy", 1)
    word.add_paragraph("A customer may return an item within 14 days.")
    buffer = io.BytesIO()
    word.save(buffer)
    done = upload(client, project, ("brd.md", BRD, "text/markdown"), ("notes.txt", b"Stories:\nAs a member I can pay a fine.", "text/plain"),
                  ("refunds.docx", buffer.getvalue(), "application/octet-stream"), ("spec.pdf", pdf_with("Shipping takes 3 days."), "application/pdf"),
                  ("evil.exe", b"MZ", "application/octet-stream"))
    assert done.status_code == 201, done.text
    body = done.json()
    assert sorted(i["filename"] for i in body["indexed"]) == ["brd.md", "notes.txt", "refunds.docx", "spec.pdf"]
    assert [r["filename"] for r in body["refused"]] == ["evil.exe"] and "not a supported type" in body["refused"][0]["error"]
    by_name = {i["filename"]: i for i in body["indexed"]}
    assert "14 days" in source_of(project, by_name["refunds.docx"]["source_path"]) and "# Refund policy" in source_of(project, by_name["refunds.docx"]["source_path"])
    assert "Shipping takes 3 days." in source_of(project, by_name["spec.pdf"]["source_path"]) and "## Page 1" in source_of(project, by_name["spec.pdf"]["source_path"])
    listed = client.get(f"/api/projects/{project['id']}/rag").json()
    assert len(listed["documents"]) == 4 and listed["search"]["keyword"] is True
    pdf_hit = client.post(f"/api/projects/{project['id']}/rag/retrieve", json={"question": "how many days does shipping take", "k": 3}).json()["chunks"][0]
    assert pdf_hit["citation"]["document"] == "spec.pdf" and pdf_hit["citation"]["page"] == 1
    assert client.post(f"/api/projects/{project['id']}/rag/documents", files=[("files", ("x.docx", b"not a zip", "application/octet-stream"))]).status_code == 400


def test_a_secret_in_an_upload_is_redacted_before_it_is_saved(client, project):
    secret = "sk-" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4"
    saved = upload(client, project, ("keys.md", f"# Keys\n\nThe service key is {secret} for payments.".encode(), "text/markdown")).json()["indexed"][0]
    assert secret not in source_of(project, saved["source_path"])
    assert not retrieve.retrieve(project["id"], secret)


# ---- the RAG eval: recall@8 and citation accuracy on the sample BRD, keyword path, no model ----

def test_recall_at_8_and_every_citation_is_verbatim_in_the_saved_source(client, project):
    saved = upload(client, project, ("sample_brd.md", BRD, "text/markdown")).json()["indexed"][0]
    on_disk = source_of(project, saved["source_path"]).splitlines()
    hits = checked = 0
    for case in QA:
        found = retrieve.retrieve(project["id"], case["question"], 8)
        assert len(found) <= 8
        hits += any(case["expect"] in c["text"] for c in found)
        for c in found:
            cite = c["citation"]
            assert cite["doc_id"] == saved["doc_id"] and cite["version"] == 1 and cite["source_path"] == saved["source_path"]
            assert c["text"] == "\n".join(on_disk[cite["line_start"] - 1 : cite["line_end"]]), "the citation's lines are the chunk text, verbatim"
            checked += 1
    recall = hits / len(QA)
    assert recall >= 0.9, f"recall@8 {recall:.2f}"
    assert checked > len(QA)
    top = retrieve.retrieve(project["id"], "What is the maximum fine for one loan?", 1)[0]
    assert top["citation"]["section"].endswith("6. Fines > 6.2 Fine cap")


def test_a_question_the_documents_do_not_answer_finds_nothing_matching(client, project):
    upload(client, project, ("sample_brd.md", BRD, "text/markdown"))
    assert retrieve.retrieve(project["id"], "zebra spaceship quantum", 8) == []
    assert client.post(f"/api/projects/{project['id']}/rag/retrieve", json={"question": "!!", "k": 8}).json()["chunks"] == []


def test_search_says_when_it_is_keyword_only(client, project):
    upload(client, project, ("sample_brd.md", BRD, "text/markdown"))
    state = client.get(f"/api/projects/{project['id']}/rag").json()
    assert state["search"]["vector"] is False and state["search"]["note"]
    assert state["documents"][0]["embedded"] == 0


# ---- embeddings through the configured endpoint, and pgvector ----

def fake_endpoint(calls):
    """A stand-in for the model endpoint's /embeddings: one vector per input, from the text's letters (the test, not the product, makes these)."""
    def handler(request: httpx.Request) -> httpx.Response:
        texts = json.loads(request.content)["input"]
        calls.append(request.url.path)
        return httpx.Response(200, json={"data": [{"index": i, "embedding": [t.lower().count(c) / (len(t) + 1) for c in "etaoinshr"]} for i, t in enumerate(texts)]})
    return httpx.MockTransport(handler)


def test_embeddings_are_never_invented(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    gone = httpx.MockTransport(lambda request: httpx.Response(404, json={"error": "no embeddings here"}))
    vectors, why = embed.embed(["hello"], transport=gone)
    assert vectors is None and "no usable embeddings API" in why and "404" in why
    vectors, why = embed.embed(["a", "b"], transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0]}]})))
    assert vectors is None and "wrong number" in why


def pgvector_reason() -> str:
    from backend.db import db

    with db() as con:
        return con.execute("SELECT name FROM pg_available_extensions WHERE name='vector'").fetchone() and "" or "pgvector is not installed in the test PostgreSQL"


def test_vector_and_keyword_are_fused_when_pgvector_exists(client, project, monkeypatch):
    if reason := pgvector_reason():
        pytest.skip(reason)  # only this vector-specific test may skip; the keyword tests above always run
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from backend.rag import ingest

    calls: list[str] = []
    transport = fake_endpoint(calls)
    real = httpx.Client
    monkeypatch.setattr(embed.httpx, "Client", lambda **kw: real(**{**kw, "transport": transport}))
    saved = ingest.add(project["id"], "sample_brd.md", BRD, author="test")
    assert saved["embedded"] == saved["chunks"] > 0 and not saved["note"]
    state = retrieve.mode(project["id"])
    assert state["vector"] is True
    found = retrieve.retrieve(project["id"], "What is the maximum fine for one loan?", 8)
    assert any(set(c["via"]) == {"keyword", "vector"} for c in found)
    assert "/embeddings" in calls[0] and len(calls) >= 2


def test_without_pgvector_embeddings_are_not_stored_and_search_says_so(client, project, monkeypatch):
    if not pgvector_reason():
        pytest.skip("pgvector is installed here, so the fallback does not apply; the fusion test above covers this database")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from backend.rag import ingest

    saved = ingest.add(project["id"], "sample_brd.md", BRD, author="test", transport=fake_endpoint([]))
    assert saved["embedded"] == 0 and "pgvector is not installed" in saved["note"] and "keyword only" in saved["note"]
    state = client.get(f"/api/projects/{project['id']}/rag").json()
    assert state["search"]["vector"] is False and "pgvector" in state["search"]["note"]
    assert retrieve.retrieve(project["id"], "What is the maximum fine for one loan?", 8), "keyword search still answers"


def test_reciprocal_rank_fusion_prefers_chunks_both_lists_rank():
    a, b, c = ({"id": i, "doc_id": "d", "line_start": n, "body": ""} for n, i in enumerate("abc"))
    merged = retrieve.fuse({"keyword": [a, b], "vector": [c, b]})
    assert [m["id"] for m in merged] == ["b", "a", "c"] and merged[0]["via"] == ["keyword", "vector"]

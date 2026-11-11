"""Document images, document lists and rollback of broken edits."""

import io
import json

from tests.helpers_api import client, project  # noqa: F401 - fixtures


PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6364f8cfc0000003010100c9fe92ef0000000049454e44ae426082")


def test_document_images_upload_serve_refuse_and_export(client, project):
    from docx import Document

    doc = client.post(f"/api/projects/{project['id']}/documents", json={"kind": "brd", "title": "Pics", "content": "# T\n"}).json()
    saved = client.post(f"/api/documents/{doc['id']}/images", files={"file": ("x.png", PNG, "image/png")})
    assert saved.status_code == 201
    url = saved.json()["url"]
    served = client.get(url)
    assert served.content == PNG and served.headers["content-type"] == "image/png" and served.headers["x-content-type-options"] == "nosniff"
    refused = client.post(f"/api/documents/{doc['id']}/images", files={"file": ("x.png", b"<svg onload=alert(1)>", "image/png")})
    assert refused.status_code == 400 and "PNG" in refused.json()["detail"]
    assert client.get(f"/api/documents/{doc['id']}/images/..%2F..%2Fsecret.png").status_code in {400, 404}
    assert client.get(f"/api/documents/{doc['id']}/images/absent.png").status_code == 404
    client.put(f"/api/documents/{doc['id']}", json={"content": f"# T\n\n![pic]({url})\n\n| A | B |\n| --- | --- |\n| x \\| y | z |\n", "note": "n"})
    word = Document(io.BytesIO(client.get(f"/api/documents/{doc['id']}/export/docx").content))
    assert len(word.inline_shapes) == 1 and word.tables[0].rows[1].cells[0].text == "x | y"
    ledger = client.get(f"/api/projects/{project['id']}/ledger").json()
    assert "document.image_added" in json.dumps(ledger)


def test_document_lists_name_the_run_that_created_them(client, project):
    from backend.core import documents

    with_run = documents.create(project["id"], "brd", "From a run", "# T\n", "agent:x")
    assert next(d for d in client.get(f"/api/projects/{project['id']}/documents").json() if d["id"] == with_run["id"])["run_id"] is None
    from backend.db import db, new_id, now

    run_id = new_id("run")
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, state, started_at) VALUES ('run_doc', ?, 'ba', 'completed', '{}', '{}', ?)", (project["id"], now()))
    made = documents.create(project["id"], "brd", "Run doc", "# T\n", "agent:x", run_id="run_doc")
    documents.save_version(made["id"], "# T\n\nMore\n", "Ann", note="edit")
    assert next(d for d in client.get(f"/api/projects/{project['id']}/documents").json() if d["id"] == made["id"])["run_id"] == "run_doc"


def test_edit_that_breaks_syntax_is_rolled_back(tmp_path):
    from backend.maf.workflows import Edit, apply_edits

    (tmp_path / "a.py").write_text("x = 1\n")
    assert "not applied" in apply_edits(tmp_path, [Edit(path="a.py", action="replace", search="x = 1", replace="x = (")])[0]
    assert (tmp_path / "a.py").read_text() == "x = 1\n"
    assert "not applied" in apply_edits(tmp_path, [Edit(path="b.py", action="create", content="def (")])[0]
    assert not (tmp_path / "b.py").exists()

"""Zip ingest, git, scanners and quote checks."""

import zipfile
from pathlib import Path

import pytest

from backend.repos import git, ingest, scan, static_analysis
from tests.helpers_core import project  # noqa: F401 - fixtures


def _zip(tmp_path: Path, entries: dict[str, str]) -> Path:
    path = tmp_path / "a.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        for name, body in entries.items():
            bundle.writestr(name, body)
    return path


def test_zip_slip_refused(tmp_path):
    archive = _zip(tmp_path, {"../evil.txt": "x"})
    with pytest.raises(ingest.IngestError):
        ingest.safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_zip_symlink_dropped(tmp_path):
    path = tmp_path / "link.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        info = zipfile.ZipInfo("link")
        info.external_attr = 0o120777 << 16
        bundle.writestr(info, "/etc/hosts")
        bundle.writestr("ok.txt", "fine")
    out = tmp_path / "out"
    out.mkdir()
    ingest.safe_extract(path, out)
    assert (out / "ok.txt").exists() and not (out / "link").exists()


def test_bad_zip_refused(tmp_path):
    path = tmp_path / "x.zip"
    path.write_text("nope")
    with pytest.raises(ingest.IngestError):
        ingest.safe_extract(path, tmp_path)


def test_zip_ingest_unwraps_and_scans(project, tmp_path):
    archive = _zip(tmp_path, {"proj/app.py": "def add(a, b):\n    return a + b\n", "proj/tests/test_app.py": "def test_x():\n    assert 1 == 1\n", "proj/requirements.txt": "fastapi>=0.1\npytest\n"})
    result = ingest.from_zip(project, archive, "a.zip")
    analysis = result["analysis"]
    assert analysis["languages"]["Python"] == 2 and "FastAPI" in analysis["frameworks"] and analysis["test_runners"] == ["pytest"]
    assert analysis["test_file_count"] == 1 and result["commit_sha"]


@pytest.mark.parametrize("url", ["file:///etc", "ssh://git@x/y", "ext::sh -c id", "http://x/y", "https://user:pw@github.com/a/b"])
def test_git_url_validation(url):
    with pytest.raises(git.GitError):
        git.validate_url(url)


def test_git_token_never_in_argv_or_config(tmp_path, monkeypatch):
    seen = {}

    def spy(command, **kwargs):
        seen["argv"], seen["env"] = command, kwargs["env"]
        raise git.GitError("stop")

    monkeypatch.setattr(git.subprocess, "run", spy)
    with pytest.raises(git.GitError):
        git.clone("https://github.com/a/b", tmp_path / "x", token="fake-value")
    assert not any("fake-value" in part for part in seen["argv"]) and "Authorization: Basic" in seen["env"]["GIT_CONFIG_VALUE_0"]


def test_analyze_finds_routes_and_symbols(tmp_path):
    (tmp_path / "main.py").write_text('from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health():\n    return 1\n')
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("ignored")
    analysis = scan.analyze(tmp_path)
    assert analysis["routes"][0] == {"method": "GET", "path": "/health", "file": "main.py", "line": 3}
    assert analysis["largest_sources"][0]["symbols"] == ["health"]
    assert analysis["total_files"] == 1


def test_empty_repo_is_greenfield(tmp_path):
    assert scan.analyze(tmp_path)["mode"] == "greenfield"


def test_ruff_finds_real_issues_with_true_lines(tmp_path):
    (tmp_path / "bad.py").write_text("import subprocess\n\ndef f(x):\n    subprocess.call(x, shell=True)\n    try:\n        return 1\n    except:\n        pass\n")
    found = static_analysis.run_ruff(tmp_path)
    assert found, "ruff must flag shell=True and bare except"
    for finding in found:
        assert finding["evidence"] == (tmp_path / "bad.py").read_text().splitlines()[finding["line"] - 1].strip()


def test_clean_repo_has_no_fabricated_findings(tmp_path):
    (tmp_path / "good.py").write_text('"""Fine."""\n\n\ndef add(a: int, b: int) -> int:\n    return a + b\n')
    assert static_analysis.run_all(tmp_path) == []


def test_secret_finding_never_stores_the_value(tmp_path):
    (tmp_path / "cfg.py").write_text("KEY = 'sk-" + "a1B2" * 10 + "'\n")
    found = static_analysis.run_secrets(tmp_path)
    assert found and "a1B2a1B2" not in found[0]["evidence"]


def test_quote_verification_rejects_hallucination(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    assert static_analysis.verify_quote(tmp_path, "a.py", 1, "y = 2") == (True, 2)
    assert static_analysis.verify_quote(tmp_path, "a.py", 1, "z = 9")[0] is False
    assert static_analysis.verify_quote(tmp_path, "missing.py", 1, "x")[0] is False
    assert static_analysis.verify_quote(tmp_path, "../a.py", 1, "x")[0] is False

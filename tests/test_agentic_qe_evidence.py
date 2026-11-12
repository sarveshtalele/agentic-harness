"""The agentic-qe Gate 1 check reads the evidence fields its own rules name, and checks each quote on disk (live cycle 2026-11-12)."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "plugins" / "agentic-qe" / "skills" / "tracing-coverage" / "scripts" / "check-gate.ts"
CONTRACTS = ROOT / "plugins" / "agentic-qe" / "skills" / "extracting-requirements" / "scripts" / "extract-contracts.ts"


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def balance(acct):\n    return lookup(acct)\n", encoding="utf-8")
    folder = tmp_path / "docs" / "qe" / "app" / "02-requirements"
    folder.mkdir(parents=True)
    (folder / "requirements.json").write_text(json.dumps({"requirements": [
        {"id": "REQ-1", "title": "Balance", "description": "Returns the balance", "source_file": "src/a.py", "line_number": 2, "quote": "return lookup(acct)"},
        {"id": "REQ-2", "title": "Invented", "description": "Cites a missing file", "source_file": "mcp/balance.py", "line_number": 4, "quote": "return 1"},
        {"id": "REQ-3", "title": "Ad hoc", "description": "A field the rules do not name", "source_evidence": "somewhere"},
    ]}), encoding="utf-8")
    return tmp_path


def _node(args, cwd):
    return subprocess.run([shutil.which("node") or "node", *map(str, args)], cwd=cwd, capture_output=True, text=True, timeout=120, check=False)


def test_gate_one_accepts_the_documented_fields_and_refuses_quotes_not_on_disk(tmp_path):
    out = _node([CHECK, "--gate", "1", "--app", "app"], _repo(tmp_path)).stdout
    assert "FAIL" in out
    lines = out.splitlines()
    no_evidence = next(line for line in lines if "without source evidence" in line)
    not_found = next(line for line in lines if "not found verbatim" in line)
    assert no_evidence.endswith("REQ-3") and not_found.endswith("REQ-2")  # REQ-1's quote is in src/a.py


def test_extract_contracts_reads_the_requirements_object_and_snake_case_fields(tmp_path):
    repo = _repo(tmp_path)
    done = _node([CONTRACTS, "docs/qe/app/02-requirements/requirements.json", "--root", "."], repo)
    result = json.loads(done.stdout)
    assert done.returncode == 1 and result["accepted"] == 1
    assert sorted(r["id"] for r in result["rejected"]) == ["REQ-2", "REQ-3"]

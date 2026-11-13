"""R5 / section 8: plugin contracts and the gate check as typed tools, read from the agentic-qe plugin in plugins/."""
import json
from types import SimpleNamespace

import pytest

from backend.core import script_runtime
from backend.maf.harness_kit import plugin_contract
from tests.helpers_api import client  # noqa: F401 - the database the plugin state lives in


def test_the_requirements_contract_names_the_fields_the_plugin_reads(client):
    text = plugin_contract.describe("docs/qe/shop/02-requirements/requirements.json")
    assert "normalizeRequirement" in text
    for field in ("id", "priority", "source_file", "line_number", "quote", "evidence"):
        assert field in text
    assert "source_evidence" not in text  # the field the live run invented is not one of them
    assert "normalizeCase" in plugin_contract.describe("docs/qe/shop/04-design/test-cases.json")


@pytest.mark.skipif(not script_runtime.node_version(), reason="no Node.js here")
def test_check_gate_runs_the_plugins_own_script(client, tmp_path):
    ws = SimpleNamespace(root=tmp_path, env=lambda: {"PATH": __import__("os").environ.get("PATH", "")})
    req = tmp_path / "docs" / "qe" / "shop" / "02-requirements"
    req.mkdir(parents=True)
    (req / "requirements.json").write_text(json.dumps({"requirements": [{"id": "REQ-1", "text": "x", "source_evidence": "app.py"}]}))
    report = plugin_contract.check(ws, 1, "shop")
    assert report.startswith("exit ") and "FAIL" in report.upper()  # no priority and no evidence the plugin reads
    assert "Refused" in plugin_contract.check(ws, 1, "../etc")

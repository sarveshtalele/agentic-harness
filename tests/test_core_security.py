"""Secrets, safe paths, the ledger and gates."""

import pytest

from backend.core import gates, ledger, security
from backend.db import db
from tests.helpers_core import project  # noqa: F401 - fixtures


def test_encrypt_round_trip_and_ciphertext_differs():
    token = security.encrypt("value-to-protect")
    assert b"value-to-protect" not in token and security.decrypt(token) == "value-to-protect"


def test_secret_scanner_flags_real_shapes():
    assert security.scan_secrets("key = 'sk-" + "a" * 30 + "'")


@pytest.mark.parametrize("text", ["sk-" + "example" * 5, "x = 1"])
def test_secret_scanner_ignores_placeholders(text):
    assert not security.scan_secrets(text)


def test_redact_masks_secret():
    assert "a" * 30 not in security.redact("token sk-" + "a" * 30)


@pytest.mark.parametrize("bad", ["../x", "a/../../x", "/etc/passwd", "..\\x"])
def test_safe_path_blocks_escape(tmp_path, bad):
    with pytest.raises(security.PathEscape):
        security.safe_path(tmp_path, bad)


def test_safe_path_blocks_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "link").symlink_to(outside)
    except OSError:
        pytest.skip("This Windows account cannot create symlinks")
    with pytest.raises(security.PathEscape):
        security.safe_path(root, "link/file")


@pytest.mark.parametrize("protected", [".git/config", "node_modules/x", ".venv/bin/python"])
def test_safe_path_write_protects_internals(tmp_path, protected):
    with pytest.raises(security.PathEscape):
        security.safe_path(tmp_path, protected, for_write=True)


def test_ledger_detects_tampering(project):
    for i in range(3):
        ledger.append(project, "tester", "act", str(i))
    assert ledger.verify(project)["valid"]
    with db() as con:
        con.execute("UPDATE ledger SET target='forged' WHERE project_id=? AND seq=2", (project,))
    assert ledger.verify(project) == {"valid": False, "entries": 3, "broken_at": 2}


def test_ledger_detects_deleted_entry(project):
    for i in range(3):
        ledger.append(project, "tester", "act", str(i))
    with db() as con:
        con.execute("DELETE FROM ledger WHERE project_id=? AND seq=2", (project,))
    assert not ledger.verify(project)["valid"]


def test_ledger_redacts_secrets(project):
    ledger.append(project, "t", "a", "x", {"v": "sk-" + "b" * 30})
    assert "b" * 30 not in ledger.entries(project)[0]["data"]


def test_gates_enforce_order_and_signer(project):
    with pytest.raises(gates.GateOrderError):
        gates.decide(project, 1, True, "ann")
    with pytest.raises(gates.GateOrderError):
        gates.decide(project, 0, True, "  ")
    gates.decide(project, 0, True, "ann")
    gates.decide(project, 1, True, "ann")
    assert gates.is_approved(project, 1)


def test_rejecting_a_gate_clears_later_approvals(project):
    gates.decide(project, 0, True, "ann")
    gates.decide(project, 1, True, "ann")
    gates.decide(project, 0, False, "ann", "scope changed")
    state = {g["gate"]: g["status"] for g in gates.status(project)}
    assert state[0] == "rejected" and state[1] == "pending"


def test_gate_signature_detects_forgery(project):
    gates.decide(project, 0, True, "ann")
    assert gates.status(project)[0]["signature_valid"] is True
    with db() as con:
        con.execute("UPDATE gates SET decided_by='mallory' WHERE project_id=?", (project,))
    assert gates.status(project)[0]["signature_valid"] is False

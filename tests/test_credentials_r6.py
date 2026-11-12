"""R6 credentials (docs/PHASE2_PLAN.md section 13): pepper, recorded cost and rehash at sign-in, password rules, and the
first admin kept as a hash only."""
import subprocess
import sys
from pathlib import Path

import pytest

from backend.core import auth
from backend.core.auth import passwords
from backend.db import db
from tests.helpers_api import USER_PASSWORD, client, make_user, unique  # noqa: F401 - fixtures

ROOT = Path(__file__).resolve().parents[1]


def _stored(username):
    with db() as con:
        return con.execute("SELECT password_hash FROM users WHERE username_lookup=?", (auth.base._lookup(username),)).fetchone()[0]


def test_old_hashes_still_sign_in_and_are_rehashed_with_the_pepper(client, monkeypatch):
    name = unique("rehash")
    make_user(client, name)
    salt = "00" * 16
    legacy = f"scrypt${salt}${passwords._digest(USER_PASSWORD, bytes.fromhex(salt), 2**14, b'')}"  # the format before R6
    with db() as con:
        con.execute("UPDATE users SET password_hash=? WHERE username_lookup=?", (legacy, auth.base._lookup(name)))
    monkeypatch.setenv("ATLAS_PASSWORD_PEPPER", "pepper-from-key-vault-" + "x" * 16)
    assert auth.login(name, USER_PASSWORD)
    fresh = _stored(name)
    assert fresh.count("$") == 4 and fresh.split("$")[2] != "-" and not passwords.needs_rehash(fresh)
    assert "pepper-from-key-vault" not in fresh  # only which pepper, never the pepper
    monkeypatch.setenv("ATLAS_PASSWORD_PEPPER", "another-pepper-" + "y" * 16)
    assert not passwords._verify_password(USER_PASSWORD, fresh)  # the database alone is not enough
    monkeypatch.setenv("ATLAS_PASSWORD_PEPPER", "pepper-from-key-vault-" + "x" * 16)
    monkeypatch.setenv("ATLAS_SCRYPT_N", str(2**15))
    assert passwords.needs_rehash(fresh)
    assert auth.login(name, USER_PASSWORD) and _stored(name).split("$")[1] == str(2**15)


@pytest.mark.parametrize("password, why", [("short-pass1", "12 characters"), ("password1234", "breached"),
                                           ("aaaaaaaaaaaaaa", "breached"), ("my-carol.tester-pw", "username")])
def test_password_rules(password, why):
    with pytest.raises(auth.AuthError, match=why):
        passwords.check_password_rules(password, "carol.tester")


def test_a_breached_list_file_is_honoured(tmp_path, monkeypatch):
    listed = tmp_path / "breached.txt"
    listed.write_text("Correct-Horse-Battery\n", encoding="utf-8")
    monkeypatch.setenv("ATLAS_BREACHED_PASSWORDS_FILE", str(listed))
    with pytest.raises(auth.AuthError, match="breached"):
        passwords.check_password_rules("correct-horse-battery")
    passwords.check_password_rules("an unlisted long phrase")


def test_the_first_admin_can_be_kept_as_a_hash_only(client, monkeypatch):
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "admin_password.py")], capture_output=True, text=True, timeout=60, check=True).stdout
    lines = out.splitlines()
    password, hashed = lines[1].strip(), lines[3].strip().split("=", 1)[1]
    assert len(password) >= 24 and password not in hashed
    monkeypatch.setenv("ATLAS_ADMIN_PASSWORD_HASH", hashed)
    monkeypatch.delenv("ATLAS_ADMIN_PASSWORD")
    assert client.post("/api/auth/login", json={"username": "qa-admin", "password": password}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "qa-admin", "password": "not-the-password-1"}).status_code == 401

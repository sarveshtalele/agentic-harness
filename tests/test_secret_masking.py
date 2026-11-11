"""Owner report 2026-11-11: with ATLAS_ADMIN_PASSWORD equal to the username "admin", every "admin" became *** ("Approved by ***").
A short secret is no longer substring-masked; a weak admin password is reported to the admin instead."""
from backend.core import security


def test_short_secret_does_not_corrupt_ordinary_words():
    security.register_secret("admin")
    assert security.redact("Approved by admin at gate 2") == "Approved by admin at gate 2"


def test_long_secret_is_still_masked_everywhere():
    value = "x" * 6 + "-not-a-real-value-" + "y" * 6
    security.register_secret(value)
    masked = security.redact(f"before {value} after")
    assert value not in masked and "***" in masked


def test_weak_admin_password_is_reported_without_returning_it():
    assert security.weak_secret("admin", "admin") == "shorter than 12 characters"
    assert security.weak_secret("Admin-account-1", "admin-account-1") == "the same as the username"
    assert security.weak_secret("a-long-unique-phrase", "admin") == ""

"""Shared fixtures and constants for the core unit tests."""

import pytest

from backend.db import db, new_id, now


@pytest.fixture
def project():
    project_id = new_id("prj")
    with db() as con:
        con.execute("INSERT INTO projects (id, name, created_at, updated_at) VALUES (?,?,?,?)", (project_id, "T", now(), now()))
    return project_id

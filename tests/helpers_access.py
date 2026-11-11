"""Shared world for the access tests: one project, one item of every kind, and an account of each kind around it."""
from __future__ import annotations

import pytest

from backend.core import auth
from backend.db import db, new_id, now
from tests.helpers_api import make_user, sign_in, unique


IDS = ("project_id", "doc_id", "run_id", "finding_id", "approval_id", "thread_id", "memory_id")


def account(admin, role="developer"):
    """A new signed-in account with the role: (client, user record)."""
    name = unique("acct")
    made = make_user(admin, name, role=role)
    other, response = sign_in(name)
    assert response.status_code == 200, response.text
    return other, made


class World:
    """One project owned by `owner`, one item of every kind in it, and an account of each kind around it."""

    def __init__(self, admin):
        self.admin = admin
        self.owner, self.owner_user = account(admin)
        self.project = self.owner.post("/api/projects", json={"name": "Shared"}).json()
        pid = self.project["id"]
        stamp = now()
        self.ids = {"project_id": pid,
                    "doc_id": self.owner.post(f"/api/projects/{pid}/documents", json={"kind": "brd", "title": "D", "content": "# T\n"}).json()["id"],
                    "thread_id": self.owner.post(f"/api/projects/{pid}/chats", json={}).json()["id"],
                    "memory_id": self.owner.post(f"/api/projects/{pid}/memories", json={"content": "note"}).json()["id"],
                    "run_id": new_id("run"), "finding_id": new_id("fnd"), "approval_id": new_id("apr")}
        with db() as con:
            con.execute("INSERT INTO runs (id, project_id, workflow, status, input, started_at) VALUES (?,?,?,?,?,?)", (self.ids["run_id"], pid, "ba", "waiting_approval", "{}", stamp))
            con.execute("INSERT INTO findings (id, project_id, source, rule, severity, title, file, line, evidence, fingerprint, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (self.ids["finding_id"], pid, "scan", "r", "low", "t", "f.py", 1, "e", new_id("fp"), stamp))
            con.execute("INSERT INTO approvals (id, run_id, project_id, gate, title, summary, created_at) VALUES (?,?,?,?,?,?,?)", (self.ids["approval_id"], self.ids["run_id"], pid, None, "T", "S", stamp))
        self.viewer, self.viewer_user = account(admin, "viewer")
        self.dev, self.dev_user = account(admin, "developer")
        self.demoted, self.demoted_user = account(admin, "developer")  # a developer account that is only a viewer in this project
        self.stranger, self.stranger_user = account(admin, "developer")
        self.lead, self.lead_user = account(admin, "qe_lead")
        for who, role in ((self.viewer_user, "developer"), (self.dev_user, "developer"), (self.demoted_user, "viewer"), (self.lead_user, "developer")):
            self.add(who, role)

    def add(self, user, role):
        response = self.owner.post(f"/api/projects/{self.project['id']}/members", json={"username": user["username"], "role": role})
        assert response.status_code == 201, response.text

    def persona(self, name):
        users = {"viewer": self.viewer_user, "developer": self.dev_user, "viewer-member": self.demoted_user, "stranger": self.stranger_user, "owner": self.owner_user}
        if name == "admin":
            return {"id": auth.ADMIN_ID, "role": "admin", "account_role": "admin"}
        return {"id": users[name]["id"], "role": "user", "account_role": users[name]["account_role"]}


@pytest.fixture
def world(client):
    return World(client)

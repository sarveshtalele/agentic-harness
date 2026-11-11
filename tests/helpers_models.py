"""Shared helpers for the model-access and limits tests."""

from contextlib import contextmanager
from datetime import datetime, timezone

from backend.core import auth, models
from backend.db import db, now

from tests.helpers_api import make_user, sign_in, unique


BA_BRIEF = {"brief": "Password reset link that expires in 30 minutes", "template_id": "builtin_brd", "title": "Reset BRD"}


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def at(monkeypatch, text: str) -> None:
    monkeypatch.setattr("backend.core.models.periods.clock", lambda: utc(text))


class As:
    """A signed-in user on the admin's test client. Background runs need that client's event loop, which a client opened without `with` closes after each request."""

    def __init__(self, admin, name):
        other, response = sign_in(name)
        assert response.status_code == 200, response.text
        self.admin, self.token = admin, other.cookies.get(auth.COOKIE)

    @contextmanager
    def _swapped(self):
        keep = self.admin.cookies.get(auth.COOKIE)
        self.admin.cookies.clear()
        self.admin.cookies.set(auth.COOKIE, self.token, domain="testserver.local", path="/")
        try:
            yield self.admin
        finally:
            self.admin.cookies.clear()
            self.admin.cookies.set(auth.COOKIE, keep, domain="testserver.local", path="/")

    def __getattr__(self, method):
        def call(*args, **kwargs):
            with self._swapped() as c:
                return getattr(c, method)(*args, **kwargs)

        return call

    @contextmanager
    def stream(self, *args, **kwargs):
        with self._swapped() as c, c.stream(*args, **kwargs) as response:
            yield response


def listed(*names):
    for name in names:
        models.add(name, enabled=True)


def account(client, models_=("m-a",), **extra):
    """A signed-in user with the given models ticked and the first as default. Returns (user record, client, project)."""
    listed(*models_)
    name = unique()
    user = make_user(client, name, models=list(models_), model=models_[0], **extra)
    other = As(client, name)
    return user, other, other.post("/api/projects", json={"name": "Mine", "description": ""}).json()


def spend(user_id, tokens, model="m-a", created_at=None, project_id=None):
    with db() as con:
        con.execute("INSERT INTO agent_calls (agent, project_id, source, prompt_ref, tokens_in, tokens_out, latency_ms, tool_calls, status, created_at, model, user_id) VALUES ('project-copilot', ?, 'chat', 'x', ?, 0, 1, 0, 'ok', ?, ?, ?)",
                    (project_id, tokens, created_at or now(), model, user_id))


def start_ba(c, project, **extra):
    return c.post(f"/api/projects/{project['id']}/runs", json={"workflow": "ba", "input": BA_BRIEF, **extra})

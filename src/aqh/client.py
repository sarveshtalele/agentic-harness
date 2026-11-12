"""The aqh client: signs in, finds the project for the current folder, and drives harness turns over AG-UI.

The same AG-UI stream the web and desktop apps use: one POST per turn, events back as server-sent events, approval
cards as interrupts the caller answers. Works with any httpx client, so tests pass FastAPI's TestClient. Every event of
a session is also written as one JSON line to `~/.aqh/projects/<folder>/<session>.jsonl` (Claude Code keeps sessions
the same way), so a session can be read back, resumed (`--resume`, `--continue`) and audited.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Callable, Iterator

from aqh import settings


class AqhError(RuntimeError):
    pass


def slug(folder: Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(folder.resolve()).strip("/\\"))[-120:] or "root"


class Session:
    def __init__(self, http, *, local: bool = True):
        self.http, self.local = http, local

    def _ok(self, response, what: str):
        if response.status_code >= 400:
            detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else response.text
            raise AqhError(f"{what} failed ({response.status_code}): {str(detail)[:300]}")
        return response.json() if response.content else {}

    def login(self, username: str, password: str) -> dict:
        return self._ok(self.http.post("/api/auth/login", json={"username": username, "password": password}), "Sign-in")

    def project_for(self, folder: Path) -> str:
        """The project for this folder: made once, bound to the folder itself in local mode."""
        index = settings.home() / "projects.json"
        known = json.loads(index.read_text(encoding="utf-8")) if index.is_file() else {}
        key = str(folder.resolve())
        project_id = known.get(key)
        if project_id and self.http.get(f"/api/projects/{project_id}").status_code == 200:
            return project_id
        made = self._ok(self.http.post("/api/projects", json={"name": folder.resolve().name or "workspace", "description": f"aqh: {key}"}), "Creating the project")
        if self.local:
            self._ok(self.http.post(f"/api/projects/{made['id']}/workspace", json={"path": key}), "Binding the folder")
        known[key] = made["id"]
        index.write_text(json.dumps(known, indent=1), encoding="utf-8")
        return made["id"]

    def new_thread(self, project_id: str) -> str:
        return self._ok(self.http.post(f"/api/projects/{project_id}/chats", json={"agent": "harness"}), "Starting a session")["id"]

    def latest_thread(self, project_id: str) -> str | None:
        threads = self._ok(self.http.get(f"/api/projects/{project_id}/chats"), "Listing sessions")
        return next((t["id"] for t in threads if t.get("agent") == "harness"), None)

    def _stream(self, thread_id: str, text: str | None, run: str, resume=None) -> Iterator[dict]:
        body = {"threadId": thread_id, "runId": run, "messages": [{"id": f"m_{run}", "role": "user", "content": text}] if text else [],
                "state": {}, "tools": [], "context": [], "forwardedProps": {}}
        if resume:
            body["resume"] = resume
        with self.http.stream("POST", "/agui/harness", json=body, timeout=None) as response:
            if response.status_code >= 400:
                raise AqhError(f"The turn failed ({response.status_code}): {response.read().decode(errors='replace')[:300]}")
            for line in response.iter_lines():
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    def turn(self, thread_id: str, text: str, decide: Callable[[dict], bool], on_event: Callable[[dict], None], folder: Path) -> None:
        """One user turn, approval cards answered by `decide(card)`, every event passed to `on_event` and the session log."""
        log = settings.home() / "projects" / slug(folder)
        log.mkdir(parents=True, exist_ok=True)
        with (log / f"{thread_id}.jsonl").open("a", encoding="utf-8") as out:
            def emit(event: dict) -> None:
                out.write(json.dumps({"t": time.time(), **event}) + "\n")
                on_event(event)

            out.write(json.dumps({"t": time.time(), "type": "USER_TEXT", "text": text}) + "\n")  # the session file only
            run, answers = f"r{int(time.time() * 1000)}", None
            for round_ in range(200):
                last = None
                for event in self._stream(thread_id, text if round_ == 0 else None, f"{run}_{round_}", answers):
                    emit(event)
                    last = event
                interrupts = (last or {}).get("outcome", {}).get("interrupts") if (last or {}).get("type") == "RUN_FINISHED" else None
                if not interrupts:
                    return
                answers = [{"interruptId": i["id"], "status": "resolved", "payload": {"approved": bool(decide(i))}} for i in interrupts]
            raise AqhError("Stopped after 200 approval rounds in one turn")

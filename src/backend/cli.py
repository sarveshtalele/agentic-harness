"""Terminal harness: the same MAF harness as the web and desktop app, reached through the running backend's AG-UI route.

The CLI holds no agent of its own, so the terminal gets the same tools, skills, plugin commands, governance, audit
and per-project memory as the browser.

Usage:
  bin/harness --project <project id> "prompt"     one turn, then exit
  bin/harness --project <project id>              interactive; /help lists the commands
  bin/harness --projects                          list the projects you can see

Sign-in: ATLAS_CLI_USERNAME and ATLAS_CLI_PASSWORD, or a prompt (the password is read with getpass and never echoed).
The backend address is ATLAS_API_URL (default http://127.0.0.1:8000).
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import uuid

import httpx

HELP = """Commands:
  /help              this list
  /new               start a new chat thread
  /todos             the thread's todos
  /commands [text]   plugin commands and skills (filtered by text)
  /exit              leave
Anything else, including /plugin:command args, goes to the harness."""
STATUS = {"scan_repository": "Analysing the repository", "run_tests": "Running tests", "load_skill": "Loading a skill",
          "start_workflow": "Starting a workflow", "save_document": "Saving a document", "read_file": "Reading a file",
          "grep": "Searching the code", "list_files": "Listing files"}


class Session:
    def __init__(self, base: str):
        self.http = httpx.Client(base_url=base, timeout=httpx.Timeout(30, read=900))

    def sign_in(self) -> None:
        user = os.environ.get("ATLAS_CLI_USERNAME") or input("Username: ")
        password = os.environ.get("ATLAS_CLI_PASSWORD") or getpass.getpass("Password: ")
        got = self.http.post("/api/auth/login", json={"username": user, "password": password})
        if got.status_code != 200:
            raise SystemExit(f"Sign-in failed ({got.status_code}): {got.json().get('detail', got.text)[:200]}")

    def get(self, path: str):
        got = self.http.get(path)
        if got.status_code >= 400:
            raise SystemExit(f"{path} failed ({got.status_code}): {got.text[:300]}")
        return got.json()

    def new_thread(self, project: str) -> str:
        got = self.http.post(f"/api/projects/{project}/chats", json={"agent": "harness", "title": "New chat"})
        if got.status_code != 201:
            raise SystemExit(f"Could not open a harness chat ({got.status_code}): {got.text[:300]}")
        return got.json()["id"]

    def turn(self, thread: str, text: str, out=sys.stdout) -> str:
        """One harness turn. Prints text as it streams and a status line per tool call; returns the reply."""
        body = {"threadId": thread, "runId": f"cli_{uuid.uuid4().hex[:12]}", "state": {}, "tools": [], "context": [], "forwardedProps": {},
                "messages": [{"id": f"m_{uuid.uuid4().hex[:12]}", "role": "user", "content": text}]}
        reply: list[str] = []
        with self.http.stream("POST", "/agui/harness", json=body) as response:
            if response.status_code != 200:
                raise SystemExit(f"Harness refused the turn ({response.status_code}): {response.read().decode()[:300]}")
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:])
                kind = event.get("type")
                if kind == "TEXT_MESSAGE_CONTENT":
                    reply.append(event["delta"])
                    out.write(event["delta"])
                    out.flush()
                elif kind == "TOOL_CALL_START":
                    name = event.get("toolCallName", "")
                    out.write(f"\n  ... {STATUS.get(name, 'Using ' + name)}\n")
                elif kind == "RUN_ERROR":
                    out.write(f"\nError {event.get('code', '')}: {event.get('message', '')}\n")
        out.write("\n")
        return "".join(reply)


def _repl(session: Session, project: str) -> None:
    thread = session.new_thread(project)
    print(f"Harness on project {project}, thread {thread}. /help lists commands.")
    while True:
        try:
            text = input("\nharness> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text in ("/exit", "/quit"):
            return
        if text == "/help":
            print(HELP)
        elif text == "/new":
            thread = session.new_thread(project)
            print(f"New thread {thread}")
        elif text == "/todos":
            todos = session.get(f"/api/chats/{thread}/todos")
            print("\n".join(f"[{'x' if t['done'] else ' '}] {t['title']}" for t in todos["todos"]) or "No todos yet")
        elif text.startswith("/commands"):
            needle = text[len("/commands"):].strip().lower()
            for entry in session.get("/api/plugins/slash"):
                if needle in entry["name"].lower():
                    print(f"/{entry['name']:<40} {entry['kind']:<8} {entry['description'][:70]}")
        else:
            session.turn(thread, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description="Agentic QE Platform harness in the terminal")
    parser.add_argument("--project", help="project id")
    parser.add_argument("--projects", action="store_true", help="list the projects you can see and exit")
    parser.add_argument("prompt", nargs="*", help="one prompt; without it the harness is interactive")
    args = parser.parse_args(argv)
    session = Session(os.environ.get("ATLAS_API_URL", "http://127.0.0.1:8000"))
    try:
        session.sign_in()
        if args.projects or not args.project:
            for project in session.get("/api/projects"):
                print(f"{project['id']:<24} {project['name']}")
            if not args.projects:
                print("\nPick one with --project <id>.")
            return 0
        if args.prompt:
            session.turn(session.new_thread(args.project), " ".join(args.prompt))
        else:
            _repl(session, args.project)
    except httpx.HTTPError as exc:
        raise SystemExit(f"Cannot reach the backend at {session.http.base_url}: {exc}. Start it with: python scripts/dev.py backend") from None
    return 0


if __name__ == "__main__":
    sys.exit(main())

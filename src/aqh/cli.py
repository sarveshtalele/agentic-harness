"""`aqh`, the Agentic QE Harness in a terminal (docs/PHASE2_PLAN.md section 11.1) on macOS, Windows and Linux.

    aqh                         interactive session in this folder
    aqh "fix the failing test"  interactive, starting with that request
    aqh -p "..." [--output-format text|json|stream-json] [--permission-mode M] [--allowedTools R ...] [--disallowedTools R ...]
    aqh --continue | --resume <session>   carry on a session of this folder
    aqh --server https://host   connected mode: a platform server instead of the local one (AQH_USERNAME / AQH_PASSWORD)
    aqh doctor                  what this machine gives the harness
    aqh config model --base-url URL --name MODEL   |   aqh config set-key   (the key goes to the OS keychain)
    aqh server status|stop
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

import httpx

from aqh import doctor, headless, server, settings
from aqh.client import AqhError, Session


def _session(args) -> tuple[Session, str]:
    if args.server:
        http = httpx.Client(base_url=args.server.rstrip("/"), timeout=None)
        session = Session(http, local=False)
        username = os.environ.get("AQH_USERNAME") or input("Username: ")
        session.login(username, os.environ.get("AQH_PASSWORD") or getpass.getpass("Password: "))
        return session, args.server
    model = settings.model({"base_url": args.base_url, "name": args.model})
    running = server.start(model, say=lambda text: print(text, file=sys.stderr))
    session = Session(httpx.Client(base_url=running["url"], timeout=None))
    creds = server.credentials()
    session.login(creds["username"], creds["password"])
    return session, running["url"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aqh", description="Agentic QE Harness in your terminal")
    parser.add_argument("words", nargs="*", help="a first request, or: doctor | config ... | server ...")
    parser.add_argument("-p", "--print", dest="headless", action="store_true", help="answer once and exit (for scripts and CI)")
    parser.add_argument("--output-format", choices=["text", "json", "stream-json"], default="text")
    parser.add_argument("--permission-mode", choices=list(headless.PERMISSION_MODES))
    parser.add_argument("--allowedTools", nargs="*", default=[])
    parser.add_argument("--disallowedTools", nargs="*", default=[])
    parser.add_argument("--continue", dest="cont", action="store_true", help="continue this folder's latest session")
    parser.add_argument("--resume", metavar="SESSION")
    parser.add_argument("--server", help="a platform server URL (connected mode)")
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--name", help="with `config model`: the model name")
    args = parser.parse_args(argv)
    words = args.words
    try:
        if words[:1] == ["doctor"]:
            print(doctor.report())
            return 0
        if words[:1] == ["server"]:
            print(server.stop() if words[1:2] == ["stop"] else (server.status() or "No local server is running."))
            return 0
        if words[:2] == ["config", "set-key"]:
            settings.keychain_set(getpass.getpass("Model API key (not shown): "))
            print("Saved in the OS keychain.")
            return 0
        if words[:2] == ["config", "model"]:
            print(f"Saved to {settings.save_model(args.base_url, args.name or args.model)}. Restart the local server: aqh server stop")
            return 0
        folder = Path.cwd()
        session, where = _session(args)
        project_id = session.project_for(folder)
        thread_id = args.resume or (session.latest_thread(project_id) if args.cont else None) or session.new_thread(project_id)
        prompt = " ".join(words)
        if args.headless:
            if not prompt:
                prompt = sys.stdin.read()
            return headless.run(session, project_id, thread_id, prompt, output=args.output_format, mode=args.permission_mode,
                                allowed=args.allowedTools, disallowed=args.disallowedTools, folder=folder)
        from aqh import repl

        if prompt:
            session.turn(thread_id, prompt, lambda card: input(f"{card.get('message')} [y/N] ").strip().lower() in ("y", "yes"),
                         repl._printer(repl.Console()), folder)
        repl.run(session, project_id, thread_id, folder)
        return 0
    except (AqhError, RuntimeError, httpx.HTTPError) as exc:
        print(f"aqh: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

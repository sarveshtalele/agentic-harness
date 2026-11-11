"""Facts and notes about the repository's test environment."""
from __future__ import annotations

import re
from pathlib import Path
from backend.qe.execution.runners import detect_python


def environment_facts(worktree: Path, declared: set[str] | frozenset = frozenset()) -> dict:
    """What the sandbox Python has, read without changing anything: httpx version, pytest-asyncio, and rate limiters in the application."""
    from backend.qe import emit
    from backend.repos import scan

    python = detect_python(worktree)
    inv = emit.inventory(python)
    versions = inv["versions"] if inv else {}
    limiters = [{"kind": name, "where": "dependency"} for name in LIMITER_PACKAGES if name in versions or name in declared]
    sources = [p for p in scan.tree(worktree, 5000) if p.endswith(".py") and not p.startswith(("tests/", "test/")) and "/tests/" not in p]
    for rel in sources[:600]:
        text = scan._read(worktree / rel)
        if found := LIMITER_CODE.search(text):
            limiters.append({"kind": "in-repository", "where": f"{rel}:{text.count(chr(10), 0, found.start()) + 1}"})
        if len(limiters) >= 6:
            break
    return {"python": python, "inventory": inv is not None, "httpx": versions.get("httpx"), "httpx_declared": "httpx" in declared, "pytest_asyncio": "pytest-asyncio" in versions,
            "pytest_asyncio_declared": "pytest-asyncio" in declared, "rate_limiters": limiters}


LIMITER_PACKAGES = ("slowapi", "flask-limiter", "fastapi-limiter", "django-ratelimit", "ratelimit")


LIMITER_CODE = re.compile(r"\bLimiter\(|@\w*limiter\.limit|\bRateLimit\w*\(|\brate_limit\w*|\bratelimit\b|slowapi|flask_limiter|status_code\s*=\s*429|HTTP_429")


def environment_notes(facts: dict, install_deps: bool = False) -> str:
    """Instructions for the generation prompt, built only from what was detected."""
    notes = []
    version = tuple(int(x) for x in re.findall(r"\d+", facts.get("httpx") or "")[:2])
    if version >= (0, 28):
        notes.append(f"httpx {facts['httpx']} is installed. It no longer accepts app=. For an ASGI app use httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test'); for a WSGI app use httpx.WSGITransport(app=app).")
    elif version:
        notes.append(f"httpx {facts['httpx']} is installed. Use app= only if that version accepts it; httpx.ASGITransport(app=app) works on it too.")
    elif facts.get("httpx_declared"):
        notes.append("httpx is a dependency but its version is not known yet. Use transport=httpx.ASGITransport(app=app) and never app=, which new versions removed.")
    if facts.get("pytest_asyncio"):
        notes.append("pytest-asyncio is available and the platform runs with asyncio_mode=auto, so async def tests need no marker.")
    elif install_deps:
        notes.append("pytest-asyncio will be installed before the tests run, and the platform runs with asyncio_mode=auto, so async def tests need no marker.")
    else:
        notes.append("pytest-asyncio is NOT available. Write only synchronous tests and call asyncio.run() for any coroutine.")
    if facts.get("rate_limiters"):
        where = ", ".join(f"{x['kind']} ({x['where']})" for x in facts["rate_limiters"][:4])
        notes.append(f"The application has a rate limiter: {where}. Reset or disable it in a fixture (for example limiter.reset() or limiter.enabled = False) and send as few requests as the case needs. Never expect 429 unless the case says so.")
    notes.append("Do not assume a server is running on any port. Call the application object through its test client.")
    return "ENVIRONMENT (detected on this machine):\n" + "\n".join(f"- {n}" for n in notes)

"""The stable build has no harness, desktop app or command-line tool (docs/STABLE_BUILD_PLAN.md, Part A).

They moved to branch feature/harness-rebuild. This test fails if any of them comes back by accident: a route, an import,
a page or a link."""
import re
from pathlib import Path

from tests.helpers_api import client, project  # noqa: F401 - fixtures

ROOT = Path(__file__).resolve().parents[1]
GONE = re.compile(r"maf\.harness|harness_kit|from backend\.maf import harness|core\.auth\.desktop|cli_workspaces|\baqh\b")


def test_harness_routes_answer_404(client, project):  # noqa: F811
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"})
    assert thread.status_code == 400  # "harness" is not an agent any more
    assert client.post("/agui/harness", json={"threadId": "thr_x", "messages": []}).status_code == 404
    for path in ("/api/chats/thr_x/todos", "/api/chats/thr_x/terminal", "/api/downloads", "/api/auth/desktop"):
        assert client.get(path).status_code in (404, 405), path


def test_no_source_imports_or_links_the_harness():
    python = [p for p in (ROOT / "src").rglob("*.py") if "__pycache__" not in p.parts]
    assert not [str(p) for p in python if GONE.search(p.read_text(encoding="utf-8"))]
    ui = [p for p in (ROOT / "src" / "frontend").rglob("*.tsx") if "node_modules" not in p.parts and not any(s.startswith(".next") for s in p.parts)]
    assert not [str(p) for p in ui if re.search(r"""["'`]/harness\b|DesktopDownloads|TerminalPane""", p.read_text(encoding="utf-8"))]
    assert not (ROOT / "apps" / "desktop" / "package.json").exists() and not (ROOT / "src" / "aqh").exists()

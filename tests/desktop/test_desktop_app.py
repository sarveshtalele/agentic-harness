"""Drives the dev-mode Electron app with Playwright against a real platform server on loopback (the team's server in
R6 central sign-in). Needs: npm install in apps/desktop, a UI build (python scripts/desktop_build.py --ui), and
AQE_DESKTOP_TEST=1."""
import os
import secrets
import socket
import sys
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import pytest

DESKTOP = Path(__file__).resolve().parents[2] / "apps" / "desktop"
ELECTRON = DESKTOP / "node_modules" / ".bin" / ("electron.cmd" if os.name == "nt" else "electron")

pytestmark = [
    pytest.mark.desktop,
    pytest.mark.skipif(os.environ.get("AQE_DESKTOP_TEST") != "1" or not ELECTRON.exists(),
                       reason="Electron is not installed: run npm install in apps/desktop and set AQE_DESKTOP_TEST=1"),
]


class _App:
    """The real Electron app, attached over CDP (Python Playwright has no Electron launcher)."""

    def __init__(self, browser):
        self.browser = browser

    def _pump(self):
        """Let Playwright process CDP events (new windows); time.sleep alone would not."""
        try:
            self.browser.contexts[0].wait_for_event("page", timeout=1000)
        except Exception:  # a timeout only means no new window this second
            pass

    def windows(self):
        return [page for context in self.browser.contexts for page in context.pages]

    def first_window(self, timeout=60.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.windows():
                return self.windows()[0]
            self._pump()
        raise AssertionError("the app opened no window")

    def wait_for_window(self, predicate, timeout=150.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            found = [w for w in self.windows() if predicate(w)]
            if found:
                return found[0]
            self._pump()
        raise AssertionError("the expected window never opened")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """The team's server: the platform in the local profile, with a member created by its admin."""
    root, port = DESKTOP.parents[1], _free_port()
    env = {**os.environ, "ATLAS_PROFILE": "local", "ATLAS_DATA_DIR": str(tmp_path_factory.mktemp("server-data")),
           "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)])}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=root, env=env)
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 90
        while True:
            try:
                if httpx.get(f"{url}/api/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            assert proc.poll() is None and time.time() < deadline, "the server did not start"
            time.sleep(0.5)
        admin = httpx.Client(base_url=url)
        assert admin.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        member = {"username": f"desk{time.time_ns()}", "password": secrets.token_urlsafe(18)}
        assert admin.post("/api/users", json={**member, "role": "developer"}).status_code == 201
        yield url, member
    finally:
        proc.terminate()
        proc.wait(timeout=30)


@pytest.fixture(scope="module")
def app(server):
    from playwright.sync_api import sync_playwright

    user_data = os.environ.get("AQE_DESKTOP_USER_DATA_DIR") or tempfile.mkdtemp(prefix="aqe-desktop-")
    port = os.environ.get("AQE_DESKTOP_CDP_PORT", "19222")
    env = {**os.environ, "AQE_DESKTOP_USER_DATA": user_data, "AQE_DESKTOP_SERVER": server[0]}
    process = subprocess.Popen([str(ELECTRON), str(DESKTOP), f"--remote-debugging-port={port}"], env=env)
    try:
        with sync_playwright() as p:
            deadline = time.time() + 60
            while True:
                try:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                    break
                except Exception:
                    if time.time() > deadline or process.poll() is not None:
                        raise
                    time.sleep(1)
            yield _App(browser)
    finally:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
        if not os.environ.get("AQE_DESKTOP_KEEP"):  # keep logs for debugging a failed start
            shutil.rmtree(user_data, ignore_errors=True)


def test_sign_in_through_the_server_then_the_app_opens_signed_in(app, server):
    url, member = server
    form = app.first_window()
    assert "sign-in" in form.title().lower() and form.input_value("#server") == url
    form.fill("#username", member["username"])
    form.fill("#password", "not-the-password-at-all")
    form.click("#save")
    form.locator("#error").filter(has_text="not correct").wait_for(timeout=30000)  # the page's CSP forbids eval
    form.fill("#password", member["password"])
    form.click("#save")
    # the form closes; the main window opens signed in as that member, with no local admin and no local password
    main = app.wait_for_window(lambda w: w.url.startswith("http://127.0.0.1") and "/login" not in w.url)
    main.wait_for_load_state()
    origin = "/".join(main.url.split("/")[:3])
    me = main.request.get(f"{origin}/api/auth/me")
    assert me.status == 200 and me.json()["username"] == member["username"] and me.json()["role"] != "admin"
    assert main.request.get(f"{origin}/harness").status < 500


def test_the_terminal_pane_runs_a_real_shell_in_the_project_workspace(app, server):
    import io
    import zipfile

    main = app.wait_for_window(lambda w: w.url.startswith("http://127.0.0.1") and "/login" not in w.url)
    origin = "/".join(main.url.split("/")[:3])
    project = main.request.post(f"{origin}/api/projects", data={"name": f"term{time.time_ns()}"}).json()
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w") as z:
        z.writestr("README.md", "# terminal fixture\n")
        z.writestr("src/main.py", "print('hi')\n")
    uploaded = main.request.post(f"{origin}/api/projects/{project['id']}/repo/zip",
                                 multipart={"file": {"name": "app.zip", "mimeType": "application/zip", "buffer": packed.getvalue()}})
    assert uploaded.ok, uploaded.text()
    thread = main.request.post(f"{origin}/api/projects/{project['id']}/chats", data={"agent": "harness"}).json()
    found = main.evaluate("""async (threadId) => {
        let out = "";
        const stop = window.aqeTerminal.onData((id, data) => { out += data; });
        const made = await window.aqeTerminal.open(threadId, 100, 24);
        if (made.error) return { error: made.error };
        window.aqeTerminal.write(made.id, "ls\\r");
        window.aqeTerminal.write(made.id, "echo TERM-$((40 + 2))\\r");
        for (let i = 0; i < 100 && !out.includes("TERM-42"); i++) await new Promise((r) => setTimeout(r, 100));
        window.aqeTerminal.close(made.id);
        stop();
        return { ...made, out };
    }""", thread["id"])
    assert "error" not in found, found
    assert "TERM-42" in found["out"] and "README.md" in found["out"]  # a real shell, started in the project's workspace
    assert main.evaluate("window.aqeTerminal.open('thr_not_mine', 80, 24)").get("error")  # another chat's folder is refused
    # the pane on the harness page: a new terminal tab renders xterm and echoes what is typed
    main.goto(f"{origin}/harness?project={project['id']}")
    main.get_by_role("button", name="New terminal").click(timeout=60000)
    main.locator("[data-testid=terminal-pty] .xterm").wait_for(timeout=30000)
    main.locator("[data-testid=terminal-pty] .xterm").click()
    main.keyboard.type("echo PANE-$((6 * 7))\n")
    main.locator("[data-testid=terminal-pty]").filter(has_text="PANE-42").wait_for(timeout=30000)
    shots = Path(os.environ.get("AQE_DESKTOP_SHOTS") or tempfile.gettempdir())  # the prompt shows the machine's user and host
    shots.mkdir(parents=True, exist_ok=True)
    main.screenshot(path=str(shots / "terminal-pane.png"))

"""Drives the dev-mode Electron app with Playwright. Needs: npm install in apps/desktop, a UI build
(python scripts/desktop_build.py --ui), and AQE_DESKTOP_TEST=1."""
import os
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

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


@pytest.fixture(scope="module")
def app():
    from playwright.sync_api import sync_playwright

    user_data = os.environ.get("AQE_DESKTOP_USER_DATA_DIR") or tempfile.mkdtemp(prefix="aqe-desktop-")
    port = os.environ.get("AQE_DESKTOP_CDP_PORT", "19222")
    env = {**os.environ, "AQE_DESKTOP_USER_DATA": user_data}
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


def test_first_run_setup_then_login_then_harness(app):
    setup = app.first_window()
    assert "setup" in setup.title().lower()
    setup.fill("#username", "desktop-admin")
    setup.fill("#password", "short")
    setup.click("#save")
    assert "12 characters" in setup.inner_text("#error")
    setup.fill("#password", secrets.token_urlsafe(18))
    setup.click("#save")
    # the setup window closes; the main window opens on /login once the backend and UI answer
    main = app.wait_for_window(lambda w: "/login" in w.url)
    main.wait_for_load_state()
    assert "/login" in main.url
    assert main.locator("input[type=password]").count() >= 1
    # the harness page is routed (it redirects to login until signed in, so check the route answers)
    response = main.request.get(main.url.replace("/login", "/harness"))
    assert response.status < 500

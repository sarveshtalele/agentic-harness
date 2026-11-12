"""UI audit (owner request, 2026-11-12): every page, signed out and as admin, desktop and phone, light and dark.

Each page gets a full-page screenshot in docs/evidence/ui-audit/ and automatic checks:
- browser errors (page errors and console errors) and failed requests (HTTP 400 or more, network failures);
- leaked raw text: undefined, null, NaN, [object Object], template braces, stack traces, raw error JSON;
- layout: horizontal page scroll, and text cut off inside a box that hides overflow;
- accessibility basics: images without alt text, buttons and links without a name.
Findings go to docs/evidence/ui-audit/findings.json; the test fails while any remain.
"""
import json
import re

import pytest

from tests.e2e.conftest import EVIDENCE, UI

pytestmark = pytest.mark.e2e
OUT = EVIDENCE / "ui-audit"
SIGNED_OUT = ["/", "/login"]
PAGES = ["/projects", "/harness", "/documents", "/templates", "/skills", "/skills/studio", "/agents", "/mcp", "/capabilities",
         "/approvals", "/findings", "/traces", "/observability", "/usage", "/users", "/settings", "/account", "/docs"]
PROJECT_PAGES = ["", "/chat", "/ba", "/qe", "/bugs", "/feature", "/documents", "/repository", "/runs", "/approvals", "/governance",
                 "/observability", "/prompts"]
LEAK = re.compile(r"\bundefined\b|\bNaN\b|\[object Object\]|\{\{|\}\}|Traceback \(most recent|at [A-Za-z_.]+ \(.*:\d+:\d+\)|"
                  r"\"detail\":|Internal Server Error|\bnull\b")
CHECKS = """() => {
  const out = {overflowX: document.documentElement.scrollWidth > window.innerWidth + 1, clipped: [], noAlt: [], noName: []};
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || !el.offsetParent && s.position !== 'fixed') continue;
    const text = (el.innerText || '').trim();
    if (text && el.children.length === 0 && (s.overflow === 'hidden' || s.overflowX === 'hidden') && s.textOverflow !== 'ellipsis'
        && el.scrollWidth > el.clientWidth + 2) out.clipped.push(text.slice(0, 60));
  }
  for (const img of document.querySelectorAll('img')) if (!img.hasAttribute('alt')) out.noAlt.push(img.src.slice(-60));
  for (const el of document.querySelectorAll('button, a[href]')) {
    const name = (el.getAttribute('aria-label') || el.innerText || el.title || '').trim();
    if (!name && !el.querySelector('img[alt]:not([alt=""]), svg title')) out.noName.push(el.outerHTML.slice(0, 80));
  }
  out.clipped = out.clipped.slice(0, 10); out.noName = out.noName.slice(0, 10);
  return out;
}"""


def _audit(browser_page, path: str, label: str, findings: list) -> None:
    errors, failed = [], []
    browser_page.on("pageerror", lambda e: errors.append(f"page error: {str(e)[:200]}"))
    browser_page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text[:200]}"))
    browser_page.on("response", lambda r: r.status >= 400 and failed.append(f"HTTP {r.status} {r.url.replace(UI, '')[:120]}"))
    browser_page.on("requestfailed", lambda r: failed.append(f"failed {r.url.replace(UI, '')[:120]}"))
    browser_page.goto(f"{UI}{path}", wait_until="networkidle")
    browser_page.wait_for_timeout(800)
    name = f"{label}{path.replace('/', '_') or '_home'}.png"
    browser_page.screenshot(path=str(OUT / name), full_page=True)
    text = browser_page.inner_text("body")
    leaks = sorted({m.group(0) for m in LEAK.finditer(text)})
    layout = browser_page.evaluate(CHECKS)
    for kind, items in (("browser error", errors), ("request", failed), ("leaked text", leaks), ("clipped text", layout["clipped"]),
                        ("image without alt", layout["noAlt"]), ("control without a name", layout["noName"])):
        for item in items:
            findings.append({"page": path, "view": label, "kind": kind, "detail": item, "screenshot": name})
    if layout["overflowX"]:
        findings.append({"page": path, "view": label, "kind": "horizontal scroll", "detail": "page is wider than the window", "screenshot": name})


def test_every_page_is_clean_in_every_view(page):
    OUT.mkdir(parents=True, exist_ok=True)
    project = page.request.post(f"{UI}/api/projects", data={"name": "UI audit", "description": "audit of every page"}).json()
    paths = PAGES + [f"/projects/{project['id']}{p}" for p in PROJECT_PAGES]
    storage = page.context.storage_state()
    browser = page.context.browser
    findings: list = []
    views = [("desktop-light", {"width": 1440, "height": 900}, "light"), ("desktop-dark", {"width": 1440, "height": 900}, "dark"),
             ("phone-light", {"width": 390, "height": 844}, "light")]
    for label, viewport, scheme in views:
        signed_out = browser.new_context(viewport=viewport, color_scheme=scheme)
        for path in SIGNED_OUT:
            tab = signed_out.new_page()
            _audit(tab, path, f"{label}-out", findings)
            tab.close()
        signed_out.close()
        signed_in = browser.new_context(viewport=viewport, color_scheme=scheme, storage_state=storage)
        for path in paths:
            tab = signed_in.new_page()
            _audit(tab, path, label, findings)
            tab.close()
        signed_in.close()
    (OUT / "findings.json").write_text(json.dumps(findings, indent=1), encoding="utf-8")
    summary = {}
    for f in findings:
        summary[f["kind"]] = summary.get(f["kind"], 0) + 1
    assert not findings, f"{len(findings)} UI findings {summary}; see {OUT / 'findings.json'}"

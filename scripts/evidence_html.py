"""HTML evidence report: one section per user story with its test results and screenshots. Standard library only.

A story's result comes only from JUnit cases whose test name carries the story id (test_us51_..., test_hs01_hs03_...):
PASS when every matching case passed, FAIL when any failed, NOT RUN when no case matched. Screenshots are matched the
same way by file name (us-51-*.png, hs-01-03-*.png) and copied next to the report, so the folder is self-contained.
"""
from __future__ import annotations

import html
import re
import shutil
import defusedxml.ElementTree as ET  # JUnit files can carry text from the code under test
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORY_FILES = (ROOT / "docs" / "USER_STORIES.md", ROOT / "docs" / "HARNESS_USER_STORIES.md")
ROW = re.compile(r"^\|\s*((?:US|HS)-\d+)\s*\|(.+)\|\s*$")


def stories() -> list[dict]:
    """Every story row in the story documents: id, the row's cells, and the oracle (last cell)."""
    found, seen = [], set()
    for path in STORY_FILES:
        for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
            match = ROW.match(line)
            if match and match.group(1) not in seen:
                seen.add(match.group(1))
                cells = [c.strip() for c in match.group(2).split("|")]
                found.append({"id": match.group(1), "cells": cells, "oracle": cells[-1]})
    return found


def _ids_in(name: str) -> set[str]:
    """Story ids named in a test or file name: test_us51_x -> US-51; hs-01-03-plan -> HS-01, HS-03."""
    found = set()
    for kind, rest in re.findall(r"(?i)(us|hs)[-_]?((?:\d{2}[-_]?)+)", name):
        found |= {f"{kind.upper()}-{n}" for n in re.findall(r"\d{2}", rest)}
    return found


def cases(junit_files: list[Path]) -> list[dict]:
    out = []
    for path in junit_files:
        if not path.is_file():
            continue
        for case in ET.parse(path).getroot().iter("testcase"):
            bad = case.find("failure") if case.find("failure") is not None else case.find("error")
            state = "skipped" if case.find("skipped") is not None else ("failed" if bad is not None else "passed")
            out.append({"name": case.get("name", ""), "state": state, "time": float(case.get("time", 0) or 0),
                        "message": (bad.get("message") or "")[:400] if bad is not None else "", "ids": _ids_in(case.get("name", ""))})
    return out


def _status(matched: list[dict]) -> str:
    ran = [c for c in matched if c["state"] != "skipped"]
    if not ran:
        return "NOT RUN"
    return "FAIL" if any(c["state"] == "failed" for c in ran) else "PASS"


def write(report: dict, out: Path, junit_files: list[Path], screens: Path | None) -> Path:
    all_cases = cases(junit_files)
    shots = sorted(screens.rglob("*.png")) if screens and screens.is_dir() else []
    (out / "shots").mkdir(parents=True, exist_ok=True)
    sections, counts = [], {"PASS": 0, "FAIL": 0, "NOT RUN": 0}
    for story in stories():
        matched = [c for c in all_cases if story["id"] in c["ids"]]
        images = [s for s in shots if story["id"] in _ids_in(s.stem)]
        for image in images:
            shutil.copy2(image, out / "shots" / image.name)
        status = _status(matched)
        counts[status] += 1
        rows = "".join(f"<li class='{c['state']}'>{html.escape(c['name'])} <b>{c['state']}</b> {c['time']:.1f}s"
                       f"{'<pre>' + html.escape(c['message']) + '</pre>' if c['message'] else ''}</li>" for c in matched)
        figs = "".join(f"<figure><a href='shots/{html.escape(i.name)}'><img src='shots/{html.escape(i.name)}' alt='{html.escape(i.stem)}'></a>"
                       f"<figcaption>{html.escape(i.stem)}</figcaption></figure>" for i in images)
        sections.append(f"<section id='{story['id']}'><h2><span class='{status.replace(' ', '-')}'>{status}</span> {story['id']}</h2>"
                        f"<p>{html.escape(' · '.join(story['cells'][:-1]))}</p><p><b>Oracle:</b> {html.escape(story['oracle'])}</p>"
                        f"<ul>{rows or '<li>No test ran for this story.</li>'}</ul><div class='shots'>{figs or '<p>No screenshot.</p>'}</div></section>")
    levels = "".join(f"<tr><td>{html.escape(n)}</td><td>{lv['verdict']}</td><td>{lv.get('executed', 'not run')}</td><td>{lv.get('passed', '')}</td>"
                     f"<td>{lv.get('failures', '')}</td><td>{lv.get('errors', '')}</td></tr>" for n, lv in report["levels"].items())
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidence {html.escape(report['git'])}</title><style>
body{{font:14px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:16px;color:#1e293b;background:#fff}}
table{{border-collapse:collapse}}td,th{{border:1px solid #cbd5e1;padding:4px 8px}}section{{border-top:1px solid #e2e8f0;padding:8px 0}}
.PASS{{color:#047857}}.FAIL{{color:#b91c1c}}.NOT-RUN{{color:#92400e}}li.failed{{color:#b91c1c}}pre{{white-space:pre-wrap;background:#f8fafc}}
.shots{{display:flex;flex-wrap:wrap;gap:8px}}img{{max-width:320px;border:1px solid #cbd5e1}}figure{{margin:0}}figcaption{{font-size:12px}}
</style></head><body><h1>Evidence report {html.escape(report['git'])}</h1>
<p>Generated {html.escape(report['generated_at'])} · model {html.escape(report['model'])} · overall <b>{report['overall']}</b> ·
stories: {counts['PASS']} pass, {counts['FAIL']} fail, {counts['NOT RUN']} not run</p>
<table><tr><th>Level</th><th>Verdict</th><th>Executed</th><th>Passed</th><th>Failed</th><th>Errors</th></tr>{levels}</table>
{''.join(sections)}</body></html>"""
    target = out / "report.html"
    target.write_text(page, encoding="utf-8")
    return target

#!/usr/bin/env python3
"""Evidence report from what actually ran. Standard library only.

  python scripts/evidence_report.py --level unit=data/evidence/unit.xml --level smoke=data/evidence/smoke.xml \
      [--screens docs/evidence/screens] [--model <id>] [--out docs/evidence/runs]

Each level's verdict is computed here from its JUnit XML, never typed in:
PASS when executed > 0 and failures + errors = 0, FAIL when any failed, INCONCLUSIVE when nothing executed
or the file is missing. Levels that did not run are listed under "Not verified".
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_junit(path: Path) -> dict:
    """Totals and failing cases from a pytest or Playwright JUnit file."""
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    total = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    failing = []
    for suite in suites:
        for key in ("tests", "failures", "errors", "skipped"):
            total[key] += int(suite.get(key, 0) or 0)
        total["time"] += float(suite.get("time", 0) or 0)
        for case in suite.iter("testcase"):
            bad = case.find("failure")
            bad = bad if bad is not None else case.find("error")
            if bad is not None:
                name = f"{case.get('classname', '')}::{case.get('name', '')}"
                failing.append({"case": name, "message": (bad.get("message") or "").strip()[:300]})
    executed = total["tests"] - total["skipped"]
    total.update(executed=executed, passed=executed - total["failures"] - total["errors"], failing=failing)
    return total


def verdict(result: dict | None) -> str:
    if not result or result["executed"] <= 0:
        return "INCONCLUSIVE"
    return "PASS" if result["failures"] + result["errors"] == 0 else "FAIL"


def git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def build(levels: dict[str, Path], screens: Path | None, model: str) -> dict:
    results = {}
    for name, path in levels.items():
        results[name] = parse_junit(path) if path.is_file() else None
    shots = sorted(str(p.relative_to(ROOT)) for p in screens.rglob("*.png")) if screens and screens.is_dir() else []
    overall = [verdict(r) for r in results.values()]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_sha(),
        "model": model or "not recorded",
        "levels": {n: {"verdict": verdict(r), "source": str(levels[n]), **(r or {})} for n, r in results.items()},
        "overall": "FAIL" if "FAIL" in overall else ("PASS" if overall and all(v == "PASS" for v in overall) else "INCONCLUSIVE"),
        "screenshots": shots,
        "not_verified": [n for n, r in results.items() if verdict(r) == "INCONCLUSIVE"],
    }


def markdown(report: dict) -> str:
    lines = [f"# Evidence report {report['git']}", "",
             f"Generated {report['generated_at']} · model {report['model']} · overall **{report['overall']}**", "",
             "| Level | Verdict | Executed | Passed | Failed | Errors | Skipped | Seconds | Source |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, lv in report["levels"].items():
        if lv.get("tests") is None:
            lines.append(f"| {name} | {lv['verdict']} | not run | | | | | | `{lv['source']}` (missing) |")
            continue
        lines.append(f"| {name} | {lv['verdict']} | {lv['executed']} | {lv['passed']} | {lv['failures']} | {lv['errors']} "
                     f"| {lv['skipped']} | {lv['time']:.1f} | `{lv['source']}` |")
    failing = [(n, f) for n, lv in report["levels"].items() for f in lv.get("failing", [])]
    if failing:
        lines += ["", "## Failing cases", ""] + [f"- **{n}** `{f['case']}`: {f['message'] or 'no message'}" for n, f in failing]
    if report["screenshots"]:
        lines += ["", "## Screenshots", ""] + [f"- `{s}`" for s in report["screenshots"]]
    lines += ["", "## Not verified", ""]
    lines += [f"- {n}: no tests executed or no result file" for n in report["not_verified"]] or ["- Every listed level executed tests."]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", action="append", default=[], help="name=path/to/junit.xml (repeatable)")
    ap.add_argument("--screens", type=Path)
    ap.add_argument("--model", default="")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "evidence" / "runs")
    args = ap.parse_args(argv)
    levels = {}
    for item in args.level:
        name, _, path = item.partition("=")
        if not name or not path:
            ap.error(f"--level needs name=path, got {item!r}")
        levels[name] = Path(path) if Path(path).is_absolute() else ROOT / path
    if not levels:
        ap.error("give at least one --level")
    screens = args.screens if not args.screens or args.screens.is_absolute() else ROOT / args.screens
    report = build(levels, screens, args.model)
    out = args.out / f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-{report['git']}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "REPORT.md").write_text(markdown(report), encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import evidence_html  # noqa: E402 - sibling script, stdlib only
    page = evidence_html.write(report, out, list(levels.values()), screens)
    print(f"{report['overall']}: {out / 'REPORT.md'} and {page}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

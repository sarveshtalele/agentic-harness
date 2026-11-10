"""The evidence report computes verdicts from JUnit counts: nothing executed is INCONCLUSIVE, never PASS."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("evidence_report", Path(__file__).resolve().parents[1] / "scripts" / "evidence_report.py")
er = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(er)


def _junit(tmp_path: Path, name: str, body: str, tests: int, failures: int = 0, skipped: int = 0) -> Path:
    path = tmp_path / name
    path.write_text(f'<testsuites><testsuite name="s" tests="{tests}" failures="{failures}" errors="0" skipped="{skipped}" time="1.5">'
                    f"{body}</testsuite></testsuites>", encoding="utf-8")
    return path


def test_verdicts_come_from_counts(tmp_path):
    ok = _junit(tmp_path, "ok.xml", '<testcase classname="t" name="a"/>', 1)
    bad = _junit(tmp_path, "bad.xml", '<testcase classname="t" name="b"><failure message="boom"/></testcase>', 1, failures=1)
    empty = _junit(tmp_path, "empty.xml", '<testcase classname="t" name="c"><skipped/></testcase>', 1, skipped=1)
    assert er.verdict(er.parse_junit(ok)) == "PASS"
    assert er.verdict(er.parse_junit(bad)) == "FAIL"
    assert er.verdict(er.parse_junit(empty)) == "INCONCLUSIVE"  # all skipped means zero executed
    assert er.verdict(None) == "INCONCLUSIVE"  # level never ran


def test_relative_screens_path_resolves_from_repo_root(tmp_path):
    ok = _junit(tmp_path, "ok.xml", '<testcase classname="t" name="a"/>', 1)
    assert er.main(["--level", f"unit={ok}", "--screens", "docs/evidence/screens", "--out", str(tmp_path / "out")]) == 0


def test_report_lists_failures_and_unrun_levels(tmp_path):
    bad = _junit(tmp_path, "bad.xml", '<testcase classname="t" name="b"><failure message="boom"/></testcase>', 1, failures=1)
    report = er.build({"unit": bad, "e2e": tmp_path / "missing.xml"}, None, "")
    assert report["overall"] == "FAIL"
    assert report["not_verified"] == ["e2e"]
    text = er.markdown(report)
    assert "`t::b`: boom" in text and "e2e: no tests executed" in text

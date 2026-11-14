"""The downloadable zip: tests/ (valid), needs-review/ (invalid, with the failed check and fix), VALIDATION.md, coverage-map.md."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

RUN_COMMAND = {"pytest": "python -m pytest tests/agentic_qe", "vitest": "npx vitest run tests/agentic_qe", "jest": "npx jest tests/agentic_qe", "playwright": "npx playwright test tests/agentic_qe"}


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def validation_md(validation: dict, framework: str) -> str:
    runner = next((r for r in RUN_COMMAND if r in (framework or "").lower()), "pytest")
    rows = ["| Test | Case | Valid | V3 collect | V4 symbols | V5 assertions | V6 trace |", "|---|---|---|---|---|---|---|"]
    for t in validation["tests"]:
        rows.append(f"| {_cell(t['path'])} | {_cell(t['case_id'])} | {'yes' if t['valid'] else 'no'} | " + " | ".join(f"{c['status']}: {_cell(c['message'])}" for c in (t["checks"][k] for k in ("V3", "V4", "V5", "V6"))) + " |")
    c = validation["counts"]
    plugin = validation.get("plugin_check") or {}
    return (f"# Validation\n\n{c['valid']} of {c['total']} tests valid. Valid tests are in `tests/`. The others are in `needs-review/`; each row below says what failed and how to fix it.\n"
            "No test body was run by the platform: a test is valid when it parses, collects, imports real names, asserts the expected result and carries its case id.\n\n"
            f"## How to run\n\nFrom the repository root, with the repository's dependencies installed, copy `tests/` into the repository and run:\n\n    {RUN_COMMAND[runner]}\n\n"
            "## Per test\n\n" + "\n".join(rows) + "\n\n## Plugin Gate 4 check\n\n" + (f"ok: {plugin.get('ok')}. {plugin.get('error') or ''}\n" + "".join(f"- {g}\n" for g in plugin.get("gaps", [])[:20]) if plugin else "Not run.\n"))


def build(worktree: Path, validation: dict, framework: str, fixtures: Path | None, coverage_map: Path | None) -> bytes:
    """Files are read from the worktree, so the zip holds what is on disk."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        for t in validation["tests"]:
            source = worktree / t["path"]
            if source.is_file():
                bundle.write(source, t["path"] if t["valid"] else f"needs-review/{Path(t['path']).name}")
        for extra in sorted(worktree.glob("tests/agentic_qe/conftest.py")) + sorted(worktree.glob("tests/conftest.py")):
            bundle.write(extra, extra.relative_to(worktree).as_posix())
        if fixtures and fixtures.is_file():
            bundle.write(fixtures, "tests/agentic_qe/fixtures.json")
        bundle.writestr("VALIDATION.md", validation_md(validation, framework))
        if coverage_map and coverage_map.is_file():
            bundle.write(coverage_map, "coverage-map.md")
    return buffer.getvalue()

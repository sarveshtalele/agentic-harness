"""CI gate: source files stay at 200 lines or fewer (CLAUDE.md, owner rule 2026-11-10).

tests/file_size_baseline.json lists the files still over the limit and their line counts. A listed file may shrink, never
grow; a file not listed may not go over 200. Refresh after splitting some:  python tests/test_file_size.py --write-baseline
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(__file__).with_name("file_size_baseline.json")
LIMIT = 200
SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs"}
SKIP_PARTS = {"node_modules", ".next", ".next-e2e", "dist", "build", ".venv"}
# plugins/ and skills/ hold distributable skill content (scripts written for Claude Code and Codex), not platform code
SKIP_ROOTS = {"plugins", "skills"}


def _files() -> list[str]:
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, timeout=60, check=True)
    return sorted(p for p in listed.stdout.splitlines() if Path(p).suffix in SUFFIXES and not SKIP_PARTS & set(Path(p).parts) and Path(p).parts[0] not in SKIP_ROOTS and (ROOT / p).is_file())


def counts() -> dict[str, int]:
    found = {}
    for rel in _files():
        with (ROOT / rel).open("rb") as handle:
            lines = sum(1 for _ in handle)
        if lines > LIMIT:
            found[rel] = lines
    return found


def test_no_file_grows_past_the_limit_or_its_baseline():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    over = {f: n for f, n in counts().items() if n > baseline.get(f, LIMIT)}
    assert not over, f"Files over {LIMIT} lines (or over their baseline); split them into feature modules: {over}"


if __name__ == "__main__":
    if "--write-baseline" in sys.argv:
        BASELINE.write_text(json.dumps(counts(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE} ({len(counts())} files over {LIMIT})")

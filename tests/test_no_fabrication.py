"""CI gate 1 from docs/HARNESS_REBUILD_PLAN.md Section 3.2: no fabricated values in production code.

Production code under src/ may not gain new literal scores, "connected" statuses, mock content, brand claims,
fake project fallbacks, fake latency, or success=True returned from an except block. Known cases are a ratchet in
tests/fabrication_baseline.json: a count may fall, never rise, a new file starts at 0, and the baseline itself may
never be above the last committed one. Refresh after fixing some:  python tests/test_no_fabrication.py --write-baseline
Gate 4 (agents approve nothing) lives in tests/test_agents_approve_nothing.py.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
BASELINE = Path(__file__).with_name("fabrication_baseline.json")
FRONTEND_DIRS = ("app", "components", "content", "lib")
SCORE_NAME = re.compile(r"(?i)score|confidence|grade|health")
# A line may opt out only with a stated reason of at least 10 characters.
OPT_OUT = re.compile(r"fabrication-ok:\s*\S.{9,}")

RULES = {
    "connected-literal": re.compile(r"""["']?status["']?\s*[:=]\s*["']connected["']"""),
    "mock-content": re.compile(r"(?i)mock sandbox|mock content|\bsimulated\b"),
    "fixed-score": re.compile(r"""["'](?:score|totalScore|specterScore|confidenceScore|review_score|specterHealth)["']\s*:\s*\d{2,3}\b"""),
    "grade-literal": re.compile(r"""["']A\+["']"""),
    "brand-claim": re.compile(r"Skill Specter|Cloudflare"),
    "fake-project-fallback": re.compile(r"""(?:\bor|\|\|)\s+["'](?:prj_|p\d+["'])"""),
    "fake-latency": re.compile(r"\bsleep\(\s*0?\.\d+\s*\)"),
}


def _production_files() -> list[Path]:
    files = sorted((SRC / "backend").rglob("*.py"))
    for d in FRONTEND_DIRS:
        files += sorted(p for p in (SRC / "frontend" / d).rglob("*") if p.suffix in {".ts", ".tsx"})
    return [p for p in files if "__pycache__" not in p.parts and "node_modules" not in p.parts]


def _ast_counts(tree: ast.AST, skip_lines: set[int]) -> Counter:
    """success=True in an except block, and a number of 50 or more given to a score-like name."""
    c = Counter()
    for handler in (n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)):
        for node in ast.walk(handler):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == "success" and isinstance(v, ast.Constant) and v.value is True:
                        c["success-in-except"] += 1

    def big(v: ast.AST) -> bool:
        return isinstance(v, ast.Constant) and isinstance(v.value, (int, float)) and not isinstance(v.value, bool) and v.value >= 50

    for node in ast.walk(tree):
        if getattr(node, "lineno", 0) in skip_lines:
            continue
        pairs = []
        if isinstance(node, ast.keyword) and node.arg:
            pairs.append((node.arg, node.value))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            pairs += [(t.attr, node.value) for t in targets if isinstance(t, ast.Attribute)]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and len(node.args) == 2 \
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            pairs.append((node.args[0].value, node.args[1]))
        c["score-constant"] += sum(1 for name, v in pairs if SCORE_NAME.search(name) and big(v))
    return c


def scan() -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for path in _production_files():
        raw = path.read_text(encoding="utf-8", errors="replace")
        lines = raw.splitlines()
        skip = {i + 1 for i, line in enumerate(lines) if OPT_OUT.search(line)}
        text = "\n".join("" if i + 1 in skip else line for i, line in enumerate(lines))
        counts = Counter({name: len(rx.findall(text)) for name, rx in RULES.items()})
        if path.suffix == ".py":
            counts += _ast_counts(ast.parse(raw), skip)
        counts = {k: v for k, v in counts.items() if v}
        if counts:
            result[path.relative_to(SRC).as_posix()] = dict(sorted(counts.items()))
    return result


def _over(current: dict, allowed: dict) -> list[str]:
    return [f"{f}: {r} {allowed.get(f, {}).get(r, 0)} -> {n}" for f, counts in current.items() for r, n in counts.items()
            if n > allowed.get(f, {}).get(r, 0)]


def test_gate1_no_new_fabricated_values():
    grown = _over(scan(), json.loads(BASELINE.read_text(encoding="utf-8")))
    assert not grown, "New fabricated values in production code:\n" + "\n".join(grown)


def test_gate1_baseline_never_rises_above_the_committed_one():
    shown = subprocess.run(["git", "show", "HEAD:tests/fabrication_baseline.json"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    if shown.returncode != 0:  # not committed yet: the working baseline is the first one
        return
    raised = _over(json.loads(BASELINE.read_text(encoding="utf-8")), json.loads(shown.stdout))
    assert not raised, "The baseline was raised instead of the code being fixed:\n" + "\n".join(raised)


def test_gate1_detects_planted_values():
    """The rules must fire on what they exist for, so an empty scan is not mistaken for a clean one."""
    planted = 'x = {"status": "connected", "score": 98, "grade": "A+"}\nawait asyncio.sleep(0.04)\npid = a or "prj_demo"\nq = b or "p1"\n'
    hits = Counter({name: len(rx.findall(planted)) for name, rx in RULES.items()})
    assert +hits == Counter({"connected-literal": 1, "fixed-score": 1, "grade-literal": 1, "fake-latency": 1, "fake-project-fallback": 2})
    tree = ast.parse("try:\n    pass\nexcept Exception:\n    r = {'success': True}\n"
                     "card(confidenceScore=95)\nself.score = 94\nv = d.get('score', 90)\nlimit = 3\n")
    assert _ast_counts(tree, set()) == Counter({"success-in-except": 1, "score-constant": 3})
    assert OPT_OUT.search("x  # fabrication-ok: poll interval for run events") and not OPT_OUT.search("x  # fabrication-ok:")


if __name__ == "__main__":
    if "--write-baseline" in sys.argv:
        BASELINE.write_text(json.dumps(scan(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE}")
    else:
        print(json.dumps(scan(), indent=2, sort_keys=True))

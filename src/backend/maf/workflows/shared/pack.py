"""Repository facts and the line-numbered code packs sent to agents."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend.config import repo_dir
from backend.core.security import redact, safe_path
from backend.repos import ingest, scan, static_analysis

MAX_SOURCE_CHARS = 60_000

def _analysis(project_id: str) -> dict:
    repo = ingest.get(project_id)
    return repo["analysis"] if repo else {"mode": "greenfield", "languages": {}, "frameworks": [], "test_runners": [], "total_files": 0, "test_file_count": 0}


def _brief_of_analysis(a: dict) -> str:
    keep = {k: a.get(k) for k in ("mode", "languages", "frameworks", "test_runners", "test_file_count", "entrypoints", "ci")}
    keep["routes"] = a.get("routes", [])[:60]
    keep["largest_sources"] = [{"path": s["path"], "lines": s["lines"], "symbols": s["symbols"][:10]} for s in a.get("largest_sources", [])[:40]]
    return json.dumps(keep)


def _window(numbered: list[str], lines: list[int], radius: int) -> str:
    """Only the numbered lines within `radius` of the given lines, with a gap marker between separate runs."""
    keep = sorted({n for line in lines for n in range(max(line - radius, 1), min(line + radius, len(numbered)) + 1)})
    out, last = [], 0
    for n in keep:
        out.append("..." if last and n > last + 1 else "")
        out.append(numbered[n - 1])
        last = n
    return "\n".join(x for x in out if x)


def code_pack(project_id: str, root: Path | None = None, paths: list[str] | None = None, limit: int = 40_000, around: dict[str, list[int]] | None = None, radius: int = 40) -> str:
    """Line-numbered source for one agent message, riskiest files first and bounded in size.

    `around` maps a path to cited lines: for those files only the lines within `radius` of a citation are sent, with their real line numbers.

    Agents get code up front instead of exploring with tools. That keeps token use predictable, and it avoids the
    long tool loops that outgrow model context.
    """
    base = root or repo_dir(project_id)
    if not base.exists():
        return "(no repository)"
    chosen = paths or static_analysis.rank_files_for_review(base, _analysis(project_id), 40)
    parts, used = [], 0
    for path in chosen:
        try:
            text = redact(scan._read(safe_path(base, path)))
        except ValueError:
            continue
        if not text:
            continue
        numbered = [f"{i}: {line}" for i, line in enumerate(text.splitlines(), 1)]
        shown = _window(numbered, around[path], radius) if around and around.get(path) else "\n".join(numbered)
        block = f"--- FILE {path} ---\n{shown}\n"
        if used + len(block) > limit:
            continue
        parts.append(block)
        used += len(block)
    return "\n".join(parts) or "(no readable source files)"


REVIEW_EVIDENCE_CHARS = 12_000  # one review batch's whole evidence; the rubric is in the agent's prompt and is never cut


def review_evidence(project_id: str, requirements: list[dict], root: Path | None = None, limit: int = REVIEW_EVIDENCE_CHARS) -> str:
    """What one review batch needs: the requirements its items cover with their quotes, and the source lines near each citation.

    The reviewer's own citations are still checked on disk by code, so a smaller view cannot make a case pass.
    """
    head = "REQUIREMENTS:\n" + json.dumps([{k: r.get(k, "") for k in ("id", "priority", "statement", "file", "line", "quote")} for r in requirements])
    around: dict[str, list[int]] = {}
    for r in requirements:
        if r.get("file"):
            around.setdefault(r["file"], []).append(int(r.get("line") or 1))
    code = code_pack(project_id, root, list(around), max(limit - len(head) - 200, 0), around) if around else "(the requirements cite no file)"
    return f"{head}\n\nCODE NEAR EACH CITATION (line numbers are before each line):\n{code}"[:limit]  # ponytail: a batch of very many requirements is cut at the end


def discovery_pack(project_id: str, limit: int = 70_000) -> str:
    """What explains a repository from end to end comes first: its readme, manifests, and entry points, then its riskiest code."""
    a = _analysis(project_id)
    root = repo_dir(project_id)
    files = scan.tree(root, limit=100_000)
    front = [f for f in files if "/" not in f and re.match(r"(?i)(readme|pyproject\.toml|package\.json|requirements.*\.txt|dockerfile|docker-compose|makefile)", f)]
    paths = list(dict.fromkeys([*front, *a.get("entrypoints", []), *{r["file"] for r in a.get("routes", [])}, *static_analysis.rank_files_for_review(root, a, 60)]))
    return code_pack(project_id, paths=paths, limit=limit)

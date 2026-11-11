"""Groundedness: the share of a reply's cited files, lines and quotes that really exist."""
from __future__ import annotations

import re
from pathlib import Path

from backend.core.security import safe_path
from backend.maf.evals.metrics.ratios import ratio
from backend.repos import static_analysis

PATH_LINE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.[A-Za-z]{1,5}):(\d+)\b")


def citations(reply: str) -> list[dict]:
    """Every file, line, and quote the reply cites: from JSON objects when it has them, else path:line in prose."""
    from backend.maf import runtime as agents  # late: runtime imports the model layer

    found: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            path = node.get("file") or node.get("path")
            if isinstance(path, str) and (node.get("quote") or node.get("line")):
                found.append({"file": path, "line": int(node["line"]) if str(node.get("line") or "").isdigit() else 0, "quote": str(node.get("quote") or "")})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    try:
        walk(agents.extract_json(reply))
    except ValueError:
        pass
    if not found:
        found = [{"file": path, "line": int(line), "quote": ""} for path, line in PATH_LINE.findall(reply)]
    return found


def _context_files(context: str) -> dict[str, str]:
    """Files in a supplied context written as `--- FILE name ---` blocks, with or without `N: ` line prefixes."""
    parts = re.split(r"^--- FILE (.+?) ---\s*$", context, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def _check_one(cite: dict, root: Path | None, files: dict[str, str]) -> str:
    """"" when the citation is real, else why not."""
    path, line, quote = cite["file"].replace("\\", "/"), cite["line"], cite["quote"]
    if root is not None:
        try:
            target = safe_path(root, path)
        except ValueError:
            return f"{path} is outside the repository"
        if not target.is_file():
            return f"{path} does not exist"
        if quote.strip():
            return "" if static_analysis.verify_quote(root, path, line, quote)[0] else f"the quote is not in {path}"
        count = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
        return "" if 1 <= line <= count else f"{path} has no line {line}"
    text = files.get(path)
    if text is None:
        return f"{path} is not in the given context"
    body = "\n".join(re.sub(r"^\s*\d+:\s?", "", row) for row in text.strip("\n").splitlines())
    if quote.strip():
        return "" if " ".join(quote.split()) in " ".join(body.split()) else f"the quote is not in {path}"
    return "" if 1 <= line <= len(body.splitlines()) else f"{path} has no line {line}"


def groundedness(reply: str, *, root: Path | None = None, context: str = "") -> dict:
    """Share of the reply's citations that exist. Checks the repository on disk when `root` is given, else the given context text.

    `value` is None when the reply cites nothing: that is "not measured", not a perfect score.
    """
    cites = citations(reply)
    files = _context_files(context)
    bad = []
    for cite in cites:
        why = _check_one(cite, root, files)
        if why:
            bad.append({**cite, "reason": why})
    return {"value": ratio(len(cites) - len(bad), len(cites)), "n": len(cites), "bad": bad}

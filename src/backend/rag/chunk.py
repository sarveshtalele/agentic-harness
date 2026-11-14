"""Split a parsed source text into chunks that keep where they came from (docs/QE_V2_PLAN.md section 5).

A chunk is a run of whole source lines, so its text is the exact slice `lines[line_start-1:line_end]` of the saved source file and a
quote from it is found verbatim on disk. Chunks break at every heading and every page; inside a section paragraphs are packed up
to about TARGET_TOKENS, and the next chunk starts with the last paragraphs of the one before (about OVERLAP of the target).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TARGET_TOKENS = 800
OVERLAP = 0.15
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
PAGE = re.compile(r"^(?:Page|Slide)\s+(\d+)$", re.I)  # what core/source_text.py writes for a PDF page or a slide


@dataclass(frozen=True)
class Chunk:
    ord: int
    section: str
    page: int | None
    line_start: int
    line_end: int
    text: str


def tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ponytail: four characters a token, no tokenizer; a model-specific count would only shift the size a little


def _units(lines: list[str]) -> list[tuple[tuple, int, int]]:
    """Paragraphs as (key, first line, last line), 1-based; the key is (heading path, page), which never changes inside a unit."""
    out, path, page, start, key = [], [], None, None, ()
    for number, line in enumerate(lines, 1):
        head = HEADING.match(line)
        if head and start is not None:  # a heading closes the paragraph before it
            out.append((key, start, number - 1))
            start = None
        if head:
            level, title = len(head.group(1)), head.group(2).strip()
            if found := PAGE.match(title):
                page = int(found.group(1))
            else:
                path = path[: level - 1] + [""] * (level - 1 - len(path)) + [title]
        if not line.strip():
            if start is not None:
                out.append((key, start, number - 1))
                start = None
            continue
        if start is None:
            start, key = number, (" > ".join(p for p in path if p), page)
    if start is not None:
        out.append((key, start, len(lines)))
    return out


def _split(unit: tuple, lines: list[str], limit: int) -> list[tuple]:
    """A paragraph over the limit is cut at line breaks (a single line longer than the limit stays whole)."""
    key, first, last = unit
    if tokens("\n".join(lines[first - 1 : last])) <= limit:
        return [unit]
    out, start = [], first
    for n in range(first, last + 1):
        if n > start and tokens("\n".join(lines[start - 1 : n])) > limit:
            out.append((key, start, n - 1))
            start = n
    return [*out, (key, start, last)]


def chunk_text(text: str, target: int = TARGET_TOKENS, overlap: float = OVERLAP) -> list[Chunk]:
    lines = text.splitlines()
    units = [p for u in _units(lines) for p in _split(u, lines, target)]
    out: list[Chunk] = []
    group: list[tuple] = []

    def flush(carry: bool) -> None:
        nonlocal group
        if not group:
            return
        first, last = group[0][1], group[-1][2]
        key = group[0][0]
        out.append(Chunk(len(out), key[0], key[1], first, last, "\n".join(lines[first - 1 : last])))
        keep: list[tuple] = []
        size = 0
        for unit in reversed(group[1:] if carry else []):  # never carry the whole chunk, or it would repeat itself
            part = tokens("\n".join(lines[unit[1] - 1 : unit[2]]))
            if size + part > target * overlap and (keep or part > 2 * target * overlap):  # the last paragraph always carries unless it is far over
                break
            size += part
            keep.insert(0, unit)
        group = keep

    for unit in units:
        if group and (unit[0] != group[-1][0] or tokens("\n".join(lines[group[0][1] - 1 : unit[2]])) > target):
            same = unit[0] == group[-1][0]
            flush(carry=same)
            if not same:
                group = []
        group.append(unit)
    flush(carry=False)
    return out

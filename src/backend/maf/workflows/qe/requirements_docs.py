"""Greenfield requirements read from the uploaded documents (RAG): chunks per topic with citations, and the quote check against the saved text.

Document text is untrusted data: the model gets it as chunks to read, never as instructions, and code (not the model) checks every quote.
"""
from __future__ import annotations

import re

from backend.maf.engine import RunContext
from backend.rag import analyst, retrieve, store

QUESTIONS = ("functional requirements", "validation rules and limits", "error messages and status codes", "non-functional requirements",
             "business rules", "users and roles", "acceptance criteria", "out of scope")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*$", re.M)
MAX_HEADINGS, PER_HEADING, PER_QUESTION, MIN_QUOTE = 40, 2, 6, 8  # ponytail: a very long document is covered by its first 40 headings plus the questions


async def gather(rc: RunContext, limit: int = 40_000) -> tuple[str, list[str]]:
    """(the chunk pack for the analyst's prompt, the ids of the chunks in it). Each chunk shows its source file, section and lines."""
    chunks: dict[str, dict] = {}
    order = {s["doc_id"]: n for n, s in enumerate(store.sources(rc.project_id))}
    for source in store.sources(rc.project_id):
        for heading in HEADING.findall(analyst.source_text(rc.project_id, source["source_path"]))[:MAX_HEADINGS]:
            for c in retrieve.retrieve(rc.project_id, heading, PER_HEADING):
                chunks.setdefault(c["id"], c)
    for question in QUESTIONS:
        for c in await analyst.retrieve_reranked(rc.project_id, question, PER_QUESTION, run_id=rc.run_id):
            chunks.setdefault(c["id"], c)
    ordered = sorted(chunks.values(), key=lambda c: (order.get(c["citation"]["doc_id"], 0), c["citation"]["line_start"]))
    parts, used = [], 0
    for c in ordered:
        k = c["citation"]
        block = f"[{c['id']}] file: {k['source_path']} | document: {k['document']} (id {k['doc_id']}) | section: {k['section'] or '-'} | lines {k['line_start']}-{k['line_end']}\n{c['text']}\n"
        if used + len(block) > limit:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts), [c["id"] for c in ordered]


def verify(project_id: str, requirement) -> tuple[bool, int]:
    """The quote must appear verbatim in the saved text of an indexed document. Returns (found, 1-based line of its first character).

    The model names the file as the chunk header shows it; a `sandbox/` prefix is tolerated. Anything else is not evidence.
    """
    wanted = requirement.file.replace("\\", "/").removeprefix("sandbox/")
    if wanted not in {s["source_path"] for s in store.sources(project_id)}:
        return False, 0
    requirement.file = wanted
    quote = requirement.quote.strip()
    text = analyst.source_text(project_id, wanted)
    at = text.find(quote)
    return (False, 0) if len(quote) < MIN_QUOTE or at < 0 else (True, text.count("\n", 0, at) + 1)

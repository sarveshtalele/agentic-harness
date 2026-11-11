"""What the harness calls: `find_capability` (BM25, standard library only), `describe_capability`, and `index_text`.

Each capability is one document: its name and qualified name (counted three times), its description, and the names
of everything linked to it in either direction. Words are lowercased and lightly stemmed so "plan", "plans" and
"planning" meet. Every function sees only the user's visible slice.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from backend.core.registry.read import detail, visible_links, visible_rows

K1, B = 1.5, 0.75
STOP = frozenset("a an and are as at be by do for from how i in is it me my of on or our please the this to use we what when with you".split())
KIND_ORDER = ("command", "skill", "workflow", "agent", "tool", "mcp_tool", "plugin", "mcp_server", "stage", "gate", "hook", "script")


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    return word[:-1] if len(word) > 3 and word[-1] == word[-2] and word[-1] not in "aeiou" else word


def words(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


def _documents(found: dict[str, dict]) -> dict[str, list[str]]:
    linked: dict[str, list[str]] = {cid: [] for cid in found}
    for link in visible_links(found):
        linked[link["from_id"]].append(found[link["to_id"]]["qualified_name"])
        linked[link["to_id"]].append(found[link["from_id"]]["qualified_name"])
    return {cid: words(f"{i['name']} {i['qualified_name']} " * 3 + f"{i['description']} {i['when_to_use']} {' '.join(linked[cid])}")
            for cid, i in found.items()}


def bm25(query: str, docs: dict[str, list[str]]) -> list[tuple[float, str]]:
    terms = words(query)
    if not terms or not docs:
        return []
    average = sum(len(d) for d in docs.values()) / len(docs)
    frequency = Counter(t for d in docs.values() for t in set(d))
    scored = []
    for cid, doc in docs.items():
        counts, score = Counter(doc), 0.0
        for term in terms:
            if counts[term]:
                idf = math.log(1 + (len(docs) - frequency[term] + 0.5) / (frequency[term] + 0.5))
                score += idf * counts[term] * (K1 + 1) / (counts[term] + K1 * (1 - B + B * len(doc) / average))
        if score > 0:
            scored.append((score, cid))
    return sorted(scored, key=lambda s: (-s[0], s[1]))


def find_capability(query: str, user: dict | None, limit: int = 8) -> list[dict]:
    found = visible_rows(user)
    return [{"id": cid, "kind": found[cid]["kind"], "qualified_name": found[cid]["qualified_name"], "description": found[cid]["description"][:200],
             "needs_approval": found[cid]["needs_approval"], "score": round(score, 3)} for score, cid in bm25(query, _documents(found))[: max(1, limit)]]


def describe_capability(name_or_id: str, user: dict | None) -> dict | None:
    return detail(user, name_or_id)


def _key_links(cid: str, item: dict, found: dict, out: dict[str, list]) -> str:
    """The links that matter for choosing: a command's skills and scripts, a workflow's stages and agents, an agent's delegates and skills."""
    if item["kind"] == "command":
        parts = [f"{r}: {', '.join(found[t]['qualified_name'] for t in out.get((cid, r), []))}" for r in ("applies_skill", "runs_script") if out.get((cid, r))]
    elif item["kind"] == "workflow":
        stages = sorted(out.get((cid, "contains"), []), key=lambda s: found[s]["meta"].get("order", 0))
        parts = ["stages: " + ", ".join(found[s]["name"] + "".join(f"->{found[a]['name']}" for a in out.get((s, "performed_by"), [])) for s in stages)] if stages else []
    elif item["kind"] == "agent":
        parts = [f"{r}: {', '.join(found[t]['qualified_name'] for t in out.get((cid, r), []))}" for r in ("delegates_to", "applies_skill") if out.get((cid, r))]
    else:
        parts = []
    return f" [{'; '.join(parts)}]" if parts else ""


def index_text(user: dict | None) -> str:
    """One line per capability by kind, with key links; stages, gates, hooks and scripts are reached through their parents."""
    found = visible_rows(user)
    out: dict[tuple, list] = {}
    for link in visible_links(found):
        out.setdefault((link["from_id"], link["relation"]), []).append(link["to_id"])
    lines = []
    for kind in KIND_ORDER[:8]:
        items = sorted((i for i in found.values() if i["kind"] == kind), key=lambda i: i["qualified_name"])
        if items:
            lines.append(f"## {kind} ({len(items)})")
            lines += [f"- {i['qualified_name']}: {i['description'][:120]}{_key_links(i['id'], i, found, out)}" for i in items]
    return "\n".join(lines) if lines else "The capability registry is empty for this user (not synced yet, or nothing is granted)."

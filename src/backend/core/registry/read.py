"""Reading the registry for one user: the flat listing, one capability with its links up and down, and the nested tree."""
from __future__ import annotations

from backend.core.registry import store
from backend.core.registry.visibility import checker, live

# which links to follow down from each kind in the tree, so a node nests what it holds or uses
DOWN = {"plugin": ("contains",), "command": ("runs_script", "applies_skill"), "skill": ("runs_script",), "workflow": ("contains",),
        "stage": ("performed_by", "gates"), "agent": ("uses_tool", "applies_skill", "delegates_to"), "mcp_server": ("serves",)}
ROOTS = ("plugin", "workflow", "mcp_server")
BRIEF = ("id", "kind", "name", "qualified_name", "description", "enabled", "needs_approval", "risk")


def visible_rows(user: dict | None) -> dict[str, dict]:
    ok = checker(user)
    return {item["id"]: item for item in live(store.capabilities()) if ok(item)}


def visible_links(found: dict[str, dict]) -> list[dict]:
    return [link for link in store.links() if link["from_id"] in found and link["to_id"] in found]


def listing(user: dict | None, kind: str = "", q: str = "", plugin: str = "") -> list[dict]:
    words = q.lower().split()
    return [item for item in visible_rows(user).values()
            if (not kind or item["kind"] == kind) and (not plugin or item["plugin"] == plugin)
            and all(w in f"{item['qualified_name']} {item['description']}".lower() for w in words)]


def resolve(found: dict[str, dict], name_or_id: str) -> dict | None:
    """By id, then qualified name, then plain name (the first by kind when a name is shared)."""
    if name_or_id in found:
        return found[name_or_id]
    for field in ("qualified_name", "name"):
        same = sorted((i for i in found.values() if i[field] == name_or_id), key=lambda i: (i["kind"], i["qualified_name"]))
        if same:
            return same[0]
    return None


def _brief(item: dict) -> dict:
    return {k: item[k] for k in BRIEF}


def detail(user: dict | None, name_or_id: str) -> dict | None:
    found = visible_rows(user)
    item = resolve(found, name_or_id)
    if not item:
        return None
    links = visible_links(found)
    down = [{"relation": l["relation"], "detail": l["detail"], **_brief(found[l["to_id"]])} for l in links if l["from_id"] == item["id"]]
    up = [{"relation": l["relation"], "detail": l["detail"], **_brief(found[l["from_id"]])} for l in links if l["to_id"] == item["id"]]
    return {**item, "down": down, "up": up}


def _order(link: dict, found: dict) -> tuple:
    detail = link["detail"]
    return (int(detail) if detail.isdigit() else 0, found[link["to_id"]]["kind"], found[link["to_id"]]["qualified_name"])


def tree(user: dict | None, depth: int = 4) -> list[dict]:
    """Plugins, workflows and MCP servers, each with what it holds nested below (a stage's agents, their tools and skills)."""
    found = visible_rows(user)
    children: dict[str, list[dict]] = {}
    for link in visible_links(found):
        children.setdefault(link["from_id"], []).append(link)

    def node(cid: str, relation: str, left: int, seen: frozenset) -> dict:
        item = found[cid]
        below = [] if left == 0 or cid in seen else sorted(
            (l for l in children.get(cid, []) if l["relation"] in DOWN.get(item["kind"], ())), key=lambda l: _order(l, found))
        return {**_brief(item), "relation": relation, "children": [node(l["to_id"], l["relation"], left - 1, seen | {cid}) for l in below]}

    roots = sorted((i for i in found.values() if i["kind"] in ROOTS and not (i["kind"] == "mcp_server" and i["plugin"])),
                   key=lambda i: (ROOTS.index(i["kind"]), i["qualified_name"]))
    return [node(i["id"], "", depth, frozenset()) for i in roots]

"""An invented tool name gets the nearest real names back (docs/PHASE2_PLAN.md section 8, guards).

MAF answers a call to a name it does not have with `Error: Requested function "x" not found.` before any function
middleware runs, and the model often tries a second invented name. This chat middleware runs before each model call and
adds the three closest names (offered tools and the deferred catalogue) to that answer, plus how to load a deferred one.
"""
from __future__ import annotations

import difflib
import re

from agent_framework import chat_middleware

NOT_FOUND = re.compile(r'Requested function "([^"]+)" not found')
MARK = "Closest real tools:"


# words models use for a tool's purpose -> the real tools for it (the first that exist are suggested)
PURPOSE = {("shell", "exec", "command", "terminal", "cmd", "bash", "sh", "run_command", "powershell", "pwsh", "background", "run_in_background"): ("bash", "powershell", "run_shell"),
           ("read", "open", "cat", "view", "get_file"): ("file_access_read", "read_file"),
           ("write", "create", "save", "put_file"): ("file_access_write",),
           ("edit", "replace", "patch", "modify", "update_file"): ("file_access_replace", "file_access_replace_lines"),
           ("ls", "list", "dir", "tree", "glob"): ("file_access_ls", "list_files"),
           ("search", "grep", "find_in", "rg"): ("file_access_grep", "grep"),
           ("test", "pytest"): ("run_tests", "bash")}


def suggest(name: str, offered: set[str], deferred: set[str]) -> str:
    pool = sorted(offered | deferred)
    words = set(re.split(r"[_.\-\s]", name.lower()))
    by_purpose = [t for keys, tools in PURPOSE.items() if words & set(keys) or name.lower() in keys for t in tools if t in pool]
    near = list(dict.fromkeys(by_purpose + difflib.get_close_matches(name, pool, n=3, cutoff=0.5)))[:3]
    if not near:
        return f" {MARK} none similar. Use find_tools to search by purpose."
    loading = [n for n in near if n in deferred and n not in offered]
    return f" {MARK} {', '.join(near)}." + (f" Load {', '.join(loading)} with load_tools first." if loading else "")


def unknown_tool_hints(catalogue, loaded=None):
    """`catalogue`: this turn's deferred tools; `loaded`: the thread's LoadedTools, so a deferred platform tool the model
    called by name is loaded on the spot (the 2026-11-13 eval: run_tests and project_status were called unloaded 9 times)."""

    @chat_middleware
    async def hints(context, call_next) -> None:
        tools = context.options.get("tools")
        offered = {getattr(t, "name", "") for t in tools or []}
        for message in context.messages or []:
            for content in getattr(message, "contents", None) or []:
                result = getattr(content, "result", None)
                if getattr(content, "type", "") == "function_result" and isinstance(result, str) and MARK not in result:
                    if found := NOT_FOUND.search(result):
                        name = found[1]
                        if loaded is not None and name in getattr(catalogue, "tools", {}) and name not in offered and tools is not None:
                            loaded.add([name])
                            tools.extend(catalogue.resolve([name]))
                            offered.add(name)
                            content.result = result + f" {MARK} {name} was not loaded yet; it is loaded now, so call it again."
                        else:
                            content.result = result + suggest(name, offered, set(catalogue.descriptions()))
        await call_next()

    return hints

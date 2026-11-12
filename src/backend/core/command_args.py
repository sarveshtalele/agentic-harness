"""Claude Code's substitutions in plugin and skill commands (docs/PHASE2_PLAN.md section 7.2)."""
from __future__ import annotations

import re
from pathlib import Path


def substitute(body: str, args: str, named=None, project_dir: Path | None = None) -> str:
    """Claude Code's command substitutions: `$ARGUMENTS`, `$ARGUMENTS[N]` and `$N` (0-based, quoted words stay whole),
    `$name` for frontmatter `arguments` (by position), `${CLAUDE_PROJECT_DIR}`, and `\\$` for a literal dollar sign. With no
    placeholder at all the arguments are appended as `ARGUMENTS: ...`. Values are inserted as typed, never re-expanded."""
    import shlex

    try:
        words = shlex.split(args)
    except ValueError:
        words = args.split()
    names = named.split() if isinstance(named, str) else [str(n) for n in named or []]
    values = {**{n: words[i] if i < len(words) else "" for i, n in enumerate(names)}}
    token = re.compile(r"\\\$|\$\{CLAUDE_PROJECT_DIR\}|\$ARGUMENTS\[(\d+)\]|\$ARGUMENTS\b|\$(\d+)\b|\$([A-Za-z_]\w*)\b")
    used = False

    def fill(m: re.Match) -> str:
        nonlocal used
        text = m.group(0)
        if text == "\\$":
            return "$"
        if text == "${CLAUDE_PROJECT_DIR}":
            return str(project_dir) if project_dir else text
        index = m.group(1) or m.group(2)
        if index is not None:
            used = True
            return words[int(index)] if int(index) < len(words) else ""
        if text == "$ARGUMENTS":
            used = True
            return args
        if m.group(3) in values:
            used = True
            return values[m.group(3)]
        return text  # $HOME and other shell variables stay for the shell

    out = token.sub(fill, body)
    return out if used or not args else f"{out}\n\nARGUMENTS: {args}"

"""JavaScript import checks and the language dispatcher."""
from __future__ import annotations

import re
from pathlib import Path
from backend.qe.emit.python import check_python


JS_EXTENSIONS = ("", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".json", "/index.js", "/index.ts")


JS_IMPORT = re.compile(r"""(?:\bfrom\s+|\brequire\(\s*|\bimport\(\s*|\bimport\s+)['"](\.{1,2}/[^'"]*)['"]""")


def check_js(worktree: Path, path: str, code: str) -> list[str]:
    """ponytail: JavaScript and TypeScript get only a check that a relative import path exists. Names and calls are not checked, because that needs the TypeScript compiler. Add it with a Node step."""
    base = (worktree / path).parent
    return [f"{path}: the import {target!r} does not exist" for target in dict.fromkeys(JS_IMPORT.findall(code)) if not any((base / (target + ext)).is_file() for ext in JS_EXTENSIONS)]


def check(worktree: Path, path: str, code: str, env: dict | None = None, declared: set[str] | frozenset = frozenset()) -> list[str]:
    if path.endswith(".py"):
        return check_python(worktree, path, code, env, declared)
    if path.endswith((".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs")):
        return check_js(worktree, path, code)
    return []

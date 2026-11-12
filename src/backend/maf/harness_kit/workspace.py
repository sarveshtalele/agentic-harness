"""The harness's execution world (plan H2): one workspace per project and chat thread.

The workspace root is the project's sandbox clone (`repos.sandbox.initialize_sandbox`, which refuses without a repository,
so nothing is invented in its place). Each thread also gets a scratch folder under the harness state dir, used as the
shell's temp folder. MAF's `FileSystemAgentFileStore` already refuses absolute paths, `..`, symlinks and paths that
resolve outside its root; `WorkspaceStore` adds the platform's `safe_path` on every path, and on writes its protected
folders (`.git`, `.venv`, `node_modules`, `.qe`), since a written `.git/config` could make a read-only git verb run code
and `.qe/` belongs to the agentic-qe plugin's hooks.

Plugins see the workspace as `CLAUDE_PROJECT_DIR`. `HOME` for hooks and shell commands is one harness-owned folder
(`data/harness/plugin-home`), so a plugin's per-user state (agentic-qe's ledger anchors and its validator's Python
environment) is shared by its hooks and the scripts the model runs, and never lands in the server user's real home.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_framework import ContextProvider, FileSystemAgentFileStore

from backend.config import DATA_DIR
from backend.core import cli_workspaces, plugins
from backend.core.errors import RepoError
from backend.core.security import safe_path
from backend.maf.harness_kit.catalog import THREAD_ID
from backend.repos import sandbox

PLUGIN_HOME = DATA_DIR / "harness" / "plugin-home"


@dataclass(frozen=True)
class Workspace:
    project_id: str
    thread_id: str
    user_id: str | None
    root: Path
    scratch: Path
    direct: bool = False  # a folder on the person's own machine (aqh CLI), not a sandbox clone

    def env(self) -> dict[str, str]:
        """What hooks and shell commands see besides the clean environment."""
        temp = str(self.scratch)
        home = {} if self.direct else {"HOME": str(PLUGIN_HOME), "USERPROFILE": str(PLUGIN_HOME)}  # the CLI keeps the person's own HOME
        return {**home, "TMPDIR": temp, "TMP": temp, "TEMP": temp,
                "CLAUDE_PROJECT_DIR": str(self.root), "CLAUDECODE": "1",  # plugins detect Claude Code by this variable
                "AGENTIC_QE_DASHBOARD": "off"}  # the plugin's live dashboard opens a browser window: not on a server


def open_workspace(project_id: str, thread_id: str, user_id: str | None) -> Workspace | None:
    """The thread's workspace, or None when the project has no repository (the harness then has no write or shell tools)."""
    if not THREAD_ID.match(thread_id):
        raise ValueError("Unexpected thread id")
    bound = cli_workspaces.path_of(project_id)
    if bound is None:
        try:
            root = sandbox.initialize_sandbox(project_id).resolve()
        except RepoError:
            return None
    else:
        root = bound.resolve()
    scratch = DATA_DIR / "harness" / project_id / "scratch" / thread_id
    scratch.mkdir(parents=True, exist_ok=True)
    PLUGIN_HOME.mkdir(parents=True, exist_ok=True)
    return Workspace(project_id, thread_id, user_id, root, scratch.resolve(), direct=bound is not None)


class WorkspaceStore(FileSystemAgentFileStore):
    """MAF's disk store, with every path also checked by `safe_path` and writes kept out of protected folders."""

    def _resolve_safe_path(self, relative_path: str) -> Path:
        safe_path(self.root_path, relative_path)
        return super()._resolve_safe_path(relative_path)

    def _resolve_safe_directory_path(self, relative_directory: str) -> Path:
        safe_path(self.root_path, relative_directory or ".")
        return super()._resolve_safe_directory_path(relative_directory)

    async def write(self, path: str, content: str, *, overwrite: bool = True) -> None:
        safe_path(self.root_path, path, for_write=True)
        await super().write(path, content, overwrite=overwrite)

    async def delete(self, path: str) -> bool:
        safe_path(self.root_path, path, for_write=True)
        return await super().delete(path)

    async def create_directory(self, path: str) -> None:
        safe_path(self.root_path, path, for_write=True)
        await super().create_directory(path)

    async def delete_directory(self, path: str) -> bool:
        safe_path(self.root_path, path, for_write=True)
        return await super().delete_directory(path)


class WorkspaceContext(ContextProvider):
    """Tells the model where it works and where plugin scripts live (Claude Code's ${CLAUDE_PLUGIN_ROOT}), or that there is no workspace."""

    def __init__(self, workspace: Workspace | None):
        super().__init__("harness-workspace")
        self.workspace = workspace

    async def before_run(self, *, agent, session, context, state) -> None:
        ws = self.workspace
        if ws is None:
            context.extend_instructions(self.source_id, "Workspace: none. This project has no repository, so there are no file write or shell tools. Say so if a task needs them.")
            return
        roots = [f"- {p.id}: {p.root}" for p in plugins.discover() if p.id != "local-skills" and p.enabled and (p.root / "hooks").is_dir()]
        context.extend_instructions(self.source_id, "\n".join([
            f"Workspace (the project's sandbox clone; CLAUDE_PROJECT_DIR): {ws.root}. File tools take paths relative to it.",
            f"Scratch folder for this chat (the shell's temp folder): {ws.scratch}",
            "Plugin folders (${CLAUDE_PLUGIN_ROOT} in plugin instructions; write the full path in shell commands):", *roots]))

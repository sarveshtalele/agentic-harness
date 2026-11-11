"""Each project's sandbox: its own folder with a full clone, one worktree per run, its own Python environment.

Test code runs with clean_env(), so it cannot see platform secrets.
ponytail: this isolates by folder and environment, not by operating system. Use a container per project before running repositories you do not trust.
"""
from __future__ import annotations

from backend.config import project_dir, repo_dir, sandbox_dir
from .setup import (
    complete_history,
    ensure_sandbox,
    initialize_sandbox,
    info,
)
from .env import (
    SENSITIVE_ENV_PATTERN,
    clean_sandbox_env,
)
from .commands import (
    execute_command,
    run_npx,
    run_tests,
)
from .runtime import (
    execute_code,
    install_dependencies,
)
from .git_ops import (
    create_file,
    create_branch,
    commit_changes,
)

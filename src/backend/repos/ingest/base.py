"""Ingest error type and tree removal."""
from __future__ import annotations

import shutil
import stat
from pathlib import Path
from backend.core.errors import RepoError


class IngestError(RepoError, ValueError):
    pass


def _rm_tree(path: Path) -> None:
    def retry(func, target, _exc):  # git pack files are read-only, which blocks deletion on Windows
        Path(target).chmod(stat.S_IWRITE)
        func(target)

    if path.exists():
        shutil.rmtree(path, onexc=retry)

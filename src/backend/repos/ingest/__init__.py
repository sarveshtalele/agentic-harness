"""Bring code into a project: clone a git URL (public or with a saved token) or unpack a ZIP safely."""
from __future__ import annotations

from .base import (
    IngestError,
    _rm_tree,
)
from .zips import (
    MAX_ZIP_FILES,
    MAX_RATIO,
    safe_extract,
)
from .analysis import (
    normalize_analysis,
    _is_partial_analysis,
)
from .state import (
    get,
    disconnect,
)
from .sources import (
    _record,
    from_git,
    from_zip,
    from_local,
    resync,
)

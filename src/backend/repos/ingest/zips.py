"""Safe ZIP extraction."""
from __future__ import annotations

import shutil
import stat
import zipfile
from pathlib import Path
from backend.config import MAX_UPLOAD_BYTES
from backend.repos.ingest.base import IngestError


MAX_ZIP_FILES = 100_000


MAX_RATIO = 200


def safe_extract(archive: Path, target: Path) -> None:
    """Refuse traversal, absolute paths, symlinks, and zip bombs before anything reaches disk."""
    try:
        bundle = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise IngestError("The file is not a valid ZIP archive") from exc
    with bundle:
        infos = bundle.infolist()
        if len(infos) > MAX_ZIP_FILES:
            raise IngestError(f"ZIP has more than {MAX_ZIP_FILES} entries")
        total = sum(i.file_size for i in infos)
        if total > MAX_UPLOAD_BYTES * 10 or total > max(archive.stat().st_size, 1) * MAX_RATIO + 50_000_000:
            raise IngestError("ZIP expands too far and looks like a zip bomb")
        base = target.resolve()
        for info in infos:
            name = info.filename.replace("\\", "/")
            if stat.S_ISLNK(info.external_attr >> 16):
                continue  # symlinks can point outside the workspace, so they are dropped
            destination = (base / name).resolve()
            if not destination.is_relative_to(base):
                raise IngestError(f"ZIP entry escapes the workspace: {info.filename}")
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, destination.open("wb") as sink:
                shutil.copyfileobj(source, sink)

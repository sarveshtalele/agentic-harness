"""Install a plugin from a zip into ROOT/plugins/<id>/. Every member is checked before anything is written.

Refused: a zip over 20 MB (or over 100 MB unpacked), a member that escapes the folder (zip-slip), a symlink, a missing
or invalid manifest, a bad id, and an id that is already installed.
"""
from __future__ import annotations

import io
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

from backend.config import ROOT
from backend.core import plugins
from backend.core.security import PathEscape, safe_path

MAX_ZIP = 20 * 1024 * 1024
MAX_UNPACKED = 100 * 1024 * 1024
PLUGIN_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def _members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = archive.infolist()
    if sum(i.file_size for i in infos) > MAX_UNPACKED:
        raise ValueError("The zip unpacks to more than 100 MB")
    for info in infos:
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"The zip holds a symlink, which is not allowed: {info.filename}")
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
            raise PathEscape(f"Absolute path in zip: {info.filename}")
    return infos


def _prefix(infos: list[zipfile.ZipInfo]) -> str:
    """A zip of a folder holds `name/...`: strip that one top folder when the manifest is inside it."""
    names = [i.filename.replace("\\", "/") for i in infos]
    if any(n in plugins.MANIFESTS for n in names):
        return ""
    tops = {n.split("/", 1)[0] for n in names}
    return f"{tops.pop()}/" if len(tops) == 1 and all("/" in n for n in names) else ""


def install_zip(data: bytes, root: Path | None = None) -> plugins.Plugin:
    if len(data) > MAX_ZIP:
        raise ValueError("A plugin zip may be at most 20 MB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Not a zip file: {exc}") from exc
    base = (root or ROOT).resolve() / "plugins"
    with archive, tempfile.TemporaryDirectory(prefix="aqe-plugin-") as tmp:
        staging = Path(tmp) / "plugin"
        staging.mkdir()
        infos = _members(archive)
        prefix = _prefix(infos)
        targets = []
        for info in infos:  # check every member first, so a refused zip writes nothing
            rel = info.filename.replace("\\", "/")[len(prefix):]
            if rel and not info.is_dir():
                targets.append((info, safe_path(staging, rel, for_write=True)))
        for info, target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
        found = plugins._plugin(staging)
        if not found.manifest or any(p.startswith(found.manifest) for p in found.problems):
            raise ValueError("The zip needs a valid plugin.json or .claude-plugin/plugin.json: " + "; ".join(found.problems))
        if not PLUGIN_ID.match(found.id):
            raise ValueError("A plugin id is lowercase letters, digits, dot, dash or underscore, at most 64 characters")
        dest = base / found.id
        if dest.exists() or found.id in {p.id for p in plugins.discover(root)}:
            raise FileExistsError(f"A plugin named {found.id} is already installed")
        base.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(dest))
    return next(p for p in plugins.discover(root) if p.id == found.id)

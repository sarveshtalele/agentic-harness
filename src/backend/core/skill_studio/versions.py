"""Published skills: immutable versions in skill_versions, the installed folder under SKILLS_DIR, zip in and out."""
from __future__ import annotations

import io
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from backend import config
from backend.core import ledger
from backend.core import skills as catalog
from backend.core.security import PathEscape, safe_path
from backend.core.skill_studio import checks
from backend.core.skill_studio.checks import NAME_RULE
from backend.db import db, now, rows

# The agentic-qe plugin's own skills and the platform's tools. The Studio never overwrites or deletes them.
CORE_SYSTEM_SKILLS = frozenset({
    "analyzing-repositories", "authoring-user-stories", "building-qe-dashboard", "designing-test-cases", "evaluator", "executing-tests",
    "extracting-requirements", "generating-test-code", "generating-test-data", "healing-tests", "planning-tests", "tracing-coverage", "skill-creator",
})
MAX_ZIP_BYTES = 10 * 1024 * 1024
MAX_ZIP_FILES = 200


class PublishRefused(ValueError):
    """Answered 409: a core skill, failing checks, or a broken upload."""


def skills_dir() -> Path:
    return config.SKILLS_DIR


def _install(name: str, source: Path) -> None:
    if name in CORE_SYSTEM_SKILLS:
        raise PublishRefused(f"{name} is a core platform skill and is read-only.")
    target = safe_path(skills_dir(), name, for_write=True)
    if target.exists():
        shutil.rmtree(target)  # the previous version stays in skill_versions
    shutil.copytree(source, target, symlinks=False)
    catalog.load(force=True)


def publish(name: str, folder: Path, *, author: str, project_id: str, plan_id: str | None, prompt_ref: str) -> dict:
    """Checks must all pass. The row is written before the folder is installed, so every installed state has a version."""
    if name in CORE_SYSTEM_SKILLS:
        raise PublishRefused(f"{name} is a core platform skill and is read-only.")
    found = checks.run(folder)
    if not checks.summary(found)["all_passed"]:
        raise PublishRefused("Checks failed: " + "; ".join(f"{c['check']}: {c['detail']}" for c in found if not c["passed"]))
    files = checks.read_files(folder)
    digest = checks.digest(files)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        version = con.execute("SELECT COALESCE(MAX(version),0)+1 FROM skill_versions WHERE name=?", (name,)).fetchone()[0]
        con.execute("INSERT INTO skill_versions (name, version, sha256, files_json, author, plan_id, project_id, prompt_ref, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (name, version, digest, json.dumps(files, ensure_ascii=False), author, plan_id, project_id, prompt_ref, now()))
    _install(name, folder)
    ledger.append(project_id, author, "skill.published", name, {"version": version, "sha256": digest, "plan_id": plan_id})
    return {"name": name, "version": version, "sha256": digest, "checks": found}


def history(name: str) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT name, version, sha256, author, plan_id, project_id, prompt_ref, created_at FROM skill_versions WHERE name=? ORDER BY version DESC", (name,)))


def zip_of(name: str, version: int) -> bytes:
    with db() as con:
        found = con.execute("SELECT files_json FROM skill_versions WHERE name=? AND version=?", (name, version)).fetchone()
    if not found:
        raise KeyError(f"{name} v{version}")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in json.loads(found[0]):
            archive.writestr(f"{name}/{item['path']}", item["content"])
    return buffer.getvalue()


def _members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = [i for i in archive.infolist() if not i.is_dir()]
    if len(infos) > MAX_ZIP_FILES:
        raise PublishRefused(f"The zip holds {len(infos)} files, over the {MAX_ZIP_FILES} limit.")
    if sum(i.file_size for i in infos) > MAX_ZIP_BYTES:
        raise PublishRefused(f"The zip unpacks to more than {MAX_ZIP_BYTES // (1024 * 1024)} MB.")
    for info in infos:
        if stat.S_ISLNK(info.external_attr >> 16):
            raise PublishRefused(f"{info.filename} is a symbolic link; links are refused.")
        parts = PurePosixPath(info.filename.replace("\\", "/")).parts
        if info.filename.startswith(("/", "\\")) or ".." in parts or (parts and ":" in parts[0]):
            raise PublishRefused(f"{info.filename} points outside the skill folder.")
    return infos


def upload(blob: bytes, *, author: str, project_id: str) -> dict:
    """A zip of one skill folder (`<name>/SKILL.md ...`) or of its contents (`SKILL.md ...`). Checked like a generated skill."""
    if len(blob) > MAX_ZIP_BYTES:
        raise PublishRefused(f"The zip is over {MAX_ZIP_BYTES // (1024 * 1024)} MB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as exc:
        raise PublishRefused(f"Not a zip file: {exc}") from None
    with archive, tempfile.TemporaryDirectory(prefix="skill-upload-") as scratch:
        infos = _members(archive)
        names = [i.filename.replace("\\", "/") for i in infos]
        tops = {n.split("/", 1)[0] for n in names}
        prefix = f"{tops.pop()}/" if len(tops) == 1 and all("/" in n for n in names) else ""
        skill_md = next((archive.read(i).decode("utf-8", errors="replace") for i, n in zip(infos, names) if n == f"{prefix}SKILL.md"), None)
        if skill_md is None:
            raise PublishRefused("The zip has no SKILL.md at its top level.")
        name = str((checks.frontmatter(skill_md)[0] or {}).get("name", ""))
        if not NAME_RULE.fullmatch(name) or len(name) > 64:
            raise PublishRefused(f"SKILL.md name {name!r} does not follow the name rule.")
        folder = Path(scratch) / name
        folder.mkdir()
        for info, member in zip(infos, names):
            try:
                target = safe_path(folder, member[len(prefix):], for_write=True)
            except PathEscape as exc:
                raise PublishRefused(f"{member} points outside the skill folder: {exc}") from None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
        return publish(name, folder, author=author, project_id=project_id, plan_id=None, prompt_ref="upload")


def delete(name: str, *, by: str, project_id: str) -> dict:
    """Removes the installed folder only. Every skill_versions row stays, and the ledger records who deleted it."""
    if name in CORE_SYSTEM_SKILLS:
        raise PublishRefused(f"{name} is a core platform skill and is read-only.")
    if not NAME_RULE.fullmatch(name):
        raise KeyError(f"skill {name}")
    target = safe_path(skills_dir(), name, for_write=True)
    if not target.is_dir():
        raise KeyError(f"skill {name}")
    shutil.rmtree(target)
    catalog.load(force=True)
    kept = len(history(name))
    ledger.append(project_id, by, "skill.deleted", name, {"versions_kept": kept})
    return {"name": name, "deleted": True, "versions_kept": kept}

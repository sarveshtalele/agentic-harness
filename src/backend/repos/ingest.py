"""Bring code into a project: clone a git URL (public or with a saved token) or unpack a ZIP safely."""
from __future__ import annotations

import json
import re
import shutil
import stat
import zipfile
from pathlib import Path

from backend.config import MAX_UPLOAD_BYTES, project_dir, repo_dir
from backend.core import ledger
from backend.core.errors import RepoError
from backend.db import db, now, row
from backend.repos import git, github, scan

MAX_ZIP_FILES = 100_000
MAX_RATIO = 200


class IngestError(RepoError, ValueError):
    pass


def _rm_tree(path: Path) -> None:
    def retry(func, target, _exc):  # git pack files are read-only, which blocks deletion on Windows
        Path(target).chmod(stat.S_IWRITE)
        func(target)

    if path.exists():
        shutil.rmtree(path, onexc=retry)


def _record(project_id: str, kind: str, url: str, ref: str, credential_id: str | None, actor: str) -> dict:
    repo = repo_dir(project_id)
    analysis = scan.analyze(repo)
    commit = git.head(repo)
    with db() as con:
        con.execute("INSERT OR REPLACE INTO repo_sources VALUES (?,?,?,?,?,?,?,?)", (project_id, kind, url, ref, credential_id, commit, json.dumps(analysis), now()))
    ledger.append(project_id, actor, "repo.ingested", url or "zip", {"kind": kind, "commit": commit, "files": analysis["total_files"]})
    return get(project_id)


def from_git(project_id: str, url: str, ref: str = "", credential_id: str | None = None, actor: str = "user") -> dict:
    if re.fullmatch(r"[\w.-]+/[\w.-]+", url.strip()):  # owner/repo shorthand
        url = f"https://github.com/{url.strip()}"
    token = github.token_for(credential_id)
    project_dir(project_id).mkdir(parents=True, exist_ok=True)
    staging = project_dir(project_id) / "repo.incoming"
    _rm_tree(staging)
    git.clone(url, staging, ref, token)  # the current repo survives a failed clone
    _rm_tree(repo_dir(project_id))
    staging.replace(repo_dir(project_id))
    return _record(project_id, "git", url, ref, credential_id, actor)


def from_zip(project_id: str, archive: Path, filename: str, actor: str = "user") -> dict:
    project_dir(project_id).mkdir(parents=True, exist_ok=True)
    staging = project_dir(project_id) / "repo.incoming"
    _rm_tree(staging)
    staging.mkdir(parents=True)
    safe_extract(archive, staging)
    entries = [p for p in staging.iterdir() if p.name != "__MACOSX"]
    root = entries[0] if len(entries) == 1 and entries[0].is_dir() else staging  # unwrap "project-main/" folders
    _rm_tree(repo_dir(project_id))
    root.replace(repo_dir(project_id))
    _rm_tree(staging)
    _rm_tree(repo_dir(project_id) / "__MACOSX")
    git.init_snapshot(repo_dir(project_id), f"Agentic QE Platform snapshot of {filename}")
    return _record(project_id, "zip", filename, "", None, actor)


def from_local(project_id: str, folder: str, actor: str = "user") -> dict:
    """Copy a local folder into the project. The original is never modified and symlinks are not followed."""
    source = Path(folder).expanduser()
    if not source.is_dir():
        raise IngestError(f"Not a folder: {folder}")
    project_dir(project_id).mkdir(parents=True, exist_ok=True)
    staging = project_dir(project_id) / "repo.incoming"
    _rm_tree(staging)
    shutil.copytree(source, staging, symlinks=True, ignore=lambda _d, names: [n for n in names if n in scan.SKIP_DIRS and n != ".git"] + [n for n in names if (Path(_d) / n).is_symlink()])
    _rm_tree(repo_dir(project_id))
    staging.replace(repo_dir(project_id))
    if git.is_repo(repo_dir(project_id)):
        return _record(project_id, "local", str(source), "", None, actor)
    git.init_snapshot(repo_dir(project_id), f"Agentic QE Platform snapshot of {source.name}")
    return _record(project_id, "local", str(source), "", None, actor)


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


def resync(project_id: str, actor: str = "user") -> dict:
    current = get(project_id)
    if not current:
        raise IngestError("No repository connected")
    if current["kind"] != "git":
        raise IngestError("Only Git sources can re-sync. Upload a new ZIP or import the folder again")
    return from_git(project_id, current["url"], current["ref"], current["credential_id"], actor)


def normalize_analysis(analysis: dict | None, root: Path | None = None) -> dict:
    """Normalize repository analysis dict so all expected keys always exist with safe defaults."""
    if not isinstance(analysis, dict):
        analysis = {}

    mode = analysis.get("mode") or "brownfield"

    # Languages: normalize to dict {str: int}
    raw_langs = analysis.get("languages")
    if isinstance(raw_langs, dict):
        languages = {str(k): int(v) if isinstance(v, (int, float)) else 1 for k, v in raw_langs.items()}
    elif isinstance(raw_langs, list):
        languages = {str(k): 1 for k in raw_langs if k}
    else:
        languages = {}

    # Lines of code: normalize to dict {str: int}
    raw_loc = analysis.get("lines_of_code")
    if isinstance(raw_loc, dict) and raw_loc:
        lines_of_code = {str(k): int(v) if isinstance(v, (int, float)) else 1 for k, v in raw_loc.items()}
    else:
        lines_of_code = {}
        if languages:
            for lang, count in languages.items():
                c = count if isinstance(count, int) and count > 1 else 1
                lines_of_code[lang] = c * 50 if c > 1 else 100
        elif root and root.exists() and root.is_dir():
            try:
                for p in scan.iter_files(root):
                    l = scan.LANGUAGES.get(p.suffix.lower())
                    if l:
                        lines_of_code[l] = lines_of_code.get(l, 0) + 20
            except Exception:
                pass

    # Test files and counts
    test_files = list(analysis.get("test_files") or []) if isinstance(analysis.get("test_files"), list) else []
    test_file_count = int(analysis.get("test_file_count") if analysis.get("test_file_count") is not None else len(test_files))

    # Total & Source files
    total_files = int(analysis.get("total_files") or 0)
    source_files = int(analysis.get("source_files") or 0)
    if total_files == 0 and root and root.exists() and root.is_dir():
        try:
            total_files = len(scan.tree(root, limit=5000))
        except Exception:
            pass
    if source_files == 0 and total_files > 0:
        source_files = max(total_files - test_file_count, 1)

    # Lists
    frameworks = list(analysis.get("frameworks") or []) if isinstance(analysis.get("frameworks"), list) else []
    test_runners = list(analysis.get("test_runners") or []) if isinstance(analysis.get("test_runners"), list) else []
    routes = list(analysis.get("routes") or []) if isinstance(analysis.get("routes"), list) else []
    ci = list(analysis.get("ci") or []) if isinstance(analysis.get("ci"), list) else []
    entrypoints = list(analysis.get("entrypoints") or []) if isinstance(analysis.get("entrypoints"), list) else []
    docs = list(analysis.get("docs") or []) if isinstance(analysis.get("docs"), list) else []

    # Manifests
    manifests = analysis.get("manifests")
    if not isinstance(manifests, dict):
        manifests = {
            "dependencies": analysis.get("dependencies", {}) if isinstance(analysis.get("dependencies"), dict) else {},
            "scripts": analysis.get("scripts", {}) if isinstance(analysis.get("scripts"), dict) else {},
        }

    # Top imports: always a list
    raw_imports = analysis.get("top_imports")
    if isinstance(raw_imports, list):
        top_imports = raw_imports
    elif isinstance(raw_imports, dict):
        top_imports = list(raw_imports.keys())
    else:
        top_imports = []

    normalized = {
        **analysis,
        "mode": str(mode),
        "total_files": total_files,
        "source_files": source_files,
        "test_file_count": test_file_count,
        "test_files": test_files,
        "languages": languages,
        "lines_of_code": lines_of_code,
        "frameworks": frameworks,
        "test_runners": test_runners,
        "routes": routes,
        "ci": ci,
        "entrypoints": entrypoints,
        "manifests": manifests,
        "docs": docs,
        "top_imports": top_imports,
    }
    return normalized


def _is_partial_analysis(analysis: dict | None) -> bool:
    if not analysis or not isinstance(analysis, dict):
        return True
    if not analysis.get("lines_of_code"):
        return True
    if not analysis.get("source_files") or not analysis.get("total_files"):
        return True
    for key in ("mode", "languages", "frameworks", "test_runners", "test_files", "routes", "ci", "entrypoints"):
        if key not in analysis:
            return True
    return False


def get(project_id: str) -> dict | None:
    try:
        with db() as con:
            found = row(con.execute("SELECT * FROM repo_sources WHERE project_id=?", (project_id,)))
    except Exception:
        return None
    if not found:
        return None

    raw_analysis = found.get("analysis")
    analysis = {}
    if isinstance(raw_analysis, str):
        try:
            analysis = json.loads(raw_analysis or "{}")
        except Exception:
            analysis = {}
    elif isinstance(raw_analysis, dict):
        analysis = raw_analysis

    repo = repo_dir(project_id)
    if repo.exists() and repo.is_dir():
        try:
            has_files = any(p.is_file() for p in repo.iterdir() if p.name != ".git") or any(scan.iter_files(repo))
        except Exception:
            has_files = False

        if has_files and _is_partial_analysis(analysis):
            try:
                fresh = scan.analyze(repo)
                if fresh:
                    analysis = fresh
                    commit = git.head(repo) or found.get("commit_sha", "")
                    with db() as con:
                        con.execute("UPDATE repo_sources SET analysis=?, commit_sha=? WHERE project_id=?", (json.dumps(analysis), commit, project_id))
                    found["commit_sha"] = commit
            except Exception:
                pass

    found["analysis"] = normalize_analysis(analysis, repo)
    try:
        found["log"] = git.log(repo) if repo.exists() and git.is_repo(repo) else []
    except Exception:
        found["log"] = []
    return found


def disconnect(project_id: str, actor: str = "user") -> None:
    with db() as con:
        con.execute("DELETE FROM repo_sources WHERE project_id=?", (project_id,))
    _rm_tree(repo_dir(project_id))
    ledger.append(project_id, actor, "repo.disconnected")

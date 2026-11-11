"""Projects API: export the project as a ZIP with source, documents and setup scripts."""
from __future__ import annotations

import io
import os
import zipfile

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.common import _project
from backend.api.projects.scripts import readme, setup_bat, setup_sh
from backend.config import project_dir
from backend.core import documents

router = APIRouter()


@router.get("/api/projects/{project_id}/export-zip")
def export_project_zip(project_id: str):
    """
    Exports the complete project SDLC package as a downloadable ZIP archive containing:
    1. Scaffolding / source files from data/projects/{project_id}/sandbox (or repo)
    2. Governed requirements and test specifications (.md)
    3. Automated setup script for Mac/Linux (setup_mac_linux.sh)
    4. Automated setup script for Windows (setup_windows.bat)
    5. README_SETUP.md with quickstart and test execution instructions
    """
    proj = _project(project_id)
    buf = io.BytesIO()

    # Determine files to include
    p_dir = project_dir(project_id)
    sandbox_dir = p_dir / "sandbox"
    docs_dir = p_dir / "documents"

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        files_added = 0

        # 1. Add files from sandbox
        if sandbox_dir.exists() and sandbox_dir.is_dir():
            for root, dirs, files in os.walk(sandbox_dir):
                # Skip build artifacts / venvs
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache")]
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, sandbox_dir)
                    zip_file.write(full_p, arcname=f"src/{rel_p}")
                    files_added += 1

        # 2. Add governed documents
        if docs_dir.exists() and docs_dir.is_dir():
            for root, _, files in os.walk(docs_dir):
                for file in files:
                    if file.endswith((".md", ".json", ".feature")):
                        full_p = os.path.join(root, file)
                        rel_p = os.path.relpath(full_p, docs_dir)
                        zip_file.write(full_p, arcname=f"docs/{rel_p}")
                        files_added += 1

        # 3. Add database documents if docs directory is sparse
        proj_docs = documents.list_for(project_id)
        for doc in proj_docs:
            d_full = documents.get(doc["id"])
            arc_name = f"docs/{doc['kind']}_{doc['id']}.md"
            if arc_name not in zip_file.namelist():
                content = d_full.get("content", f"# {doc['title']}\n\nVersion: {doc['current_version']}\n")
                zip_file.writestr(arc_name, content)
                files_added += 1

        # 4. Generate setup_mac_linux.sh
        zip_file.writestr("setup_mac_linux.sh", setup_sh(proj))

        # 5. Generate setup_windows.bat
        zip_file.writestr("setup_windows.bat", setup_bat(proj))

        # 6. Generate README_SETUP.md
        zip_file.writestr("README_SETUP.md", readme(proj, project_id))

    buf.seek(0)
    filename = f"{project_id}_sdlc_export.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )

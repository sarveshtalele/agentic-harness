"""Text of an uploaded source file, in sections that name where each part came from (docs/PHASE2_PLAN.md R3).

PDF pages become "## Page N", PowerPoint slides "## Slide N" with the speaker notes under "Notes:", Word documents keep
their headings, spreadsheets one section per sheet. Old binary .ppt and .doc files are converted by LibreOffice when it
is installed (`soffice`), otherwise the upload is refused with what to install. The caller redacts the text and keeps
the original file; nothing here runs the file's own content.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".feature", ".rst"}
MAX_BYTES = int(os.environ.get("ATLAS_MAX_UPLOAD_MB", "25")) * 1024 * 1024
SOFFICE_PLACES = ["/Applications/LibreOffice.app/Contents/MacOS/soffice", r"C:\Program Files\LibreOffice\program\soffice.exe"]


class UnsupportedFile(ValueError):
    pass


def soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice") or next((p for p in SOFFICE_PLACES if Path(p).is_file()), None)


def _converted(filename: str, blob: bytes, to: str) -> bytes:
    """An old .ppt or .doc converted to .pptx or .docx by LibreOffice, in a temporary folder."""
    from backend.qe.execution.runners import clean_env

    program = soffice()
    if not program:
        raise UnsupportedFile(f"{Path(filename).suffix} files need LibreOffice on the server to read them. Save the file as .{to} "
                              "and upload that, or ask the administrator to install LibreOffice")
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / f"upload{Path(filename).suffix.lower()}"
        source.write_bytes(blob)
        profile = Path(tmp, "profile").as_uri()  # its own profile, so a running LibreOffice does not block the conversion
        done = subprocess.run([program, f"-env:UserInstallation={profile}", "--headless", "--convert-to", to, "--outdir", tmp, str(source)],
                              capture_output=True, timeout=180, check=False, env=clean_env())
        out = Path(tmp) / f"upload.{to}"
        if done.returncode or not out.is_file():
            raise UnsupportedFile(f"LibreOffice could not convert {filename} (exit {done.returncode}). Save it as .{to} and upload that")
        return out.read_bytes()


def _pptx(blob: bytes) -> str:
    from pptx import Presentation

    parts = []
    for number, slide in enumerate(Presentation(io.BytesIO(blob)).slides, 1):
        text = "\n".join(s.text_frame.text for s in slide.shapes if s.has_text_frame and s.text_frame.text.strip())
        notes = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide and slide.notes_slide.notes_text_frame else ""
        parts.append(f"## Slide {number}\n{text}" + (f"\n\nNotes: {notes}" if notes else ""))
    return "\n\n".join(parts)


def extract_text(filename: str, blob: bytes) -> str:
    if len(blob) > MAX_BYTES:
        raise UnsupportedFile(f"{filename} is {len(blob) // (1024 * 1024)} MB; the limit is {MAX_BYTES // (1024 * 1024)} MB (ATLAS_MAX_UPLOAD_MB)")
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in TEXT_SUFFIXES:
        return blob.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n\n".join(f"## Page {n}\n{page.extract_text() or ''}" for n, page in enumerate(PdfReader(io.BytesIO(blob)).pages, 1))
    if suffix in (".docx", ".doc"):
        from backend.repos.doc_parser import parse_docx_to_markdown

        return parse_docx_to_markdown(_converted(filename, blob, "docx") if suffix == ".doc" else blob)
    if suffix == ".xlsx":
        from openpyxl import load_workbook

        book = load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
        return "\n\n".join(f"## {sheet.title}\n" + "\n".join(" | ".join("" if c is None else str(c) for c in row) for row in sheet.iter_rows(values_only=True)) for sheet in book)
    if suffix in (".pptx", ".ppt"):
        return _pptx(_converted(filename, blob, "pptx") if suffix == ".ppt" else blob)
    raise UnsupportedFile(f"Unsupported file type {suffix or filename}. Use .md, .txt, .pdf, .docx, .pptx, .xlsx, .csv, .json, .yaml "
                          "(.doc and .ppt with LibreOffice on the server)")

"""Size, XXE and zip-bomb limits for uploaded documents."""
from __future__ import annotations

import io
import re
import shutil
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET  # noqa: F401 - the Element type callers receive

import defusedxml.ElementTree as defused_ET  # a requirement: there is no unsafe fallback parser
import defusedxml.common as defused_common

HAVE_DEFUSEDXML = True


# Maximum upload size for documents: 20 MB
MAX_DOC_SIZE = 20 * 1024 * 1024


# Maximum uncompressed size for zip/archive payloads: 100 MB
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024


# Maximum compression ratio to prevent zip bombs
MAX_COMPRESSION_RATIO = 100


# Maximum file count in an archive
MAX_ZIP_ENTRIES = 5000


class DocumentSecurityError(ValueError):
    """Base error for document security violations."""
    pass


class XXEError(DocumentSecurityError):
    """Raised when XXE, DTD or forbidden entity expansions are detected."""
    pass


class ZipSlipError(DocumentSecurityError):
    """Raised when an archive entry attempts directory traversal / zip slip."""
    pass


class ZipBombError(DocumentSecurityError):
    """Raised when an archive entry size or compression ratio exceeds safe limits."""
    pass


def safe_parse_xml(content: str | bytes, forbid_dtd: bool = True, forbid_entities: bool = True) -> ET.Element:
    """Safely parse XML content, preventing XXE injection and Billion Laughs DoS."""
    raw_str = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content

    # Heuristic check for explicit DTD / ENTITY / SYSTEM attacks
    if forbid_dtd and re.search(r"<!DOCTYPE\b", raw_str, re.IGNORECASE):
        if re.search(r"<!ENTITY\b", raw_str, re.IGNORECASE):
            raise XXEError("XML contains forbidden entity declarations (XXE / Entity expansion)")
        if re.search(r"\bSYSTEM\b|\bPUBLIC\b", raw_str, re.IGNORECASE):
            raise XXEError("XML contains external entity or DTD reference (XXE)")

    if forbid_entities and re.search(r"<!ENTITY\b", raw_str, re.IGNORECASE):
        raise XXEError("XML contains forbidden entity declarations")

    if HAVE_DEFUSEDXML:
        try:
            return defused_ET.fromstring(
                content,
                forbid_dtd=forbid_dtd,
                forbid_entities=forbid_entities,
                forbid_external=True,
            )
        except (defused_common.DefusedXmlException, defused_common.EntitiesForbidden, defused_common.DTDForbidden) as exc:
            raise XXEError(f"Secure XML parser blocked unsafe payload: {exc}") from exc
        except Exception as exc:
            raise DocumentSecurityError(f"XML parse failure: {exc}") from exc
    raise DocumentSecurityError("XML parsing needs defusedxml")  # unreachable while defusedxml is installed


def validate_zip_archive(
    archive_blob_or_path: bytes | Path | io.BytesIO,
    max_size: int = MAX_DOC_SIZE,
    max_uncompressed: int = MAX_UNCOMPRESSED_SIZE,
) -> zipfile.ZipFile:
    """Validate archive integrity, checking for Zip Slip, excessive entries, and Zip Bombs."""
    if isinstance(archive_blob_or_path, (bytes, bytearray)):
        if len(archive_blob_or_path) > max_size:
            raise ZipBombError(f"Upload size {len(archive_blob_or_path)} bytes exceeds maximum {max_size} bytes")
        stream = io.BytesIO(archive_blob_or_path)
    elif isinstance(archive_blob_or_path, io.BytesIO):
        blob = archive_blob_or_path.getvalue()
        if len(blob) > max_size:
            raise ZipBombError(f"Upload size {len(blob)} bytes exceeds maximum {max_size} bytes")
        stream = archive_blob_or_path
    elif isinstance(archive_blob_or_path, Path):
        st_size = archive_blob_or_path.stat().st_size
        if st_size > max_size:
            raise ZipBombError(f"Upload size {st_size} bytes exceeds maximum {max_size} bytes")
        stream = open(archive_blob_or_path, "rb")
    else:
        raise TypeError("Expected bytes, BytesIO, or Path")

    try:
        zf = zipfile.ZipFile(stream)
    except zipfile.BadZipFile as exc:
        raise DocumentSecurityError("Invalid or corrupted zip archive") from exc

    infos = zf.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise ZipBombError(f"Archive entry count {len(infos)} exceeds maximum {MAX_ZIP_ENTRIES}")

    total_uncompressed = 0
    for info in infos:
        clean_name = info.filename.replace("\\", "/")
        if clean_name.startswith("/") or clean_name.startswith("../") or "/../" in clean_name or clean_name == "..":
            raise ZipSlipError(f"Zip Slip / traversal detected in entry: {info.filename}")

        parts = Path(clean_name).parts
        if ".." in parts:
            raise ZipSlipError(f"Zip Slip / traversal path detected: {info.filename}")

        total_uncompressed += info.file_size
        if total_uncompressed > max_uncompressed:
            raise ZipBombError(f"Uncompressed archive size exceeds limit ({max_uncompressed} bytes)")

        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > MAX_COMPRESSION_RATIO and info.file_size > 1_000_000:
                raise ZipBombError(f"Zip bomb detected: compression ratio {ratio:.1f} exceeds limit")

    return zf


def safe_extract_zip(
    archive: bytes | Path | io.BytesIO,
    target_dir: Path,
    sanitize_names: bool = True,
) -> list[Path]:
    """Safely extract archive entries, strictly sanitizing filenames and confirming destination bounds."""
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    zf = validate_zip_archive(archive)

    extracted_paths: list[Path] = []
    with zf:
        for info in zf.infolist():
            raw_name = info.filename.replace("\\", "/")
            if sanitize_names:
                safe_name = Path(raw_name).name
                if not safe_name:
                    continue
                dest = (target_dir / safe_name).resolve()
            else:
                dest = (target_dir / raw_name).resolve()

            if not dest.is_relative_to(target_dir):
                raise ZipSlipError(f"Entry {info.filename} escapes destination directory {target_dir}")

            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted_paths.append(dest)

    return extracted_paths

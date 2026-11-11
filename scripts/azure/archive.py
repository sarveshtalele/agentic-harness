"""Create and verify the deployment zips."""
from __future__ import annotations

import hashlib
import os
import zipfile
from pathlib import Path
from typing import Any, Optional

from scripts.azure.files import SKIP_DIRS, SKIP_FILES


def create_zip(target_path: Path, entries: dict[str, Path]) -> dict[str, Any]:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    uncompressed_size = 0
    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, src in sorted(entries.items()):
            file_bytes = src.read_bytes()
            uncompressed_size += len(file_bytes)
            # Preserve unix permissions (especially executable bit for .sh scripts)
            zinfo = zipfile.ZipInfo(name)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            is_executable = src.suffix == ".sh" or os.access(src, os.X_OK)
            zinfo.external_attr = ((0o755 if is_executable else 0o644) & 0xFFFF) << 16
            archive.writestr(zinfo, file_bytes)
    return {
        "path": target_path,
        "count": len(entries),
        "uncompressed_bytes": uncompressed_size,
        "compressed_bytes": target_path.stat().st_size,
        "sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
    }


def verify_kudu(meta: dict[str, Any], expected_critical_files: list[str], log, error) -> bool:
    zip_path: Path = meta["path"]
    log(f"Verifying {zip_path.name}...")
    valid = True
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            bad_file = archive.testzip()
            if bad_file:
                error(f"CRC check failed on file: {bad_file} in {zip_path.name}")
                return False
            names = set(archive.namelist())
            for req in expected_critical_files:
                if req not in names:
                    error(f"Missing required file '{req}' in {zip_path.name}!")
                    valid = False
            for name in names:
                parts = Path(name).parts
                if any(p in SKIP_DIRS for p in parts) or any(p.startswith(".next") for p in parts):
                    error(f"Forbidden directory '{name}' leaked into {zip_path.name}!")
                    valid = False
                if Path(name).name in SKIP_FILES:
                    error(f"Forbidden file '{name}' leaked into {zip_path.name}!")
                    valid = False
    except Exception as exc:
        error(f"Failed to read {zip_path.name}: {exc}")
        return False
    return valid


def verify_convert(meta: dict[str, Any], required_files: list[str], error, allowed_dirs: Optional[set[str]] = None) -> bool:
    zip_path: Path = meta["path"]
    valid = True
    effective_skip = SKIP_DIRS - (allowed_dirs or set())
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            corrupt = zf.testzip()
            if corrupt:
                error(f"  CRC check failed on file: {corrupt} in {zip_path.name}")
                return False
            names = set(zf.namelist())
            for req in required_files:
                if req not in names:
                    error(f"  Required file '{req}' missing from {zip_path.name}!")
                    valid = False
            for name in names:
                parts = Path(name).parts
                if any(p in effective_skip for p in parts):
                    error(f"  Forbidden directory leaked into {zip_path.name}: {name}")
                    valid = False
                if Path(name).name in SKIP_FILES:
                    error(f"  Forbidden file leaked into {zip_path.name}: {name}")
                    valid = False
    except Exception as exc:
        error(f"  Failed reading archive {zip_path.name}: {exc}")
        return False
    return valid

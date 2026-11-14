"""Verified download and atomic extraction for toolchains.py: a wrong hash deletes the file and installs nothing."""
from __future__ import annotations

import hashlib
import tarfile
import time
import urllib.request
from pathlib import Path


def log(message: str) -> None:
    print(f"[agentic-qe toolchains] {message}", flush=True)


def download(url: str, algo: str, digest: str, target: Path) -> None:
    """Stream url to target, hashing as it goes. The file is kept only if the digest matches the pinned one."""
    hasher = hashlib.new(algo)
    request = urllib.request.Request(url, headers={"User-Agent": "agentic-qe-toolchains"})
    last: Exception | None = None
    for attempt in range(1, 4):
        hasher = hashlib.new(algo)
        try:
            size = 0
            with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as out:
                for chunk in iter(lambda: response.read(1 << 20), b""):
                    hasher.update(chunk)
                    out.write(chunk)
                    size += len(chunk)
                expected = int(response.headers.get("Content-Length") or size)
            if size != expected:
                raise OSError(f"connection closed after {size} of {expected} bytes")  # truncated: retried, not a checksum failure
            if hasher.hexdigest() != digest:
                target.unlink(missing_ok=True)
                raise RuntimeError(f"{algo} mismatch for {url}: expected {digest[:16]}..., got {hasher.hexdigest()[:16]}... (file removed, not installed)")
            return
        except RuntimeError:
            raise  # a wrong checksum is never retried into acceptance
        except OSError as exc:
            last = exc
            log(f"download attempt {attempt} failed: {exc}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"could not download {url}: {last}")


def extract(archive: Path, destination: Path, strip: int) -> None:
    """Unpack into destination, dropping `strip` leading path parts. Members that would land outside it are refused."""
    destination.mkdir(parents=True)
    base = destination.resolve()
    with tarfile.open(archive) as tar:
        members = []
        for member in tar.getmembers():
            parts = Path(member.name).parts[strip:]
            if not parts:
                continue
            member.name = Path(*parts).as_posix()
            if not (base / member.name).resolve().is_relative_to(base):
                raise RuntimeError(f"refusing archive member outside the folder: {member.name}")
            members.append(member)
        tar.extractall(destination, members=members, filter="data" if hasattr(tarfile, "data_filter") else None)

"""`http` hooks (Claude Code's hook type): POST the hook's JSON to a URL and read the answer like a command hook's output.

Only https URLs, or http to this machine (localhost, 127.0.0.1, ::1), so hook payloads never cross a network in clear
text. Headers are taken as written (no environment variables are expanded into them). A 2xx answer's body is parsed as the
hook's JSON output; any other status is a non-blocking hook error, as a command hook exiting with a code other than 0 or 2.
"""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlparse

LOCAL = frozenset({"localhost", "127.0.0.1", "::1"})


def post(url: str, payload: dict, headers: dict | None, timeout: int) -> subprocess.CompletedProcess:
    parsed = urlparse(url)
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in LOCAL):
        raise ValueError(f"http hook URL must be https (or http to localhost): {parsed.scheme}://{parsed.hostname}")
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", **{str(k): str(v) for k, v in (headers or {}).items()}})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310 - scheme checked above
            return subprocess.CompletedProcess([url], 0, answer.read().decode("utf-8", errors="replace"), "")
    except urllib.error.HTTPError as exc:
        return subprocess.CompletedProcess([url], 1, "", f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:400]}")
    except urllib.error.URLError as exc:
        raise OSError(f"http hook could not reach {parsed.hostname}: {exc.reason}") from exc

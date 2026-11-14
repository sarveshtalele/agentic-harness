"""Embeddings from the configured OpenAI-compatible endpoint (POST {base_url}/embeddings). Never invented.

A missing key, a name the endpoint does not know, or an endpoint without an embeddings API gives `None` and a reason, and search
stays keyword only; the reason is stored on the source and returned by the API.
"""
from __future__ import annotations

import os

import httpx

from backend.core.security import redact
from backend.maf import llm

DEFAULT_MODEL = "text-embedding-3-small"  # tried only when ATLAS_EMBEDDING_MODEL or the llm_embedding_model setting is not set
BATCH = 64


def model_name() -> str:
    return llm._get("llm_embedding_model") or os.environ.get("ATLAS_EMBEDDING_MODEL", "") or DEFAULT_MODEL


def embed(texts: list[str], *, transport: httpx.BaseTransport | None = None) -> tuple[list[list[float]] | None, str]:
    """(one vector per text, "") or (None, why there are none). `transport` is a test seam for a local stand-in endpoint."""
    cfg = llm.current()
    if not cfg["api_key"]:
        return None, "No model endpoint key is configured, so there are no embeddings."
    base = (cfg["base_url"] or "https://api.openai.com/v1").rstrip("/")
    name, out = model_name(), []
    try:
        with httpx.Client(timeout=60, transport=transport) as http:
            for i in range(0, len(texts), BATCH):
                reply = http.post(f"{base}/embeddings", headers={"Authorization": f"Bearer {cfg['api_key']}"}, json={"model": name, "input": texts[i : i + BATCH]})
                if reply.status_code != 200:
                    return None, redact(f"The endpoint has no usable embeddings API for {name} (HTTP {reply.status_code}: {reply.text[:160]}).")
                data = sorted(reply.json().get("data") or [], key=lambda d: d.get("index", 0))
                if len(data) != len(texts[i : i + BATCH]) or not all(d.get("embedding") for d in data):
                    return None, f"The endpoint answered {name} with the wrong number of embeddings."
                out += [[float(x) for x in d["embedding"]] for d in data]
    except (httpx.HTTPError, ValueError) as exc:
        return None, redact(f"The embeddings call failed: {str(exc) or type(exc).__name__}")
    return out, ""

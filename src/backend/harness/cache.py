"""Harness Semantic & Prompt Caching Mechanism.
Reduces LLM token consumption by caching deterministic tool outcomes,
AST representations, and prompt responses using SHA-256 signatures.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple


class HarnessCache:
    """In-memory LRU and disk-backed cache for prompt completions and tool evaluations."""

    _instance: Optional[HarnessCache] = None

    def __new__(cls) -> HarnessCache:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: Dict[str, Tuple[Any, float, int]] = {}
            cls._instance._max_size = 500
            cls._instance._ttl_seconds = 3600 * 4  # 4 hours
            cls._instance._total_hits = 0
            cls._instance._total_tokens_saved = 0
        return cls._instance

    @staticmethod
    def compute_key(prefix: str, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}:{digest}"

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        value, timestamp, tokens = self._cache[key]
        if time.time() - timestamp > self._ttl_seconds:
            del self._cache[key]
            return None
        self._total_hits += 1
        self._total_tokens_saved += tokens
        return value

    def set(self, key: str, value: Any, estimated_tokens: int = 250) -> None:
        if len(self._cache) >= self._max_size:
            # Evict oldest 20% entries
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
            for k in sorted_keys[: len(sorted_keys) // 5]:
                del self._cache[k]
        self._cache[key] = (value, time.time(), estimated_tokens)

    def stats(self) -> Dict[str, Any]:
        return {
            "entriesCount": len(self._cache),
            "totalHits": self._total_hits,
            "tokensSaved": self._total_tokens_saved,
            "maxSize": self._max_size,
        }


global_harness_cache = HarnessCache()

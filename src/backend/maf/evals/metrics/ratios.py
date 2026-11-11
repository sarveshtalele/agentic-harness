"""The arithmetic of evaluation: ratios, one-to-one matching of found items to a key, and keyword coverage. Nothing to measure is None."""
from __future__ import annotations

import json
from typing import Callable


def ratio(part: float, whole: float) -> float | None:
    """None when the whole is zero: nothing was there to measure."""
    return None if not whole else part / whole


def precision(tp: int, fp: int) -> float | None:
    return ratio(tp, tp + fp)


def recall(tp: int, fn: int) -> float | None:
    return ratio(tp, tp + fn)


def f1(tp: int, fp: int, fn: int) -> float | None:
    return ratio(2 * tp, 2 * tp + fp + fn)


def match(found: list[dict], key: list[dict], same: Callable[[dict, dict], bool]) -> dict:
    """One-to-one matching of found items to key items. Returns the counts and the lists behind them."""
    left = list(key)
    hits, extras = [], []
    for item in found:
        target = next((k for k in left if same(item, k)), None)
        if target is None:
            extras.append(item)
        else:
            left.remove(target)
            hits.append({"found": item, "key": target})
    tp, fp, fn = len(hits), len(extras), len(left)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision(tp, fp), "recall": recall(tp, fn), "f1": f1(tp, fp, fn), "missed": left, "extra": extras}


def at_location(item: dict, key: dict) -> bool:
    """Same file and a line within `tolerance` of the key's line."""
    same_file = str(item.get("file", "")).replace("\\", "/") == key.get("file")
    return same_file and abs(int(item.get("line") or 0) - int(key.get("line") or 0)) <= int(key.get("tolerance", 3))


def has_keywords(item: dict, key: dict) -> bool:
    """Every keyword of the key appears in the item's text, which is how requirements and answers are matched."""
    text = json.dumps(item, default=str).lower()
    return bool(key.get("keywords")) and all(word.lower() in text for word in key["keywords"])


def coverage(text: str, key: list[dict]) -> dict:
    """Facts-in-text key: which labelled facts appear in a prose answer. Extras cannot be counted in prose, so fp is None and only recall has a value."""
    hits = [k for k in key if has_keywords({"text": text}, k)]
    return {"tp": len(hits), "fp": None, "fn": len(key) - len(hits), "precision": None, "recall": recall(len(hits), len(key) - len(hits)), "f1": None,
            "missed": [k for k in key if k not in hits], "extra": []}

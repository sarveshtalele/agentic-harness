"""The admin token usage report."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter
from fastapi.responses import Response

from backend.core import auth, models

router = APIRouter()

@router.get("/api/usage")
def usage(days: int = 30, format: str = "json"):
    """Admin only (rule in core/auth.py). Everything comes from recorded calls; with none, the lists are empty."""
    days = max(1, min(days, 366))
    found = models.usage_rows(days)
    names = auth.display_names({r["user_id"] for r in found if r["user_id"]})
    for item in found:
        item["user"] = names.get(item["user_id"], item["user_id"] or "(not recorded)")
    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["day", "user", "model", "agent", "calls", "tokens_in", "tokens_out"])
        for r in found:
            writer.writerow([r["day"], r["user"], r["model"] or "(not recorded)", r["agent"], r["calls"], r["tokens_in"], r["tokens_out"]])
        return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="usage-{days}d.csv"'})

    def total(key: str) -> list[dict]:
        sums: dict[str, int] = {}
        for r in found:
            label = r[key] or "(not recorded)"
            sums[label] = sums.get(label, 0) + r["tokens_in"] + r["tokens_out"]
        return [{"name": k, "tokens": v} for k, v in sorted(sums.items(), key=lambda kv: -kv[1])]

    by_day = total("day")
    return {"days": days, "timezone": models.timezone_name(), "calls": sum(r["calls"] for r in found), "tokens": sum(r["tokens_in"] + r["tokens_out"] for r in found),
            "by_user": total("user"), "by_model": total("model"), "by_agent": total("agent"), "by_day": sorted(by_day, key=lambda r: r["name"])}

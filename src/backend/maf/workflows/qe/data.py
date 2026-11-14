"""QE Test Data Stage: Synthesizing deterministic fixtures and data contracts without model token costs."""
from __future__ import annotations

import asyncio
import json
from backend.core import documents
from backend.maf.engine import RunContext
from backend.qe import plugin_bridge, test_data


async def qe_data(rc: RunContext, state: dict) -> dict:
    """Plugin command qe-data (skill generating-test-data). Code builds the datasets deterministically. Part of Gate 3."""
    fixtures = test_data.build_fixtures(state["cases"], state["requirements"])
    used = sorted(fixtures["datasets"])
    doc = documents.create(rc.project_id, "test_data", "Synthesized Test Fixtures & Data Contracts", "```json\n" + json.dumps(fixtures, indent=2, ensure_ascii=False) + "\n```", "system", data=fixtures, run_id=rc.run_id)
    rc.log(f"Test data built for {len(fixtures['cases'])} cases from {len(used)} shared datasets ({', '.join(used) or 'none needed'}); no model call", {"document_id": doc["id"]}, "artifact")
    check = {"ok": None, "error": (state.get("design_audit") or {}).get("error") or "greenfield: the plugin's gate check needs code-evidenced requirements"}
    if state["mode"] == "brownfield" and (state.get("design_audit") or {}).get("app"):
        app = state["design_audit"]["app"]
        plugin_bridge.write(rc.project_id, app, "04-design/fixtures.json", fixtures)
        check = await asyncio.to_thread(plugin_bridge.check_gate, rc.project_id, app, 3)  # Gate 3 sensor: design and data together
        rc.log(f"agentic-qe Gate 3 check: {'PASS' if check['ok'] else 'FAIL'}" + (f"; {check['error']}" if check["error"] else ""), check)
    return {"fixtures": fixtures, "fixtures_doc": doc["id"], "design_plugin_check": check}

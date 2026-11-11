"""QE Test Data Stage: Synthesizing deterministic fixtures and data contracts without model token costs."""
from __future__ import annotations

import json
from backend.core import documents
from backend.maf.engine import RunContext
from backend.qe import test_data


async def qe_data(rc: RunContext, state: dict) -> dict:
    """Plugin command qe-data (skill generating-test-data). Code builds the datasets deterministically. Part of Gate 3."""
    fixtures = test_data.build_fixtures(state["cases"], state["requirements"])
    used = sorted(fixtures["datasets"])
    doc = documents.create(rc.project_id, "test_data", "Synthesized Test Fixtures & Data Contracts", "```json\n" + json.dumps(fixtures, indent=2, ensure_ascii=False) + "\n```", "system", data=fixtures, run_id=rc.run_id)
    rc.log(f"Test data built for {len(fixtures['cases'])} cases from {len(used)} shared datasets ({', '.join(used) or 'none needed'}); no model call", {"document_id": doc["id"]}, "artifact")
    return {"fixtures": fixtures, "fixtures_doc": doc["id"]}

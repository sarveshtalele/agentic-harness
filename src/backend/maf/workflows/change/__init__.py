"""Change workflow: feature, bug fix, or traceback diagnosis on an isolated branch with real tests."""
from __future__ import annotations

from backend.maf.engine import REGISTRY, Definition, StageSpec
from backend.maf.workflows.change.deliver import change_deliver, change_gate
from backend.maf.workflows.change.implement import _fix_file_by_file, change_implement
from backend.maf.workflows.change.prepare import MAX_FIX_ALL, _chosen_findings, _rescan, change_prepare
from backend.maf.workflows.change.scope import FileSelection, _select_files, safe_exists, spec_gaps
from backend.maf.workflows.change.verify import _changed_assertions, _failing_files, cap_for_failed_tests, change_verify


def change_definition() -> Definition:
    return Definition("change", [
        StageSpec("prepare", change_prepare, "Prepare branch", next="implement"),
        StageSpec("implement", change_implement, "Implement", next="verify"),
        StageSpec("verify", change_verify, "Run tests", approval=lambda rc, s: None if s.get("_next") else change_gate(rc, s), on_approved=change_deliver, on_rejected="implement", next="END"),
    ], routes={"verify": ["implement"]})


REGISTRY["change"] = change_definition


__all__ = ["FileSelection", "MAX_FIX_ALL", "_changed_assertions", "_chosen_findings", "_failing_files", "_fix_file_by_file", "_rescan", "_select_files", "cap_for_failed_tests", "change_definition",
           "change_deliver", "change_gate", "change_implement", "change_prepare", "change_verify", "safe_exists", "spec_gaps"]

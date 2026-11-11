"""Shared helpers for the execution stage tests."""


def junit_result(*messages):
    cases = [{"name": f"test_TC_APP_00{i}", "classname": f"tests.agentic_qe.test_tc_app_00{i}", "time": 0, "status": "failed", "message": m} for i, m in enumerate(messages, 1)]
    return {"runner": "pytest", "verdict": "FAIL", "reason": "", "exit_code": 1, "passed": 3, "failed": len(cases), "skipped": 0, "total": 3 + len(cases), "cases": cases}

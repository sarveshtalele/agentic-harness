"""Structured QE artifacts and the plugin's validators, ported from TypeScript to Python."""
from __future__ import annotations

from .schemas import (
    CASE_TYPES,
    ORACLES,
    Requirement,
    COMMENT_START,
    is_comment,
    RequirementSet,
    PlanArea,
    TestPlan,
    ConfidenceReview,
    AuditVerdict,
    AuditSet,
    ArchitectureNote,
)
from .cases import (
    TestCase,
    CaseSet,
    CASE_COLUMNS,
    _FIELDS,
    _steps,
    cases_from_table,
    _same,
)
from .quota import (
    coverage_gaps,
    level_gaps,
    planned_levels,
    duplicate_scenarios,
    plan_confidence,
    ExecutionSummary,
    PRIORITY_RANK,
    limit_cases,
    FULL_QUOTA,
    case_quota,
    apply_quota,
)
from .domain import (
    case_problems,
    data_kind,
    input_type,
    states_error,
)

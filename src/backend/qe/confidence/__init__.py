"""Per-case confidence, ported from the plugin's confidence.ts. The reviewer model scores; this code decides.

The total is the sum of the scores, the verdict follows the rule, and every cited file:line must exist in the repository
under test. A score whose evidence cannot be found is a REJECT, so an invented review cannot pass a weak case.
"""
from __future__ import annotations

from .rubric import (
    RUBRIC,
    THRESHOLD,
    ASSERTION_FLOOR,
    MAX_FILE_BYTES,
    TEST_FAIL_CAP,
    RANK,
    Component,
    Flaw,
    Item,
    Review,
    verdict_for,
    worst,
)
from .check import (
    parse_cite,
    _whole,
    cite_status,
    check_item,
    not_run,
    check_doc,
)
from .summary import (
    summarise,
    cap_failed,
    reject_ids,
    flaw_lines,
)

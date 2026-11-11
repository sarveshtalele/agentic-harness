"""Registered test runners, JUnit parsing, honest verdicts. No shell, bounded time, scrubbed environment."""
from __future__ import annotations

from .runners import (
    SENSITIVE_ENV,
    TAIL,
    GIT_AUTHOR,
    clean_env,
    parse_junit,
    verdict,
    detect_python,
    _pytest,
    _node_tool,
    build_command,
    REGISTERED,
    pick_runner,
    run_suite,
)
from .install import (
    _commit_date,
    _test_extras,
    install_dependencies,
    async_test_files,
    install_pytest_asyncio,
)
from .code import (
    syntax_error,
    ASSERTION,
    WEAKENING,
    assertions_preserved,
    _module_names,
    invalid_test_code,
)
from .failures import (
    failed_names,
    compare_to_baseline,
    choose_runners,
    CLASSIFICATION,
    ENV_EVIDENCE,
    ASSERTION_LINE,
    _first_line,
    _rate_limited,
    classify_failure,
    HEALING_PATTERNS,
    SPECIFIC,
    failure_record,
    failure_counts,
)
from .environment import (
    environment_facts,
    LIMITER_PACKAGES,
    LIMITER_CODE,
    environment_notes,
)
from .verdicts import (
    code_summary,
    summary_evidence,
    summary_problems,
    heal_allowed,
)

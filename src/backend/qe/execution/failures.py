"""Failure classification, healing patterns and baseline comparison."""
from __future__ import annotations

import re
from backend.qe.execution.runners import REGISTERED


def failed_names(result: dict) -> list[str]:
    return [f"{c['classname']}::{c['name']}" for c in result.get("cases", []) if c["status"] == "failed"]


def compare_to_baseline(results: list[dict], baseline: dict) -> dict:
    """Judge a change by what it broke. Failures that existed before it are reported but are not its fault."""
    if not results or not any(r["passed"] + r["failed"] for r in results):
        return {"verdict": "INCONCLUSIVE", "reason": "No test ran", "new_failures": [], "existing_failures": 0}
    new, existing = [], 0
    for result in results:
        before = set(baseline.get(result["runner"], []))
        for case in result["cases"]:
            if case["status"] != "failed":
                continue
            if f"{case['classname']}::{case['name']}" in before:
                existing += 1
            else:
                new.append(case)
    if new:
        environment = all(classify_failure(c["message"]) == "ENVIRONMENT" for c in new)
        return {"verdict": "INCONCLUSIVE" if environment else "FAIL", "reason": "Tests could not run in this environment" if environment else "", "new_failures": new, "existing_failures": existing}
    if existing:
        return {"verdict": "NO NEW FAILURES", "reason": f"{existing} tests were already failing before this change", "new_failures": [], "existing_failures": existing}
    return {"verdict": "PASS", "reason": "", "new_failures": [], "existing_failures": 0}


def choose_runners(analysis: dict) -> list[str]:
    runners = [r for r in analysis.get("test_runners", []) if r in REGISTERED]
    return runners or (["pytest"] if "Python" in analysis.get("languages", {}) else [])


CLASSIFICATION = {"DEFECT": "defect", "SELECTOR_DRIFT": "test problem", "FIXTURE_DRIFT": "test problem", "ENVIRONMENT": "environment"}


ENV_EVIDENCE = re.compile(
    r"modulenotfounderror|importerror|command not found|connection refused|econnrefused|cannot find module|no module named|browser.*not found|timed out waiting for server|not natively supported"
    r"|connecterror|all connection attempts failed|max retries exceeded with url|errno 111|errno 61|winerror 10061|actively refused|name or service not known|nodename nor servname"
    r"|429 too many requests")


ASSERTION_LINE = re.compile(r"(?i)^(assert\b|assertionerror\b)")


def _first_line(message: str) -> str:
    return next((line.strip() for line in message.splitlines() if line.strip()), "")


def _rate_limited(message: str) -> bool:
    """A test that expected another status and got 429 was stopped by the application's rate limiter, which is the environment."""
    first = _first_line(message)
    for pattern in (r"(?i)^assert\s+429\s*==\s*(\d{3})\b", r"(?i)^assertionerror:\s*429\s*!=\s*(\d{3})\b"):
        if (found := re.match(pattern, first)) and found.group(1) != "429":
            return True
    if (found := re.match(r"(?i)^assert\s+(\d{3})\s*==\s*429\b", first)) and found.group(1) != "429":
        return "where 429 =" in message  # the 429 is the response, not the expectation
    listed = re.match(r"(?i)^assert\s+429\s+in\s+[(\[]([^)\]]*)[)\]]", first)
    return bool(listed) and "429" not in listed.group(1)


def classify_failure(message: str) -> str:
    """Port of diagnose-failure.ts, with the failures seen on real repositories. Only drift classes may be healed; DEFECT stays a failing test.

    A failure whose first line is an assertion is never ENVIRONMENT, so words inside an assertion cannot hide a real failure.
    The one exception is a 429 where the test expected another status: the application's own rate limiter answered.
    """
    text = message.lower()
    if _rate_limited(message):
        return "ENVIRONMENT"
    if ASSERTION_LINE.match(_first_line(message)):
        return "SELECTOR_DRIFT" if re.search(r"locator|selector|getby|strict mode violation", text) else "DEFECT"
    if "cannot import name" in text:  # the module exists but the test asks for a wrong name: the test is wrong, not the machine
        return "FIXTURE_DRIFT"
    if ENV_EVIDENCE.search(text):
        return "ENVIRONMENT"
    if re.search(r"locator|selector|getby|element not found|no element|waiting for|strict mode violation", text):
        return "SELECTOR_DRIFT"
    if re.search(r"fixture|keyerror|filenotfounderror|seed|attributeerror: 'nonetype'|typeerror: .*(argument|keyword)", text):
        return "FIXTURE_DRIFT"
    return "DEFECT"


# The rows of skills/healing-tests/references/HEALING_PATTERNS.md, plus the environment signatures seen on real repositories.
HEALING_PATTERNS = {
    "DEFECT": {"pattern": "Real App Bug", "cause": "The test ran and its assertion about the application's behaviour failed.",
               "fix": "Fix the application so it meets the requirement. The test is not changed and stays failing until then. Forbidden: weakening the assertion."},
    "SELECTOR_DRIFT": {"pattern": "Selector Drift", "cause": "The page no longer has the element the test looks for.",
                       "fix": "Update the selector to a stable one such as getByRole or getByTestId. Forbidden: deleting the interaction step."},
    "FIXTURE_DRIFT": {"pattern": "Fixture Outdated", "cause": "The test passes data or arguments the code does not accept, or reads data that is not there.",
                      "fix": "Correct the fixture or the call to match the real signature or schema. Forbidden: removing the request or the assertion."},
    "ENVIRONMENT": {"pattern": "Environment", "cause": "The test could not run properly in this environment.",
                    "fix": "Fix the environment: install the missing package, or provide the service. The application is not at fault."},
}


SPECIFIC = (  # evidence signature to a more exact cause and fix; the first match wins
    (re.compile(r"(?i)429 too many|assert 429|where 429"), "The application's rate limiter answered 429 because the test sent more requests than it allows.", "Reset or disable the limiter in a fixture, or send fewer requests. Expect 429 only when the case says so."),
    (re.compile(r"(?i)no module named '([^']+)'"), "The package '{0}' is not installed in the test environment.", "Install '{0}' as a dependency of the repository, or stop importing it in the test."),
    (re.compile(r"(?i)not natively supported|pytest.mark.asyncio"), "The test is async and pytest-asyncio is not installed.", "Install pytest-asyncio and run with asyncio_mode=auto, or write a synchronous test."),
    (re.compile(r"(?i)connecterror|connection refused|econnrefused|all connection attempts failed|errno 111|errno 61|winerror 10061"), "The test needs a running server and nothing is listening.", "Call the application object through a test client, or start the application before the test."),
    (re.compile(r"(?i)got an unexpected keyword argument '([^']+)'"), "The test passes the keyword '{0}', which the function or class does not accept.", "Call it with the parameter names of the real signature."),
    (re.compile(r"(?i)missing (\d+) required (?:positional|keyword-only) arguments?"), "The test omits arguments the function requires.", "Pass every required argument of the real signature."),
    (re.compile(r"(?i)cannot import name '([^']+)'"), "The test imports the name '{0}', which the module does not have.", "Import a name the module really defines."),
)


def failure_record(case: dict, klass: str, healed: bool = False, note: dict | None = None) -> dict:
    """One failed test as a defect record: what failed, how it is classified, the evidence, and the cause and fix from the healing patterns.

    `note` may carry sharper `cause` and `fix` text from the defect diagnostician. The classification is never taken from it.
    """
    from backend.core.security import redact

    message = case.get("message", "")
    pattern = HEALING_PATTERNS[klass]
    cause, fix = pattern["cause"], pattern["fix"]
    for regex, specific_cause, specific_fix in SPECIFIC:
        if klass != "DEFECT" and (found := regex.search(message)):
            cause, fix = specific_cause.format(*found.groups()), specific_fix.format(*found.groups())
            break
    if note:
        cause, fix = (str(note.get("cause") or cause)[:600], str(note.get("fix") or fix)[:600])
    case_id = next(iter(re.findall(r"TC[-_][\w-]*\d+", f"{case.get('classname', '')} {case.get('name', '')}", re.I)), "")
    raw_name = case.get("name", "")
    classname = case.get("classname", "")
    test_ident = f"{classname}::{raw_name}" if classname else raw_name
    if "tests.agentic_qe." in test_ident:
        test_ident = test_ident.split("tests.agentic_qe.")[-1]
    elif "tests/agentic_qe/" in test_ident:
        test_ident = test_ident.split("tests/agentic_qe/")[-1]
    test_ident = test_ident.lstrip(".:/")
    return {"test": test_ident or raw_name or "test_case", "case_id": case_id.upper().replace("_", "-"), "classification": CLASSIFICATION[klass], "class": klass,
            "evidence": redact(message)[:600], "cause": cause, "fix": fix, "pattern": pattern["pattern"], "healed": healed}


def failure_counts(results: list[dict]) -> dict:
    """Failed tests by class, from the JUnit results. Every failure is counted once and none is hidden."""
    counts = {"defect": 0, "test problem": 0, "environment": 0}
    for suite in results:
        for case in suite.get("cases", []):
            if case["status"] == "failed":
                counts[CLASSIFICATION[classify_failure(case["message"])]] += 1
    return counts

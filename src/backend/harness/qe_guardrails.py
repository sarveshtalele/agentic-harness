import re
import os
from typing import Tuple

class QEGuardrails:
    """
    Agentic QE Guardrails (Hardened against Cloudflare Security Audit findings)
    Enforces test isolation, runner binary allowlisting, path traversal containment,
    and the strict Assertion Preservation Rule.
    """
    ALLOWED_BINARIES = [
        "npx",
        "vitest",
        "playwright",
        "pytest",
        "python",
        "npm",
        "node",
        "mvn",
        "./gradlew",
    ]

    ALLOWED_RUNNER_PREFIXES = [
        "npx --no-install playwright test",
        "npx playwright test",
        "playwright test",
        "npx --no-install vitest run",
        "npx vitest run",
        "vitest run",
        "vitest",
        "npm test",
        "python -m pytest",
        "pytest",
        "node --test",
        "mvn test",
    ]

    @classmethod
    def validate_bash_command(cls, command: str) -> Tuple[bool, str]:
        cmd = command.strip()
        if not cmd:
            return False, "Command cannot be empty."

        # Check for dangerous shell metacharacters and patterns
        dangerous = [
            r"curl\s+", r"wget\s+", r"rm\s+-rf", r">\s*/dev/", r"nc(\s+|$)", r"ssh\s+",
            r";", r"\|", r"&", r"`", r"\$\(", r"socket"  # Block command chaining and substitution metacharacters
        ]
        for pattern in dangerous:
            if re.search(pattern, cmd, re.IGNORECASE):
                return False, f"Security Guardrail: Disallowed shell metacharacter or pattern in '{command}'"

        # Check runner prefix
        is_allowed = any(cmd.startswith(prefix) for prefix in cls.ALLOWED_RUNNER_PREFIXES)
        if not is_allowed:
            return False, f"Runner Guardrail: Command '{command}' is not in the registered test runners whitelist."

        return True, ""

    @classmethod
    def validate_assertion_preservation(cls, original_content: str, proposed_content: str) -> Tuple[bool, str]:
        """
        NEVER weaken, delete, or comment out assertions to make a test pass.
        Zero Trust Assertion Preservation Rule (Cloudflare P0 / NVIDIA Specter).
        """
        assertion_regex = r"(expect\([^)]+\)\.[a-zA-Z0-9_]+|assert\s+[a-zA-Z0-9_]+|assertEquals|assertTrue)"
        orig_matches = [m.strip() for m in re.findall(assertion_regex, original_content)]
        prop_matches = [m.strip() for m in re.findall(assertion_regex, proposed_content)]

        if len(prop_matches) < len(orig_matches):
            return False, (
                f"Assertion Preservation Guardrail: Healing candidate dropped assertions "
                f"({len(orig_matches)} -> {len(prop_matches)}). Weakening assertions is strictly forbidden."
            )

        # Check for trivial assertions or skips
        trivial_regex = r"(expect\(true\)\.toBe\(true\)|assert\s+True|assert\s+1\s*==\s*1|assert\s+2\s*==\s*2|pytest\.skip|test\.skip)"
        if re.search(trivial_regex, proposed_content, re.IGNORECASE) and not re.search(trivial_regex, original_content, re.IGNORECASE):
            return False, "Assertion Preservation Guardrail: Introduced trivial assertion or test skip. Real behavior assertions must be preserved."

        return True, ""

    @classmethod
    def validate_write_path(cls, workspace_dir: str, target_path: str) -> Tuple[bool, str]:
        """
        Hardened Canonical Path Validation: Strictly prevents path traversal attacks (SEC-03).
        """
        canonical_target = os.path.realpath(os.path.abspath(os.path.join(workspace_dir, target_path)))
        canonical_workspace = os.path.realpath(os.path.abspath(workspace_dir))

        # Check that target strictly starts within workspace
        if not canonical_target.startswith(canonical_workspace):
            return False, f"Path Traversal Guardrail: Path '{target_path}' resolves outside the authorized workspace."

        rel = os.path.relpath(canonical_target, canonical_workspace).replace("\\", "/")
        allowed_dirs = [
            "tests/", "__tests__/", "e2e/", "specs/", "docs/qe/", ".sessions/",
            "src/", "lib/", "app/", "features/", "data/projects/"
        ]

        if not any(rel.startswith(d.rstrip("/")) for d in allowed_dirs):
            return False, f"Write Guardrail: File '{rel}' is outside authorized test directories ({', '.join(allowed_dirs)})."

        return True, ""

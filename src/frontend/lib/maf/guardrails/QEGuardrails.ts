/**
 * Agentic QE Guardrails (mapped from agentic-qe/hooks/src/guard-bash.ts & guard-write.ts)
 * Enforces test isolation, command execution whitelisting, and the fundamental
 * Assertion Preservation Rule.
 */
export class QEGuardrails {
  private static ALLOWED_RUNNERS = [
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
    "mvn test",
    "./gradlew test",
    "node --test",
  ];

  /**
   * Validates if a bash test runner command is permitted.
   */
  public static validateBashCommand(command: string): { allowed: boolean; reason?: string } {
    const trimmed = command.trim();

    // Check for dangerous patterns
    const dangerousPatterns = [
      /curl\s+/i,
      /wget\s+/i,
      /rm\s+-rf\s+\//i,
      />\s*\/dev\//i,
      /nc\s+-e/i,
      /ssh\s+/i,
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(trimmed)) {
        return {
          allowed: false,
          reason: `Security Guardrail: Disallowed dangerous command pattern in '${command}'`,
        };
      }
    }

    // Check runner whitelist
    const isAllowedRunner = this.ALLOWED_RUNNERS.some((runner) =>
      trimmed.startsWith(runner)
    );

    if (!isAllowedRunner) {
      return {
        allowed: false,
        reason: `Runner Guardrail: Command '${command}' is not in the registered test runners whitelist (${this.ALLOWED_RUNNERS.slice(0, 4).join(", ")}...)`,
      };
    }

    return { allowed: true };
  }

  /**
   * Fundamental Rule: NEVER weaken, delete, or comment out assertions to make a test pass.
   */
  public static validateAssertionPreservation(
    originalContent: string,
    proposedContent: string
  ): { allowed: boolean; reason?: string } {
    const assertionRegex = /(expect\([^)]+\)\.[a-zA-Z0-9_]+|assert\s+[a-zA-Z0-9_]+|assertEquals|assertTrue)/g;

    const originalMatches = originalContent.match(assertionRegex) || [];
    const proposedMatches = proposedContent.match(assertionRegex) || [];

    // Check if assertions were deleted or reduced
    if (proposedMatches.length < originalMatches.length) {
      return {
        allowed: false,
        reason: `Assertion Preservation Guardrail: Healing candidate dropped assertions (${originalMatches.length} -> ${proposedMatches.length}). Weakening assertions to force tests to pass is strictly forbidden.`,
      };
    }

    // Check for trivial assertions like assert True or expect(true).toBe(true)
    const trivialRegex = /(expect\(true\)\.toBe\(true\)|assert\s+True|assert\s+1\s*==\s*1)/i;
    if (trivialRegex.test(proposedContent) && !trivialRegex.test(originalContent)) {
      return {
        allowed: false,
        reason: "Assertion Preservation Guardrail: Introduced trivial assertion (assert True or expect(true).toBe(true)). Real behavior assertions must be preserved.",
      };
    }

    return { allowed: true };
  }

  /**
   * Enforces directory scoping for test file writes.
   */
  public static validateWritePath(targetPath: string): { allowed: boolean; reason?: string } {
    const normalized = targetPath.replace(/\\/g, "/");

    // Permitted write paths
    const allowedPrefixes = [
      "tests/",
      "__tests__/",
      "e2e/",
      "specs/",
      "docs/qe/",
      "test/",
      ".sessions/",
    ];

    const isAllowed = allowedPrefixes.some((prefix) => normalized.includes(prefix));

    if (!isAllowed) {
      return {
        allowed: false,
        reason: `Write Guardrail: File '${targetPath}' is outside the authorized test and docs directories (${allowedPrefixes.join(", ")}).`,
      };
    }

    return { allowed: true };
  }
}

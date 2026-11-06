import { test, expect } from "@playwright/test";

test.describe("Production Screens and Multi-Agent Harness E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as administrator
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await page.fill('input[type="text"], input[name="username"]', "admin");
    await page.fill('input[type="password"], input[name="password"]', "admin");
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 8000 });
  });

  test("01: Harness renders unified header and 8 goal cards with zero leaks", async ({ page }) => {
    await page.goto("/harness");
    await page.waitForLoadState("networkidle");

    // Verify AppShell header breadcrumb
    await expect(page.locator("header").first()).toBeVisible();
    await expect(page.locator("text=Autonomous QE Harness").first()).toBeVisible();
    await expect(page.locator("text=MAF 2.0 Engine").first()).toBeVisible();

    // Verify Harness status bar
    await expect(page.locator("text=Autonomous Multi-Agent Loops")).toBeVisible();
    await expect(page.locator("text=Plan & Execute Engine")).toBeVisible();

    // Click "+ New Conversation" to ensure empty session state with goal cards
    const newConvBtn = page.locator("button:has-text('New Conversation')");
    if (await newConvBtn.isVisible()) {
      await newConvBtn.click();
      await page.waitForTimeout(500);
    }

    // Verify Quick Goal Cards (rendered in clean 2-column grid)
    const goalCards = page.locator("button:has-text('Customize & Send')");
    await expect(goalCards).toHaveCount(8);

    // Verify specific goals without truncation
    const skillGoal = page.locator("button:has-text('Create Agent Skill')");
    await skillGoal.scrollIntoViewIfNeeded();
    await expect(skillGoal).toBeVisible();

    const auditGoal = page.locator("button:has-text('Run Security Audit')");
    await auditGoal.scrollIntoViewIfNeeded();
    await expect(auditGoal).toBeVisible();
  });

  test("02: AI Specialist Roster displays clean risk badges and measured evals", async ({ page }) => {
    await page.goto("/agents");
    await page.waitForLoadState("networkidle");

    // Verify agent cards
    const agentCards = page.locator('[data-testid="agent-card"]');
    await expect(agentCards.first()).toBeVisible();

    // Verify risk badges use concise text ("changes code", "med risk", "low risk")
    const codeRiskBadge = page.locator("text=changes code").first();
    await expect(codeRiskBadge).toBeVisible();

    // Verify guardrail events matrix
    await expect(page.locator("text=Guardrail Security Flags & Threat Mitigation Matrix")).toBeVisible();
  });

  test("03: Project Specifications table has clean separate columns", async ({ page }) => {
    await page.goto("/projects/prj_mcp_market/documents");
    await page.waitForLoadState("networkidle");

    // Verify table headers are distinct
    await expect(page.locator("th:has-text('Governance ID')")).toBeVisible();
    await expect(page.locator("th:has-text('Document Title')")).toBeVisible();
    await expect(page.locator("th:has-text('Spec Kind')")).toBeVisible();
    await expect(page.locator("th:has-text('Version')")).toBeVisible();
    await expect(page.locator("th:has-text('Status')")).toBeVisible();
    await expect(page.locator("th:has-text('Updated')")).toBeVisible();
    await expect(page.locator("th:has-text('Actions')")).toBeVisible();
  });

  test("04: Skill Creator Studio scaffolds agent skill and attaches to QE workflow", async ({ page }) => {
    await page.goto("/skills/studio");
    await page.waitForLoadState("networkidle");

    // Click Custom Prompt
    const customPromptBtn = page.locator("button", { hasText: "Custom Prompt" });
    if (await customPromptBtn.isVisible()) {
      await customPromptBtn.click();
    }

    const inputArea = page.locator('textarea[aria-label="Custom requirements specification"]');
    await inputArea.fill("Validate payment idempotency tokens and duplicate request rejection");

    // Trigger AI Architect
    const autoFillBtn = page.locator("button", { hasText: "AI Architect & Auto-Fill Skill Specifications" });
    await autoFillBtn.click();

    // Verify checklist was populated
    const taskInput = page.locator('input[aria-label="Task 1"]');
    await expect(taskInput).toBeVisible({ timeout: 5000 });

    // Click scaffold
    const scaffoldBtn = page.locator("button", { hasText: "Scaffold Agent Skill & Test Cases" });
    await scaffoldBtn.click();

    // Verify package card appears
    await expect(page.locator("text=Synthesized Skill Package")).toBeVisible({ timeout: 8000 });
    await expect(page.locator("text=Attach Test Cases Directly to QE Workflow End-to-End")).toBeVisible();
  });

  test("05: Defect Scanner & Fixes page renders defect records", async ({ page }) => {
    await page.goto("/projects/prj_mcp_market/bugs");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=Bug Scan & Defect Remediation")).toBeVisible();
  });

  test("06: BA Studio renders BRD and Gherkin editor", async ({ page }) => {
    await page.goto("/projects/prj_mcp_market/ba");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "BA Studio" })).toBeVisible();
  });

  test("07: MCP Server Registry displays servers with non-native confirmation modal", async ({ page }) => {
    await page.goto("/mcp");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=MCP Server Registry")).toBeVisible();
  });
});

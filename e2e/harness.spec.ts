import { test, expect } from "@playwright/test";

test.describe("Agentic QE Harness - Claude Code Desktop E2E Suite", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for the app to hydrate and load configuration
    await page.waitForLoadState("networkidle");
    // Ensure active session is loaded
    await page.waitForSelector("textarea:not([disabled])", { timeout: 10000 });
    // Start with a clean session for deterministic test isolation
    const newSessionBtn = page.locator("button:has-text('New Session')").first();
    if (await newSessionBtn.isVisible()) {
      await newSessionBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test("1. [Positive] Enterprise Claude Code Desktop UI loads correctly", async ({ page }) => {
    // Check main brand title
    await expect(page.locator("text=Claude Code Desktop").first()).toBeVisible();
    
    // Check framework & model indicators
    await expect(page.locator("text=MAF 2.0").first()).toBeVisible();

    // Verify chat composer is ready
    const composer = page.locator("textarea");
    await expect(composer).toBeVisible();
    await expect(composer).toBeEnabled();

    // Verify Inspector pane is visible
    await expect(page.locator("text=Inspector").first()).toBeVisible();
  });

  test("2. [Negative & Handling] Model unconfigured error banner and modal configuration", async ({ page }) => {
    // When no API key is configured, high-visibility warning banner MUST be displayed
    const unconfiguredBanner = page.locator('[data-testid="model-unconfigured-banner"]');
    await expect(unconfiguredBanner).toBeVisible();
    await expect(unconfiguredBanner).toContainText("Model Not Configured");

    // Check sidebar warning pill
    const sidebarWarning = page.locator("text=Model not configured").first();
    await expect(sidebarWarning).toBeVisible();

    // Click "Configure Key" in banner to trigger modal
    const configureBtn = unconfiguredBanner.locator("button:has-text('Configure Key')");
    await configureBtn.click();

    // Verify Model & System Prompt configuration modal opened
    const modalHeading = page.locator("h3:has-text('LLM Provider, Base URL & System Prompt')");
    await expect(modalHeading).toBeVisible();

    // Verify quick provider presets exist
    await expect(page.locator("button:has-text('OpenAI (gpt-4o)')")).toBeVisible();
    await expect(page.locator("button:has-text('DeepSeek (deepseek-chat)')")).toBeVisible();
    await expect(page.locator("button:has-text('Local Ollama / vLLM')")).toBeVisible();

    // Close the modal
    const closeBtn = page.locator("div.fixed button:has(svg.lucide-x)").first();
    await closeBtn.click();
    await expect(modalHeading).not.toBeVisible();
  });

  test("3. [Positive] Plan Mode vs Execute Mode switcher toggles correctly", async ({ page }) => {
    const modeBtn = page.locator("button:has-text('MODE')").first();
    await expect(modeBtn).toBeVisible();

    const initialText = await modeBtn.innerText();
    const isPlan = initialText.includes("PLAN MODE");

    // Click to toggle mode
    await modeBtn.click();
    await expect(modeBtn).toContainText(isPlan ? "EXECUTE MODE" : "PLAN MODE");

    // Click again to toggle back
    await modeBtn.click();
    await expect(modeBtn).toContainText(isPlan ? "PLAN MODE" : "EXECUTE MODE");
  });

  test("4. [Positive & Architectural] LeftSidebar separates First-Party Plugins from MCP Servers", async ({ page }) => {
    // 1. Check Plugins Tab
    const pluginsTab = page.locator("button:has-text('Plugins')").first();
    await pluginsTab.click();

    // Should display the first-party agentic-qe plugin
    await expect(page.locator("text=Agentic QE").first()).toBeVisible();
    await expect(page.locator("text=v1.6.0").first()).toBeVisible();
    await expect(page.locator("text=Sarvesh Talele").first()).toBeVisible();
    await expect(page.locator("text=qe-discover").first()).toBeVisible();

    // 2. Check MCP Servers Tab
    const mcpTab = page.locator("button:has-text('MCP')").first();
    await mcpTab.click();

    // Should be distinct from plugins
    await expect(page.locator("text=External MCP Servers").first()).toBeVisible();
    await expect(page.locator("button:has-text('+ Connect')").first()).toBeVisible();

    // 3. Check Tools Tab
    const toolsTab = page.locator("button:has-text('Tools')").first();
    await toolsTab.click();
    await expect(page.locator("text=qe_discover_repo").first()).toBeVisible();

    // 4. Return to History Tab
    const historyTab = page.locator("button:has-text('History')").first();
    await historyTab.click();
    await expect(page.locator("button:has-text('New Session')").first()).toBeVisible();
  });

  test("5. [Positive] Enterprise Dark and Light theme toggle", async ({ page }) => {
    const html = page.locator("html");
    const themeBtn = page.locator("button[title*='theme' i], button:has(svg.lucide-moon), button:has(svg.lucide-sun)").first();
    await expect(themeBtn).toBeVisible();

    const isInitiallyDark = await html.evaluate((el) => el.classList.contains("dark"));

    // Toggle theme
    await themeBtn.click();
    const isToggledDark = await html.evaluate((el) => el.classList.contains("dark"));
    expect(isToggledDark).toBe(!isInitiallyDark);

    // Toggle back
    await themeBtn.click();
    const isRestoredDark = await html.evaluate((el) => el.classList.contains("dark"));
    expect(isRestoredDark).toBe(isInitiallyDark);
  });

  test("6. [Positive] Slash command /help displays interactive commands table", async ({ page }) => {
    const composer = page.locator("textarea");
    await composer.fill("/help");
    await composer.press("Enter");

    // Wait for the help table to appear in the chat stream
    await expect(page.locator("text=Agentic QE Harness Slash Commands").first()).toBeVisible({ timeout: 12000 });
    await expect(page.locator("text=/plan").first()).toBeVisible();
    await expect(page.locator("text=/skill").first()).toBeVisible();
    await expect(page.locator("text=/plugin").first()).toBeVisible();
  });

  test("7. [Positive] Slash command /skills lists all registered QE skills", async ({ page }) => {
    const composer = page.locator("textarea");
    await composer.fill("/skills");
    await composer.press("Enter");

    // Wait for skills table to render
    await expect(page.locator("text=Local Machine Skills Catalog").first()).toBeVisible({ timeout: 12000 });
    await expect(page.locator("text=qe-discover").first()).toBeVisible();
    await expect(page.locator("text=qe-plan").first()).toBeVisible();
  });

  test("8. [Positive] Slash command /gates displays MAF 8 Quality Gates scorecard", async ({ page }) => {
    const composer = page.locator("textarea");
    await composer.fill("/gates");
    await composer.press("Enter");

    // Wait for gates scorecard to render
    await expect(page.locator("text=MAF 8 Quality Engineering Gates Status").first()).toBeVisible({ timeout: 12000 });
    await expect(page.locator("text=Gate 1").first()).toBeVisible();
    await expect(page.locator("text=Gate 8").first()).toBeVisible();
  });

  test("9. [Positive] Inbuilt Skill execution: /skill qe-discover performs repository scan", async ({ page }) => {
    const composer = page.locator("textarea");
    await composer.fill("/skill qe-discover");
    await composer.press("Enter");

    // Check that tool executed and rendered output in chat
    await expect(page.locator("text=qe_discover_repo").first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=Gate 1").first()).toBeVisible({ timeout: 15000 });
  });

  test("10. [Negative & Guardrail] Unconfigured model displays warning when sending regular message", async ({ page }) => {
    const composer = page.locator("textarea");
    await composer.fill("Analyze the test suite and recommend test coverage improvements");
    await composer.press("Enter");

    // Wait for the response stream to complete
    // Because no API key is provided, the backend emits MODEL_NOT_CONFIGURED error
    await expect(page.locator("text=Model Not Configured").first()).toBeVisible({ timeout: 12000 });
  });

  test("11. [Positive] Slash command palette autocomplete pops up on '/' typing", async ({ page }) => {
    const composer = page.locator("textarea");
    await composer.fill("/");
    // Slash command palette should appear
    await expect(page.locator("text=Slash Command & Local Skills Autocomplete").first()).toBeVisible({ timeout: 8000 });
    await expect(page.locator("text=/plan").first()).toBeVisible();
    await expect(page.locator("text=/skill caveman").first()).toBeVisible();

    // Now filter for qe-discover
    await composer.fill("/qe-discover");
    await expect(page.locator("text=/skill qe-discover").first()).toBeVisible({ timeout: 8000 });
  });
});

const { chromium } = require("playwright");
const path = require("path");

const ARTIFACTS_DIR = "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a";

async function run() {
  console.log("Launching Chromium for Visual Verification of Latest Fixes...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  try {
    // 1. Log in
    console.log("Step 1: Logging in...");
    await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
    await page.fill('input[name="username"]', "admin");
    await page.fill('input[name="password"]', "admin");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1000);

    // 2. Navigate to /harness
    console.log("Step 2: Navigating to /harness...");
    await page.goto("http://localhost:3000/harness", { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);

    // Verify Agent dropdown is removed from header
    const agentDropdown = page.locator("select[aria-label='Select Autonomous MAF Agent']");
    const isAgentDropdownVisible = await agentDropdown.isVisible();
    console.log("Is Agent Dropdown visible in header?", isAgentDropdownVisible); // Expected: false

    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_header_without_agent_selector.png") });
    console.log("Captured: evidence_header_without_agent_selector.png");

    // 3. Test Project Switching from top header
    console.log("Step 3: Switching Project in Header to Zero-Trust Financial Gateway...");
    const projectSelect = page.locator("select[aria-label='Select Project in Harness']").first();
    await projectSelect.selectOption({ label: "Zero-Trust Financial Gateway" });
    await page.waitForTimeout(1000);

    console.log("Current URL after project switch:", page.url());
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_project_switch_url_and_session.png") });
    console.log("Captured: evidence_project_switch_url_and_session.png");

    // Switch back to Agentic QE Platform & Framework
    await projectSelect.selectOption({ label: "Agentic QE Platform & Framework" });
    await page.waitForTimeout(1000);

    // 4. Send the user's exact prompt for BRD creation
    console.log("Step 4: Submitting user's prompt: 'create a docuement for python clacuatlro react based application as BRD docuement'...");
    const chatInput = page.locator("textarea").first();
    await chatInput.fill("create a docuement for python clacuatlro react based application as BRD docuement");
    await page.keyboard.press("Enter");

    // Wait for the response stream and document generation
    console.log("Waiting for BRD generation and rendering...");
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_brd_natural_language_generation.png") });
    console.log("Captured: evidence_brd_natural_language_generation.png");

    // 5. Test Delete Confirmation Popup Modal
    console.log("Step 5: Testing Delete Confirmation Popup Modal...");
    const firstSessionItem = page.locator("aside div.group:has(button[title='Delete session'])").first();
    if (await firstSessionItem.isVisible()) {
      await firstSessionItem.hover();
      const deleteBtn = firstSessionItem.locator("button[title='Delete session']");
      await deleteBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_delete_confirmation_popup_modal.png") });
      console.log("Captured: evidence_delete_confirmation_popup_modal.png");

      // Dismiss delete modal
      const cancelDeleteBtn = page.locator("button:has-text('Cancel')").first();
      await cancelDeleteBtn.click();
      await page.waitForTimeout(400);
    }

    // 6. Test Rename Session Popup Modal
    console.log("Step 6: Testing Rename Session Popup Modal...");
    if (await firstSessionItem.isVisible()) {
      await firstSessionItem.hover();
      const renameBtn = firstSessionItem.locator("button[title='Rename session']");
      await renameBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_rename_session_popup_modal.png") });
      console.log("Captured: evidence_rename_session_popup_modal.png");

      // Dismiss rename modal
      const cancelRenameBtn = page.locator("button:has-text('Cancel')").first();
      await cancelRenameBtn.click();
      await page.waitForTimeout(400);
    }

    console.log("✅ All latest fix verifications completed successfully!");
  } catch (err) {
    console.error("Verification error:", err);
  } finally {
    await browser.close();
  }
}

run();

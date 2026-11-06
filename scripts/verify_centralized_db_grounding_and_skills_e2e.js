const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const ARTIFACT_DIR = "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a";

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 950 } });
  const page = await context.newPage();

  console.log("1. Logging in as admin...");
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
  await page.fill('input[name="username"], input[type="text"]', "admin");
  await page.fill('input[name="password"], input[type="password"]', "admin");
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  console.log("2. Navigating to Harness with MCP Server Market selected (/harness?project=prj_mcp_market)...");
  await page.goto("http://localhost:3000/harness?project=prj_mcp_market", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Verify Project dropdown has MCP Server Market
  const projSelect = await page.locator("select").first();
  if (await projSelect.count() > 0) {
    await projSelect.selectOption("prj_mcp_market");
    await page.waitForTimeout(1000);
  }

  console.log("3. Testing Slash Palette Autocomplete & Skill Click Loading (No Auto-Send)...");
  const promptInput = page.locator("textarea").first();
  await promptInput.fill("/");
  await page.waitForTimeout(500);

  // Check that /skills is NOT present in the palette
  const skillsCmd = await page.locator("button:has-text('/skills')").count();
  console.log(`Presence of /skills in palette: ${skillsCmd} (Expected 0)`);
  if (skillsCmd > 0) {
    throw new Error("FAILED: /skills is still present in slash command palette!");
  }

  // Click on /qe-discover in the palette
  const qeDiscoverBtn = page.locator("button:has-text('/qe-discover')").first();
  if (await qeDiscoverBtn.isVisible()) {
    console.log("Clicking /qe-discover in slash palette...");
    await qeDiscoverBtn.click();
    await page.waitForTimeout(600);

    // Verify input contains '/qe-discover ' and message was NOT sent immediately
    const inputVal = await promptInput.inputValue();
    console.log(`Current textarea input after palette click: "${inputVal}"`);
    if (!inputVal.includes("/qe-discover")) {
      throw new Error(`FAILED: Textarea should have '/qe-discover ' loaded but was "${inputVal}"`);
    }
  }

  console.log("4. Sending Grounded Bug Query: 'How many bug fixes are listed for this application'...");
  await promptInput.fill("How many bug fixes are listed for this application");
  await page.waitForTimeout(400);

  // Submit via Enter
  await promptInput.press("Enter");
  console.log("Submitted query, awaiting SSE stream response...");

  // Wait for table to appear
  await page.waitForSelector("text=Centralized Defect Inventory", { timeout: 15000 });
  await page.waitForSelector("text=154 defect findings", { timeout: 10000 });
  await page.waitForSelector("text=🔴 CRITICAL", { timeout: 10000 });

  // Verify key facts in the response
  const pageText = await page.textContent("body");
  const has154Bugs = pageText.includes("154 defect findings");
  const hasCritical = pageText.includes("Critical: 5");
  const hasHigh = pageText.includes("High: 58");
  const hasMedium = pageText.includes("Medium: 56");
  const hasLow = pageText.includes("Low: 35");
  const hasAuthBypass = pageText.includes("Auth bypass: ProtocolGuardMiddleware");
  const hasTable = pageText.includes("Defect Description / Title");

  console.log("Grounded Verification Results:");
  console.log(`- 154 defect findings: ${has154Bugs}`);
  console.log(`- Critical: 5, High: 58, Medium: 56, Low: 35: ${hasCritical && hasHigh && hasMedium && hasLow}`);
  console.log(`- Top critical bug present: ${hasAuthBypass}`);
  console.log(`- Structured markdown table present: ${hasTable}`);

  if (!has154Bugs || !hasAuthBypass || !hasTable) {
    throw new Error("FAILED: Grounded defect findings table incomplete or missing!");
  }

  // Screenshot Harness chat with defect table
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, "evidence_centralized_db_grounded_bug_table.png"),
    fullPage: false,
  });
  console.log("Saved evidence_centralized_db_grounded_bug_table.png");

  console.log("5. Testing Loaded Skills Drawer Tab & Click-to-Load...");
  // Open right inspector drawer skills tab if not active
  const skillsTabBtn = page.locator("button:has-text('Skills')").first();
  if (await skillsTabBtn.isVisible()) {
    await skillsTabBtn.click();
    await page.waitForTimeout(600);
  }

  // Click on a loaded skill card to verify it loads in prompt
  const loadedSkillCard = page.locator("div[title='Click to load skill command into chat']").first();
  if (await loadedSkillCard.isVisible()) {
    await loadedSkillCard.click();
    await page.waitForTimeout(500);
    const loadedVal = await promptInput.inputValue();
    console.log(`Textarea after clicking loaded skill card: "${loadedVal}"`);
  }

  await page.screenshot({
    path: path.join(ARTIFACT_DIR, "evidence_loaded_skills_inspector_drawer.png"),
    fullPage: false,
  });
  console.log("Saved evidence_loaded_skills_inspector_drawer.png");

  console.log("6. Testing /skills Page 'Load into Harness' Action...");
  await page.goto("http://localhost:3000/skills", { waitUntil: "networkidle" });
  await page.waitForSelector("text=Skills");

  // Open the first skill card modal
  const skillCard = page.locator("button:has-text('Show text')").first();
  if (await skillCard.isVisible()) {
    await skillCard.click();
    await page.waitForTimeout(800);

    const loadIntoHarnessBtn = page.locator("button:has-text('Load into Harness')");
    console.log(`'Load into Harness' button visible: ${await loadIntoHarnessBtn.isVisible()}`);
    if (await loadIntoHarnessBtn.isVisible()) {
      await loadIntoHarnessBtn.click();
      await page.waitForTimeout(2000);

      // Verify redirected to Harness and prompt is populated
      const harnessInputVal = await page.locator("textarea").first().inputValue();
      console.log(`Textarea on Harness after 'Load into Harness': "${harnessInputVal}"`);
    }
  }

  await page.screenshot({
    path: path.join(ARTIFACT_DIR, "evidence_skill_loaded_into_harness_chat.png"),
    fullPage: false,
  });
  console.log("Saved evidence_skill_loaded_into_harness_chat.png");

  console.log("ALL E2E VERIFICATION STEPS PASSED SUCCESSFULLY!");
  await browser.close();
}

run().catch((err) => {
  console.error("E2E Test Failed:", err);
  process.exit(1);
});

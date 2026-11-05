const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const ARTIFACTS_DIR = "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a";

async function run() {
  console.log("Launching Chromium for E2E Visual Verification...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  try {
    // 1. Log in
    console.log("Step 1: Navigating to /login...");
    await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
    await page.fill('input[name="username"]', "admin");
    await page.fill('input[name="password"]', "admin");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1000);

    // 2. Navigate to /harness
    console.log("Step 2: Navigating to /harness...");
    await page.goto("http://localhost:3000/harness", { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);

    // Screenshot: Base Harness with Clean Top Header & Co-Located Chat Input
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_harness_co_located_chat_input.png") });
    console.log("Captured: evidence_harness_co_located_chat_input.png");

    // 3. Open Model Dropdown in Bottom Toolbar
    console.log("Step 3: Opening Model Dropdown Menu in Chat Input...");
    const modelBtn = page.locator("button:has-text('GPT-4o')").or(page.locator("button:has-text('Select Model')")).or(page.locator("button:has(svg.lucide-sparkles)")).first();
    await modelBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_chat_model_dropdown.png") });
    console.log("Captured: evidence_chat_model_dropdown.png");

    // Click to select Claude 3.5 Sonnet
    const claudeOption = page.locator("button:has-text('Claude 3.5 Sonnet')").first();
    if (await claudeOption.isVisible()) {
      await claudeOption.click();
      await page.waitForTimeout(500);
    }

    // 4. Open Mode Dropdown in Bottom Toolbar
    console.log("Step 4: Opening Mode Dropdown Menu in Chat Input...");
    const modeBtn = page.locator("button:has-text('Plan Mode')").or(page.locator("button:has-text('Execute Mode')")).first();
    await modeBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_chat_mode_dropdown.png") });
    console.log("Captured: evidence_chat_mode_dropdown.png");

    // Close mode dropdown
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);

    // 5. Inspect Evals Tab (RAGAS, Faithfulness, Groundedness, Recall@K)
    console.log("Step 5: Opening Inspector Evals Tab...");
    const evalsTab = page.locator("button:has-text('Evals')").first();
    await evalsTab.click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_agent_evals_cards.png") });
    console.log("Captured: evidence_agent_evals_cards.png");

    // 6. Inspect Skills Tab (NVIDIA Skill Specter cards)
    console.log("Step 6: Opening Inspector Skills Tab...");
    const skillsTab = page.locator("button:has-text('Skills')").first();
    await skillsTab.click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_skills_specter_cards.png") });
    console.log("Captured: evidence_skills_specter_cards.png");

    // 7. Click a Skill Card to open NVIDIA Skill Specter Preview Modal
    console.log("Step 7: Opening Skill Preview Modal...");
    const firstSkillCard = page.locator("div.cursor-pointer:has-text('SPECTER')").or(page.locator("div.cursor-pointer:has-text('Preview & Inspect')")).first();
    if (await firstSkillCard.isVisible()) {
      await firstSkillCard.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_skill_preview_modal.png") });
      console.log("Captured: evidence_skill_preview_modal.png");

      // Close modal
      const closeBtn = page.locator("button:has-text('Close')").first();
      await closeBtn.click();
      await page.waitForTimeout(400);
    }

    // 8. Generate Documentation in Chat
    console.log("Step 8: Sending /doc command to generate documentation...");
    const chatInput = page.locator("textarea").first();
    await chatInput.fill("/doc QE Test Strategy & Architecture");
    await page.keyboard.press("Enter");
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_doc_generation_and_download.png") });
    console.log("Captured: evidence_doc_generation_and_download.png");

    // 9. Inspect Project Header QE Harness Button
    console.log("Step 9: Navigating to /projects/prj_agentic_qe to verify top QE Harness button...");
    await page.goto("http://localhost:3000/projects/prj_agentic_qe", { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, "evidence_project_header_harness_button.png") });
    console.log("Captured: evidence_project_header_harness_button.png");

    console.log("✅ All visual evidence screenshots captured successfully!");
  } catch (err) {
    console.error("Verification error:", err);
  } finally {
    await browser.close();
  }
}

run();

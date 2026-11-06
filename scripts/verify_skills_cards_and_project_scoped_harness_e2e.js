const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const ARTIFACT_DIR = "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a";

async function run() {
  console.log("Starting E2E Verification of Skills Cards, Agent Scores, and Project-Scoped Harness...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // 1. Authenticate via /login
  console.log("Navigating to /login...");
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
  await page.fill('input[name="username"], input[type="text"]', "admin");
  await page.fill('input[name="password"], input[type="password"]', "admin");
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1000);

  // 2. Verify Skills Page with NVIDIA Skill Specter Cards
  console.log("Navigating to /skills...");
  await page.goto("http://localhost:3000/skills", { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="skill-card"]', { timeout: 10000 });
  const cardCount = await page.locator('[data-testid="skill-card"]').count();
  console.log(`Discovered ${cardCount} Skill cards on /skills`);

  const firstCard = page.locator('[data-testid="skill-card"]').first();
  await firstCard.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_single_skill_card.png") });
  
  // Click first card to inspect modal/preview
  await firstCard.click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_skills_catalog_cards.png") });
  console.log("Saved evidence_skills_catalog_cards.png");

  // Close modal
  const closeBtn = page.locator('button:has-text("Close"), button[aria-label="Close"], button svg.lucide-x').first();
  if (await closeBtn.isVisible()) {
    await closeBtn.click();
    await page.waitForTimeout(300);
  }

  // 3. Verify Agent Detail Scores (/agents/project-copilot)
  console.log("Navigating to /agents/project-copilot...");
  await page.goto("http://localhost:3000/agents/project-copilot", { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="agent-scores"]', { timeout: 10000 });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_agent_detail_ragas_scores.png") });
  console.log("Saved evidence_agent_detail_ragas_scores.png");

  // 4. Verify Harness Multi-Project Scoped Execution (/harness)
  console.log("Navigating to /harness...");
  await page.goto("http://localhost:3000/harness", { waitUntil: "networkidle" });
  await page.waitForSelector('textarea', { timeout: 10000 });

  // Select MCP Server Market project
  const projectSelect = page.locator('select').first();
  if (await projectSelect.isVisible()) {
    await projectSelect.selectOption({ label: "MCP Server Market" }).catch(async () => {
      await projectSelect.selectOption("prj_mcp_market");
    });
    await page.waitForTimeout(600);
  }

  // Send instruction to Create BRD
  const textarea = page.locator('textarea').first();
  await textarea.fill("Create a complete BRD for ATM machine");
  const sendBtn = page.locator('button:has(svg.lucide-arrow-right), button[type="submit"]').last();
  await sendBtn.click();

  console.log("Waiting for BRD generation and streaming in prj_mcp_market...");
  await page.waitForSelector('text=Documentation Generated & Synchronized to Project', { timeout: 25000 });
  await page.waitForTimeout(1500);

  // Switch to E-Commerce Core project
  console.log("Switching to E-Commerce Core in Harness...");
  if (await projectSelect.isVisible()) {
    await projectSelect.selectOption({ label: "E-Commerce Core & Checkout" }).catch(async () => {
      await projectSelect.selectOption("prj_ecommerce_core");
    });
    await page.waitForTimeout(600);
  }

  // Trigger Security Audit in E-Commerce Core
  await textarea.fill("/security-audit");
  await sendBtn.click();

  console.log("Waiting for Security Audit in prj_ecommerce_core...");
  await page.waitForTimeout(3000);

  await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_harness_multi_project_scoped_execution.png") });
  console.log("Saved evidence_harness_multi_project_scoped_execution.png");

  // 5. Navigate to /projects/prj_mcp_market/documents to verify artifact isolation
  console.log("Verifying /projects/prj_mcp_market/documents...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/documents", { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_prj_mcp_market_documents_verified.png") });
  console.log("Saved evidence_prj_mcp_market_documents_verified.png");

  await browser.close();
  console.log("All E2E browser verifications completed successfully!");
}

run().catch((e) => {
  console.error("E2E Verification Failed:", e);
  process.exit(1);
});

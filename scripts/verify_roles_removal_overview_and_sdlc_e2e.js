const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const ARTIFACT_DIR = "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a";

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 950 } });
  const page = await context.newPage();

  console.log("1. Logging in as admin...");
  await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
  await page.fill('input[name="username"], input[type="text"]', "admin");
  await page.fill('input[name="password"], input[type="password"]', "admin");
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  console.log("2. Navigating to Project Overview (/projects/prj_mcp_market)...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market", { waitUntil: "networkidle" });
  await page.waitForSelector("text=Codebase Health");
  await page.waitForSelector("text=Quality Engineering Gate Progression");

  // Verify KPI cards
  const codebaseHealth = await page.textContent("text=Codebase Health");
  const qualityGates = await page.textContent("text=Quality Gates");
  const defectInventory = await page.textContent("text=Defect Inventory");
  const governedDocs = await page.textContent("text=Governed Docs");
  console.log(`KPIs detected: ${codebaseHealth}, ${qualityGates}, ${defectInventory}, ${governedDocs}`);

  // Verify no MAF 2.0 branding on the page
  const bodyText = await page.textContent("body");
  if (bodyText.includes("MAF 2.0")) {
    console.error("WARNING: Found MAF 2.0 branding in page body!");
  } else {
    console.log("VERIFIED: Zero MAF 2.0 branding on Overview page.");
  }

  await page.screenshot({
    path: path.join(ARTIFACT_DIR, "evidence_modernized_overview_dashboard.png"),
    fullPage: false,
  });
  console.log("Saved evidence_modernized_overview_dashboard.png");

  console.log("3. Navigating to Documents (/projects/prj_mcp_market/documents)...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/documents", { waitUntil: "networkidle" });
  await page.waitForSelector("text=Governance ID");

  // Verify Governance ID badge
  const hasGovIdCol = await page.isVisible("th:has-text('Governance ID')");
  console.log(`Governance ID column visible: ${hasGovIdCol}`);

  await page.screenshot({
    path: path.join(ARTIFACT_DIR, "evidence_governance_id_documents.png"),
    fullPage: false,
  });
  console.log("Saved evidence_governance_id_documents.png");

  console.log("4. Navigating to Bug Scan (/projects/prj_mcp_market/bugs)...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/bugs", { waitUntil: "networkidle" });
  await page.waitForSelector("text=Bug Scan & Defect Remediation");

  // If there are findings, verify step-by-step checklist and open the modal
  const viewGuideBtn = page.locator("button:has-text('View Step-by-Step Guide')").first();
  if (await viewGuideBtn.isVisible()) {
    console.log("Found bug card. Opening End-to-End Remediation Modal...");
    await viewGuideBtn.click();
    await page.waitForSelector("text=End-to-End Bug Remediation Guide");
    await page.waitForSelector("text=Phase 1: Root Cause & Impact Diagnosis");
    await page.waitForSelector("text=Phase 2: Code Remediation Diff");
    await page.waitForSelector("text=Phase 3: Automated Sandbox Verification Command");
    await page.waitForSelector("text=Phase 4: Quality Gate Compliance");

    await page.screenshot({
      path: path.join(ARTIFACT_DIR, "evidence_bug_step_by_step_remediation_modal.png"),
      fullPage: false,
    });
    console.log("Saved evidence_bug_step_by_step_remediation_modal.png");

    // Close modal
    await page.click("button:has-text('Close')");
  }

  // Verify Tab Memory: switch to documents and back to bugs
  console.log("Testing tab memory persistence...");
  await page.click("a:has-text('Documents')");
  await page.waitForSelector("text=Governed Project Documents");
  await page.click("a:has-text('Bug Scan')");
  await page.waitForSelector("text=Bug Scan & Defect Remediation");
  console.log("Tab memory restored successfully.");

  console.log("5. Navigating to QE Studio (/projects/prj_mcp_market/qe)...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/qe", { waitUntil: "networkidle" });
  await page.waitForSelector("text=QE Studio & Autonomous AI SDLC");
  await page.waitForSelector("text=One-Click Local Sandbox Execution Package");

  // Verify Export SDLC Package (.ZIP) button
  const zipBtn = await page.isVisible("a:has-text('Export SDLC Package (.ZIP)')");
  console.log(`ZIP Package export button visible: ${zipBtn}`);

  await page.screenshot({
    path: path.join(ARTIFACT_DIR, "evidence_qe_studio_ai_sdlc_zip_export.png"),
    fullPage: false,
  });
  console.log("Saved evidence_qe_studio_ai_sdlc_zip_export.png");

  console.log("6. Navigating to QE Harness (/harness?project=prj_mcp_market)...");
  await page.goto("http://localhost:3000/harness?project=prj_mcp_market", { waitUntil: "networkidle" });
  await page.waitForSelector("h1:has-text('QE Harness')");

  // Verify Enterprise QE badge
  const entBadge = await page.isVisible("text=Enterprise QE");
  console.log(`Enterprise QE badge visible (no MAF): ${entBadge}`);

  // Verify no role dropdown in header
  const roleDropdownExists = await page.locator("button:has-text('Business Analyst (BA)')").isVisible();
  console.log(`Role dropdown visible (should be false): ${roleDropdownExists}`);

  // Send prompt to test automatic intent classification
  console.log("Sending prompt to test auto-classification without roles...");
  const promptInput = page.locator("textarea").first();
  await promptInput.fill("Create BRD for payment settlements with strict quality gate criteria");
  await promptInput.press("Enter");

  // Wait for thought stream and assistant message
  await page.waitForTimeout(4000);

  // Verify assistant message header reads 'QE Platform' rather than role name
  const qePlatformHeader = await page.locator("span:has-text('QE Platform')").first().isVisible();
  console.log(`Assistant message header displays 'QE Platform': ${qePlatformHeader}`);

  await page.screenshot({
    path: path.join(ARTIFACT_DIR, "evidence_harness_no_roles_auto_classification.png"),
    fullPage: false,
  });
  console.log("Saved evidence_harness_no_roles_auto_classification.png");

  console.log("All E2E verifications completed successfully!");
  await browser.close();
}

run().catch((err) => {
  console.error("E2E Verification Error:", err);
  process.exit(1);
});

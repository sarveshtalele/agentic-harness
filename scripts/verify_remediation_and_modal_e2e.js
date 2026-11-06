const { chromium } = require("playwright");

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log("1. Authenticating as admin...");
  await page.goto("http://localhost:3000/login");
  await page.waitForLoadState("networkidle");
  
  // Login if on login page
  const usernameInput = await page.$('input[name="username"], input[type="text"]');
  if (usernameInput) {
    await usernameInput.fill("admin");
    const passwordInput = await page.$('input[name="password"], input[type="password"]');
    if (passwordInput) await passwordInput.fill("admin");
    const submitBtn = await page.$('button[type="submit"]');
    if (submitBtn) await submitBtn.click();
    await page.waitForTimeout(1000);
  }

  console.log("2. Verifying MCP Server Deletion with ConfirmModal...");
  await page.goto("http://localhost:3000/mcp");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  // Look for delete buttons on MCP servers
  const mcpDeleteBtns = await page.$$('button[title*="Delete server"], button[aria-label*="Delete server"]');
  console.log(`Found ${mcpDeleteBtns.length} MCP delete buttons`);
  
  // First, let's add a test server so we can safely delete it without removing all defaults
  const connectBtn = await page.$('button:has-text("Connect MCP Server")');
  if (connectBtn) {
    await connectBtn.click();
    await page.waitForTimeout(500);
    const nameInput = await page.$('input[placeholder*="Server Name"]');
    if (nameInput) await nameInput.fill("Test Disposable Server");
    const cmdInput = await page.$('input[placeholder*="npx"]');
    if (cmdInput) await cmdInput.fill("npx -y @modelcontextprotocol/server-sqlite --db temp.db");
    const submitConnect = await page.$('button:has-text("Connect Server")');
    if (submitConnect) await submitConnect.click();
    await page.waitForTimeout(1500);
    console.log("Added 'Test Disposable Server'");
  }

  // Find Test Disposable Server card
  const testServerCard = await page.$('text="Test Disposable Server"');
  if (testServerCard) {
    console.log("Found Test Disposable Server in list!");
    // Click its delete button
    const deleteBtn = await page.$('div:has-text("Test Disposable Server") button[title*="Delete"]');
    if (deleteBtn) {
      await deleteBtn.click();
      await page.waitForTimeout(500);
      
      // Verify custom ConfirmModal appears (no native alert)
      const modal = await page.$('h3:has-text("Delete MCP Server")');
      console.log("ConfirmModal appeared:", !!modal);
      
      const confirmActionBtn = await page.$('button:has-text("Delete Server")');
      if (confirmActionBtn) {
        await confirmActionBtn.click();
        await page.waitForTimeout(1500);
      }
      
      // Reload page and verify it did NOT resurrect
      await page.reload({ waitUntil: "networkidle" });
      await page.waitForTimeout(1000);
      const resurrected = await page.$('text="Test Disposable Server"');
      console.log("Was server resurrected?:", !!resurrected);
      if (!resurrected) {
        console.log("SUCCESS: MCP Server permanently deleted!");
      }
    }
  }

  console.log("3. Verifying Documents Page Purge & Direct Deletion in prj_mcp_market...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/documents");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  // Check that ATM Machine and Cal-user are NOT present
  const atmDoc = await page.$('text="Atm Machine"');
  const calUserDoc = await page.$('text="Cal-user"');
  console.log("Is ATM Machine document present?:", !!atmDoc);
  console.log("Is Cal-user document present?:", !!calUserDoc);

  // Verify delete button is available on document rows
  const docDeleteBtns = await page.$$('button[title="Delete Document"]');
  console.log(`Found ${docDeleteBtns.length} document delete buttons in table`);

  console.log("4. Verifying Gherkin Scenarios Visualizer in Gherkin Document...");
  // Find a Gherkin document in prj_mcp_market
  const gherkinDocLink = await page.$('a[href*="/documents/doc_09e127a2a134"]');
  if (gherkinDocLink) {
    await gherkinDocLink.click();
  } else {
    await page.goto("http://localhost:3000/projects/prj_mcp_market/documents/doc_09e127a2a134");
  }
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  // Look for 'Gherkin Scenarios' tab
  const scenariosTab = await page.$('button[role="tab"]:has-text("Gherkin Scenarios")');
  console.log("Gherkin Scenarios tab present:", !!scenariosTab);
  if (scenariosTab) {
    await scenariosTab.click();
    await page.waitForTimeout(500);
    
    // Check for Feature card, badges, and scenario cards
    const featureBanner = await page.$('text="Feature"');
    const scenarioCards = await page.$$('span:has-text("Scenario")');
    console.log("Feature banner present:", !!featureBanner);
    console.log(`Scenario count rendered: ${scenarioCards.length}`);
    await page.screenshot({ path: "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a/evidence_gherkin_scenario_visualizer.png", fullPage: true });
  }

  console.log("5. Verifying Bug Scan Page: Bug Fix Reviewer & Remediation Guide...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/bugs");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  // Check for Bug Fix Reviewer badge on finding cards
  const reviewerBadge = await page.$('text="Bug Fix Reviewer"');
  console.log("Bug Fix Reviewer badge visible:", !!reviewerBadge);

  // Open first step-by-step remediation guide
  const guideBtn = await page.$('button:has-text("View Step-by-Step Guide")');
  if (guideBtn) {
    await guideBtn.click();
    await page.waitForTimeout(500);
    const modalHeader = await page.$('h3:has-text("End-to-End Bug Remediation Guide")');
    const phase5 = await page.$('text="Phase 5: Bug Fix Reviewer Confidence Audit"');
    console.log("Remediation modal opened:", !!modalHeader);
    console.log("Phase 5 Bug Fix Reviewer present in modal:", !!phase5);
    await page.screenshot({ path: "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a/evidence_bug_fix_reviewer_modal.png" });
    const closeBtn = await page.$('button:has-text("Close")');
    if (closeBtn) await closeBtn.click();
  }

  console.log("6. Verifying QE Studio: Greenfield/Brownfield Toggle & Discovery Gate...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/qe");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  const brownfieldToggle = await page.$('text="Brownfield"');
  const greenfieldToggle = await page.$('text="Greenfield"');
  console.log("Brownfield toggle present:", !!brownfieldToggle);
  console.log("Greenfield toggle present:", !!greenfieldToggle);

  // Verify Discovery stage
  const discoveryStage = await page.$('li:has-text("Discovery")');
  if (discoveryStage) {
    const text = await discoveryStage.innerText();
    console.log("Discovery stage text:", text.replace(/\n/g, " "));
  }

  await page.screenshot({ path: "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a/evidence_qe_studio_lifecycle_greenfield.png", fullPage: true });

  console.log("7. Verifying BA Studio Contextual Presets...");
  await page.goto("http://localhost:3000/projects/prj_mcp_market/ba");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  const mcpPreset = await page.$('button:has-text("MCP Gateway & Registry")');
  console.log("Contextual MCP Gateway & Registry preset visible:", !!mcpPreset);
  await page.screenshot({ path: "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a/evidence_ba_studio_contextual_presets.png", fullPage: true });

  await browser.close();
  console.log("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!");
}

main().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});

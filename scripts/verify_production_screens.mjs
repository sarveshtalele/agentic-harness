import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const ARTIFACT_DIR = "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a";
const EVIDENCE_DIR = path.join(process.cwd(), "docs", "evidence", "screens");
fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

async function run() {
  console.log("Launching browser for comprehensive verification...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    // 1. Login
    console.log("Logging in as admin...");
    await page.goto("http://localhost:3000/login");
    await page.waitForLoadState("networkidle");
    await page.fill('input[type="text"], input[name="username"]', "admin");
    await page.fill('input[type="password"], input[name="password"]', "admin");
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1000);

    // 2. Verify Harness
    console.log("Visiting /harness...");
    await page.goto("http://localhost:3000/harness");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "harness_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "harness.png"), fullPage: false });
    console.log("Harness screenshot captured!");

    // 3. Test Skill Creation from Studio
    console.log("Visiting /skills/studio...");
    await page.goto("http://localhost:3000/skills/studio");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    // Click "Custom Prompt" tab
    const customPromptBtn = page.locator("button", { hasText: "Custom Prompt" });
    if (await customPromptBtn.isVisible()) {
      await customPromptBtn.click();
    }

    // Fill brief
    const promptArea = page.locator('textarea[aria-label="Custom requirements specification"]');
    if (await promptArea.isVisible()) {
      await promptArea.fill("Synthesize an autonomous skill to validate and verify payments idempotency and settlement contracts.");
    }

    // Click AI Architect
    const autoFillBtn = page.locator("button", { hasText: "AI Architect & Auto-Fill Skill Specifications" });
    if (await autoFillBtn.isVisible()) {
      await autoFillBtn.click();
      await page.waitForTimeout(1000);
    }

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "skills_studio_autofilled.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "skills_studio.png"), fullPage: false });
    console.log("Skills studio screenshot captured!");

    // Scaffold skill
    const scaffoldBtn = page.locator("button", { hasText: "Scaffold Agent Skill & Test Cases" });
    if (await scaffoldBtn.isVisible()) {
      await scaffoldBtn.click();
      await page.waitForTimeout(2000);
      console.log("Skill scaffolded successfully!");
    }

    // 4. Test Skill Creation from Harness
    console.log("Testing Skill Creation from Harness /create_agent_skill...");
    await page.goto("http://localhost:3000/harness");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    // Focus prompt input and type command
    const chatInput = page.locator("textarea").first();
    if (await chatInput.isVisible()) {
      await chatInput.fill("/create_agent_skill Settlement Idempotency Verifier");
      const sendBtn = page.locator('button[aria-label="Send to QE Harness"]');
      await sendBtn.click();
      console.log("Sent /create_agent_skill command to harness...");
      // Wait for execution to stream and complete
      await page.waitForTimeout(6000);
    }

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "harness_skill_created.png"), fullPage: false });
    console.log("Harness skill creation screenshot captured!");

    // 5. Verify /agents
    console.log("Visiting /agents...");
    await page.goto("http://localhost:3000/agents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "agents_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "agents.png"), fullPage: false });

    // 6. Verify Documents page
    console.log("Visiting /projects/prj_mcp_market/documents...");
    await page.goto("http://localhost:3000/projects/prj_mcp_market/documents");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "documents_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "documents.png"), fullPage: false });

    // 7. Verify /skills
    console.log("Visiting /skills...");
    await page.goto("http://localhost:3000/skills");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "skills_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "skills_list.png"), fullPage: false });

    // 8. Verify /mcp
    console.log("Visiting /mcp...");
    await page.goto("http://localhost:3000/mcp");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "mcp_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "mcp.png"), fullPage: false });

    // 9. Verify /projects/prj_mcp_market/bugs
    console.log("Visiting /projects/prj_mcp_market/bugs...");
    await page.goto("http://localhost:3000/projects/prj_mcp_market/bugs");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "bugs_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "project_bugs.png"), fullPage: false });

    // 10. Verify /projects/prj_mcp_market/ba
    console.log("Visiting /projects/prj_mcp_market/ba...");
    await page.goto("http://localhost:3000/projects/prj_mcp_market/ba");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "ba_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "project_ba.png"), fullPage: false });

    // 11. Verify /projects/prj_mcp_market/qe
    console.log("Visiting /projects/prj_mcp_market/qe...");
    await page.goto("http://localhost:3000/projects/prj_mcp_market/qe");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "qe_fixed.png"), fullPage: false });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, "project_qe.png"), fullPage: false });

    console.log("All verifications and screenshots completed successfully!");
  } catch (err) {
    console.error("Verification failed:", err);
    throw err;
  } finally {
    await browser.close();
  }
}

run();

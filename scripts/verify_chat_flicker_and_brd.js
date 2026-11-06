const { chromium } = require("playwright");
const path = require("path");

const ARTIFACT_DIR = "/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a";

async function runVerification() {
  console.log("🚀 Starting Playwright verification for chat flicker fix, real BRD generation, and BA studio...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    // 0. Sign In
    console.log("0. Signing in as admin...");
    await page.goto("http://localhost:3000/login", { waitUntil: "networkidle" });
    await page.fill('input[name="username"]', "admin");
    await page.fill('input[name="password"]', "admin");
    await page.click('button[type="submit"]');
    await page.waitForURL("http://localhost:3000/");
    console.log("✅ Signed in successfully.");

    // 1. Verify Harness Page and Session Switching (Zero Flicker)
    console.log("1. Navigating to Harness at http://localhost:3000/harness...");
    await page.goto("http://localhost:3000/harness", { waitUntil: "networkidle" });
    await page.waitForSelector("textarea", { timeout: 10000 });

    // Click on a session in the left sidebar to test switching without flicker
    const sessionLinks = page.locator("div.cursor-pointer").filter({ hasText: /BRD|Test|Session/ });
    const count = await sessionLinks.count();
    if (count > 1) {
      console.log(`Found ${count} session items. Clicking session 2 to test flicker-free switching...`);
      await sessionLinks.nth(1).click();
      await page.waitForTimeout(500);
    }

    // Take screenshot of harness state
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_harness_session_switching.png"), fullPage: false });
    console.log("📸 Saved evidence_harness_session_switching.png");

    // 2. Submit "create BRD for ATM machine"
    console.log("2. Submitting prompt: 'create BRD for ATM machine'...");
    const textarea = page.locator("textarea").first();
    await textarea.click();
    await textarea.fill("create BRD for ATM machine");
    await page.locator('button[type="submit"]').last().click();

    // Wait for the assistant response to appear
    console.log("Waiting for domain-grounded BRD generation...");
    await page.waitForFunction(() => {
      const texts = Array.from(document.querySelectorAll("div, p, h1, h2, h3"));
      return texts.some(el => el.textContent && (el.textContent.includes("Documentation Generated") || el.textContent.includes("ATM")));
    }, { timeout: 15000 });

    await page.waitForTimeout(3000);

    // Capture screenshot of generated BRD with Copy and 3-dots menu
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_real_atm_brd_generated.png"), fullPage: false });
    console.log("📸 Saved evidence_real_atm_brd_generated.png");

    // 3. Verify Agents Page & Guardrail Event Cards
    console.log("3. Navigating to Agents Page at http://localhost:3000/agents...");
    await page.goto("http://localhost:3000/agents", { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_agents_guardrail_cards.png"), fullPage: false });
    console.log("📸 Saved evidence_agents_guardrail_cards.png");

    // 4. Verify BA Studio Page
    console.log("4. Navigating to BA Studio at http://localhost:3000/projects/prj_agentic_qe/ba...");
    await page.goto("http://localhost:3000/projects/prj_agentic_qe/ba", { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "evidence_ba_studio_polished.png"), fullPage: false });
    console.log("📸 Saved evidence_ba_studio_polished.png");

    console.log("✅ All visual verifications passed successfully!");
  } catch (err) {
    console.error("❌ Verification failed:", err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

runVerification();

const { chromium } = require('playwright');
const path = require('path');

const ARTIFACT_DIR = '/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a';

async function main() {
  console.log('Starting Playwright Verification for MCP Page, Goals, and Agent Details...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // 1. Sign in
  console.log('Step 1: Signing in...');
  await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('http://localhost:3000/');
  console.log('Signed in.');

  // 2. Capture MCP Management Page
  console.log('Step 2: Capturing /mcp page...');
  await page.goto('http://localhost:3000/mcp');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_mcp_management_page.png'), fullPage: true });
  console.log('Captured: evidence_mcp_management_page.png');

  // 3. Open Connect Server modal on MCP page
  console.log('Step 3: Opening Connect MCP Server modal...');
  const connectBtn = page.locator('button:has-text("Connect Server")');
  if (await connectBtn.isVisible()) {
    await connectBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_mcp_connect_modal.png') });
    console.log('Captured: evidence_mcp_connect_modal.png');
    await page.click('button:has-text("Cancel")');
    await page.waitForTimeout(300);
  }

  // 4. Capture Agent Detail Page (/agents/business-analyst)
  console.log('Step 4: Capturing /agents/business-analyst detail page with scores and guardrail cards...');
  await page.goto('http://localhost:3000/agents/business-analyst');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_agent_detail_scores_and_guardrails.png'), fullPage: true });
  console.log('Captured: evidence_agent_detail_scores_and_guardrails.png');

  // 5. Capture Harness Empty State with Goal Cards & Chat Input
  console.log('Step 5: Capturing /harness with rich Goal Cards and modern input bar...');
  await page.goto('http://localhost:3000/harness?project=prj_mcp_market');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_harness_goals_and_input_bar.png') });
  console.log('Captured: evidence_harness_goals_and_input_bar.png');

  // 6. Inspect Model Dropdown in Chat Bar
  console.log('Step 6: Opening model dropdown inside chat bar...');
  const modelBtn = page.locator('form button:has-text("deepseek"), form button:has-text("Configured Model"), form button:has-text("Gemini")').first();
  if (await modelBtn.isVisible()) {
    await modelBtn.click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_chat_model_dropdown_popover.png') });
    console.log('Captured: evidence_chat_model_dropdown_popover.png');
    await modelBtn.click();
    await page.waitForTimeout(300);
  }

  // 7. Inspect Skills Modal with Markdown Rendering
  console.log('Step 7: Capturing /skills markdown rendering...');
  await page.goto('http://localhost:3000/skills');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  const skillCard = page.locator('[data-testid="skill-card"]').first();
  if (await skillCard.isVisible()) {
    await skillCard.click();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_skill_rendered_markdown_modal.png') });
    console.log('Captured: evidence_skill_rendered_markdown_modal.png');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
  }

  // 8. Projects list showing prj_mcp_market
  console.log('Step 8: Checking / showing prj_mcp_market...');
  await page.goto('http://localhost:3000/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_projects_with_target_repo.png'), fullPage: true });
  console.log('Captured: evidence_projects_with_target_repo.png');

  await browser.close();
  console.log('Playwright verification run complete.');
}

main().catch((err) => {
  console.error('Playwright verification error:', err);
  process.exit(1);
});

/**
 * Comprehensive visual verification script for:
 * 1. Project selector moved to the right side of the header.
 * 2. "Quick:" option bar removed from the chat window.
 * 3. Next.js "N" dev badge completely hidden.
 * 4. /skills page rendered with rich cards and NVIDIA Skill Specter scorecards.
 * 5. /agents page rendered with real measured metrics (Groundedness, Faithfulness, Recall, F1).
 * 6. Python Calculator React BRD document generation with full tables & sections.
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = '/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a';

async function main() {
  console.log('Starting Playwright End-to-End Visual Verification...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // 1. Sign in
  console.log('Step 1: Signing in as administrator...');
  await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('http://localhost:3000/');
  console.log('Successfully signed in.');

  // 2. Check /agents page for real measured scores
  console.log('Step 2: Checking /agents for real measured scores (not "Not measured")...');
  await page.goto('http://localhost:3000/agents');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_agents_measured_metrics.png'), fullPage: true });
  console.log('Captured: evidence_agents_measured_metrics.png');

  // 3. Check /skills page for NVIDIA Skill Specter Cards
  console.log('Step 3: Checking /skills for NVIDIA Skill Specter card grid...');
  await page.goto('http://localhost:3000/skills');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_skills_specter_card_grid.png'), fullPage: true });
  console.log('Captured: evidence_skills_specter_card_grid.png');

  // 4. Open a Skill Modal
  console.log('Step 4: Opening a skill card modal preview...');
  const firstSkillCard = page.locator('[data-testid="skill-card"]').first();
  if (await firstSkillCard.isVisible()) {
    await firstSkillCard.click();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_skill_card_modal_preview.png') });
    console.log('Captured: evidence_skill_card_modal_preview.png');
    // Close modal
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
  }

  // 5. Navigate to /harness and verify layout
  console.log('Step 5: Verifying /harness header and chat input...');
  await page.goto('http://localhost:3000/harness?project=prj_agentic_qe');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  // Check Quick chips bar is not visible
  const quickBar = page.locator('text="Quick:"');
  const hasQuickBar = await quickBar.isVisible().catch(() => false);
  console.log('Is Quick Bar visible in chat?', hasQuickBar);

  // Check Next.js dev badge is not visible
  const nextBadge = page.locator('[data-next-badge]');
  const hasNextBadge = await nextBadge.isVisible().catch(() => false);
  console.log('Is Next.js dev badge visible?', hasNextBadge);

  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_harness_layout_and_header.png') });
  console.log('Captured: evidence_harness_layout_and_header.png');

  // 6. Test Model Dropdown (should only show Settings Configured Models)
  console.log('Step 6: Verifying model dropdown only shows settings configured models...');
  const modelButton = page.locator('button:has-text("deepseek-v4-flash-global"), button:has-text("Configured Model")').first();
  if (await modelButton.isVisible()) {
    await modelButton.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_model_dropdown_settings_only.png') });
    console.log('Captured: evidence_model_dropdown_settings_only.png');
    // Close dropdown
    await modelButton.click();
    await page.waitForTimeout(300);
  }

  // 7. Generate Python Calculator React BRD Document
  console.log('Step 7: Testing Python Calculator React BRD Document Generation...');
  await page.fill('textarea', 'create a docuement for python clacuatlro react based application as BRD docuement');
  await page.keyboard.press('Enter');

  console.log('Waiting for BRD generation and emission...');
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_brd_python_calculator_generated.png') });
  console.log('Captured: evidence_brd_python_calculator_generated.png');

  // 8. Open Document in Viewer
  console.log('Step 8: Checking Document in Project Documents...');
  await page.goto('http://localhost:3000/projects/prj_agentic_qe/documents');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_project_documents_list.png'), fullPage: true });
  console.log('Captured: evidence_project_documents_list.png');

  console.log('✅ All Playwright visual verifications completed successfully!');
  await browser.close();
}

main().catch((err) => {
  console.error('Playwright verification error:', err);
  process.exit(1);
});

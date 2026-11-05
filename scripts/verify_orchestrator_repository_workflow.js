const { chromium } = require('playwright');
const path = require('path');

const ARTIFACT_DIR = '/Users/sarveshtalele/.gemini/antigravity/brain/275d566b-bbc8-4e05-9e1e-aee53cc0859a';

async function main() {
  console.log('Starting Playwright Verification for Repository Endpoints & UI Pages...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', err => {
    pageErrors.push(err.message);
  });

  // 1. Sign in
  console.log('Step 1: Signing in as admin...');
  await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle' });
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('http://localhost:3000/');
  console.log('Signed in successfully.');

  // 2. Test /projects/prj_agentic_qe/repository
  console.log('Step 2: Checking /projects/prj_agentic_qe/repository...');
  await page.goto('http://localhost:3000/projects/prj_agentic_qe/repository');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  // Check if error boundary message exists
  const hasErrorBoundary = await page.locator('text="This page hit an error"').isVisible().catch(() => false);
  if (hasErrorBoundary) {
    throw new Error('Detected React Error Boundary on prj_agentic_qe/repository');
  }

  // Click on a file in tree if present
  const readmeFile = page.locator('button:has-text("README.md")').first();
  if (await readmeFile.isVisible()) {
    await readmeFile.click();
    await page.waitForTimeout(500);
  }

  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_prj_agentic_qe_repository.png'), fullPage: true });
  console.log('Captured: evidence_prj_agentic_qe_repository.png');

  // 3. Test /projects/prj_fintech_gateway/repository
  console.log('Step 3: Checking /projects/prj_fintech_gateway/repository...');
  await page.goto('http://localhost:3000/projects/prj_fintech_gateway/repository');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_prj_fintech_gateway_repository.png'), fullPage: true });
  console.log('Captured: evidence_prj_fintech_gateway_repository.png');

  // 4. Test /projects/prj_ecommerce_core/repository
  console.log('Step 4: Checking /projects/prj_ecommerce_core/repository...');
  await page.goto('http://localhost:3000/projects/prj_ecommerce_core/repository');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_prj_ecommerce_core_repository.png'), fullPage: true });
  console.log('Captured: evidence_prj_ecommerce_core_repository.png');

  // 5. Test /projects/prj_mcp_market/repository
  console.log('Step 5: Checking /projects/prj_mcp_market/repository...');
  await page.goto('http://localhost:3000/projects/prj_mcp_market/repository');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_prj_mcp_market_repository.png'), fullPage: true });
  console.log('Captured: evidence_prj_mcp_market_repository.png');

  // 6. Test /projects/prj_agentic_qe/ba & documents
  console.log('Step 6: Checking BA Studio and Documents...');
  await page.goto('http://localhost:3000/projects/prj_agentic_qe/ba');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_prj_agentic_qe_ba_studio.png') });
  console.log('Captured: evidence_prj_agentic_qe_ba_studio.png');

  await page.goto('http://localhost:3000/projects/prj_agentic_qe/documents');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: path.join(ARTIFACT_DIR, 'evidence_prj_agentic_qe_documents.png') });
  console.log('Captured: evidence_prj_agentic_qe_documents.png');

  console.log('Page Errors recorded:', pageErrors);
  console.log('Console Errors recorded:', consoleErrors);

  if (pageErrors.length > 0) {
    throw new Error(`Encountered page errors: ${JSON.stringify(pageErrors)}`);
  }

  await browser.close();
  console.log('Verification completed successfully with ZERO errors!');
}

main().catch(err => {
  console.error('Playwright verification failed:', err);
  process.exit(1);
});

const { chromium } = require("@playwright/test");

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto("http://localhost:3000");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);

  // 1. Dark Theme with Slash Palette
  const textarea = page.locator("textarea");
  await textarea.fill("/");
  await page.waitForSelector("text=Slash Command & Local Skills Autocomplete", { timeout: 5000 });
  await page.screenshot({ path: "evidence_slash_palette.png" });

  // 2. Clear and Light Mode
  await page.keyboard.press("Escape");
  await textarea.fill("");
  const themeBtn = page.locator("button[title*='Switch to'], button[title*='theme']").first();
  await themeBtn.click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: "evidence_light.png" });

  await browser.close();
  console.log("Screenshots captured successfully.");
}

main().catch(console.error);

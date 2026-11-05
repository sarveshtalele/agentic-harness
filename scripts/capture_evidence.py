import os
import sys
import time
from playwright.sync_api import sync_playwright

EVIDENCE_DIR = os.path.abspath("docs/evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("1. Logging in to http://localhost:3000/login...")
        page.goto("http://localhost:3000/login", wait_until="networkidle")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "admin")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1500)

        # 2. Homepage (Projects Hub) - Dark
        print("2. Capturing Homepage Dark...")
        page.goto("http://localhost:3000/", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "01_homepage_dark.png"))

        # 3. Homepage - Light
        print("3. Capturing Homepage Light...")
        theme_btn = page.locator('button[aria-label*="mode"]').first
        if theme_btn.is_visible():
            theme_btn.click()
            page.wait_for_timeout(500)
            page.screenshot(path=os.path.join(EVIDENCE_DIR, "01_homepage_light.png"))

        # 4. Project Overview - Light
        print("4. Capturing Project Overview Light...")
        page.goto("http://localhost:3000/projects/prj_agentic_qe", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "02_project_overview_light.png"))

        # 5. Project QE Harness - Light
        print("5. Capturing QE Harness Light...")
        page.goto("http://localhost:3000/projects/prj_agentic_qe/harness", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "03_harness_light.png"))

        # 6. Switch back to Dark Theme for Harness Chat
        print("6. Switching to Dark Theme for Harness Chat...")
        theme_btn = page.locator('button[aria-label*="mode"]').first
        if theme_btn.is_visible():
            theme_btn.click()
            page.wait_for_timeout(500)
            page.screenshot(path=os.path.join(EVIDENCE_DIR, "03_harness_dark.png"))

        # 7. Type a prompt in Harness and Send
        print("7. Sending prompt in Harness...")
        textarea = page.locator('textarea').first
        if textarea.is_visible():
            textarea.fill("/skills")
            send_btn = page.locator('button[aria-label="Send to QE Harness"]').first
            if send_btn.is_visible():
                send_btn.click()
            else:
                page.keyboard.press("Enter")
            page.wait_for_timeout(3500)
            page.screenshot(path=os.path.join(EVIDENCE_DIR, "04_harness_chat_stream.png"))

        print("Finished all evidence captures!")
        browser.close()

if __name__ == "__main__":
    run()

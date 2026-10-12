"""Real local Chromium smoke test; no BLE instance or model API is used."""

import unittest

from playwright.sync_api import sync_playwright


class ChromiumSmokeTests(unittest.TestCase):
    def test_chromium_launches_handles_ui_action_and_screenshot(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 640, "height": 480})
                page.set_content(
                    '<button id="save" onclick="this.textContent=\'Saved\'">Save</button>'
                )
                page.get_by_role("button", name="Save").click()
                self.assertEqual(page.get_by_role("button").inner_text(), "Saved")
                screenshot = page.screenshot(type="png")
                self.assertTrue(screenshot.startswith(b"\x89PNG\r\n\x1a\n"))
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()

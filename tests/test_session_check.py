import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from sqbf.models import Scenario
from sqbf.session_check import check_session

POLICY = Scenario.load("projects/ble-elva/scenarios/core-smoke-01.json").read_only_policy
URL = "http://127.0.0.1:5080/"


class SessionCheckTests(unittest.TestCase):
    def run_check(self, fail_context=None, fail_stage=None, visible=True, expected_products=None,
                  empty_visible=True, product_visible=True):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text(json.dumps({"cookies": [{"value": "secret-canary", "expires": 1}]}))
            p = MagicMock()
            browser = p.chromium.launch.return_value
            contexts = []
            def new_context(**kwargs):
                number = len(contexts) + 1
                context = MagicMock()
                page = context.new_page.return_value
                page.get_by_placeholder.return_value.is_visible.return_value = visible
                def text_locator(text, **kwargs):
                    locator = MagicMock()
                    locator.count.return_value = 1
                    locator.is_visible.return_value = (visible and (
                        empty_visible if text == POLICY['empty_text'] else product_visible))
                    return locator
                page.get_by_text.side_effect = text_locator
                response = MagicMock(status=200)
                stage = 0
                def navigate(url=None, **kwargs):
                    nonlocal stage
                    stage += 1
                    page.url = URL.rstrip("/") + ("/" if stage == 1 else POLICY["target_path"])
                    if number == fail_context and stage == fail_stage:
                        page.url = URL + "login?secret=secret-canary"
                    return response
                page.goto.side_effect = navigate
                page.reload.side_effect = navigate
                contexts.append(context)
                return context
            browser.new_context.side_effect = new_context
            manager = MagicMock()
            manager.__enter__.return_value = p
            with patch("playwright.sync_api.sync_playwright", return_value=manager):
                result = check_session(URL, state, POLICY, expected_products=expected_products)
            self.assertNotIn("secret-canary", json.dumps(result))
            for context in contexts:
                context.close.assert_called_once()
                page = context.new_page.return_value
                page.fill.assert_not_called()
                page.click.assert_not_called()
            browser.close.assert_called_once()
            return result, contexts

    def test_present_expired_state_redirect_is_blocked(self):
        result, _ = self.run_check(1, 1)
        self.assertEqual(result["status"], "BLOCKED_SESSION")
        self.assertEqual(result["checks"][0]["path"], "/login")

    def test_authenticated_product_page_contexts_and_reload_pass(self):
        result, contexts = self.run_check()
        self.assertEqual(result["status"], "SESSION_RESTORED")
        self.assertEqual(len(result["checks"]), 6)
        self.assertEqual(len(contexts), 2)
        self.assertFalse(result["identity_verified"])
        self.assertEqual(result["model_calls"], 0)

    def test_reload_invalidates_session(self):
        result, _ = self.run_check(1, 3)
        self.assertEqual(result["reason"], "UNEXPECTED_PAGE")

    def test_new_context_invalidates_session(self):
        result, _ = self.run_check(2, 1)
        self.assertEqual(result["status"], "BLOCKED_SESSION")

    def test_missing_ui_does_not_pass(self):
        result, _ = self.run_check(visible=False)
        self.assertEqual(result["reason"], "MISSING_EXPECTED_UI")

    def test_populated_fixture_requires_explicit_visible_products_and_no_empty_state(self):
        result, _ = self.run_check(expected_products=['synthetic STS'], empty_visible=False)
        self.assertEqual(result['status'], 'SESSION_RESTORED')
        self.assertFalse(result['identity_verified'])
        result, _ = self.run_check(expected_products=['synthetic STS'], empty_visible=False, product_visible=False)
        self.assertEqual(result['status'], 'BLOCKED_SESSION')
        result, _ = self.run_check(expected_products=['synthetic STS'], empty_visible=True)
        self.assertEqual(result['status'], 'BLOCKED_SESSION')

    def test_empty_fixture_default_is_not_silently_relaxed(self):
        result, _ = self.run_check(empty_visible=False)
        self.assertEqual(result['status'], 'BLOCKED_SESSION')

    def test_invalid_populated_expectations_block_before_browser(self):
        with patch('playwright.sync_api.sync_playwright') as browser:
            for names in ([], ['duplicate', 'duplicate'], [None], 'synthetic STS'):
                self.assertEqual(check_session(URL, 'unused', POLICY, expected_products=names)['reason'],
                                 'INVALID_PRODUCT_EXPECTATION')
            browser.assert_not_called()

    def test_missing_file_and_external_url_without_browser(self):
        with patch("playwright.sync_api.sync_playwright") as browser:
            self.assertEqual(check_session(URL, "nonexistent-session.json", POLICY)["reason"], "MISSING_SESSION")
            self.assertEqual(check_session("https://example.com/", "x", POLICY)["reason"], "UNAPPROVED_ORIGIN")
            browser.assert_not_called()

    def test_cli_preflight_blocks_stale_session(self):
        from sqbf.cli import main
        with patch("sqbf.session_check.check_session", return_value={"status": "BLOCKED_SESSION"}), patch("builtins.print"):
            self.assertEqual(main(["preflight", "--scenario", "projects/ble-elva/scenarios/core-smoke-01.json",
                                   "--storage-state", "expired.json"]), 2)

    def test_run_checks_session_before_authorization_or_inference(self):
        from sqbf.cli import main
        with tempfile.TemporaryDirectory() as directory, \
             patch("sqbf.session_check.check_session",return_value={"status":"BLOCKED_SESSION"}), \
             patch("sqbf.plan_login.authorize") as auth,patch("sqbf.bounded.invoke_worker") as worker,patch("sqbf.cli.run") as runner,patch("builtins.print"):
            state=Path(directory)/"state.json";state.write_text('{}')
            code=main(['run','--scenario','projects/ble-elva/scenarios/core-smoke-01.json',
                       '--url',URL,'--software-version','synthetic','--fixture-ready',
                       '--executor-provider','chatgpt_plan','--executor-model','gpt-6-luna',
                       '--analyst-provider','chatgpt_plan','--analyst-model','gpt-6.1-sol',
                       '--storage-state',str(state)])
            self.assertEqual(code,2)
            auth.assert_not_called();worker.assert_not_called();runner.assert_not_called()

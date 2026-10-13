import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from sqbf.cli import save_session, main
from sqbf.session_credentials import load_credentials


class SessionLoginTests(unittest.TestCase):
    def test_atomic_form_submission_survives_input_reset_canary(self):
        from playwright.sync_api import sync_playwright
        from urllib.parse import parse_qs
        with sync_playwright() as p:
            browser=p.chromium.launch()
            page=browser.new_page()
            submitted=[]
            def capture(route):
                submitted.append(parse_qs(route.request.post_data or ""))
                route.fulfill(status=200,body="Synthetic login canary")
            page.route("http://127.0.0.1:54321/**",capture)
            page.set_content('''<form method="post" action="http://127.0.0.1:54321/login">
            <input name="username" required><input name="password" type="password" required>
            <button type="submit">Login</button></form>
            <script>document.addEventListener('input',()=>document.querySelector('[name=username]').value='');</script>''')
            page.locator('[name=username]').fill('benchmark-user')
            self.assertEqual(page.locator('[name=username]').input_value(),'')
            page.locator('form').evaluate('''(f,c)=>{
                f.elements.namedItem('username').value=c.username;
                f.elements.namedItem('password').value=c.password;
                f.requestSubmit();
            }''',{'username':'benchmark-user','password':'synthetic-canary'})
            page.wait_for_url('http://127.0.0.1:54321/login')
            self.assertEqual(submitted,[{'username':['benchmark-user'],'password':['synthetic-canary']}])
            browser.close()

    def test_dpapi_is_user_bound_and_identity_checked(self):
        result = MagicMock(stdout=json.dumps({"username": "benchmark-user", "password": "secret-canary"}))
        with patch("sqbf.session_credentials.subprocess.run", return_value=result) as process:
            data = load_credentials("local.dpapi.json", "benchmark-user")
            self.assertEqual(data["username"], "benchmark-user")
            self.assertNotIn("secret-canary", str(process.call_args))
            script = process.call_args.args[0][-1]
            self.assertIn("AreAccessRulesProtected", script)
            self.assertIn("ZeroFreeBSTR", script)
            self.assertFalse(any(k.lower() == "psmodulepath" for k in process.call_args.kwargs["env"]))

    def test_account_mismatch_redacted(self):
        result = MagicMock(stdout=json.dumps({"username": "wrong-user", "password": "secret-canary"}))
        with patch("sqbf.session_credentials.subprocess.run", return_value=result):
            with self.assertRaises(ValueError) as failure:
                load_credentials("local.dpapi.json", "benchmark-user")
            self.assertNotIn("secret-canary", str(failure.exception))

    def test_decrypt_error_redacted(self):
        with patch("sqbf.session_credentials.subprocess.run", side_effect=RuntimeError("secret-canary")):
            with self.assertRaises(ValueError) as failure:
                load_credentials("local.dpapi.json", "benchmark-user")
            self.assertNotIn("secret-canary", str(failure.exception))

    def test_login_sets_both_fields_and_submits_once(self):
        with tempfile.TemporaryDirectory() as directory:
            p = MagicMock()
            browser = p.chromium.launch.return_value
            context = browser.new_context.return_value
            page = context.new_page.return_value
            page.url = "http://127.0.0.1:5080/"
            manager = MagicMock()
            manager.__enter__.return_value = p
            data = {"username": "benchmark-user", "password": "secret-canary"}
            with patch("playwright.sync_api.sync_playwright", return_value=manager), \
                 patch("sqbf.session_credentials.load_credentials", return_value=data), patch("builtins.input") as input_fn:
                save_session(page.url, Path(directory)/"new.json", "local.dpapi.json", "benchmark-user")
                input_fn.assert_not_called()
                form = page.locator.return_value
                form.evaluate.assert_called_once()
                self.assertIn("requestSubmit", form.evaluate.call_args.args[0])
                form.fill.assert_not_called()
                context.storage_state.assert_called_once()
                self.assertEqual(data, {})

    def test_failed_login_never_saves_or_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            p = MagicMock();page=p.chromium.launch.return_value.new_context.return_value.new_page.return_value
            page.wait_for_url.side_effect=RuntimeError("secret-canary")
            manager=MagicMock();manager.__enter__.return_value=p
            with patch("playwright.sync_api.sync_playwright",return_value=manager), \
                 patch("sqbf.session_credentials.load_credentials",return_value={"username":"benchmark-user","password":"secret-canary"}):
                with self.assertRaises(ValueError) as failure:
                    save_session("http://127.0.0.1:5080/",Path(directory)/"new.json","local.dpapi.json","benchmark-user")
                self.assertNotIn("secret-canary",str(failure.exception))
                p.chromium.launch.return_value.new_context.return_value.storage_state.assert_not_called()
                page.locator.return_value.evaluate.assert_called_once()

    def test_cli_failure_is_sanitized(self):
        with patch("sqbf.cli.save_session",side_effect=ValueError("secret-canary")),patch("builtins.print") as output:
            self.assertEqual(main(["session","--url","http://127.0.0.1:5080/"]),2)
            self.assertNotIn("secret-canary",str(output.call_args))

    def test_existing_state_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"state.json";path.write_text("preserved")
            with self.assertRaises(ValueError):save_session("http://127.0.0.1:5080/",path)
            self.assertEqual(path.read_text(),"preserved")

import contextlib
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqbf import bounded, plan_credentials as pc, plan_login
from sqbf.providers import CHATGPT_PLAN_SCOPE, ChatGPTPlanCredential

SCOPE = "openid offline_access " + CHATGPT_PLAN_SCOPE


def clock_at(start=1_000_000.0):
    state = {"now": start}

    def clock():
        return state["now"]
    clock.state = state
    return clock


def record(clock, **changes):
    base = {"version": 1, "refresh_token": "refresh-1", "access_token": "access-1", "client_id": "oaiapp_test", "subject": "sub-1", "scope": SCOPE,
            "login_at": clock(), "access_expires_at": clock() + 3600, "max_age_days": 7}
    return dict(base, **changes)


def store_in(directory, clock):
    # A reversible stand-in for DPAPI keeps most tests portable; the real DPAPI has its own test below.
    return pc.PlanTokenStore(directory, protect=lambda data: data[::-1], unprotect=lambda data: data[::-1], clock=clock)


class Endpoint:
    """Fake OAuth token endpoint: returns queued answers (dicts) or raises queued errors; remembers every form it received."""

    def __init__(self, *answers, delay=0.0):
        self.answers, self.forms, self.delay, self.lock = list(answers), [], delay, threading.Lock()

    def __call__(self, request):
        if self.delay:
            time.sleep(self.delay)
        with self.lock:
            self.forms.append(dict(urllib.parse.parse_qsl(request.data.decode())))
            answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


def tokens(access="access-2", refresh="refresh-2", expires_in=3600, **extra):
    return dict({"access_token": access, "refresh_token": refresh, "expires_in": expires_in, "token_type": "Bearer", "scope": SCOPE}, **extra)


class PlanCredentialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "plan-login"
        self.clock = clock_at()

    def store(self):
        return store_in(self.dir, self.clock)

    # ---- store ------------------------------------------------------------------------------------------------------------------------
    def test_the_store_round_trips_and_is_encrypted_at_rest_with_a_private_file(self):
        store = self.store()
        self.assertIsNone(store.load());self.assertFalse(store.exists())
        store.save(record(self.clock))
        self.assertTrue(store.exists());self.assertEqual(store.load()["refresh_token"],"refresh-1")
        self.assertNotIn(b"refresh-1",store.path.read_bytes())  # base64 of the reversed JSON, not the token in clear
        self.assertEqual([p.name for p in self.dir.iterdir() if p.suffix == ".tmp"],[])  # the temporary file is gone

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_real_dpapi_round_trip_binds_to_the_windows_user_and_hides_the_text(self):
        secret = b"refresh-token-value-123"
        blob = pc.dpapi_protect(secret)
        self.assertNotIn(secret, blob);self.assertEqual(pc.dpapi_unprotect(blob), secret)
        with self.assertRaises(pc.PlanAuthorizationError) as caught:pc.dpapi_unprotect(blob[:-3] + b"xyz")
        self.assertEqual(caught.exception.code, "PLAN_STORE_UNREADABLE")
        store = pc.PlanTokenStore(self.dir, clock=self.clock);store.save(record(self.clock))
        self.assertNotIn(b"refresh-1", store.path.read_bytes());self.assertEqual(store.load()["access_token"], "access-1")

    def test_damaged_or_wrong_records_are_refused_with_a_fixed_code(self):
        store = self.store()
        for bad in (record(self.clock, scope="openid"), record(self.clock, client_id="other"), record(self.clock, refresh_token=""),
                    record(self.clock, max_age_days=0), record(self.clock, max_age_days=pc.MAX_AGE_DAYS_LIMIT + 1), record(self.clock, version=2)):
            with self.assertRaises(pc.PlanAuthorizationError) as caught:store.save(bad)
            self.assertEqual(caught.exception.code, "PLAN_STORE_UNREADABLE")
        self.dir.mkdir(parents=True, exist_ok=True);store.path.write_bytes(b"not base64 at all !!")
        with self.assertRaises(pc.PlanAuthorizationError) as caught:store.load()
        self.assertEqual(caught.exception.code, "PLAN_STORE_UNREADABLE");self.assertNotIn("refresh", str(caught.exception))

    def test_a_login_older_than_its_maximum_age_is_refused_and_forget_removes_it(self):
        store = self.store();store.save(record(self.clock, max_age_days=2))
        self.clock.state["now"] += 2 * 86400 - 10;self.assertEqual(store.load()["subject"], "sub-1")
        self.clock.state["now"] += 20
        with self.assertRaises(pc.PlanAuthorizationError) as caught:store.load()
        self.assertEqual(caught.exception.code, "PLAN_LOGIN_TOO_OLD")
        self.assertTrue(store.forget());self.assertFalse(store.exists());self.assertFalse(store.forget())
        with self.assertRaises(pc.PlanAuthorizationError) as caught:pc.RefreshingPlanCredential(store)
        self.assertEqual(caught.exception.code, "PLAN_LOGIN_MISSING")

    # ---- renewal ----------------------------------------------------------------------------------------------------------------------
    def test_renewal_spends_the_refresh_token_with_the_standard_grant_and_keeps_what_the_server_rotates(self):
        endpoint = Endpoint(tokens())
        updated = pc.renew(record(self.clock), request=endpoint, clock=self.clock)
        form = endpoint.forms[0]
        self.assertEqual((form["grant_type"], form["refresh_token"], form["client_id"]), ("refresh_token", "refresh-1", "oaiapp_test"))
        self.assertEqual((updated["access_token"], updated["refresh_token"]), ("access-2", "refresh-2"))
        self.assertEqual(updated["access_expires_at"], self.clock() + 3600);self.assertEqual(updated["login_at"], self.clock())
        kept = pc.renew(record(self.clock), request=Endpoint(tokens(refresh=None)), clock=self.clock)
        self.assertEqual(kept["refresh_token"], "refresh-1")  # no rotation: the old one stays valid

    def test_renewal_failures_are_classified_into_login_gone_and_try_again_later(self):
        for status in (400, 401, 403):
            with self.assertRaises(pc.PlanAuthorizationError) as caught:
                pc.renew(record(self.clock), request=Endpoint(RuntimeError(f"ChatGPT authorization/catalog request failed with HTTP {status}")), clock=self.clock)
            self.assertEqual(caught.exception.code, "PROVIDER_REFRESH_REJECTED")
        transient = RuntimeError("ChatGPT authorization/catalog request failed")
        endpoint = Endpoint(transient, tokens());pauses = []
        self.assertEqual(pc.renew(record(self.clock), request=endpoint, clock=self.clock, pause=pauses.append)["access_token"], "access-2")
        self.assertEqual((len(endpoint.forms), pauses), (2, [2]))
        endpoint = Endpoint(transient)
        with self.assertRaises(pc.PlanAuthorizationError) as caught:pc.renew(record(self.clock), request=endpoint, clock=self.clock, pause=lambda s: None)
        self.assertEqual((caught.exception.code, len(endpoint.forms)), ("PROVIDER_REFRESH_UNAVAILABLE", 2))  # one repeat, then stop
        self.assertNotIn("refresh-1", str(caught.exception))

    def test_a_renewal_that_loses_the_plan_scope_or_is_not_a_bearer_token_is_refused(self):
        for answer in (tokens(scope="openid"), tokens(token_type="mac"), {"token_type": "Bearer"}, tokens(access="")):
            with self.assertRaises(pc.PlanAuthorizationError) as caught:pc.renew(record(self.clock), request=Endpoint(answer), clock=self.clock)
            self.assertEqual(caught.exception.code, "PROVIDER_REFRESH_REJECTED")

    def test_the_expiry_comes_from_expires_in_then_the_token_itself_then_a_fallback(self):
        self.assertEqual(pc.access_expiry({"access_token": "x", "expires_in": 900}, 100.0), 1000.0)
        import base64
        payload = base64.urlsafe_b64encode(json.dumps({"exp": 5000}).encode()).decode().rstrip("=")
        self.assertEqual(pc.access_expiry({"access_token": "h." + payload + ".s"}, 100.0), 5000.0)
        self.assertEqual(pc.access_expiry({"access_token": "opaque"}, 100.0), 100.0 + pc.FALLBACK_LIFETIME_SECONDS)
        self.assertEqual(pc.access_expiry({"access_token": "opaque", "expires_in": True}, 100.0), 100.0 + pc.FALLBACK_LIFETIME_SECONDS)

    # ---- the credential ----------------------------------------------------------------------------------------------------------------
    def test_a_valid_token_is_served_without_renewal_and_an_expiring_one_is_renewed_once_and_shared(self):
        store = self.store();store.save(record(self.clock))
        endpoint = Endpoint(tokens())
        first = pc.RefreshingPlanCredential(store, request=endpoint, clock=self.clock)
        self.assertEqual(first.access_token, "access-1");self.assertEqual(endpoint.forms, [])
        self.assertEqual(first.granted_scopes, frozenset(SCOPE.split()))
        self.clock.state["now"] += 3600 - pc.EXPIRY_MARGIN_SECONDS + 1  # inside the safety margin
        self.assertEqual(first.access_token, "access-2");self.assertEqual(len(endpoint.forms), 1)
        # Another process (a second credential on the same store) uses the renewed token and does not spend the refresh token again.
        second = pc.RefreshingPlanCredential(store, request=endpoint, clock=self.clock)
        self.assertEqual(second.access_token, "access-2");self.assertEqual(len(endpoint.forms), 1)
        self.assertEqual(store.load()["refresh_token"], "refresh-2")

    def test_the_memory_cache_does_not_touch_the_store_on_every_request(self):
        store = self.store();store.save(record(self.clock))
        credential = pc.RefreshingPlanCredential(store, request=Endpoint(tokens()), clock=self.clock)
        with patch.object(pc.PlanTokenStore, "load", side_effect=AssertionError("the store must not be read per request")):
            credential._token, credential._expires = "cached", self.clock() + 3600
            for _ in range(50):self.assertEqual(credential.access_token, "cached")

    def test_parallel_processes_renew_exactly_once_even_while_the_refresh_token_rotates(self):
        store = self.store();store.save(record(self.clock, access_expires_at=self.clock() - 10))
        endpoint = Endpoint(tokens(), delay=0.3)
        credentials = [pc.RefreshingPlanCredential(self.store(), request=endpoint, clock=self.clock) for _ in range(5)]
        results = []
        threads = [threading.Thread(target=lambda c=c: results.append(c.access_token)) for c in credentials]
        [t.start() for t in threads];[t.join(30) for t in threads]
        self.assertEqual(results, ["access-2"] * 5);self.assertEqual(len(endpoint.forms), 1)

    def test_a_refused_renewal_surfaces_a_stop_code_and_never_the_token(self):
        store = self.store();store.save(record(self.clock, access_expires_at=self.clock() - 10))
        credential = pc.RefreshingPlanCredential(store, request=Endpoint(RuntimeError("ChatGPT authorization/catalog request failed with HTTP 400")), clock=self.clock)
        with self.assertRaises(pc.PlanAuthorizationError) as caught:credential.access_token
        self.assertEqual(caught.exception.code, "PROVIDER_REFRESH_REJECTED");self.assertIn(caught.exception.code, pc.REFUSED_CODES)
        self.assertNotIn("refresh-1", str(caught.exception));self.assertEqual(repr(credential), "RefreshingPlanCredential(<hidden>)")

    def test_renew_now_proves_the_grant_and_describe_shows_no_secret(self):
        store = self.store();store.save(record(self.clock))
        endpoint = Endpoint(tokens())
        credential = pc.RefreshingPlanCredential(store, request=endpoint, clock=self.clock)
        credential.renew_now();self.assertEqual((len(endpoint.forms), credential.access_token), (1, "access-2"))
        info = credential.describe()
        self.assertEqual(set(info), {"signed_in_hours_ago", "login_valid_for_hours", "max_age_days", "access_token_valid_for_minutes"})
        self.assertNotIn("refresh", json.dumps(info));self.assertEqual(info["max_age_days"], 7)

    def test_build_record_requires_an_issued_refresh_token(self):
        form = {"client_id": "oaiapp_test"}
        built = pc.build_record(form, tokens(), "sub-1", SCOPE, max_age_days=3, now=self.clock())
        self.assertEqual((built["refresh_token"], built["max_age_days"], built["subject"]), ("refresh-2", 3, "sub-1"))
        with self.assertRaises(pc.PlanAuthorizationError) as caught:pc.build_record(form, tokens(refresh=None), "sub-1", SCOPE, max_age_days=3, now=1.0)
        self.assertEqual(caught.exception.code, "PLAN_NO_REFRESH_TOKEN")

    # ---- worker specs ------------------------------------------------------------------------------------------------------------------
    def test_specs_carry_an_access_token_for_requests_and_only_the_store_path_for_the_suite_worker(self):
        store = self.store();store.save(record(self.clock))
        credential = pc.RefreshingPlanCredential(store, request=Endpoint(tokens()), clock=self.clock)
        from sqbf.providers import ChatGPTPlanModel
        schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False}
        model = ChatGPTPlanModel("gpt-test", credential, schema)
        request_spec = bounded.model_spec(model)
        self.assertEqual(request_spec["access_token"], "access-1");self.assertNotIn("credential_store", request_spec)
        suite_spec = bounded.suite_model_spec(model)
        self.assertNotIn("access_token", suite_spec);self.assertEqual(suite_spec["credential_store"], str(self.dir))
        for spec in (request_spec, suite_spec):self.assertNotIn("refresh", json.dumps(spec))
        # A plain credential keeps the old behaviour: the suite worker gets the access token.
        plain = ChatGPTPlanModel("gpt-test", ChatGPTPlanCredential("plain-token", frozenset(SCOPE.split())), schema)
        self.assertEqual(bounded.suite_model_spec(plain)["access_token"], "plain-token")
        with patch.object(bounded, "PlanTokenStore", lambda directory: store_in(directory, self.clock)):
            restored = bounded.restore_model(suite_spec)
        self.assertIsInstance(restored.credential, pc.RefreshingPlanCredential)
        self.assertEqual(bounded.restore_model(bounded.model_spec(plain)).credential.access_token, "plain-token")

    # ---- using the kept login ----------------------------------------------------------------------------------------------------------
    def reuse(self, host, *, stored=None, fail_renewal=False):
        store = self.store()
        store.forget()
        if stored is not None:store.save(stored)
        endpoint = Endpoint(RuntimeError("ChatGPT authorization/catalog request failed with HTTP 400") if fail_renewal else tokens())
        browser = MagicMock(return_value="browser-credential")
        real = pc.RefreshingPlanCredential
        with patch.object(plan_login, "default_directory", return_value=self.dir), patch.object(plan_login, "authorize", browser), \
             patch.object(plan_login, "PlanTokenStore", lambda directory: store_in(directory, self.clock)), \
             patch.object(plan_login, "RefreshingPlanCredential", lambda s: real(s, request=endpoint, clock=self.clock)), contextlib.redirect_stdout(io.StringIO()) as out:
            result = plan_login.authorize_or_reuse(host)
        return result, browser, out.getvalue()

    def test_a_kept_login_replaces_the_browser_and_anything_else_falls_back_to_it(self):
        result, browser, text = self.reuse({"host_id": "h"}, stored=record(self.clock))
        self.assertIsInstance(result, pc.RefreshingPlanCredential);browser.assert_not_called();self.assertIn("no browser confirmation", text)
        # Registration facts must match the kept login (same account and client).
        for host in ({"host_id": "h", "subject": "someone-else"}, {"host_id": "h", "client_id": "oaiapp_other"}):
            result, browser, _ = self.reuse(host, stored=record(self.clock));self.assertEqual(result, "browser-credential");browser.assert_called_once()
        result, browser, _ = self.reuse({"host_id": "h"});self.assertEqual(result, "browser-credential")  # nothing kept
        result, browser, text = self.reuse({"host_id": "h"}, stored=record(self.clock, access_expires_at=self.clock() - 5), fail_renewal=True)
        self.assertEqual(result, "browser-credential");self.assertIn("PROVIDER_REFRESH_REJECTED", text)  # refused renewal: browser instead, before any run
        result, browser, text = self.reuse({"host_id": "h"}, stored=record(self.clock, login_at=self.clock() - 8 * 86400))
        self.assertEqual(result, "browser-credential");self.assertIn("PLAN_LOGIN_TOO_OLD", text)

    def run_main(self, argv, **patches):
        out = io.StringIO()
        with patch.object(plan_login, "default_directory", return_value=self.dir), patch.object(plan_login, "PlanTokenStore", lambda d: store_in(d, self.clock)), \
             patch.object(plan_login, "catalog", return_value=["gpt-test"]), contextlib.redirect_stdout(out):
            code = plan_login.main(argv)
        return code, out.getvalue()

    def test_status_check_and_forget_commands_never_print_a_secret(self):
        code, text = self.run_main(["--status"]);self.assertEqual((code, json.loads(text)), (0, {"signed_in": False}))
        self.store().save(record(self.clock))
        code, text = self.run_main(["--status"]);info = json.loads(text);self.assertEqual((code, info["signed_in"], info["max_age_days"]), (0, True, 7))
        self.assertNotIn("refresh-1", text);self.assertNotIn("access-1", text)
        endpoint = Endpoint(tokens())
        real = pc.RefreshingPlanCredential
        with patch.object(plan_login, "RefreshingPlanCredential", lambda s: real(s, request=endpoint, clock=self.clock)):
            code, text = self.run_main(["--check"])
        info = json.loads(text);self.assertEqual((code, info["refresh_verified"], info["models"]), (0, True, ["gpt-test"]));self.assertNotIn("access-2", text)
        code, text = self.run_main(["--forget"]);self.assertEqual((code, json.loads(text)), (0, {"forgotten": True}))
        self.assertFalse(self.store().exists())

    def keep(self, *, renewal_ok):
        form = {"client_id": "oaiapp_test"}

        def fake_authorize(host, *, keep_days=None):
            store = store_in(self.dir, self.clock)
            store.save(pc.build_record(form, tokens(access="access-0", refresh="refresh-0"), "sub-1", SCOPE, max_age_days=keep_days, now=self.clock()))
            return pc.RefreshingPlanCredential(store, request=Endpoint(tokens() if renewal_ok else RuntimeError("ChatGPT authorization/catalog request failed with HTTP 400")),
                                               clock=self.clock)
        with patch.object(plan_login, "authorize", fake_authorize), patch.object(plan_login, "_load_host", return_value={"host_id": "urn:uuid:x"}):
            return self.run_main(["--keep-signed-in", "--max-age-days", "3"])

    def test_keeping_the_login_verifies_the_renewal_at_once_and_forgets_it_if_the_provider_refuses(self):
        code, text = self.keep(renewal_ok=True)
        info = json.loads(text);self.assertEqual(code, 0)
        self.assertEqual((info["tokens_saved"], info["refresh_verified"], info["max_age_days"], info["protected_by"]),
                         (True, True, 3, "Windows DPAPI, current user only"))
        self.assertNotIn("refresh-", text);self.assertTrue(self.store().exists())
        self.store().forget()
        code, text = self.keep(renewal_ok=False)
        self.assertEqual(code, 2);self.assertIn("login was not kept", text);self.assertIn("PROVIDER_REFRESH_REJECTED", text);self.assertFalse(self.store().exists())

    def test_max_age_is_bounded(self):
        with self.assertRaises(SystemExit),contextlib.redirect_stderr(io.StringIO()):plan_login.main(["--keep-signed-in", "--max-age-days", "99"])


class StopRuleTests(unittest.TestCase):
    def test_a_refused_or_missing_login_stops_the_suite_like_an_expired_token_and_a_transient_failure_does_not(self):
        import importlib
        from sqbf.calibration import ResourceStop, SuiteBudget
        from test_calibration import policy
        stage = importlib.import_module("projects.ble-elva.tools.stage_support")
        for code in pc.REFUSED_CODES:
            budget = SuiteBudget(policy());budget.start_task({"case_id": "T", "observation_marks": {"seconds": 600, "actions": 60}})
            evidence = MagicMock()
            with self.assertRaises(ResourceStop):
                stage.ask_executor(MagicMock(side_effect=pc.PlanAuthorizationError(code, "x")), object(), "p", b"png", budget, evidence)
            self.assertEqual(budget.stop_reason, "PROVIDER_AUTHORIZATION_EXPIRED")
            event = [c for c in evidence.event.call_args_list if c.args[0] == "executor_call_failed"][0]
            self.assertEqual((event.kwargs["error_code"], event.kwargs["exception_type"]), (code, "PlanAuthorizationError"))
        budget = SuiteBudget(policy());budget.start_task({"case_id": "T", "observation_marks": {"seconds": 600, "actions": 60}})
        with self.assertRaises(stage.ExecutorRequestFailed) as caught:
            stage.ask_executor(MagicMock(side_effect=pc.PlanAuthorizationError("PROVIDER_REFRESH_UNAVAILABLE", "x")), object(), "p", b"png", budget, MagicMock())
        self.assertEqual(caught.exception.code, "PROVIDER_REFRESH_UNAVAILABLE");self.assertIsNone(budget.stop_reason)


if __name__ == "__main__":
    unittest.main()

"""Offline OAuth checks; no browser login or real token exchange."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

try:
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:
    jwt = None

from sqbf.plan_login import LoginAttempt, ISSUER, _load_host, catalog, main, validate_tokens
from sqbf.providers import CHATGPT_PLAN_SCOPE, ChatGPTPlanCredential


@unittest.skipIf(jwt is None, "Install SQBF's [plan] extra to run JWT signature tests")
class PlanLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def tokens(self, **changes):
        claims = {"iss": ISSUER, "aud": "oaiapp_test", "sub": "synthetic-user",
                  "exp": int(time.time()) + 60, "iat": int(time.time()), "nonce": "nonce"}
        claims.update(changes)
        return {"id_token": jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "test"}),
                "access_token": "secret-canary", "token_type": "Bearer", "scope": CHATGPT_PLAN_SCOPE}

    def validate(self, tokens):
        with patch("jwt.PyJWKClient") as jwks:
            jwks.return_value.get_signing_key_from_jwt.return_value = types.SimpleNamespace(key=self.key.public_key())
            return validate_tokens(tokens, "oaiapp_test", "nonce")

    def test_authorization_has_pkce_scope_correct_callback_and_app_identity(self):
        attempt = LoginAttempt("http://127.0.0.1:12345/auth/callback")
        params = parse_qs(urlsplit(attempt.authorization_url("urn:uuid:synthetic")).query)
        self.assertEqual(params["client_id"], ["dynamic_agent_client"])
        self.assertEqual(params["agent_name_hint"], ["SQBF"])
        self.assertEqual(params["redirect_uri"], [attempt.redirect_uri])
        self.assertIn(CHATGPT_PLAN_SCOPE, params["scope"][0].split())
        challenge = base64.urlsafe_b64encode(hashlib.sha256(attempt.verifier.encode()).digest()).rstrip(b"=").decode()
        self.assertEqual(params["code_challenge"], [challenge])
        self.assertNotIn("agent_name_hint", parse_qs(urlsplit(attempt.authorization_url("host", "oaiapp_test")).query))

    def callback(self, attempt, **params):
        values = {"state": attempt.state, "code": "synthetic-code", "client_id": "oaiapp_test"}
        values.update(params)
        return "/auth/callback?" + urlencode(values)

    def test_callback_is_one_time_and_exchange_reuses_exact_uri_and_verifier(self):
        attempt = LoginAttempt("http://127.0.0.1:12345/auth/callback")
        form = attempt.consume(self.callback(attempt))
        self.assertEqual(form["redirect_uri"], attempt.redirect_uri)
        self.assertEqual(form["code_verifier"], attempt.verifier)
        self.assertNotIn("client_secret", form)
        with self.assertRaisesRegex(ValueError, "consumed"):
            attempt.consume(self.callback(attempt))

    def test_invalid_state_expiry_denial_duplicate_and_client_fail_closed(self):
        for error in ["state", "expired", "denied", "duplicate", "client"]:
            with self.subTest(error=error):
                attempt = LoginAttempt("http://127.0.0.1:12345/auth/callback")
                path = self.callback(attempt)
                if error == "state": path = self.callback(attempt, state="wrong")
                if error == "expired": attempt.expires_at = 0
                if error == "denied": path = self.callback(attempt, error="access_denied")
                if error == "duplicate": path += "&state=duplicate"
                saved = "oaiapp_other" if error == "client" else None
                with self.assertRaises(ValueError):
                    attempt.consume(path, saved)

    def test_validated_signature_identity_scope_and_secret_redaction(self):
        credential, subject = self.validate(self.tokens())
        self.assertEqual(subject, "synthetic-user")
        self.assertNotIn("secret-canary", repr(credential))
        for claims in [{"iss": "wrong"}, {"aud": "wrong"}, {"nonce": "wrong"},
                       {"exp": 1}, {"sub": ""}, {"iat": int(time.time()) + 100}]:
            with self.subTest(claims=claims), self.assertRaises(RuntimeError) as caught:
                self.validate(self.tokens(**claims))
            self.assertNotIn("secret-canary", str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)
        tokens = self.tokens()
        tokens["scope"] = "openid"
        with self.assertRaises(RuntimeError):
            self.validate(tokens)

    def test_bad_signature_and_account_switch_are_rejected(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with patch("jwt.PyJWKClient") as jwks:
            jwks.return_value.get_signing_key_from_jwt.return_value = types.SimpleNamespace(key=other.public_key())
            with self.assertRaises(RuntimeError):
                validate_tokens(self.tokens(), "oaiapp_test", "nonce")
            jwks.return_value.get_signing_key_from_jwt.return_value = types.SimpleNamespace(key=self.key.public_key())
            with self.assertRaises(RuntimeError):
                validate_tokens(self.tokens(), "oaiapp_test", "nonce", "different-user")

    def test_host_is_stable_and_no_token_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            record = _load_host(Path(directory))
            self.assertEqual(_load_host(Path(directory)), record)
            self.assertEqual(set(json.loads((Path(directory) / "registration.json").read_text())), {"host_id"})

    def test_model_catalog_only_lists_visible_account_slugs(self):
        credential = ChatGPTPlanCredential("secret-canary", frozenset({CHATGPT_PLAN_SCOPE}))
        with patch("sqbf.plan_login._json_request", return_value={"models": [
            {"slug": "allowed", "visibility": "list"}, {"slug": "hidden", "visibility": "hide"}
        ]}) as request:
            self.assertEqual(catalog(credential), ["allowed"])
        self.assertEqual(request.call_args.args[0].get_header("Authorization"), "Bearer secret-canary")

    def test_no_inference_without_explicit_flag_and_no_unlisted_model_call(self):
        cred = ChatGPTPlanCredential("secret-canary", frozenset({CHATGPT_PLAN_SCOPE}))
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"LOCALAPPDATA": directory}), \
                patch("sqbf.plan_login.authorize", return_value=cred), \
                patch("sqbf.plan_login.catalog", return_value=["allowed"]), \
                patch("sqbf.plan_login.vision_test") as vision:
            self.assertEqual(main([]), 0)
            vision.assert_not_called()
            self.assertEqual(main(["--vision-test", "--model", "not-listed"]), 2)
            vision.assert_not_called()


if __name__ == "__main__":
    unittest.main()

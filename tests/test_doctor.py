"""No-cost doctor diagnostics do not assert a functional test PASS."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqbf.doctor import check_fixture, check_health, readiness


class DoctorTests(unittest.TestCase):
    def test_rejects_non_loopback_targets_without_network(self):
        with patch("sqbf.doctor.urlopen") as opener:
            for url in ("https://example.com/", "http://example.com", "http://foo:5059/",
                        "http://user:pass@127.0.0.1:5059/", "file:///etc/passwd"):
                self.assertEqual(check_health(url)["status"], "BLOCKED")
            opener.assert_not_called()

    def test_health_endpoint_local_and_bounded(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, amount): return b"Healthy"
        with patch("sqbf.doctor.urlopen", return_value=Response()) as fn:
            self.assertEqual(check_health("http://127.0.0.1:5059")["status"], "READY")
            self.assertEqual(fn.call_args.args[0], "http://127.0.0.1:5059/health/ready")
            self.assertEqual(fn.call_args.kwargs["timeout"], 4)

    def test_fixture_not_provisioned_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "fixture.json"
            p.write_text(json.dumps({"fixture_id": "test", "status": "NOT_PROVISIONED"}))
            self.assertEqual(check_fixture(p)["status"], "BLOCKED")
            p.write_text(json.dumps({"fixture_id": "test", "status": "READY"}))
            result = check_fixture(p)
            self.assertEqual(result["status"], "DECLARED_READY")
            self.assertTrue(result["requires_external_isolation_verification"])

    def test_no_claim_of_live_ai_readiness_when_health_works(self):
        with tempfile.TemporaryDirectory() as tmp, \
            patch("sqbf.doctor.check_health", return_value={"status": "READY"}), \
            patch("sqbf.doctor.check_chromium", return_value={"status": "READY"}):
            p = Path(tmp)
            fixture = p / "fixture.json"
            fixture.write_text(json.dumps({"fixture_id": "x", "status": "NOT_PROVISIONED"}))
            outcome = readiness("http://127.0.0.1:5059", fixture, p / "missing-state.json")
            self.assertEqual(outcome["status"], "TECHNICAL_SMOKE_READY")
            self.assertFalse(outcome["live_ai_benchmark_ready"])
            self.assertFalse(outcome["extra_api_billing_allowed"])
            self.assertEqual(outcome["fixture"]["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()

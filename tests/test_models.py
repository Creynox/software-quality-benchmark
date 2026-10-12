"""Unit tests for action policy, scenario and result policy."""

import json
import tempfile
import unittest
from pathlib import Path

from sqbf.models import Scenario, assess_run, parse_json_object, safe_action_log, validate_action
from sqbf.runner import host_allowed


class ScenarioTests(unittest.TestCase):
    def test_valid_profile_and_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.json"
            p.write_text(json.dumps({
                "scenario_id": "product", "task": "Create", "url": "http://127.0.0.1:5000/",
                "persona": "Laborleitung", "fixture_id": "seed1", "expected": ["visible"]
            }), encoding="utf-8")
            s = Scenario.load(p, "http://127.0.0.1:5678/")
            self.assertEqual(s.max_minutes, 25)
            self.assertEqual(s.max_actions, 150)
            self.assertEqual(s.url, "http://127.0.0.1:5678/")
            self.assertIn("127.0.0.1", s.allowed_hosts)

    def test_unsupported_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.json"
            p.write_text(json.dumps({
                "scenario_id": "x", "task": "Do", "url": "file:///etc/passwd",
                "persona": "x", "fixture_id": "x", "expected": ["x"]
            }))
            with self.assertRaises(ValueError):
                Scenario.load(p)


class PolicyTests(unittest.TestCase):
    def test_valid_click_and_reject_hidden_techniques(self):
        self.assertEqual(validate_action({"action": "click", "x": 20, "y": 30}, 100, 100)["x"], 20)
        for invalid in (
            {"action": "click", "x": -1, "y": 0},
            {"action": "key", "key": "F12"},
            {"action": "key", "key": "ControlOrMeta+L"},
            {"action": "navigate", "url": "http://example.com"},
            {"action": "type", "text": "x" * 501},
            {"action": "scroll", "amount": 100000},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_action(invalid, 100, 100)

    def test_json_only(self):
        self.assertEqual(parse_json_object('{"action":"done"}')["action"], "done")
        with self.assertRaises(ValueError):
            parse_json_object("I think it is done")
        with self.assertRaises(ValueError):
            parse_json_object('["done"]')

    def test_typed_input_is_masked_in_events(self):
        item = safe_action_log({"action": "type", "text": "secret123"})
        self.assertNotIn("text", item)
        self.assertEqual(item["typed_chars"], 9)

    def test_host_boundary(self):
        self.assertTrue(host_allowed("https://ble.local/product", ["ble.local"]))
        self.assertFalse(host_allowed("https://ble.local.attacker.com/path", ["ble.local"]))
        self.assertFalse(host_allowed("file:///etc/passwd", ["ble.local"]))

    def test_no_fake_pass(self):
        self.assertEqual(assess_run("DONE", None, 3), "INCONCLUSIVE")
        self.assertEqual(assess_run("DONE", {"verdict": "PASS"}, 1), "INCONCLUSIVE")
        self.assertEqual(assess_run("DONE", {"verdict": "PASS"}, 2), "VISUAL_PASS_PENDING_ORACLE")
        self.assertNotEqual(assess_run("DONE", {"verdict": "PASS"}, 2), "PASS")
        self.assertEqual(assess_run("PAUSED_BUDGET", {"verdict": "PASS"}, 2), "INCONCLUSIVE")
        self.assertEqual(assess_run("ERROR", {"verdict": "PASS"}, 2), "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()

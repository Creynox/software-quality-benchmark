"""Mock Chromium integration: prove the run lifecycle without BLE or API accounts."""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from sqbf.models import Scenario
from sqbf.providers import ModelResponse
from sqbf.runner import run


class FakePage:
    url = "http://127.0.0.1:5000/"
    def __init__(self):
        self.actions = []
        self.mouse = types.SimpleNamespace(
            click=lambda *args: self.actions.append(("click", *args)),
            wheel=lambda *args: self.actions.append(("wheel", *args)),
        )
        self.keyboard = types.SimpleNamespace(
            type=lambda *args, **kw: self.actions.append(("type",)),
            press=lambda *args: self.actions.append(("key", *args)),
        )
    def goto(self, *args, **kwargs):
        pass
    def screenshot(self, **kwargs):
        return b"fake png bytes"
    def wait_for_timeout(self, *args):
        pass


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.context = self
    def new_context(self, **kwargs):
        return self
    def route(self, *args):
        pass
    def new_page(self):
        return self.page
    def close(self):
        pass


class FakePlaywright:
    def __init__(self, page):
        self.chromium = types.SimpleNamespace(launch=lambda **kw: FakeBrowser(page))
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class FakeModel:
    provider = "mock"
    model = "executor"
    def __init__(self, responses):
        self.responses = iter(responses)
    def ask(self, *args, **kwargs):
        return ModelResponse(next(self.responses), {"test": True})


class FakeAnalyst:
    provider = "mock"
    model = "analyst"
    def ask(self, *args, **kwargs):
        return ModelResponse({"verdict": "PASS", "reason": "Visible", "findings": []}, {})


class RunnerTests(unittest.TestCase):
    def test_click_then_done_and_report(self):
        scenario = Scenario(
            scenario_id="test", task="click", url="http://127.0.0.1:5000/",
            persona="Laborleitung", fixture_id="fixture", expected=["opened"],
            max_minutes=1, max_actions=10, allowed_hosts=["127.0.0.1"],
        )
        page = FakePage()
        playwright_module = types.ModuleType("playwright")
        api = types.ModuleType("playwright.sync_api")
        api.sync_playwright = lambda: FakePlaywright(page)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            sys.modules, {"playwright": playwright_module, "playwright.sync_api": api}
        ):
            folder = run(
                scenario, FakeModel([
                    {"action": "click", "x": 30, "y": 30},
                    {"action": "done"},
                ]), FakeAnalyst(), Path(tmp), headed=False,
            )
            result = json.loads((folder / "run.json").read_text())
            self.assertEqual(result["executor_status"], "DONE")
            self.assertEqual(result["verdict"], "VISUAL_PASS_PENDING_ORACLE")
            self.assertEqual(result["technical_status"], "PASS")
            self.assertEqual(result["functional_status"], "UNVERIFIED")
            self.assertEqual(result["actions"], 1)
            self.assertEqual(page.actions, [("click", 30, 30)])

    def test_no_analyst_is_inconclusive(self):
        scenario = Scenario(
            scenario_id="test", task="nothing", url="http://127.0.0.1:5000/",
            persona="Laborleitung", fixture_id="fixture", expected=["done"],
            max_minutes=1, max_actions=10, allowed_hosts=["127.0.0.1"],
        )
        playwright_module = types.ModuleType("playwright")
        api = types.ModuleType("playwright.sync_api")
        api.sync_playwright = lambda: FakePlaywright(FakePage())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            sys.modules, {"playwright": playwright_module, "playwright.sync_api": api}
        ):
            folder = run(scenario, FakeModel([{"action": "done"}]), None, Path(tmp))
            result = json.loads((folder / "run.json").read_text())
            self.assertEqual(result["verdict"], "INCONCLUSIVE")

    def test_model_wait_expiring_time_budget_prevents_next_ui_action(self):
        scenario = Scenario(
            scenario_id="test", task="click", url="http://127.0.0.1:5000/",
            persona="Laborleitung", fixture_id="fixture", expected=["opened"],
            max_minutes=1, max_actions=10, allowed_hosts=["127.0.0.1"],
        )
        clock = {"now": 0.0}

        class SlowModel(FakeModel):
            def ask(self, *args, **kwargs):
                clock["now"] += 61
                return ModelResponse(
                    {"action": "click", "x": 30, "y": 30}, {"input_tokens": 2}
                )

        page = FakePage()
        playwright_module = types.ModuleType("playwright")
        api = types.ModuleType("playwright.sync_api")
        api.sync_playwright = lambda: FakePlaywright(page)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            sys.modules, {"playwright": playwright_module, "playwright.sync_api": api}
        ), patch("sqbf.runner.time.monotonic", side_effect=lambda: clock["now"]):
            folder = run(scenario, SlowModel([]), None, Path(tmp), headed=False)
            result = json.loads((folder / "run.json").read_text())

        self.assertEqual(result["executor_status"], "PAUSED_BUDGET")
        self.assertEqual(result["actions"], 0)
        self.assertEqual(page.actions, [])
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertEqual(result["usage"][0]["usage"]["input_tokens"], 2)
        self.assertEqual(result["model_wait_seconds"], 61)


if __name__ == "__main__":
    unittest.main()

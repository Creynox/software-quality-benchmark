"""CLI for manual browser login, preflight and the first BLE micro benchmark."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from .models import Scenario
from .providers import VisionModel
from .runner import run


def ask_extension():
    print("\nPAUSED_BUDGET: Chrome and fixture remain in this process.")
    print("Enter APPROVE <extra_minutes> <extra_actions> to extend; anything else stops.")
    try:
        response = input("> ").strip().split()
    except EOFError:
        return None
    if len(response) != 3 or response[0] != "APPROVE":
        return None
    try:
        minutes, actions = int(response[1]), int(response[2])
    except ValueError:
        return None
    if 0 < minutes <= 120 and 0 < actions <= 500:
        return (minutes, actions)
    print("Rejected: extension must be positive and within 120 min / 500 actions.")
    return None


def save_session(url: str, output: Path):
    from playwright.sync_api import sync_playwright

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Session URL must be http(s)")
    if output.exists():
        raise ValueError("Session file already exists; remove manually to replace")
    output.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        print("Sign in manually in Chrome using the correct isolated benchmark account.")
        input("After sign-in has completed, press Enter to save local session state.")
        context.storage_state(path=str(output))
        browser.close()
    try:
        os.chmod(output, 0o600)
    except OSError:
        pass
    print(f"Session state saved locally: {output} (treat as confidential)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sqbf")
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight", help="Validate scenario without browser or LLM usage")
    preflight.add_argument("--scenario", required=True)
    preflight.add_argument("--url", help="Actual local BLE UI URL; overrides sample config")
    session = sub.add_parser("session", help="Save benchmark-role login session manually")
    session.add_argument("--url", required=True)
    session.add_argument("--output", default=".secrets/ble-session.json")
    execute = sub.add_parser("run", help="Run a scenario on an isolated BLE environment")
    execute.add_argument("--scenario", required=True)
    execute.add_argument("--url", required=True, help="Actual URL for isolated local BLE UI")
    execute.add_argument("--executor-provider", required=True, choices=["openai", "anthropic"])
    execute.add_argument("--executor-model", required=True, help="Verified API model identifier")
    execute.add_argument("--analyst-provider", choices=["openai", "anthropic"])
    execute.add_argument("--analyst-model")
    execute.add_argument("--no-analyst", action="store_true", help="Technical smoke only; no PASS")
    execute.add_argument("--storage-state", help="Local Playwright session state file")
    execute.add_argument("--allow-host", action="append", default=[], help="Additional trusted asset host")
    execute.add_argument("--output", default="runs")
    execute.add_argument("--headless", action="store_true")
    execute.add_argument("--fixture-ready", action="store_true", help="Assert isolated fixture was prepared")
    execute.add_argument("--interactive-budget", action="store_true", help="Explicit manual run extension")
    args = parser.parse_args(argv)

    if args.command == "session":
        save_session(args.url, Path(args.output))
        return 0

    scenario = Scenario.load(args.scenario, getattr(args, "url", None))
    if args.command == "preflight":
        print(json.dumps({
            "scenario_id": scenario.scenario_id, "persona": scenario.persona,
            "fixture_id": scenario.fixture_id, "url": scenario.url,
            "allowed_hosts": scenario.allowed_hosts,
            "budget": {"minutes": scenario.max_minutes, "actions": scenario.max_actions},
            "expected": scenario.expected,
        }, indent=2, ensure_ascii=False))
        return 0

    if not args.fixture_ready:
        parser.error("Only an isolated seeded fixture is permitted; pass --fixture-ready after verification.")
    if not args.no_analyst and not (args.analyst_provider and args.analyst_model):
        parser.error("Provide --analyst-provider and --analyst-model, or use --no-analyst for technical smoke")
    if args.storage_state and not Path(args.storage_state).is_file():
        parser.error("Session state file does not exist")
    scenario.allowed_hosts = list(set(scenario.allowed_hosts + [h.lower() for h in args.allow_host]))
    executor = VisionModel(args.executor_provider, args.executor_model)
    analyst = None if args.no_analyst else VisionModel(args.analyst_provider, args.analyst_model)
    folder = run(
        scenario, executor, analyst, Path(args.output),
        storage_state=args.storage_state,
        headed=not args.headless,
        ask_extension=ask_extension if args.interactive_budget else None,
    )
    summary = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    print(f"Run artifacts: {folder}")
    print(f"Verdict: {summary['verdict']} (executor={summary['executor_status']})")
    return 0 if summary["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

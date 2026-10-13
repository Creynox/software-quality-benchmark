"""Project-neutral CLI for scaffolding, preflight, browser login and UI runs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from .models import Scenario
from .scaffold import create_project
from .providers import ChatGPTPlanModel, VisionModel
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
    parser = argparse.ArgumentParser(prog="sqbf", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    scaffold = sub.add_parser("new-project", help="Create a blank, reproducible project profile")
    scaffold.add_argument("--slug", required=True, help="Lowercase project directory name")
    scaffold.add_argument("--name", help="Human-readable project name")
    scaffold.add_argument("--projects-dir", default="projects", help="Parent directory for project profiles")
    doctor = sub.add_parser("doctor", help="No-cost local BLE/Chromium/fixture readiness report")
    doctor.add_argument("--url", default="http://127.0.0.1:5059/")
    doctor.add_argument("--fixture", default="projects/ble-elva/fixtures/enzberg-product-core-v0.2.json")
    doctor.add_argument("--storage-state", default=".secrets/ble-session.json")
    registry=sub.add_parser("list-runs",help="Search the local run index",allow_abbrev=False)
    registry.add_argument("--output",default="runs")
    for option in ["test-id","software-version","date","role","result"]:
        registry.add_argument("--"+option)
    registry.add_argument("--min-score",type=int)
    preflight = sub.add_parser("preflight", help="Validate scenario without browser or LLM usage")
    preflight.add_argument("--scenario", required=True)
    preflight.add_argument("--url", help="Actual isolated application URL; overrides sample config")
    session = sub.add_parser("session", help="Save benchmark-role login session manually")
    session.add_argument("--url", required=True)
    session.add_argument("--output", default=".secrets/ble-session.json")
    oracle = sub.add_parser("oracle", help="Read-only independent LAB-01 persistence oracle", allow_abbrev=False)
    oracle.add_argument("--phase", required=True, choices=["before", "after"])
    oracle.add_argument("--fixture", default="projects/ble-elva/fixtures/enzberg-product-core-v0.2.json")
    oracle.add_argument("--baseline", help="Before-phase JSON report required for --phase after")
    oracle.add_argument("--output", help="Local JSON report; defaults under runs/lab01-oracle/")
    oracle.add_argument("--dsn-env", default="SQBF_ORACLE_DSN", help="Environment variable containing the restricted DSN")
    execute = sub.add_parser("run", help="Run a scenario on an isolated target application")
    execute.add_argument("--scenario", required=True)
    execute.add_argument("--url", required=True, help="Actual URL for the isolated local application")
    execute.add_argument("--software-version", "--ble-version", dest="software_version", required=True,
                         help="Exact target application commit SHA or release (old --ble-version alias supported)")
    execute.add_argument("--executor-provider", required=True, choices=["openai", "anthropic", "chatgpt_plan"])
    execute.add_argument("--executor-model", required=True, help="Verified API model identifier")
    execute.add_argument("--analyst-provider", choices=["openai", "anthropic", "chatgpt_plan"])
    execute.add_argument("--fixture",default="projects/ble-elva/fixtures/enzberg-product-core-v0.2.json")
    execute.add_argument("--analyst-model")
    execute.add_argument("--no-analyst", action="store_true", help="Technical smoke only; no PASS")
    execute.add_argument("--storage-state", help="Local Playwright session state file")
    execute.add_argument("--allow-host", action="append", default=[], help="Additional trusted asset host")
    execute.add_argument("--output", default="runs")
    execute.add_argument("--headless", action="store_true")
    execute.add_argument("--fixture-ready", action="store_true", help="Assert isolated fixture was prepared")
    execute.add_argument("--interactive-budget", action="store_true", help="Explicit manual run extension")
    args = parser.parse_args(argv)
    if args.command=="list-runs":
        path=Path(args.output)/"index.jsonl"
        rows=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line] if path.exists() else []
        for argument,key in [("test_id","scenario_id"),("software_version","software_version"),
                             ("date","date"),("result","result")]:
            value=getattr(args,argument)
            if value:rows=[row for row in rows if value in str(row.get(key,""))]
        if args.role:
            rows=[row for row in rows if any(args.role.lower() in str(row.get(key,"")).lower() for key in ["persona","executor","reviewer"])]
        if args.min_score is not None:
            rows=[row for row in rows if row.get("scores") and min(row["scores"].values())>=args.min_score]
        print(json.dumps(rows,ensure_ascii=False,indent=2))
        return 0

    if args.command == "new-project":
        try:
            destination = create_project(Path(args.projects_dir), args.slug, args.name)
        except (ValueError, FileExistsError, FileNotFoundError) as exc:
            parser.error(str(exc))
        print(f"Blank project profile created: {destination}")
        print("Configure its URL, scenario and isolated fixture before preflight or a live run.")
        return 0

    if args.command == "doctor":
        from .doctor import readiness
        result = readiness(args.url, Path(args.fixture), Path(args.storage_state))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "TECHNICAL_SMOKE_READY" else 2

    if args.command == "session":
        save_session(args.url, Path(args.output))
        return 0

    if args.command == "oracle":
        from .oracle import OracleError, verify_fixture
        dsn = os.environ.get(args.dsn_env)
        if not dsn:
            parser.error(f"Environment variable {args.dsn_env} is not set; the DSN is never accepted as a CLI argument.")
        if args.phase == "after" and not args.baseline:
            parser.error("--baseline is required for --phase after")
        output = Path(args.output) if args.output else Path("runs/lab01-oracle") / f"{args.phase}.json"
        try:
            report = verify_fixture(
                dsn, Path(args.fixture), args.phase,
                baseline_path=Path(args.baseline) if args.baseline else None,
                output_path=output,
            )
        except (OracleError, OSError, ValueError) as exc:
            parser.error(f"Oracle rejected the state: {exc}")
        print(json.dumps(report, indent=2, ensure_ascii=False))
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

    if args.executor_provider in {"openai", "anthropic"} or args.analyst_provider in {"openai", "anthropic"}:
        parser.error("Metered HTTP/API providers are disabled by the current subscription-only PO policy. Run 'doctor' and use the future verified Codex/Claude subscription adapter (#14). No API keys or pay-as-you-go fallback.")
    if not args.fixture_ready:
        parser.error("Only an isolated seeded fixture is permitted; pass --fixture-ready after verification.")
    scenario.software_version = args.software_version
    if not args.no_analyst and not (args.analyst_provider and args.analyst_model):
        parser.error("Provide --analyst-provider and --analyst-model, or use --no-analyst for technical smoke")
    if args.storage_state and not Path(args.storage_state).is_file():
        parser.error("Session state file does not exist")
    scenario.allowed_hosts = list(set(scenario.allowed_hosts + [h.lower() for h in args.allow_host]))
    if args.executor_provider == "chatgpt_plan":
        if (not scenario.read_only_policy or args.analyst_provider != "chatgpt_plan"
                or args.no_analyst or args.interactive_budget or args.allow_host
                or args.executor_model != "gpt-6-luna" or args.analyst_model == args.executor_model):
            parser.error("Only the fixed read-only pilot with Luna and a separate ChatGPT-plan reviewer is enabled")
        from .plan_login import _load_host, authorize, catalog
        from .smoke_runner import ACTION_SCHEMA, REVIEW_SCHEMA
        from .read_only import validate_policy
        validate_policy(scenario.read_only_policy)
        directory=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))/"SQBF"/"plan-login"
        record=_load_host(directory)
        try:
            credential=authorize(record)
        except RuntimeError:
            print("BLOCKED_USER_AUTHORIZATION: OpenAI authorization was not completed; zero inference calls and no benchmark started.")
            return 2
        models=catalog(credential)
        if args.executor_model not in models or args.analyst_model not in models:
            parser.error("Executor/reviewer model not in the authorized account catalog; no fallback")
        # Exactly one synthetic reviewer compatibility call, before any BLE
        # screenshots are transmitted, under the same in-memory authorization.
        from .bounded import invoke_worker, model_spec
        schema={"type":"object","properties":{"visible_text":{"type":"string"}},
                "required":["visible_text"],"additionalProperties":False}
        probe=ChatGPTPlanModel(args.analyst_model,credential,schema,timeout=30,max_response_chars=200)
        compatibility=invoke_worker("vision-test",{"provider":model_spec(probe)},45)
        print(json.dumps({"reviewer_compatibility":compatibility}))
        executor=ChatGPTPlanModel(args.executor_model,credential,ACTION_SCHEMA)
        analyst=ChatGPTPlanModel(args.analyst_model,credential,REVIEW_SCHEMA)
    else:
        parser.error("Only separately authorized ChatGPT plan usage is enabled")
    folder = run(
        scenario, executor, analyst, Path(args.output),
        storage_state=args.storage_state,
        headed=not args.headless,
        ask_extension=ask_extension if args.interactive_budget else None,
        fixture_path=Path(args.fixture),
    )
    summary = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    if args.executor_provider=="chatgpt_plan":
        summary["reviewer_compatibility"]=compatibility
        (folder/"run.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Run artifacts: {folder}")
    print(f"Verdict: {summary['verdict']} (executor={summary['executor_status']})")
    return 0 if summary["verdict"] in {"PASS","GO"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

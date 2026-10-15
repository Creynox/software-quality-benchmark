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


def prepare_session_file(output):
    """Reserve a new confidential file before writing cookies into it."""
    with output.open("x"):
        pass
    try:
        if os.name == "nt":
            import subprocess
            sid = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                  "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
                                 capture_output=True, text=True, check=True, timeout=10).stdout.strip()
            import re
            if not re.fullmatch(r"S-1-\d+(?:-\d+)+", sid):
                raise ValueError("Cannot identify session file owner")
            subprocess.run(["icacls.exe", str(output), "/inheritance:r", "/grant:r", f"*{sid}:F"],
                           capture_output=True, check=True, timeout=10)
        else:
            os.chmod(output, 0o600)
    except Exception:
        output.unlink()
        raise ValueError("Cannot enforce private session file permissions") from None


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


def save_session(url: str, output: Path, credentials_path=None, expected_username=None, *, diagnostic_output=None):
    from playwright.sync_api import sync_playwright

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Session URL must be http(s)")
    if output.exists():
        raise ValueError("Session file already exists; remove manually to replace")
    credentials = None
    diagnostic = {'login_posts': 0, 'http_status': None, 'fields_match': None, 'error_code': None}
    diagnostic_path = Path(diagnostic_output) if diagnostic_output else None
    if diagnostic_path and not credentials_path:
        raise ValueError('Guarded login diagnostics require explicit benchmark credentials')
    if diagnostic_path:
        from .artifact_privacy import create_private_file
        create_private_file(diagnostic_path)
    if credentials_path:
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Automatic benchmark login requires a clean loopback HTTP URL")
        from .session_credentials import load_credentials
        credentials = load_credentials(credentials_path, expected_username)
    output.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        if credentials and diagnostic_path:
            from urllib.parse import parse_qs, urlsplit
            endpoint = url.rstrip('/') + '/account/login'
            def guarded_login(route):
                if route.request.method != 'POST':
                    route.abort(); return
                diagnostic['login_posts'] += 1
                if diagnostic['login_posts'] != 1:
                    diagnostic['error_code'] = 'LOGIN_FIELDS_CHANGED_OR_EXTRA_POST'
                    route.abort(); return
                values = parse_qs(route.request.post_data or '')
                matched = (values.get('username') == [credentials['username']]
                           and values.get('password') == [credentials['password']])
                diagnostic['fields_match'] = matched
                if diagnostic['login_posts'] != 1 or not matched:
                    diagnostic['error_code'] = 'LOGIN_FIELDS_CHANGED_OR_EXTRA_POST'
                    route.abort(); return
                route.continue_()
            context.route(endpoint, guarded_login)
            def response_status(response):
                if response.url == endpoint:
                    diagnostic['http_status'] = response.status
                    code = parse_qs(urlsplit(response.headers.get('location', '')).query).get('error', [None])[0]
                    if code in ('invalid', 'environment'):
                        diagnostic['error_code'] = 'LOGIN_' + code.upper()
            page.on('response', response_status)
        page.goto(url, wait_until="domcontentloaded")
        if credentials:
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
                page.locator('input[name="username"]').wait_for(state="visible")
                # Blazor hydration can reset the first input during sequential
                # fills. Set both ordinary form fields and requestSubmit in one
                # browser turn; native validation and server authentication run.
                page.locator('form:has(input[name="username"]):has(input[name="password"])').evaluate("""(form, c) => {
                    form.elements.namedItem('username').value=c.username;
                    form.elements.namedItem('password').value=c.password;
                    form.requestSubmit();
                }""", credentials)
                page.wait_for_url(url, timeout=15000)
                if urlparse(page.url).path == "/login":
                    raise ValueError()
                if diagnostic_path and (diagnostic['login_posts'] != 1
                        or diagnostic['fields_match'] is not True or diagnostic['error_code'] is not None
                        or diagnostic['http_status'] not in (200, 302, 303)):
                    raise ValueError()
            except Exception:
                if diagnostic_path:
                    diagnostic['error_code'] = diagnostic['error_code'] or 'LOGIN_TIMEOUT_OR_REDIRECT'
                    diagnostic_path.write_text(json.dumps(diagnostic, indent=2), encoding='utf-8')
                browser.close()
                raise ValueError("BLOCKED_SESSION: benchmark login failed; no retry or state saved") from None
            finally:
                credentials.clear()
            if diagnostic_path:
                diagnostic_path.write_text(json.dumps(diagnostic, indent=2), encoding='utf-8')
        else:
            print("Sign in manually in Chrome using the correct isolated benchmark account.")
            input("After sign-in has completed, press Enter to save local session state.")
        try:
            prepare_session_file(output)
            context.storage_state(path=str(output))
        finally:
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
    working = sub.add_parser('working-fixture', help='New private LAB working copy; never reset/reuse a database')
    working.add_argument('--source', required=True)
    working.add_argument('--output', required=True)
    working.add_argument('--application-root', required=True)
    restart=sub.add_parser('working-web',help='Restart verified LAB clone only, without seeding or restore')
    restart.add_argument('--fixture',required=True)
    restart.add_argument('--application-root',required=True)
    registry=sub.add_parser("list-runs",help="Search the local run index",allow_abbrev=False)
    suites=sub.add_parser('suite-check',help='Validate fixed suite/dataset contracts without models or DB writes')
    suites.add_argument('--suite',required=True)
    suites.add_argument('--dataset',help='Private reviewed dataset JSON; never model credentials')
    reference=sub.add_parser('reference-project',help='Private BLE raw-measurement projection; no DB or models',allow_abbrev=False)
    reference.add_argument('--suite',required=True)
    reference.add_argument('--dataset',required=True)
    reference.add_argument('--unit-decision',required=True)
    reference.add_argument('--output',required=True,help='New private local JSON file; never overwrites')
    fixture_check=sub.add_parser('suite-fixture-check',help='Model-free NSN014 fixture and four-persona acceptance; no login/model calls',allow_abbrev=False)
    for name in ('fixture','suite','dataset','output'):
        fixture_check.add_argument('--'+name,required=True)
    sessions=sub.add_parser('suite-sessions',help='Model-free four-persona session check/one guarded renewal; no benchmark',allow_abbrev=False)
    for name in ('fixture','output','report'):
        sessions.add_argument('--'+name,required=True)
    suite_run=sub.add_parser('run-suite',help='Check suite readiness; live execution requires --execute',allow_abbrev=False)
    for name in ('suite','dataset','fixture','projection','allocations'):
        suite_run.add_argument('--'+name,required=True)
    suite_run.add_argument('--output',default='D:/Temp/sqbf-regular-runs')
    suite_run.add_argument('--executor-model',default='gpt-6-luna')
    suite_run.add_argument('--reviewer-model',default='gpt-6.1-sol')
    suite_run.add_argument('--execute',action='store_true',help='Explicit single live run after gates and fresh subscription OAuth')
    suite_run.add_argument('--headed',action='store_true')
    suite_run.add_argument('--provider-probe',help='Stored provider-probe result; a failed or stale probe blocks readiness')
    probe=sub.add_parser('suite-provider-probe',help='Two synthetic provider requests for the suite schemas; plan only without --execute',allow_abbrev=False)
    probe.add_argument('--suite',required=True)
    probe.add_argument('--output',default='D:/Temp/sqbf-provider-probes')
    probe.add_argument('--executor-model',default='gpt-6-luna')
    probe.add_argument('--reviewer-model',default='gpt-6.1-sol')
    probe.add_argument('--execute',action='store_true',help='Fresh subscription OAuth and exactly two requests, no retry')
    registry.add_argument("--output",default="runs")
    for option in ["test-id","software-version","date"]:
        registry.add_argument("--"+option, help="Case-sensitive substring match")
    registry.add_argument("--role", help="Case-insensitive substring in persona/executor/reviewer")
    registry.add_argument("--result", help="Exact case-sensitive verdict (GO, NO-GO, PARTIAL GO, etc.)")
    registry.add_argument("--run-id", help="Exact run identifier")
    registry.add_argument("--min-score",type=int)
    preflight = sub.add_parser("preflight", help="Validate scenario without browser or LLM usage")
    preflight.add_argument("--scenario", required=True)
    preflight.add_argument("--url", help="Actual isolated application URL; overrides sample config")
    preflight.add_argument("--storage-state", help="Optional model-free read-only session restoration check")
    session_check = sub.add_parser("session-check", help="Verify stored session in two new read-only contexts")
    session_check.add_argument("--scenario", required=True)
    session_check.add_argument("--url", required=True)
    session_check.add_argument("--storage-state", required=True)
    session_check.add_argument("--output", help="Local sanitized JSON evidence")
    session_check.add_argument('--expected-products',help='Local JSON array of exact names for a populated fixture; default requires empty state')
    scope_check = sub.add_parser("scope-check", help="Model-free independent signed identity and authorization gate", allow_abbrev=False)
    scope_check.add_argument("--scenario", required=True)
    scope_check.add_argument("--url", required=True)
    scope_check.add_argument("--storage-state", required=True)
    scope_check.add_argument("--fixture", default="projects/ble-elva/fixtures/enzberg-product-core-v0.2.json")
    scope_check.add_argument("--identity-application-root", required=True)
    scope_check.add_argument("--identity-verifier", required=True)
    scope_check.add_argument("--output", help="New private local JSON evidence file")
    session = sub.add_parser("session", help="Save benchmark-role login session manually")
    session.add_argument("--url", required=True)
    session.add_argument("--output", default=".secrets/ble-session.json")
    session.add_argument("--credentials", help="Explicit local user-only DPAPI benchmark credential file (Windows)")
    session.add_argument("--username", help="Required exact benchmark username for DPAPI login")
    session.add_argument('--diagnostics',help='New private redacted login transport report; permits exactly one credential-matching POST')
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
    execute.add_argument("--identity-application-root", help="Verified application's cookie discriminator/content root")
    execute.add_argument("--identity-verifier", help="Built controller-only signed-ticket verifier DLL")
    execute.add_argument("--allow-host", action="append", default=[], help="Additional trusted asset host")
    execute.add_argument("--output", default="runs")
    execute.add_argument("--headless", action="store_true")
    execute.add_argument("--fixture-ready", action="store_true", help="Assert isolated fixture was prepared")
    execute.add_argument("--interactive-budget", action="store_true", help="Explicit manual run extension")
    args = parser.parse_args(argv)
    if args.command=='run-suite':
        from .write_profile import load_suite_profile
        try:
            suite=json.loads(Path(args.suite).read_text(encoding='utf-8-sig'))
            adapter=load_suite_profile(suite.get('adapter_contract'))
            inputs=adapter.load_inputs(args.suite,args.dataset,args.fixture,args.projection,args.allocations)
            report=(adapter.run_suite(*inputs,args.output,args.executor_model,args.reviewer_model,headed=args.headed,
                                      provider_probe=args.provider_probe)
                    if args.execute else adapter.check_ready(*inputs,provider_probe=args.provider_probe,
                                                              executor_id=args.executor_model,reviewer_id=args.reviewer_model))
        except Exception:
            print('BLOCKED_SUITE_READINESS: invalid input or private evidence; no fallback/retry.')
            return 2
        print(json.dumps(report,indent=2))
        return 0 if (report['status']=='READY_FOR_SINGLE_SUITE_RUN' or
                     report['status']=='SUITE_RUN_RECORDED' and report.get('technical_status')=='COMPLETED') else 2
    if args.command=='suite-provider-probe':
        from .write_profile import load_suite_profile
        try:
            suite=json.loads(Path(args.suite).read_text(encoding='utf-8-sig'))
            report=load_suite_profile(suite.get('adapter_contract')).provider_probe(
                suite,args.output,args.executor_model,args.reviewer_model,execute=args.execute)
        except Exception:
            print('BLOCKED_PROVIDER_PROBE: invalid input, OAuth or private evidence; no fallback/retry.')
            return 2
        print(json.dumps(report,indent=2))
        return 0 if report['status'] in ('PROBE_PLAN_ONLY','PROBE_RECORDED') and report.get('verdict','PROBE_PASS')=='PROBE_PASS' else 2
    if args.command=='suite-sessions':
        from importlib import import_module
        try:
            report=import_module('projects.ble-elva.tools.suite_sessions').write_prepared_sessions(
                args.fixture,args.output,args.report)
        except Exception:
            print('BLOCKED_SESSION: invalid private output or configuration; no retry.')
            return 2
        print(json.dumps(report,indent=2))
        return 0 if report['status']=='SESSIONS_VERIFIED' else 2
    if args.command=='suite-fixture-check':
        from importlib import import_module
        try:
            report=import_module('projects.ble-elva.tools.suite_acceptance').write_acceptance(
                args.fixture,args.suite,args.dataset,args.output)
        except Exception:
            print('BLOCKED_SUITE_FIXTURE: missing contract or private output; no fallback.')
            return 2
        print(json.dumps(report,indent=2))
        return 0 if report['status']=='FIXTURE_GATES_VERIFIED' else 2
    if args.command=='reference-project':
        from importlib import import_module
        from .artifact_privacy import create_private_file
        try:
            data=json.loads(Path(args.dataset).read_text(encoding='utf-8-sig'))
            suite=json.loads(Path(args.suite).read_text(encoding='utf-8-sig'))
            unit=json.loads(Path(args.unit_decision).read_text(encoding='utf-8-sig'))
            report=import_module('projects.ble-elva.tools.reference_projection').project_reference(data,suite,unit)
            output=Path(args.output)
            if any((parent/'.git').exists() for parent in output.resolve().parents):
                raise ValueError('Private raw evidence must remain outside Git worktrees')
            create_private_file(output)
            output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        except Exception:
            print('BLOCKED_REFERENCE_PROJECTION: invalid source/unit evidence or private output; no runtime operation.')
            return 2
        print(json.dumps({key:report[key] for key in ('status','dataset_id','source_sha256','unit_decision_sha256','model_calls','database_writes')}))
        return 0
    if args.command=='suite-check':
        from .suites import suite_check
        try:
            dataset=json.loads(Path(args.dataset).read_text(encoding='utf-8-sig')) if args.dataset else None
            result=suite_check(args.suite,dataset)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            print('BLOCKED_SUITE_CONTRACT: missing or invalid suite/dataset; no runtime operation.')
            return 2
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['status']=='CONTRACT_READY' else 2
    if args.command == 'working-web':
        from .write_profile import load_write_profile
        start_working_web=load_write_profile('LAB-01-SINGLE-PRODUCT-v1','working_fixture').start_working_web
        try:
            pid=start_working_web(args.fixture,args.application_root)
        except Exception:
            print('BLOCKED_WORKING_WEB: port occupied, identity/build or private credential unavailable; no fallback.')
            return 2
        print(f'Owned working application started, PID {pid}; run session/scope gates before use.')
        return 0
    if args.command == 'working-fixture':
        from .write_profile import load_write_profile
        create_working_fixture=load_write_profile('LAB-01-SINGLE-PRODUCT-v1','working_fixture').create_working_fixture
        try:
            path = create_working_fixture(args.source,args.output,args.application_root)
        except Exception:
            print('BLOCKED_WORKING_FIXTURE: inspect private provisioning evidence; no retry/reset/fallback.')
            return 2
        print(f'Working fixture: {path}')
        return 0
    if args.command=="list-runs":
        path=Path(args.output)/"index.jsonl"
        rows=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line] if path.exists() else []
        from .registry import filter_runs
        rows=filter_runs(rows,result=args.result,run_id=args.run_id,test_id=args.test_id,
                         software_version=args.software_version,date=args.date,role=args.role,min_score=args.min_score)
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
        try:
            save_session(args.url, Path(args.output), args.credentials, args.username, diagnostic_output=args.diagnostics)
        except (ValueError, EOFError, OSError):
            print("BLOCKED_SESSION: session creation failed; no automatic retry.")
            return 2
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
    if args.command == "scope-check":
        from .scope_check import check_scope
        result = check_scope(scenario.url, args.storage_state, scenario.read_only_policy,
                             json.loads(Path(args.fixture).read_text(encoding="utf-8-sig")),
                             args.identity_application_root, args.identity_verifier)
        if args.output:
            from .artifact_privacy import create_private_file
            output = Path(args.output)
            create_private_file(output)
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "SCOPE_VERIFIED" else 2
    if args.command == "session-check" or (args.command == "preflight" and args.storage_state):
        from .session_check import check_session
        expected_products=None
        if args.command == 'session-check' and args.expected_products:
            try:
                expected_products=json.loads(Path(args.expected_products).read_text(encoding='utf-8-sig'))
                if (not isinstance(expected_products,list) or not 1<=len(expected_products)<=100
                        or any(not isinstance(name,str) or not name for name in expected_products)
                        or len(set(expected_products))!=len(expected_products)):
                    raise ValueError()
            except (OSError, ValueError, TypeError):
                print('BLOCKED_SESSION: invalid expected-product contract; no browser operation.')
                return 2
        result = (check_session(scenario.url, args.storage_state, scenario.read_only_policy)
                  if expected_products is None else check_session(scenario.url, args.storage_state,
                       scenario.read_only_policy,expected_products=expected_products))
        if args.command == "session-check" and args.output:
            from .artifact_privacy import create_private_file
            try:
                output=Path(args.output)
                create_private_file(output)
                output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            except Exception:
                print('BLOCKED_SESSION_EVIDENCE: private new output unavailable; no overwrite.')
                return 2
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "SESSION_RESTORED" else 2
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
            parser.error("Only the fixed CORE/LAB pilot with Luna and a separate ChatGPT-plan reviewer is enabled")
        from .plan_login import _load_host, authorize, catalog
        from .smoke_runner import ACTION_SCHEMA, REVIEW_SCHEMA
        from .read_only import validate_policy
        validate_policy(scenario.read_only_policy)
        fixture=json.loads(Path(args.fixture).read_text(encoding='utf-8-sig'))
        if scenario.write_policy:
            from .write_profile import load_write_profile
            validate_target=load_write_profile(scenario.write_policy['contract'],'lab_guard').validate_target
            oracle_dsn=load_write_profile(scenario.write_policy['contract'],'lab_runner').oracle_dsn
            from .oracle import collect_snapshot, verify_before
            from .no_write_oracle import snapshot
            validate_target(scenario,fixture)
            scenario.fixture_id=fixture['fixture_id']
            source=json.loads(Path(fixture['working_copy']['source_fixture']).read_text(encoding='utf-8-sig'))
            load_write_profile(scenario.write_policy['contract'],'lab_guard').validate_source(source)
            if snapshot(source)!=fixture['working_copy']['source_snapshot']:
                parser.error('Protected source changed; no model calls')
            snapshot(fixture)
            verify_before(collect_snapshot(oracle_dsn(fixture),fixture),fixture)
        from .session_check import check_session
        session_result=check_session(scenario.url,args.storage_state,scenario.read_only_policy)
        if session_result["status"] != "SESSION_RESTORED":
            print(json.dumps(session_result,indent=2))
            return 2
        from .scope_check import check_scope
        scope_result=check_scope(scenario.url,args.storage_state,scenario.read_only_policy,
                                json.loads(Path(args.fixture).read_text(encoding="utf-8-sig")),
                                args.identity_application_root,args.identity_verifier)
        if scope_result["status"] != "SCOPE_VERIFIED":
            print(json.dumps(scope_result,indent=2))
            return 2
        if args.software_version != scope_result['runtime']['assembly']:
            parser.error('Software version must match the independently verified running assembly')
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
        if scenario.write_policy:
            ACTION_SCHEMA=load_write_profile(scenario.write_policy['contract'],'lab_runner').LAB_ACTION_SCHEMA
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

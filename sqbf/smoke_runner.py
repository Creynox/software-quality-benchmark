"""Bounded screenshot-only read-only pilot; independent oracle stays in parent."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import uuid4

from .bounded import Budget, BudgetExceeded, ask_bounded, invoke_worker, model_spec, restore_model
from .models import Scenario, safe_action_log, validate_action
from .no_write_oracle import compare, snapshot
from .read_only import event_guard, validate_policy, ReadOnlyViolation, check_action, observation, request_allowed
from .reporting import Evidence, index_run


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


ACTION_SCHEMA = object_schema({
    "action": {"type": "string", "enum": ["click", "type", "key", "scroll", "wait", "done", "blocked"]},
    "x": {"type": ["number", "null"]}, "y": {"type": ["number", "null"]},
    "text": {"type": ["string", "null"]}, "key": {"type": ["string", "null"]},
    "amount": {"type": ["number", "null"]}, "seconds": {"type": ["number", "null"]},
    "reason": {"type": "string"},
})
REVIEW_SCHEMA = object_schema({
    "verdict": {"type": "string", "enum": ["PASS", "FAIL", "INCONCLUSIVE"]},
    "reason": {"type": "string"}, "findings": {"type": "array", "items": {"type": "string"}},
    "scores": object_schema({name: {"type": "integer"} for name in
                             ("findability", "clarity", "task_progress", "error_recovery")}),
})

INSTRUCTIONS = """You are a user testing a product. Use only the current screenshot, task,
and your previous visible actions. Return one JSON action with all fields; use
null for unused fields. Coordinates are screenshot pixels. No code, DOM, APIs,
DB, shell, tools, passwords, hidden URLs or browser shortcuts. This task permits
only the requested read-only navigation and search/filter operations. Never
create, edit, save, delete or change a record. If the task cannot be completed,
return blocked. Report done only after performing every requested step.
"""
REVIEW_INSTRUCTIONS = """Independently review this read-only user workflow using only the
selected screenshots (initial, search evidence when available, final) and visible
action history and timings. No DB facts are provided. Judge whether navigation,
search, empty-state interpretation and filter reset are visibly supported.
An executor done signal does not prove success. Distinguish UX difficulty from
tester failures. Give scores 0 through 5 for findability, clarity, task_progress,
error_recovery. If not evidenced, verdict INCONCLUSIVE and explain uncertainty.
No tools, URLs, code or hidden state. Return only the strict JSON object.
"""


def browser_pilot(payload):
    from playwright.sync_api import sync_playwright
    from .runner import apply_action

    scenario = Scenario(**payload["scenario"])
    executor, reviewer = restore_model(payload["executor"]), restore_model(payload["reviewer"])
    budget = Budget(payload["seconds"], scenario.max_model_calls)
    evidence = Evidence.__new__(Evidence)
    evidence.path, evidence.events, evidence.images = Path(payload["folder"]), [], []
    started = time.monotonic()
    actions, observations, usage, images = [], [], [], []
    status, review = "INCOMPLETE", None
    last = b""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not payload["headed"], timeout=min(15000, budget.remaining()*1000))
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 800},
                        storage_state=payload["storage_state"], accept_downloads=False, service_workers="block")
            context.add_init_script(event_guard(scenario.read_only_policy))
            parsed=urlsplit(scenario.url)
            origin=f"{parsed.scheme}://{parsed.netloc}"
            def route_request(route):
                if request_allowed(route.request.url, route.request.method, origin,scenario.read_only_policy):
                    route.continue_()
                else:
                    evidence.event("blocked_request", method=route.request.method,
                                   path=urlsplit(route.request.url).path)
                    route.abort()
            context.route("**/*", route_request)
            page = context.new_page()
            page.goto(scenario.url, wait_until="domcontentloaded", timeout=min(15000,budget.remaining()*1000))
            page.wait_for_timeout(1000)
            for turn in range(scenario.max_actions + 1):
                budget.remaining()
                page.set_default_timeout(min(3000,budget.remaining()*1000))
                if urlsplit(page.url).path not in scenario.read_only_policy["allowed_paths"]:
                    raise RuntimeError("Unapproved page/session")
                last = page.screenshot(animations="disabled", timeout=min(5000,budget.remaining()*1000))
                evidence.snapshot(last, f"step-{len(actions)}")
                images.append(last)
                seen = observation(page, scenario.read_only_policy)
                seen["screenshot"] = evidence.images[-1]["name"]
                observations.append(seen)
                if len(actions) >= scenario.max_actions:
                    status = "BLOCKED_ACTION_BUDGET"
                    break
                # Reserve one model call and up to 30 seconds for the reviewer.
                if budget.calls >= budget.limit - 1:
                    raise BudgetExceeded("Executor model call budget exhausted")
                result = ask_bounded(executor, INSTRUCTIONS + "\nTASK:\n" + scenario.task +
                         "\nPREVIOUS VISIBLE ACTIONS:\n" + json.dumps(actions,ensure_ascii=False), last, budget)
                usage.append({"stage": "executor", "usage": result.usage})
                action = {k: v for k, v in result.data.items() if v is not None}
                validate_action(action,1280,800)
                check_action(page,action,scenario.read_only_policy)
                evidence.event("agent_decision",**safe_action_log(action))
                if action["action"] in {"done","blocked"}:
                    status = action["action"].upper()
                    break
                apply_action(page,action)
                actions.append(action)
                page.wait_for_timeout(400)
            if last:
                evidence.snapshot(last,"final")
            # Independent reviewer sees no DOM, policy selectors, DB/Oracle or
            # technical error details. Typed text is the public task query only.
            selection = [images[0]] if images else []
            search_index = next((i for i,o in enumerate(observations) if o["query_visible"] and o["empty_visible"]), None)
            if search_index is not None:
                selection.append(images[search_index])
            if last:
                selection.append(last)
            if selection and budget.remaining() > 1:
                result = ask_bounded(reviewer, REVIEW_INSTRUCTIONS + "\n" + json.dumps({
                    "task": scenario.task, "actions": actions, "executor_observation": result.data.get("reason","")
                    if usage else "no completed observation", "wall_seconds": round(time.monotonic()-started,2)},
                    ensure_ascii=False),selection[:3],budget)
                review=result.data
                if any(not 0 <= score <= 5 for score in review["scores"].values()):
                    raise ValueError("Reviewer scores outside rubric")
                usage.append({"stage":"reviewer","usage":result.usage})
            return {"executor_status":status,"actions":len(actions),"model_calls":budget.calls,
                    "observations":observations,"review":review,"usage":usage,
                    "events":evidence.events,"images":evidence.images,
                    "wall_seconds":round(time.monotonic()-started,2)}
        except Exception as error:
            status=("BLOCKED_READ_ONLY" if isinstance(error,ReadOnlyViolation) else
                    "BLOCKED_TIMEOUT" if isinstance(error,BudgetExceeded) else "ERROR")
            evidence.event("stopped_fail_closed",error=type(error).__name__)
            return {"executor_status":status,"actions":len(actions),"model_calls":budget.calls,
                    "observations":observations,"review":review,"usage":usage,
                    "usage_unavailable_calls":budget.calls-len(usage),
                    "events":evidence.events,"images":evidence.images,
                    "wall_seconds":round(time.monotonic()-started,2)}
        finally:
            browser.close()


def run_smoke(scenario,executor,reviewer,output_root,storage_state,headed,fixture_path):
    validate_policy(scenario.read_only_policy)
    if (urlsplit(scenario.url).hostname!='127.0.0.1'
            or not 1 <= scenario.max_actions <= 10 or not 0 < scenario.max_minutes <= 5
            or not 2 <= scenario.max_model_calls <= 12 or not scenario.read_only_policy
            or not storage_state or reviewer is None):
        raise ValueError("Read-only pilot configuration violates the fixed acceptance contract")
    # Provider serialization validates type; no API/key fallback is possible.
    executor_spec,reviewer_spec=model_spec(executor),model_spec(reviewer)
    fixture=json.loads(Path(fixture_path).read_text(encoding="utf-8-sig"))
    if scenario.url!=fixture["target_url"] or scenario.fixture_id!=fixture["fixture_id"]:
        raise ValueError("Scenario and independently approved fixture target do not match")
    folder=output_root / str(uuid4())
    evidence=Evidence(folder)
    started=time.monotonic()
    manifest={"run_id":folder.name,"scenario_id":scenario.scenario_id,"scenario_version":scenario.scenario_version,
              "persona":scenario.persona,"fixture_id":scenario.fixture_id,"software_version":scenario.software_version,
              "executor_model":"chatgpt_plan:"+executor.model,"analyst_model":"chatgpt_plan:"+reviewer.model,
              "budget_actions":scenario.max_actions,"budget_minutes":scenario.max_minutes,
              "budget_model_calls":scenario.max_model_calls,"started_at":datetime.now(timezone.utc).isoformat(),
              "auth":"SEPARATE_CHATGPT_PLAN_OAUTH","tokens_persisted":False}
    result,oracle,review={}, {"status":"UNVERIFIED"},None
    after_attempted=False
    try:
        before=snapshot(fixture)
        (folder/"oracle-before.json").write_text(json.dumps(before,indent=2),encoding="utf-8")
        remaining=scenario.max_minutes*60-(time.monotonic()-started)-30
        result=invoke_worker("pilot",{"scenario":asdict(scenario),"executor":executor_spec,
                  "reviewer":reviewer_spec,"folder":str(folder.resolve()),"storage_state":str(Path(storage_state).resolve()),
                  "headed":headed,"seconds":remaining},remaining)
        evidence.events=result["events"]
        evidence.images=result["images"]
        review=result["review"]
        after_attempted=True
        after=snapshot(fixture)
        (folder/"oracle-after.json").write_text(json.dumps(after,indent=2),encoding="utf-8")
        oracle=compare(before,after,result["observations"],result["executor_status"]=="DONE")
        if time.monotonic()-started >= scenario.max_minutes*60:
            raise BudgetExceeded("Pilot total deadline exceeded")
    except Exception as error:
        # Recover locally flushed evidence when the worker was terminated.
        for name,attribute in [("events.json","events"),("evidence.json","images")]:
            path=folder/name
            if path.exists():
                setattr(evidence,attribute,json.loads(path.read_text(encoding="utf-8")))
        evidence.event("stopped_fail_closed",error=type(error).__name__)
        result["executor_status"]="BLOCKED_TIMEOUT" if isinstance(error,BudgetExceeded) else "ERROR"
        # An independent after snapshot is mandatory even for aborted runs.
        if 'before' in locals() and not after_attempted:
            try:
                after=snapshot(fixture)
                (folder/"oracle-after.json").write_text(json.dumps(after,indent=2),encoding="utf-8")
                oracle=compare(before,after,result.get("observations",[]),False)
            except Exception:
                oracle={"status":"UNVERIFIED","database_unchanged":False}
    valid_images=len(evidence.images)>=2
    for image in evidence.images:
        path=folder/image["name"]
        valid_images=valid_images and path.parent==folder and path.is_file()
        if valid_images:
            valid_images=hashlib.sha256(path.read_bytes()).hexdigest()==image["sha256"]
    technical="PASS" if result.get("executor_status")=="DONE" and review and valid_images else "FAIL"
    verdict="GO" if technical=="PASS" and oracle["status"]=="PASS" else "NO-GO"
    manifest.update({k:v for k,v in result.items() if k not in {"events","images","review"}})
    manifest.update(executor_status=result.get("executor_status","ERROR"),actions=result.get("actions",0),
                    technical_status=technical,functional_status=oracle["status"],oracle=oracle,
                    wall_seconds=round(time.monotonic()-started,2),completion_status=verdict,
                    finished_at=datetime.now(timezone.utc).isoformat())
    (folder/"oracle.json").write_text(json.dumps(oracle,indent=2),encoding="utf-8")
    (folder/"scores.json").write_text(json.dumps((review or {}).get("scores",{}),indent=2),encoding="utf-8")
    (folder/"findings.json").write_text(json.dumps((review or {}).get("findings",[]),ensure_ascii=False,indent=2),encoding="utf-8")
    evidence.finish(manifest,review,verdict)
    index_run(output_root,folder)
    return folder

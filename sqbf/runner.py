"""Guarded screenshot -> action -> screenshot black-box loop."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from .models import Scenario, assess_run, safe_action_log, validate_action
from .providers import VisionModel
from .reporting import Evidence


EXECUTOR_INSTRUCTIONS = """You are testing a software product as a real user.
Use ONLY the displayed screenshot and your mouse/keyboard actions.
Never ask for code, DB, APIs, DOM, DevTools, browser internals or secrets.
Do not use browser navigation bars, shortcuts to developer tools, or hidden URLs.
Execute the user's task on the visible interface. Do not claim completion before
reopening the record and checking the requested fields and links.
Output ONLY one JSON object per turn with:
{"action":"click","x":10,"y":20,"reason":"..."}
or {"action":"type","text":"...","reason":"..."}
or {"action":"key","key":"Enter","reason":"..."}
or {"action":"scroll","amount":400,"reason":"..."}
or {"action":"wait","seconds":1,"reason":"..."}
or {"action":"done","reason":"..."}
or {"action":"blocked","reason":"..."}.
Coordinates refer to screenshot pixels. Never type passwords/tokens.
Do not invent test outcomes. Prefer the shortest safe UI workflow.
"""

ANALYST_INSTRUCTIONS = """Review an external black-box UI test without re-running it.
Use only the supplied screenshot and summarized event evidence. Evaluate
whether the requested end state is visibly supported. Never invent application
database facts or hidden verification. A DONE agent signal is not proof.
Output ONLY a JSON object:
{"verdict":"PASS|FAIL|INCONCLUSIVE","reason":"specific evidence-based rationale",
"findings":["..."]}.
PASS only if the screenshot actually shows the created item AND all required
associations after reopening. Otherwise INCONCLUSIVE unless clear failure.
Separate agent difficulty from product UX defects. No automatic GitHub issues.
"""


def host_allowed(url: str, hosts: list[str]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in hosts


def apply_action(page, action: dict) -> None:
    operation = action["action"]
    if operation == "click":
        page.mouse.click(action["x"], action["y"])
    elif operation == "type":
        page.keyboard.type(action["text"], delay=15)
    elif operation == "key":
        page.keyboard.press(action["key"])
    elif operation == "scroll":
        page.mouse.wheel(0, action.get("amount", 400))
    elif operation == "wait":
        page.wait_for_timeout(round(float(action.get("seconds", 1)) * 1000))
    else:
        raise ValueError("Action is not a UI action")


def run(
    scenario: Scenario, executor: VisionModel, analyst: VisionModel | None,
    output_root: Path, storage_state: str | None = None, headed: bool = True,
    ask_extension=None,
    fixture_path=None,
) -> Path:
    """Execute browser UI only. Fixture preparation is a separate prerequisite."""
    if scenario.read_only_policy:
        if ask_extension or fixture_path is None:
            raise ValueError("Read-only pilot requires its Oracle fixture and permits no budget extensions")
        from .smoke_runner import run_smoke
        return run_smoke(scenario,executor,analyst,output_root,storage_state,headed,fixture_path)
    from playwright.sync_api import sync_playwright

    run_id = str(uuid4())
    evidence = Evidence(output_root / run_id)
    started = time.monotonic()
    allowed_seconds = scenario.max_minutes * 60
    allowed_actions = scenario.max_actions
    count, errors = 0, 0
    model_wait_seconds = 0.0
    executor_status = "INCOMPLETE"
    usage: list[dict] = []
    review: dict | None = None
    last_png = b""
    viewport = {"width": 1280, "height": 800}

    manifest = {
        "run_id": run_id, "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.scenario_version,
        "persona": scenario.persona, "fixture_id": scenario.fixture_id,
        "software_version": scenario.software_version,
        "url_host": urlparse(scenario.url).hostname,
        "executor_model": f"{executor.provider}:{executor.model}",
        "analyst_model": f"{analyst.provider}:{analyst.model}" if analyst else None,
        "budget_actions": allowed_actions, "budget_minutes": scenario.max_minutes,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not headed)
            context = browser.new_context(
                viewport=viewport, storage_state=storage_state or None,
                accept_downloads=False, service_workers="block",
            )

            def limit_requests(route):
                if host_allowed(route.request.url, scenario.allowed_hosts):
                    route.continue_()
                else:
                    route.abort()

            context.route("**/*", limit_requests)
            page = context.new_page()
            page.goto(scenario.url, wait_until="domcontentloaded", timeout=30_000)
            evidence.event("started", scenario=scenario.scenario_id)
            try:
                while True:
                    elapsed = time.monotonic() - started
                    if count >= allowed_actions or elapsed >= allowed_seconds:
                        executor_status = "PAUSED_BUDGET"
                        evidence.event("budget_pause", actions=count, elapsed_seconds=round(elapsed, 2))
                        if not ask_extension:
                            break
                        extension = ask_extension()
                        if not extension:
                            break
                        more_minutes, more_actions = extension
                        if more_minutes <= 0 or more_actions <= 0:
                            break
                        allowed_seconds += more_minutes * 60
                        allowed_actions += more_actions
                        evidence.event("budget_extended", minutes=more_minutes, actions=more_actions)
                    if not host_allowed(page.url, scenario.allowed_hosts):
                        executor_status = "BLOCKED_NAVIGATION"
                        evidence.event("blocked_external_navigation")
                        break
                    last_png = page.screenshot(type="png", animations="disabled", timeout=15_000)
                    if count == 0 or count % 5 == 0:
                        evidence.snapshot(last_png, f"step-{count}")
                    elapsed = time.monotonic() - started
                    if elapsed >= allowed_seconds:
                        executor_status = "PAUSED_BUDGET"
                        evidence.event(
                            "budget_pause", actions=count,
                            elapsed_seconds=round(elapsed, 2),
                            reason="time_limit_during_screenshot",
                        )
                        break
                    prompt = (
                        EXECUTOR_INSTRUCTIONS + "\nUSER TASK:\n" + scenario.task +
                        "\nEXPECTED VISIBLE END STATE:\n" +
                        "\n".join(scenario.expected) +
                        f"\nCompleted UI actions: {count}. Reply with just one JSON action."
                    )
                    model_started = time.monotonic()
                    try:
                        result = executor.ask(prompt, last_png)
                    finally:
                        model_wait_seconds += time.monotonic() - model_started
                    usage.append({"stage": "executor", "usage": result.usage})
                    # A slow provider response must not authorize one more UI
                    # action after the wall-clock budget has expired.
                    elapsed = time.monotonic() - started
                    if elapsed >= allowed_seconds:
                        executor_status = "PAUSED_BUDGET"
                        evidence.event(
                            "budget_pause", actions=count,
                            elapsed_seconds=round(elapsed, 2),
                            reason="time_limit_during_model_wait",
                        )
                        break
                    try:
                        action = validate_action(result.data, viewport["width"], viewport["height"])
                    except ValueError as exc:
                        errors += 1
                        evidence.event("invalid_agent_action", error=str(exc))
                        if errors >= 3:
                            executor_status = "BLOCKED_INVALID_ACTION"
                            break
                        continue
                    errors = 0
                    evidence.event("agent_decision", **safe_action_log(action))
                    if action["action"] == "done":
                        executor_status = "DONE"
                        evidence.snapshot(last_png, "done")
                        break
                    if action["action"] == "blocked":
                        executor_status = "BLOCKED"
                        evidence.snapshot(last_png, "blocked")
                        break
                    apply_action(page, action)
                    count += 1
                    page.wait_for_timeout(250)
            except Exception as exc:
                executor_status = "ERROR"
                evidence.event("runner_error", error=type(exc).__name__)
            finally:
                try:
                    last_png = page.screenshot(type="png", animations="disabled", timeout=10_000)
                    evidence.snapshot(last_png, "final")
                except Exception:
                    evidence.event("final_screenshot_unavailable")
                browser.close()
    except Exception as exc:
        executor_status = "ERROR"
        evidence.event("startup_error", error=type(exc).__name__)

    if analyst and executor_status == "DONE" and last_png:
        try:
            summary = {
                "scenario_id": scenario.scenario_id,
                "task": scenario.task, "expected": scenario.expected,
                "executor_status": executor_status, "actions": count,
                "events": evidence.events[-40:],
            }
            model_started = time.monotonic()
            try:
                result = analyst.ask(ANALYST_INSTRUCTIONS + "\nRUN:\n" + json.dumps(
                    summary, ensure_ascii=False
                ), last_png, max_tokens=850)
            finally:
                model_wait_seconds += time.monotonic() - model_started
            usage.append({"stage": "analyst", "usage": result.usage})
            review = result.data
            if not isinstance(review.get("findings"), list):
                review["findings"] = []
        except Exception as exc:
            evidence.event("analyst_error", error=type(exc).__name__)
    elapsed = time.monotonic() - started
    manifest.update({
        "executor_status": executor_status, "actions": count,
        "wall_seconds": round(elapsed, 2),
        "model_wait_seconds": round(model_wait_seconds, 2),
        "active_seconds_excluding_model_wait": round(max(0.0, elapsed - model_wait_seconds), 2),
        "budget_actions": allowed_actions,
        "budget_minutes": round(allowed_seconds / 60, 2),
        "usage": usage, "finished_at": datetime.now(timezone.utc).isoformat(),
    })
    verdict = assess_run(executor_status, review, len(evidence.images))
    manifest["technical_status"] = (
        "PASS" if evidence.images and executor_status != "ERROR" else "FAIL"
    )
    manifest["functional_status"] = "UNVERIFIED"
    evidence.finish(manifest, review, verdict)
    return evidence.path

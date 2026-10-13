"""Read-only local readiness checks; not a functional BLE or model test."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


def check_health(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        return {"status": "BLOCKED", "reason": "doctor only probes local HTTP loopback"}
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return {"status": "BLOCKED", "reason": "URL must not contain credentials or query parameters"}
    try:
        port = parsed.port
    except ValueError:
        return {"status": "BLOCKED", "reason": "Invalid loopback URL port"}
    origin = f"http://{parsed.hostname}:{port}" if port else f"http://{parsed.hostname}"
    try:
        with urlopen(origin + "/health/ready", timeout=4) as response:
            payload = response.read(2048).decode("utf-8", errors="replace")
            return {"status": "READY" if response.status == 200 and "Healthy" in payload else "BLOCKED",
                    "http_status": response.status}
    except Exception as exc:
        return {"status": "BLOCKED", "reason": type(exc).__name__}


def check_fixture(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "BLOCKED", "reason": type(exc).__name__}
    # Metadata assertions are NOT evidence that a real isolated fixture exists.
    declared = data.get("status")
    if declared in {"READY", "READY_FOR_UI_PROCESS_PILOT"}:
        status = "DECLARED_READY"
    elif declared == "PROVISIONED_UI_VERIFIED_PRODUCT_NOT_CREATED":
        status = "PROVISIONED_SCENARIO_BLOCKED"
    else:
        status = "BLOCKED"
    return {"status": status,
            "fixture_id": data.get("fixture_id"),
            "fixture_status": data.get("status"),
            "requires_external_isolation_verification": True}


def check_chromium() -> dict:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_content("<main>local runner smoke</main>")
                png = page.screenshot(type="png")
                return {"status": "READY" if png.startswith(b"\x89PNG\r\n\x1a\n") else "BLOCKED"}
            finally:
                browser.close()
    except Exception as exc:
        return {"status": "BLOCKED", "reason": type(exc).__name__}


def readiness(url: str, fixture: Path, storage_state: Path) -> dict:
    health = check_health(url)
    browser = check_chromium()
    auth = {"status": "PRESENT_UNVERIFIED" if storage_state.is_file() else "MISSING"}
    fixture_result = check_fixture(fixture)
    # CLI detection is NOT proof of an active subscription or proper sandbox.
    clients = {
        "codex": {"installed": bool(shutil.which("codex")), "authenticated": "NOT_VERIFIED"},
        "claude": {"installed": bool(shutil.which("claude")), "authenticated": "NOT_VERIFIED"},
    }
    basic_ready = health["status"] == "READY" and browser["status"] == "READY"
    pending = []
    if not basic_ready:
        pending.append("Local BLE health and Chromium must both be READY")
    if auth["status"] != "PRESENT_UNVERIFIED":
        pending.append("Create a local benchmark-role Playwright session")
    if fixture_result["status"] == "BLOCKED":
        pending.append("Provision and independently verify isolated BLE fixture")
    elif fixture_result["status"] == "PROVISIONED_SCENARIO_BLOCKED":
        pending.append("Verify sanctioned STS product references and persistable UI workflow")
    pending.append("Verify subscription-based vision agent and tool isolation (#14)")
    pending.append("Run the independent before/after persistence oracle from the dedicated read-only environment")
    return {
        "status": "TECHNICAL_SMOKE_READY" if basic_ready else "BLOCKED",
        "live_ai_benchmark_ready": False,
        "python": sys.version.split()[0], "ble_health": health,
        "chromium": browser, "session": auth, "fixture": fixture_result,
        "subscription_clients": clients,
        "extra_api_billing_allowed": False,
        "pending": pending,
    }

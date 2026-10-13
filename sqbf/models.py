"""Configuration, guarded actions, and deterministic run utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_ACTIONS = {"click", "type", "key", "scroll", "wait", "done", "blocked"}
SAFE_KEYS = {
    "Enter", "Tab", "Shift+Tab", "Escape", "Backspace", "Delete",
    "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End",
    "ControlOrMeta+A", "Space",
}
SEARCH_KEYS = ("ControlOrMeta+A", "Backspace", "Delete", "Enter")


class ActionValidationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass
class Scenario:
    scenario_id: str
    task: str
    url: str
    persona: str
    fixture_id: str
    expected: list[str]
    max_minutes: int = 25
    max_actions: int = 150
    allowed_hosts: list[str] = field(default_factory=list)
    software_version: str = "unknown"
    scenario_version: str = "1"
    read_only_policy: dict | None = None
    max_model_calls: int = 12
    write_policy: dict | None = None

    @classmethod
    def load(cls, path: str | Path, base_url: str | None = None) -> "Scenario":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if base_url:
            data["url"] = base_url
            # An explicit local target overrides the illustrative sample host.
            data["allowed_hosts"] = [urlparse(base_url).hostname]
        for key in ("scenario_id", "task", "url", "persona", "fixture_id", "expected"):
            if not data.get(key):
                raise ValueError(f"Missing scenario field: {key}")
        # A copied blank project must not accidentally run merely because
        # an operator supplied a real URL before configuring the scenario.
        for key in ("task", "persona", "fixture_id", "software_version"):
            value = data.get(key, "")
            if isinstance(value, str) and value.startswith("CONFIGURE_"):
                raise ValueError(f"Unconfigured scenario placeholder: {key}")
        if any(isinstance(item, str) and item.startswith("CONFIGURE_") for item in data["expected"]):
            raise ValueError("Unconfigured scenario placeholder: expected")
        parsed = urlparse(data["url"])
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Scenario URL must be http(s) with a hostname")
        if not isinstance(data["expected"], list):
            raise ValueError("expected must be a list")
        if int(data.get("max_minutes", 25)) < 1 or int(data.get("max_actions", 150)) < 1:
            raise ValueError("Budgets must be positive")
        if "allowed_hosts" not in data or not data["allowed_hosts"]:
            data["allowed_hosts"] = [parsed.hostname]
        hosts = [str(host).lower() for host in data["allowed_hosts"]]
        if parsed.hostname.lower() not in hosts:
            raise ValueError("Starting host must be allowlisted")
        data["allowed_hosts"] = hosts
        return cls(**data)


def parse_json_object(raw: str) -> dict:
    """Require a JSON object from the model (optionally fenced)."""
    text = raw.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response must be a single JSON object") from exc
    if not isinstance(obj, dict):
        raise ValueError("Model response must be a JSON object")
    return obj


def validate_action(data: dict, width: int, height: int) -> dict:
    action = data.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ActionValidationError("ACTION_NOT_ALLOWED")
    if action == "click":
        x, y = data.get("x"), data.get("y")
        if not isinstance(x, (float, int)) or not isinstance(y, (float, int)):
            raise ActionValidationError("CLICK_COORDINATES_INVALID")
        if not (0 <= x < width and 0 <= y < height):
            raise ActionValidationError("CLICK_OUTSIDE_VIEWPORT")
    if action == "type":
        value = data.get("text")
        if not isinstance(value, str) or len(value) > 500:
            raise ActionValidationError("TYPE_TEXT_INVALID")
    if action == "key" and data.get("key") not in SAFE_KEYS:
        raise ActionValidationError("KEY_NOT_ALLOWED")
    if action == "scroll":
        if 'x' in data or 'y' in data:
            x,y=data.get('x'),data.get('y')
            if not all(type(v) in (int,float) for v in (x,y)) or not (0<=x<width and 0<=y<height):
                raise ActionValidationError('SCROLL_COORDINATES_INVALID')
        amount = data.get("amount", 400)
        if not isinstance(amount, (float, int)) or abs(amount) > 1400:
            raise ActionValidationError("SCROLL_OUT_OF_BOUNDS")
    if action == "wait":
        seconds = data.get("seconds", 1)
        if not isinstance(seconds, (int, float)) or not 0 <= seconds <= 2:
            raise ActionValidationError("WAIT_OUT_OF_BOUNDS")
    return data


def safe_action_log(action: dict) -> dict:
    """Never retain typed text in an event log."""
    result = {k: v for k, v in action.items() if k != "text"}
    if action.get("action") == "type":
        result["typed_chars"] = len(action.get("text", ""))
    return result


def assess_run(executor_status: str, review: dict | None, evidence_count: int) -> str:
    """Keep visual review separate from a functional PASS requiring an Oracle."""
    if executor_status != "DONE":
        return "INCONCLUSIVE" if executor_status.startswith("PAUSED") else "INCOMPLETE"
    if evidence_count < 2 or not review:
        return "INCONCLUSIVE"
    verdict = review.get("verdict", "INCONCLUSIVE")
    if verdict == "PASS":
        return "VISUAL_PASS_PENDING_ORACLE"
    return "VISUAL_FAIL" if verdict == "FAIL" else "INCONCLUSIVE"

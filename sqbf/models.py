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

    @classmethod
    def load(cls, path: str | Path, base_url: str | None = None) -> "Scenario":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if base_url:
            data["url"] = base_url
        for key in ("scenario_id", "task", "url", "persona", "fixture_id", "expected"):
            if not data.get(key):
                raise ValueError(f"Missing scenario field: {key}")
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
        raise ValueError(f"Disallowed action: {action!r}")
    if action == "click":
        x, y = data.get("x"), data.get("y")
        if not isinstance(x, (float, int)) or not isinstance(y, (float, int)):
            raise ValueError("click requires numeric x/y")
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError("click coordinates outside screenshot")
    if action == "type":
        value = data.get("text")
        if not isinstance(value, str) or len(value) > 500:
            raise ValueError("type requires <=500 characters")
    if action == "key" and data.get("key") not in SAFE_KEYS:
        raise ValueError("Unsupported keyboard shortcut")
    if action == "scroll":
        amount = data.get("amount", 400)
        if not isinstance(amount, (float, int)) or abs(amount) > 1400:
            raise ValueError("scroll amount out of bounds")
    if action == "wait":
        seconds = data.get("seconds", 1)
        if not isinstance(seconds, (int, float)) or not 0 <= seconds <= 2:
            raise ValueError("wait must be between 0 and 2 seconds")
    return data


def safe_action_log(action: dict) -> dict:
    """Never retain typed text in an event log."""
    result = {k: v for k, v in action.items() if k != "text"}
    if action.get("action") == "type":
        result["typed_chars"] = len(action.get("text", ""))
    return result


def assess_run(executor_status: str, review: dict | None, evidence_count: int) -> str:
    """Never assert a PASS based on the executor self-report alone."""
    if executor_status != "DONE":
        return "INCONCLUSIVE" if executor_status.startswith("PAUSED") else "INCOMPLETE"
    if evidence_count < 2 or not review:
        return "INCONCLUSIVE"
    verdict = review.get("verdict", "INCONCLUSIVE")
    return verdict if verdict in {"PASS", "FAIL"} else "INCONCLUSIVE"

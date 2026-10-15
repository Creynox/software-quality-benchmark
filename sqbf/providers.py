"""Single-turn screenshot vision adapters; model IDs come from config."""

from __future__ import annotations

import base64
import copy
import json
import math
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .models import parse_json_object


@dataclass
class ModelResponse:
    data: dict
    usage: dict


CHATGPT_PLAN_SCOPE = "chatgpt.tokens.use.direct"


def _strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("Non-finite JSON number")

    def number(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError("Non-finite JSON number")
        return value

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=number)


def _check_output_item(item: dict) -> None:
    if not isinstance(item, dict):
        raise RuntimeError("Malformed ChatGPT plan output item")
    if item.get("type") not in {"message", "reasoning"}:
        raise RuntimeError("ChatGPT plan response attempted a tool call or unsupported output")
    if item.get("type") == "message":
        if item.get("role") != "assistant":
            raise RuntimeError("Unexpected ChatGPT plan message role")
        content = item.get("content", [])
        if not isinstance(content, list) or any(
            not isinstance(block, dict) or block.get("type") != "output_text"
            for block in content
        ):
            raise RuntimeError("ChatGPT plan response contained non-text output or refusal")


@dataclass(frozen=True)
class ChatGPTPlanCredential:
    """Credential supplied by a separately authorized trusted controller.

    This class deliberately does not implement OAuth or read Codex CLI state.
    The caller must obtain and validate the consented ChatGPT-plan scopes via
    Sign in with ChatGPT before constructing it.
    """

    access_token: str = field(repr=False)
    granted_scopes: frozenset[str]

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("A ChatGPT plan access token is required")
        if CHATGPT_PLAN_SCOPE not in self.granted_scopes:
            raise ValueError("ChatGPT plan usage was not authorized")


def _validate_schema_value(value, schema: dict, path: str = "$", *, strict: bool = True) -> None:
    """Validate the JSON Schema subset used by strict SQBF response schemas."""
    expected = schema.get("type")
    expected_types = expected if isinstance(expected, list) else [expected]
    if expected and not any(
        (kind == "null" and value is None)
        or (kind == "object" and isinstance(value, dict))
        or (kind == "array" and isinstance(value, list))
        or (kind == "string" and isinstance(value, str))
        or (kind == "boolean" and isinstance(value, bool))
        or (kind == "integer" and isinstance(value, int) and not isinstance(value, bool))
        or (kind == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
        for kind in expected_types
    ):
        raise ValueError(f"Structured response has invalid type at {path}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"Structured response has invalid value at {path}")
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if any(key not in value for key in required):
            raise ValueError(f"Structured response is missing a required field at {path}")
        if strict and schema.get("additionalProperties") is not False:
            raise ValueError("SQBF strict response schemas must forbid additional properties")
        if strict and any(key not in properties for key in value):
            raise ValueError(f"Structured response has an unexpected field at {path}")
        for key, child in properties.items():
            if key in value:
                _validate_schema_value(value[key], child, f"{path}.{key}", strict=strict)
    if schema.get("type") == "array" and "items" in schema:
        for index, item in enumerate(value):
            _validate_schema_value(item, schema["items"], f"{path}[{index}]", strict=strict)


def _validate_strict_schema_contract(schema: dict) -> None:
    """Reject schemas that do not meet the strict structured-output contract."""
    if not isinstance(schema, dict):
        raise ValueError("Response schema nodes must be objects")
    kind = schema.get("type")
    allowed = {"type", "enum", "description", "title"}
    if kind == "object":
        allowed |= {"properties", "required", "additionalProperties"}
    elif kind == "array":
        allowed.add("items")
    if set(schema) - allowed:
        raise ValueError("Unsupported response schema keyword; constraints cannot be ignored")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        raise ValueError("Response schema enum must be a nonempty list")
    if isinstance(kind, list):
        if not kind or not all(
            isinstance(item, str) and item in ("string", "number", "integer", "boolean", "null")
            for item in kind
        ):
            raise ValueError("Unsupported strict response schema type")
        return
    if kind == "object":
        properties = schema.get("properties")
        required = schema.get("required")
        if not isinstance(properties, dict) or schema.get("additionalProperties") is not False:
            raise ValueError("Strict object schemas require properties and additionalProperties=false")
        if (not isinstance(required, list) or not all(isinstance(k, str) for k in required)
                or len(required) != len(set(required)) or set(required) != set(properties)):
            raise ValueError("Strict object schemas must require every property")
        for child in properties.values():
            _validate_strict_schema_contract(child)
    elif kind == "array":
        if not isinstance(schema.get("items"), dict):
            raise ValueError("Strict array schemas require an item schema")
        _validate_strict_schema_contract(schema["items"])
    elif not isinstance(kind, str) or kind not in ("string", "number", "integer", "boolean", "null"):
        raise ValueError("Unsupported strict response schema type")


class ChatGPTPlanModel:
    """Tool-free Responses API adapter for an explicitly authorized plan token.

    It has the same ``ask`` interface as VisionModel, but sends no tools and
    accepts a strict JSON Schema for local validation. OAuth lifecycle and
    secure credential storage belong to a separate trusted controller.
    """

    provider = "chatgpt_plan"

    def __init__(
        self,
        model: str,
        credential: ChatGPTPlanCredential,
        response_schema: dict,
        *,
        schema_name: str = "sqbf_response",
        timeout: int = 90,
        max_response_chars: int = 8_000,
    ):
        if not model or model == "SET_MODEL_ID":
            raise ValueError("Set an account-authorized model ID")
        if not isinstance(response_schema, dict) or response_schema.get("type") != "object":
            raise ValueError("A strict object response schema is required")
        _validate_strict_schema_contract(response_schema)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", schema_name):
            raise ValueError("Schema name must be 1 to 64 letters, digits, underscores or hyphens")
        if timeout <= 0 or max_response_chars <= 0:
            raise ValueError("Request timeout and response limit must be positive")
        self.model = model
        self.credential = credential
        self.response_schema = copy.deepcopy(response_schema)
        self.schema_name = schema_name
        self.timeout = timeout
        self.max_response_chars = max_response_chars

    def ask(self, prompt: str, screenshot_png: bytes, *, max_tokens: int = 450) -> ModelResponse:
        if max_tokens <= 0:
            raise ValueError("Requested output limit must be positive")
        # ChatGPT plan usage currently rejects `max_output_tokens`; keep the
        # existing adapter signature, omit that request field, and cap the
        # accepted streamed result locally instead.
        images = screenshot_png if isinstance(screenshot_png, list) else [screenshot_png]
        if not 1 <= len(images) <= 3 or any(not isinstance(png, bytes) or len(png) > 2_000_000 for png in images):
            raise ValueError("Provide one to three bounded screenshot byte strings")
        payload = {
            "model": self.model,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}] + [
                {"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(png).decode("ascii")}
                for png in images
            ]}],
            "text": {"format": {
                "type": "json_schema", "name": self.schema_name,
                "strict": True, "schema": self.response_schema,
            }},
            "store": False,
            "stream": True,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.credential.access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        chunks: list[str] = []
        response_chars = 0
        usage: dict = {}
        completed = False
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    content = line[5:].strip()
                    if content == "[DONE]":
                        break
                    try:
                        event = _strict_json(content)
                    except (ValueError, TypeError):
                        raise RuntimeError("Malformed ChatGPT plan stream JSON") from None
                    if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                        raise RuntimeError("Malformed ChatGPT plan stream event")
                    event_type = event.get("type", "")
                    tool_markers = (
                        "function_call", "computer_call", "web_search_call",
                        "code_interpreter", "mcp_", "custom_tool_call", "shell_call",
                        "file_search_call", "image_generation_call", "tool_search_call",
                    )
                    if any(marker in event_type for marker in tool_markers):
                        raise RuntimeError("ChatGPT plan response attempted a tool call")
                    if event_type in {"response.output_item.added", "response.output_item.done"}:
                        _check_output_item(event.get("item"))
                    if "refusal" in event_type or event_type == "error":
                        raise RuntimeError("ChatGPT plan response refused or reported an error")
                    if event_type == "response.output_text.delta":
                        delta = event.get("delta", "")
                        if not isinstance(delta, str) or response_chars + len(delta) > self.max_response_chars:
                            raise RuntimeError("ChatGPT plan response exceeded the local size limit")
                        chunks.append(delta)
                        response_chars += len(delta)
                    elif event_type == "response.failed":
                        code = (event.get("response", {}).get("error") or {}).get("code", "")
                        safe_codes = {
                            "subscription_sharing_usage_limit_exceeded",
                            "subscription_sharing_usage_unavailable",
                            "invalid_request_error", "server_error", "rate_limit_exceeded",
                            "model_not_found", "insufficient_quota", "unsupported_parameter",
                        }
                        if not isinstance(code, str) or code not in safe_codes:
                            code = "unknown_error"
                        raise RuntimeError(f"ChatGPT plan request failed ({code})")
                    elif event_type == "response.incomplete":
                        raise RuntimeError("ChatGPT plan response was incomplete")
                    elif event_type == "response.completed":
                        result = event.get("response")
                        if not isinstance(result, dict):
                            raise RuntimeError("Malformed ChatGPT plan completed response")
                        for item in result.get("output", []):
                            _check_output_item(item)
                        usage = result.get("usage") or {}
                        completed = True
                        break
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"ChatGPT plan request failed with HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise RuntimeError("ChatGPT plan request failed due to a network or timeout error") from None
        if not completed:
            raise RuntimeError("ChatGPT plan stream ended without response.completed")
        try:
            data = _strict_json("".join(chunks))
        except (ValueError, TypeError):
            raise ValueError("ChatGPT plan response was not valid JSON") from None
        if not isinstance(data, dict):
            raise ValueError("ChatGPT plan response must be a JSON object")
        _validate_schema_value(data, self.response_schema)
        return ModelResponse(data=data, usage=usage)


class VisionModel:
    """No browser, database or repository tools are available to a model."""

    def __init__(self, provider: str, model: str, *, timeout: int = 90):
        if provider not in {"openai", "anthropic"}:
            raise ValueError("Provider must be 'openai' or 'anthropic'")
        if not model or model == "SET_MODEL_ID":
            raise ValueError("Set an actual provider model ID")
        self.provider, self.model, self.timeout = provider, model, timeout

    def ask(self, prompt: str, screenshot_png: bytes, *, max_tokens: int = 450) -> ModelResponse:
        image = base64.b64encode(screenshot_png).decode("ascii")
        if self.provider == "openai":
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY is required")
            # Use Responses API: it accepts image input and is the current
            # interface for the configured GPT-6 model family.
            url = "https://api.openai.com/v1/responses"
            headers = {"Authorization": f"Bearer {key}"}
            payload = {
                "model": self.model, "max_output_tokens": max_tokens,
                "input": [{"role": "user", "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": "data:image/png;base64," + image},
                ]}],
            }
        else:
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError("ANTHROPIC_API_KEY is required")
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
            payload = {
                "model": self.model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/png", "data": image
                    }},
                ]}],
            }
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{self.provider} request failed with HTTP {exc.code}") from exc
        if self.provider == "openai":
            text = result.get("output_text")
            if text is None:
                text = "\n".join(
                    block["text"]
                    for item in result.get("output", [])
                    for block in item.get("content", [])
                    if block.get("type") == "output_text"
                )
        else:
            text = "\n".join(block["text"] for block in result["content"] if block["type"] == "text")
        return ModelResponse(data=parse_json_object(text), usage=result.get("usage") or {})


_PROVIDER_ERROR_CODES = (
    (RuntimeError, r"ChatGPT plan request failed with HTTP (\d{3})", lambda m: "PROVIDER_HTTP_" + m.group(1)),
    (RuntimeError, r"ChatGPT plan request failed \(([a-z_]{1,40})\)", lambda m: "PROVIDER_FAILED_" + m.group(1)),
    (RuntimeError, r"ChatGPT plan request failed due to a network or timeout error", lambda m: "PROVIDER_NETWORK_OR_TIMEOUT"),
    (RuntimeError, r"ChatGPT plan response refused or reported an error", lambda m: "PROVIDER_REFUSAL_OR_ERROR_EVENT"),
    (RuntimeError, r"ChatGPT plan response was incomplete", lambda m: "PROVIDER_INCOMPLETE"),
    (RuntimeError, r"ChatGPT plan response exceeded the local size limit", lambda m: "PROVIDER_RESPONSE_TOO_LARGE"),
    (RuntimeError, r"ChatGPT plan stream ended without response\.completed", lambda m: "PROVIDER_STREAM_INCOMPLETE"),
    (RuntimeError, r"Malformed ChatGPT plan .*", lambda m: "PROVIDER_STREAM_MALFORMED"),
    (RuntimeError, r"ChatGPT plan response attempted a tool call", lambda m: "PROVIDER_TOOL_CALL"),
    (ValueError, r"ChatGPT plan response was not valid JSON", lambda m: "RESPONSE_NOT_JSON"),
    (ValueError, r"ChatGPT plan response must be a JSON object", lambda m: "RESPONSE_NOT_OBJECT"),
    (ValueError, r"Structured response .*", lambda m: "RESPONSE_SCHEMA_MISMATCH"),
)


def safe_error_code(error: BaseException):
    """Map this module's own constant failure messages to a fixed diagnostic code.

    Anything else, including foreign exceptions whose text could carry payload or token
    fragments, returns None so the isolated worker stays silent as before.
    """
    for kind, pattern, code in _PROVIDER_ERROR_CODES:
        if type(error) is kind:
            match = re.fullmatch(pattern, str(error))
            if match:
                return code(match)
    return None

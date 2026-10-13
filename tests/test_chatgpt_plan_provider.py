"""Offline-only tests for the tool-free ChatGPT-plan Responses adapter."""

import base64
import json
import os
import unittest
from unittest.mock import patch

from sqbf.providers import CHATGPT_PLAN_SCOPE, ChatGPTPlanCredential, ChatGPTPlanModel


ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["done", "blocked"]},
        "reason": {"type": "string"},
    },
    "required": ["action", "reason"],
    "additionalProperties": False,
}


def sse(*events):
    return b"".join(b"data: " + json.dumps(event).encode() + b"\n\n" for event in events)


class FakeStream:
    def __init__(self, body):
        self.lines = iter(body.splitlines(keepends=True))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.lines)


def provider():
    credential = ChatGPTPlanCredential(
        "synthetic-plan-token", frozenset({"openid", CHATGPT_PLAN_SCOPE})
    )
    return ChatGPTPlanModel("account-model-id", credential, ACTION_SCHEMA)


class ChatGPTPlanProviderTests(unittest.TestCase):
    def test_sends_image_json_schema_and_no_tools_then_validates_response(self):
        output = json.dumps({"action": "done", "reason": "visible target found"})
        body = sse(
            {"type": "response.output_text.delta", "delta": output},
            {"type": "response.completed", "response": {"usage": {"input_tokens": 12}}},
        )
        with patch("urllib.request.urlopen", return_value=FakeStream(body)) as open_url:
            result = provider().ask("synthetic task", b"synthetic png")

        request = open_url.call_args.args[0]
        sent = json.loads(request.data.decode())
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-plan-token")
        self.assertEqual(sent["store"], False)
        self.assertEqual(sent["stream"], True)
        self.assertNotIn("tools", sent)
        self.assertNotIn("tool_choice", sent)
        self.assertEqual(sent["text"]["format"]["type"], "json_schema")
        self.assertEqual(sent["text"]["format"]["strict"], True)
        image = sent["input"][0]["content"][1]["image_url"]
        self.assertEqual(
            base64.b64decode(image.split(",", 1)[1]), b"synthetic png"
        )
        self.assertEqual(result.data["action"], "done")
        self.assertEqual(result.usage["input_tokens"], 12)

    def test_plan_scope_is_required_and_token_is_not_in_repr(self):
        with self.assertRaisesRegex(ValueError, "not authorized"):
            ChatGPTPlanCredential("secret-canary", frozenset({"openid"}))
        cred = ChatGPTPlanCredential("secret-canary", frozenset({CHATGPT_PLAN_SCOPE}))
        self.assertNotIn("secret-canary", repr(cred))

    def test_strict_schema_requires_all_properties(self):
        invalid_schema = {
            "type": "object",
            "properties": {"action": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["action"],
            "additionalProperties": False,
        }
        with self.assertRaisesRegex(ValueError, "require every property"):
            ChatGPTPlanModel(
                "account-model-id",
                ChatGPTPlanCredential("synthetic-plan-token", frozenset({CHATGPT_PLAN_SCOPE})),
                invalid_schema,
            )

    def test_no_api_key_fallback(self):
        body = sse(
            {"type": "response.output_text.delta", "delta": '{"action":"done","reason":"ok"}'},
            {"type": "response.completed", "response": {"usage": {}}},
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "do-not-use"}), patch(
            "urllib.request.urlopen", return_value=FakeStream(body)
        ) as open_url:
            provider().ask("task", b"png")
        self.assertEqual(
            open_url.call_args.args[0].get_header("Authorization"),
            "Bearer synthetic-plan-token",
        )

    def test_rejects_invalid_json_and_invalid_schema_value(self):
        invalid_json = sse(
            {"type": "response.output_text.delta", "delta": "not-json"},
            {"type": "response.completed", "response": {"usage": {}}},
        )
        with patch("urllib.request.urlopen", return_value=FakeStream(invalid_json)):
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                provider().ask("task", b"png")

        invalid_value = sse(
            {"type": "response.output_text.delta", "delta": '{"action":"run_shell","reason":"x"}'},
            {"type": "response.completed", "response": {"usage": {}}},
        )
        with patch("urllib.request.urlopen", return_value=FakeStream(invalid_value)):
            with self.assertRaisesRegex(ValueError, "invalid value"):
                provider().ask("task", b"png")

    def test_rejects_any_unexpected_tool_call_event(self):
        body = sse({
            "type": "response.output_item.added",
            "item": {"type": "function_call", "name": "read_file"},
        })
        with patch("urllib.request.urlopen", return_value=FakeStream(body)):
            with self.assertRaisesRegex(RuntimeError, "attempted a tool call"):
                provider().ask("task", b"png")

    def test_does_not_expose_credential_in_provider_failures(self):
        body = sse({
            "type": "response.failed",
            "response": {"error": {"code": "subscription_sharing_usage_unavailable"}},
        })
        with patch("urllib.request.urlopen", return_value=FakeStream(body)):
            with self.assertRaises(RuntimeError) as caught:
                provider().ask("task", b"png")
        self.assertNotIn("synthetic-plan-token", str(caught.exception))
        self.assertIn("subscription_sharing_usage_unavailable", str(caught.exception))

    def test_incomplete_stream_fails_closed(self):
        body = sse({"type": "response.output_text.delta", "delta": '{"action":"done","reason":"ok"}'})
        with patch("urllib.request.urlopen", return_value=FakeStream(body)):
            with self.assertRaisesRegex(RuntimeError, "without response.completed"):
                provider().ask("task", b"png")

    def test_response_size_limit_and_timeout_are_bounded(self):
        limited = ChatGPTPlanModel(
            "account-model-id",
            ChatGPTPlanCredential("synthetic-plan-token", frozenset({CHATGPT_PLAN_SCOPE})),
            ACTION_SCHEMA,
            timeout=2,
            max_response_chars=8,
        )
        body = sse({"type": "response.output_text.delta", "delta": "x" * 9})
        with patch("urllib.request.urlopen", return_value=FakeStream(body)) as open_url:
            with self.assertRaisesRegex(RuntimeError, "size limit"):
                limited.ask("task", b"png")
        self.assertEqual(open_url.call_args.kwargs["timeout"], 2)

        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(RuntimeError, "network or timeout"):
                provider().ask("task", b"png")


if __name__ == "__main__":
    unittest.main()

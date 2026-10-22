"""Exercise HTTP image payloads without calling any external provider."""

import io
import json
import os
import unittest
from unittest.mock import patch

from sqbf.providers import VisionModel


class FakeHttpResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.body


class ProviderTests(unittest.TestCase):
    def test_openai_responses_vision_payload(self):
        response = {"output": [{"content": [{"type": "output_text", "text": '{"action":"done"}'}]}], "usage": {"total_tokens": 10}}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "TEST_KEY"}), patch(
            "urllib.request.urlopen", return_value=FakeHttpResponse(response)
        ) as urlopen:
            result = VisionModel("openai", "fake-model").ask("do something", b"png")
            sent = json.loads(urlopen.call_args.args[0].data.decode())
        self.assertEqual(result.data["action"], "done")
        self.assertEqual(result.usage["total_tokens"], 10)
        self.assertTrue(urlopen.call_args.args[0].full_url.endswith("/v1/responses"))
        self.assertTrue(sent["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,"))
        self.assertEqual(sent["max_output_tokens"], 450)

    def test_anthropic_messages_vision_payload(self):
        response = {"content": [{"type": "text", "text": '{"action":"blocked"}'}], "usage": {"input_tokens": 10}}
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "TEST_KEY"}), patch(
            "urllib.request.urlopen", return_value=FakeHttpResponse(response)
        ) as urlopen:
            result = VisionModel("anthropic", "fake-model").ask("do something", b"png")
            sent = json.loads(urlopen.call_args.args[0].data.decode())
        self.assertEqual(result.data["action"], "blocked")
        self.assertEqual(sent["messages"][0]["content"][1]["source"]["type"], "base64")

    def test_no_api_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                VisionModel("openai", "fake-model").ask("prompt", b"png")


if __name__ == "__main__":
    unittest.main()


class SafeProviderErrorCodeTests(unittest.TestCase):
    def test_only_the_modules_own_constant_messages_map_to_codes(self):
        from sqbf.providers import safe_error_code
        cases = [(RuntimeError('ChatGPT plan request failed with HTTP 400'), 'PROVIDER_HTTP_400'),
                 (RuntimeError('ChatGPT plan request failed (invalid_request_error)'), 'PROVIDER_FAILED_invalid_request_error'),
                 (RuntimeError('ChatGPT plan request failed due to a network or timeout error'), 'PROVIDER_NETWORK_OR_TIMEOUT'),
                 (RuntimeError('ChatGPT plan response exceeded the local size limit'), 'PROVIDER_RESPONSE_TOO_LARGE'),
                 (RuntimeError('ChatGPT plan stream ended without response.completed'), 'PROVIDER_STREAM_INCOMPLETE'),
                 (ValueError('ChatGPT plan response was not valid JSON'), 'RESPONSE_NOT_JSON'),
                 (ValueError('Structured response has invalid type at $.scores.clarity'), 'RESPONSE_SCHEMA_MISMATCH')]
        for error, code in cases:
            self.assertEqual(safe_error_code(error), code)
        for error in (RuntimeError('Bearer abc.def.ghi'), RuntimeError('ChatGPT plan request failed with HTTP 400; token=x'),
                      KeyError('access_token'), ValueError('prompt text'), RuntimeError('ChatGPT plan request failed with HTTP 4000'),
                      type('Sub', (RuntimeError,), {})('ChatGPT plan request failed with HTTP 400')):
            self.assertIsNone(safe_error_code(error))

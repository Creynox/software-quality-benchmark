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

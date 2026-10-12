"""Single-turn screenshot vision adapters; model IDs come from config."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .models import parse_json_object


@dataclass
class ModelResponse:
    data: dict
    usage: dict


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
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}"}
            payload = {
                "model": self.model, "max_completion_tokens": max_tokens,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image}},
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
            text = result["choices"][0]["message"]["content"]
        else:
            text = "\n".join(block["text"] for block in result["content"] if block["type"] == "text")
        return ModelResponse(data=parse_json_object(text), usage=result.get("usage") or {})

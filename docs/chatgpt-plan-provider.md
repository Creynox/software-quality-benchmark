# ChatGPT-plan provider prototype

**Status: `BLOCKED_ELIGIBILITY` for OAuth registration and live inference.** The offline provider prototype is implemented and tested; it does not perform sign-in, read Codex CLI credentials, list account models, or make network calls unless its `ask` method is called by an explicitly constructed trusted controller.

## Eligibility and authorization

OpenAI documents ChatGPT-plan usage for open-source apps and selected private clients. The SQBF GitHub repository is public, but the checked-out tree has no `LICENSE` file. Public visibility alone does not establish that this project qualifies as an open-source client, and no private-client selection or client registration has been verified. No license was added; Product Owner approval is required before adding one. Therefore the SQBF eligibility gate remains unresolved and must be closed before creating a Sign in with ChatGPT client or asking for OAuth consent.

The documented sign-in flow is a separate app authorization, not reuse of Codex CLI's existing ChatGPT login. It requires a registered/dynamic client, a stable opaque host ID, browser consent through PKCE, ID-token validation, and a token response granting `chatgpt.tokens.use.direct`. This prototype accepts a credential object only after a trusted controller has performed that flow. It intentionally has no OAuth, token storage, refresh, browser, or environment-variable implementation.

## Tool-free request contract

`sqbf.providers.ChatGPTPlanModel` has the same `ask(prompt, screenshot_png)` shape as the current vision provider. The controller sends one `input_text` item and one base64 PNG `input_image` item to the documented public Responses endpoint. The request sets `store: false`, `stream: true`, and strict `text.format` JSON Schema. It sends no `tools` or `tool_choice` fields. Any unexpected function, computer, web-search, code-interpreter, or MCP tool-call event is rejected; this provider never dispatches model output as a tool call.

The stream is accepted only after `response.completed`. Failed, incomplete, timed-out, oversized, malformed, or schema-invalid responses raise sanitized errors. Local schema validation runs after parsing. The controller/harness remains responsible for separately validating a UI action before any Playwright call. The model receives no shell, browser, MCP, filesystem, repository, database, or Playwright tool.

The subscription-sharing preview requires `store: false` and `stream: true`; it does not support `max_output_tokens`. The adapter therefore omits that field, uses an HTTP timeout, and bounds the locally accepted streamed JSON size. That local bound cannot cap server-side generation cost.

## Account-specific model and image support

Do not select a hard-coded model ID. The official guidance is to query `/v1/models` using the same authorized plan token, then choose an account-listed model that accepts image input and structured outputs. The account-specific list is not available until OAuth is authorized. No model catalog or image capability was queried in this task. A previous Codex CLI synthetic-image success is not evidence for this separate OAuth client.

## Offline verification

`tests/test_chatgpt_plan_provider.py` uses synthetic bytes and mocked streaming responses only. It checks image encoding, request fields, absence of tools, output schema, scope gating, no API-key fallback, tool-call rejection, malformed/schema-invalid output, sanitized errors, bounded response size, timeout, and incomplete streams. It performs no HTTP request and does not verify eligibility, subscription billing, model access, or a live OAuth flow.

## Official references

- [ChatGPT plan usage quickstart](https://developers.openai.com/siwc/quickstart)
- [Open-source registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Plan-sharing preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)

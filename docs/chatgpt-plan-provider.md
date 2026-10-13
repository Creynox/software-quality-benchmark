# ChatGPT-plan provider prototype

**Status: `GO` for integration into the SQBF harness, not for a BLE benchmark.** Separate user-authorized ChatGPT-plan OAuth, the account catalog, and exactly one synthetic vision/JSON inference succeeded on 2026-10-13. The provider and local OAuth diagnostic are tested offline. Durable sessions, hard total request deadlines, and harness call budgets remain integration work.

## Eligibility and authorization

Correction to the initial report: the official plan-sharing overview explicitly covers **open-source and locally hosted apps**. It does not specify a repository `LICENSE` file as a technical prerequisite. SQBF is being tested as a local application; absence of that file alone is insufficient evidence for `BLOCKED_ELIGIBILITY`. This does not establish open-source status, guarantee acceptance by OpenAI, or authorize paid/remotely hosted distribution. No license was added; Product Owner approval remains required before adding one.

The actual account gate is the user's separate SQBF browser authorization, a validated identity token, the token response's `chatgpt.tokens.use.direct` scope, and account-specific model availability. If registration or plan permission is denied, stop without inference or API-key fallback. The local-hosted interpretation is documentation-based; actual account acceptance was verified by the successful flow described below. This is an account-specific result, not a guarantee for other plans or distribution modes.

The documented sign-in flow is a separate app authorization, not reuse of Codex CLI's existing ChatGPT login. `sqbf.plan_login` prepares a stable opaque host ID, uses the system browser and PKCE, binds a one-time loopback callback to state, and verifies the ID token against OpenAI's JWKS (RS256, issuer, client audience, expiry, issuance time, nonce, subject). It rejects a different account when reusing an issued registration. The plan scope is checked in the token response. Callback request logging is disabled.

The diagnostic intentionally keeps **all tokens in process memory**, with no refresh/storage implementation. Only host ID, issued client ID and validated account subject are saved locally under `%LOCALAPPDATA%/SQBF/plan-login/registration.json`; they are registration metadata, not bearer credentials. A future production session manager still needs protected persistent credentials and refresh handling. No Codex files or browser cookies are read. There is no API-key path.

## Local diagnostic

Install the optional JWT signature-verification dependency into the existing environment:

```powershell
python -m pip install 'PyJWT[crypto]>=2.10,<3'
python -m sqbf.plan_login
```

The default command opens **Continue with ChatGPT**, waits up to five minutes for the user's own authorization, validates the result and lists account model slugs. It makes **zero inference requests**. Exit 0 means successful authorization and model catalog retrieval; exit 2 means a blocked diagnostic. Tokens are never printed or saved.

For the separately authorized single synthetic-image check, use an explicitly selected account-listed model:

```powershell
python -m sqbf.plan_login --vision-test --model <account-listed-model-slug>
```

This signs in again without stored credentials, checks the account catalog, renders a synthetic PNG containing `SQBF VISION TEST`, and sends exactly one inference request. No retries, automatic model fallback, BLE screenshots, or browser actions are involved. Missing model access stops before inference. Only model ID, usage and fixed PASS fields are reported after an exact text match. Availability in the catalog does not itself prove image/structured-output support; that requires the actual test.

## Tool-free request contract

`sqbf.providers.ChatGPTPlanModel` has the same `ask(prompt, screenshot_png)` shape as the current vision provider. The controller sends one `input_text` item and one base64 PNG `input_image` item to the documented public Responses endpoint. The request sets `store: false`, `stream: true`, and strict `text.format` JSON Schema. It sends no `tools` or `tool_choice` fields. Any unexpected function, computer, web-search, code-interpreter, or MCP tool-call event is rejected; this provider never dispatches model output as a tool call.

The stream is accepted only after `response.completed`. Output items are restricted to assistant text messages and reasoning; unknown output kinds, tool calls (including ones present only in the terminal response), and refusals are rejected. Failed, incomplete, oversized, malformed, or schema-invalid responses raise sanitized errors. Duplicate JSON keys and non-finite numeric constants are rejected. The small supported schema subset is checked locally; unsupported schema keywords fail at construction instead of silently losing constraints. Schema input is copied to prevent caller mutations. The controller/harness remains responsible for separately validating a UI action before any Playwright call. The model receives no shell, browser, MCP, filesystem, repository, database, or Playwright tool.

The subscription-sharing preview requires `store: false` and `stream: true`; it does not support `max_output_tokens`. The adapter therefore omits that field, uses an HTTP I/O timeout, and bounds the locally accepted streamed JSON size. The timeout is not a hard total wall-clock deadline, and the local size bound cannot cap server-side generation. Hard harness deadlines and total request budgets remain required before benchmark integration. The diagnostic offers no retries and at most one inference.

## Account-specific model and image support

The official guidance is to query `/v1/models` using the same authorized plan token, then choose an account-listed model that accepts image input and structured outputs. The diagnostic checks the explicitly requested model against that live list before inference. The successful catalog contained `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna`. Only `gpt-6-luna` image/structured-output capability was actually tested. A previous Codex CLI synthetic-image success is not evidence for this separate OAuth client.

## Completion evidence, 2026-10-13

- Local command: `python -m unittest discover -s tests -v`; **51/51 PASS, zero skipped, exit 0**, with PyJWT 2.15.1 and cryptography 50.0.2 installed in the existing environment.
- Live command: `python -m sqbf.plan_login --vision-test --model gpt-6-luna`; **exit 0**, exactly one inference, no retry/fallback. The user completed OpenAI authentication and consent in the system browser. Identity signature, issuer, audience, expiry, issuance time, nonce, subject and the granted plan scope passed validation before the catalog/inference calls.
- Synthetic image exact text match `SQBF VISION TEST`: **PASS**. Strict JSON object/schema: **PASS**. Complete response stream: **PASS**. No model tools offered or dispatched. No API keys or Codex credentials read; OAuth tokens were kept in process memory and not persisted.
- Reported usage: **143 input + 19 output = 162 total tokens**, zero reasoning tokens. These are usage metrics, not a separate monetary charge. The authorized plan endpoint was used; no independent invoice/billing export was inspected.
- Live process ran the prepared worktree source subsequently committed as `fb2883cdf6744f313079b71f95d029af9a43b64b`. After that process started, only sanitized HTTP-error formatting in the login helper was added; the final commit's full suite passed. No second inference was made to repeat an unchanged successful path.
- Local completion evidence: `D:/Temp/sqbf-plan-vision-20261013/completion.json` and `report.md`. The synthetic PNG was generated in memory; its original bytes were not archived, and no reconstructed image is claimed as the original request.
- No BLE access, database changes, license changes, GitHub Actions or merge. Existing dirty/detached worktrees stayed intact.
- Next step: wire this tool-free provider into the bounded harness, then prepare CORE-SMOKE-01 separately. The current `sqbf run` CLI remains blocked for metered legacy API providers.

## Offline verification

`tests/test_chatgpt_plan_provider.py` uses synthetic bytes and mocked streaming responses only. It checks image encoding, request fields, absence of tools, output schema, scope gating, no API-key fallback, tool-call rejection, malformed/schema-invalid output, sanitized errors, bounded response size, timeout, and incomplete streams. It performs no HTTP request and does not verify eligibility, subscription billing, model access, or a live OAuth flow.

## Official references

- [Plan usage for open-source and locally hosted apps](https://developers.openai.com/siwc/token-sharing-open-source)
- [ChatGPT plan usage quickstart](https://developers.openai.com/siwc/quickstart)
- [Open-source registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Plan-sharing preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)

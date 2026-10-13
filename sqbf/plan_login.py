"""One-shot local ChatGPT plan diagnostic. Credentials remain in memory only.

No Codex credentials, environment API keys, refresh storage, or BLE access.
The user authorizes SQBF separately in the system browser. This is a diagnostic,
not a durable account/session manager or a benchmark provider integration.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer

from .providers import CHATGPT_PLAN_SCOPE, ChatGPTPlanCredential, ChatGPTPlanModel

ISSUER = "https://auth.openai.com"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
JWKS_URL = ISSUER + "/.well-known/jwks.json"
RESOURCE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke " + CHATGPT_PLAN_SCOPE


@dataclass(repr=False)
class LoginAttempt:
    redirect_uri: str
    state: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    verifier: str = field(default_factory=lambda: secrets.token_urlsafe(64))
    expires_at: float = field(default_factory=lambda: time.monotonic() + 300)
    consumed: bool = False

    def authorization_url(self, host_id: str, client_id: str | None = None) -> str:
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()
        params = {
            "client_id": client_id or "dynamic_agent_client",
            "ext_agent_host_id": host_id, "response_type": "code",
            "redirect_uri": self.redirect_uri, "scope": SCOPES,
            "resource": RESOURCE, "state": self.state, "nonce": self.nonce,
            "code_challenge_method": "S256", "code_challenge": challenge,
        }
        if not client_id:
            params["agent_name_hint"] = "SQBF"
        return ISSUER + "/api/accounts/authorize?" + urllib.parse.urlencode(params)

    def consume(self, path: str, saved_client: str | None = None) -> dict:
        if self.consumed or time.monotonic() >= self.expires_at:
            raise ValueError("OAuth attempt expired or was already consumed")
        self.consumed = True
        parsed = urllib.parse.urlsplit(path)
        if parsed.path != "/auth/callback":
            raise ValueError("Unexpected OAuth callback path")
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if any(len(values) != 1 for values in params.values()):
            raise ValueError("Duplicate OAuth callback parameter")
        returned_state = params.get("state", [""])[0]
        if not secrets.compare_digest(returned_state, self.state):
            raise ValueError("OAuth state did not match")
        if "error" in params:
            raise ValueError("OAuth consent was declined or registration unavailable")
        code = params.get("code", [""])[0]
        client = params.get("client_id", [saved_client or ""])[0]
        if not code or not re.fullmatch(r"oaiapp_[A-Za-z0-9_-]+", client):
            raise ValueError("OAuth registration did not return an issued client and code")
        if saved_client and client != saved_client:
            raise ValueError("OAuth client did not match the saved registration")
        return {
            "grant_type": "authorization_code", "client_id": client,
            "code": code, "code_verifier": self.verifier,
            "redirect_uri": self.redirect_uri, "resource": RESOURCE,
        }


def _json_request(request):
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(1_000_001)
        if len(body) > 1_000_000:
            raise ValueError("OAuth/catalog response exceeded local limit")
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError("OAuth/catalog response must be an object")
        return result
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"ChatGPT authorization/catalog request failed with HTTP {error.code}") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise RuntimeError("ChatGPT authorization/catalog request failed") from None


def validate_tokens(tokens: dict, client: str, nonce: str, expected_subject=None):
    """Verify the signature and all OIDC bindings before accepting plan scope."""
    import jwt

    try:
        id_token = tokens["id_token"]
        access = tokens["access_token"]
        if not isinstance(id_token, str) or not isinstance(access, str) or not access:
            raise ValueError("Missing tokens")
        if tokens.get("token_type", "").lower() != "bearer":
            raise ValueError("Unexpected token type")
        scope = tokens.get("scope")
        if not isinstance(scope, str) or CHATGPT_PLAN_SCOPE not in scope.split():
            raise ValueError("Plan scope not granted")
        key = jwt.PyJWKClient(JWKS_URL, timeout=20).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token, key.key, algorithms=["RS256"], issuer=ISSUER,
            audience=client, leeway=5,
            options={"require": ["iss", "aud", "exp", "iat", "sub", "nonce"]},
        )
        if not isinstance(claims["sub"], str) or not claims["sub"]:
            raise ValueError("Missing subject")
        if not isinstance(claims["nonce"], str) or not secrets.compare_digest(claims["nonce"], nonce):
            raise ValueError("Nonce mismatch")
        if expected_subject and claims["sub"] != expected_subject:
            raise ValueError("Different account")
        return ChatGPTPlanCredential(access, frozenset(scope.split())), claims["sub"]
    except Exception:
        # Never expose token data or upstream exception contents/chains.
        raise RuntimeError("ChatGPT identity or plan authorization could not be verified") from None


def _load_host(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "registration.json"
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
        host = record["host_id"]
        if (not isinstance(host, str) or not host.startswith("urn:uuid:")
                or str(uuid.UUID(host.removeprefix("urn:uuid:"))) != host.removeprefix("urn:uuid:")):
            raise ValueError("Invalid saved host ID")
        return record
    record = {"host_id": "urn:uuid:" + str(uuid.uuid4())}
    path.write_text(json.dumps(record), encoding="utf-8")
    return record


def authorize(record: dict):
    # Loopback only. No callback URLs, codes, tokens, or identities in HTTP logs.
    outcome = {}
    attempt = None

    class Callback(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(2)

        def log_message(self, *_):
            pass

        def do_GET(self):
            if urllib.parse.urlsplit(self.path).path != "/auth/callback":
                self.send_error(404)
                return
            try:
                outcome["form"] = attempt.consume(self.path, record.get("client_id"))
            except ValueError:
                outcome["failed"] = True
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(b"SQBF callback received. Return to the local application for the result.")

    with HTTPServer(("127.0.0.1", 0), Callback) as server:
        server.timeout = 1
        attempt = LoginAttempt(f"http://127.0.0.1:{server.server_port}/auth/callback")
        if not webbrowser.open(attempt.authorization_url(record["host_id"], record.get("client_id"))):
            raise RuntimeError("System browser could not be opened")
        print("Continue with ChatGPT: authorize SQBF in the system browser. No inference yet.", flush=True)
        while not outcome and time.monotonic() < attempt.expires_at:
            server.handle_request()
    if "form" not in outcome:
        raise RuntimeError("ChatGPT authorization was declined, invalid, or timed out")
    form = outcome["form"]
    tokens = _json_request(urllib.request.Request(
        TOKEN_URL, data=urllib.parse.urlencode(form).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
    ))
    credential, subject = validate_tokens(tokens, form["client_id"], attempt.nonce, record.get("subject"))
    record.update(client_id=form["client_id"], subject=subject)
    return credential


def catalog(credential):
    result = _json_request(urllib.request.Request(
        RESOURCE + "/models", headers={"Authorization": "Bearer " + credential.access_token},
    ))
    models = result.get("models")
    if not isinstance(models, list):
        raise RuntimeError("ChatGPT plan model catalog missing")
    return [m["slug"] for m in models if isinstance(m, dict)
            and m.get("visibility") == "list" and isinstance(m.get("slug"), str)]


def vision_test(credential, model):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 500, "height": 160})
        page.set_content('<div style="font: bold 32px sans-serif; padding:32px">SQBF VISION TEST</div>')
        png = page.screenshot()
        browser.close()
    schema = {
        "type": "object", "properties": {"visible_text": {"type": "string"}},
        "required": ["visible_text"], "additionalProperties": False,
    }
    result = ChatGPTPlanModel(model, credential, schema, timeout=30, max_response_chars=200).ask(
        "Read the visible text in the image exactly. Return only the requested JSON object.", png,
    )
    if result.data["visible_text"].strip() != "SQBF VISION TEST":
        raise RuntimeError("Synthetic image interpretation did not match")
    return {"image": "PASS", "json": "PASS", "tools": "NONE_OFFERED", "model": model, "usage": result.usage}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--vision-test", action="store_true", help="Exactly one synthetic inference after browser consent")
    parser.add_argument("--model", help="Must be present in the authorized account catalog")
    args = parser.parse_args(argv)
    if args.vision_test and not args.model:
        parser.error("--vision-test requires an explicitly selected --model")
    directory = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "SQBF" / "plan-login"
    try:
        record = _load_host(directory)
        credential = authorize(record)
        # Only non-token host/client identity metadata is persisted. All OAuth
        # tokens (including returned refresh token) die with this process.
        temporary = directory / "registration.tmp"
        temporary.write_text(json.dumps(record), encoding="utf-8")
        temporary.replace(directory / "registration.json")
        models = catalog(credential)
        print(json.dumps({"auth": "CHATGPT_PLAN_OAUTH", "models": models, "tokens_saved": False}))
        if args.vision_test:
            if args.model not in models:
                raise RuntimeError("Selected model is not available to this authorized account")
            print(json.dumps(vision_test(credential, args.model)))
        return 0
    except (RuntimeError, ValueError) as error:
        # Messages in this module/adapter are fixed, sanitized diagnostic text;
        # errors from untrusted libraries are handled by the generic branch.
        print("BLOCKED_AUTH: " + str(error) + "; no fallback or retry was attempted.")
        return 2
    except Exception:
        print("BLOCKED_AUTH: ChatGPT plan diagnostic failed; no fallback or retry was attempted.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

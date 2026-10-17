"""Opt-in persistent ChatGPT-plan login: confirm once in the browser, then many runs and agents reuse it.

Why it exists: the plan access token lives about one hour. A complete NSN014 suite needs two to three hours (live run 6c23f768 stopped at 3603 s
with HTTP 401), and the PO does not want to confirm in the browser for every run, hour and agent (decision of 2026-10-17, confirmed explicitly:
"Ja, verschluesselt speichern"). The login therefore can be kept on this computer: the tokens are encrypted with the Windows user's DPAPI, stored
in a file only that user can read, and renewed automatically with the OAuth refresh grant. All processes of the same Windows user share one store;
a lock serialises renewals so that a rotating refresh token is never spent twice.

Boundaries that stay: nothing is stored unless the PO runs `python -m sqbf.plan_login --keep-signed-in`; the refresh token never leaves this module,
the store file and the memory of the controller processes (it is not part of any model request, worker payload, run artifact or log); the stored
login ends after a maximum age (default seven days) and can be removed at once with `--forget` or revoked in the ChatGPT account settings.
"""
from __future__ import annotations

import base64
import contextlib
import ctypes
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .artifact_privacy import create_private_file
from .providers import CHATGPT_PLAN_SCOPE

STORE_NAME = "plan-tokens.dpapi"
LOCK_NAME = "plan-tokens.lock"
STORE_VERSION = 1
DEFAULT_MAX_AGE_DAYS = 7
MAX_AGE_DAYS_LIMIT = 30
EXPIRY_MARGIN_SECONDS = 300
FALLBACK_LIFETIME_SECONDS = 1800
LOCK_TIMEOUT_SECONDS = 60
ENTROPY = b"SQBF plan login store v1"

# Codes the controllers treat as "authorization is gone": the suite stops at once (stage_support.AUTHORIZATION_FAILURES).
REFUSED_CODES = ("PROVIDER_REFRESH_REJECTED", "PLAN_LOGIN_TOO_OLD", "PLAN_LOGIN_MISSING")


class PlanAuthorizationError(RuntimeError):
    """Fixed, sanitised failure of the stored login; `code` is a fixed identifier, never token or provider text."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ---- Windows DPAPI (current user) ---------------------------------------------------------------------------------------------------

def _dpapi(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        raise PlanAuthorizationError("PLAN_STORE_UNSUPPORTED", "Protected plan login storage requires Windows")
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    function.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR if protect else ctypes.c_void_p, ctypes.POINTER(Blob),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    def make(value: bytes):
        buffer = ctypes.create_string_buffer(value, len(value))
        return Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer

    source, keep_source = make(data)
    entropy, keep_entropy = make(ENTROPY)
    out = Blob()
    # CRYPTPROTECT_UI_FORBIDDEN = 1: never show a prompt.
    ok = function(ctypes.byref(source), "SQBF plan login" if protect else None, ctypes.byref(entropy), None, None, 1, ctypes.byref(out))
    del keep_source, keep_entropy
    if not ok:
        raise PlanAuthorizationError("PLAN_STORE_UNREADABLE", "The stored ChatGPT login could not be decrypted by this Windows user")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


def dpapi_protect(data: bytes) -> bytes:
    return _dpapi(data, True)


def dpapi_unprotect(data: bytes) -> bytes:
    return _dpapi(data, False)


# ---- store ----------------------------------------------------------------------------------------------------------------------------

@contextlib.contextmanager
def _file_lock(path: Path, timeout: float = LOCK_TIMEOUT_SECONDS):
    """Exclusive cross-process lock; waits up to `timeout` seconds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise PlanAuthorizationError("PLAN_STORE_LOCKED", "The stored ChatGPT login is in use by another process") from None
                time.sleep(0.2)
        try:
            yield
        finally:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


class PlanTokenStore:
    """The encrypted login of this Windows user: refresh token, latest access token and the facts needed to renew and bound them."""

    def __init__(self, directory, *, protect=dpapi_protect, unprotect=dpapi_unprotect, clock=time.time):
        self.directory = Path(directory)
        self.path = self.directory / STORE_NAME
        self.lock_path = self.directory / LOCK_NAME
        self._protect, self._unprotect, self.clock = protect, unprotect, clock

    def locked(self):
        return _file_lock(self.lock_path)

    def exists(self) -> bool:
        return self.path.is_file()

    def save(self, record: dict) -> None:
        """Encrypt and replace atomically. The file is created current-user-only before any content is written."""
        _validate(record)
        self.directory.mkdir(parents=True, exist_ok=True)
        data = self._protect(json.dumps(record, sort_keys=True).encode("utf-8"))
        temporary = self.directory / ("plan-tokens-" + uuid.uuid4().hex + ".tmp")
        create_private_file(temporary)
        try:
            temporary.write_bytes(base64.b64encode(data))
            temporary.replace(self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def load(self) -> dict | None:
        """The stored record, None if there is none. Raises PlanAuthorizationError if it is unreadable or older than its maximum age."""
        if not self.exists():
            return None
        try:
            record = json.loads(self._unprotect(base64.b64decode(self.path.read_bytes())).decode("utf-8"))
            _validate(record)
        except PlanAuthorizationError:
            raise
        except Exception:
            raise PlanAuthorizationError("PLAN_STORE_UNREADABLE", "The stored ChatGPT login is damaged") from None
        if self.clock() - record["login_at"] > record["max_age_days"] * 86400:
            raise PlanAuthorizationError("PLAN_LOGIN_TOO_OLD", "The stored ChatGPT login reached its maximum age; sign in again")
        return record

    def forget(self) -> bool:
        with self.locked():
            if self.path.exists():
                self.path.unlink()
                return True
        return False


def _validate(record) -> None:
    try:
        if (not isinstance(record, dict) or record.get("version") != STORE_VERSION
                or not all(isinstance(record.get(key), str) and record[key] for key in ("refresh_token", "access_token", "client_id", "subject", "scope"))
                or CHATGPT_PLAN_SCOPE not in record["scope"].split()
                or not re.fullmatch(r"oaiapp_[A-Za-z0-9_-]+", record["client_id"])
                or not all(isinstance(record.get(key), (int, float)) and not isinstance(record.get(key), bool) for key in ("login_at", "access_expires_at"))
                or type(record.get("max_age_days")) is not int or not 1 <= record["max_age_days"] <= MAX_AGE_DAYS_LIMIT):
            raise ValueError()
    except Exception:
        raise PlanAuthorizationError("PLAN_STORE_UNREADABLE", "The stored ChatGPT login is damaged") from None


# ---- renewal --------------------------------------------------------------------------------------------------------------------------

def _jwt_expiry(token: str):
    """Unverified `exp` of a JWT access token; only used to estimate when to renew, never to trust the token."""
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        value = claims.get("exp")
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    except Exception:
        return None


def access_expiry(tokens: dict, now: float) -> float:
    lifetime = tokens.get("expires_in")
    if isinstance(lifetime, (int, float)) and not isinstance(lifetime, bool) and lifetime > 0:
        return now + float(lifetime)
    return _jwt_expiry(tokens["access_token"]) or now + FALLBACK_LIFETIME_SECONDS


def renew(record: dict, *, request=None, clock=time.time, pause=time.sleep) -> dict:
    """Spend the refresh token once (one bounded repeat for a transient failure) and return the updated record."""
    from . import plan_login

    request = request or plan_login._json_request
    form = {"grant_type": "refresh_token", "refresh_token": record["refresh_token"], "client_id": record["client_id"], "resource": plan_login.RESOURCE}
    for attempt in range(2):
        try:
            tokens = request(urllib.request.Request(
                plan_login.TOKEN_URL, data=urllib.parse.urlencode(form).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"))
            break
        except RuntimeError as error:
            found = re.search(r"HTTP (\d+)", str(error))
            if found and int(found.group(1)) in (400, 401, 403):
                raise PlanAuthorizationError("PROVIDER_REFRESH_REJECTED", "The ChatGPT login was refused; sign in again") from None
            if attempt == 0:
                pause(2)
    else:
        raise PlanAuthorizationError("PROVIDER_REFRESH_UNAVAILABLE", "The ChatGPT login could not be renewed right now") from None
    now = clock()
    try:
        access = tokens["access_token"]
        if not isinstance(access, str) or not access or str(tokens.get("token_type", "bearer")).lower() != "bearer":
            raise ValueError()
        scope = tokens.get("scope", record["scope"])
        if not isinstance(scope, str) or CHATGPT_PLAN_SCOPE not in scope.split():
            raise ValueError()
        rotated = tokens.get("refresh_token")
        updated = dict(record, access_token=access, access_expires_at=access_expiry(tokens, now), scope=scope,
                       refresh_token=rotated if isinstance(rotated, str) and rotated else record["refresh_token"])
        _validate(updated)
        return updated
    except Exception:
        raise PlanAuthorizationError("PROVIDER_REFRESH_REJECTED", "The ChatGPT login renewal was not accepted; sign in again") from None


class RefreshingPlanCredential:
    """Stands in for ChatGPTPlanCredential: `access_token` is renewed on access, for every process that shares the store."""

    def __init__(self, store: PlanTokenStore, *, request=None, clock=time.time):
        self.store, self._request, self._clock = store, request, clock
        self._guard = threading.Lock()
        self._token, self._expires = None, 0.0
        record = self._record()
        self.granted_scopes = frozenset(record["scope"].split())

    def _record(self) -> dict:
        record = self.store.load()
        if record is None:
            raise PlanAuthorizationError("PLAN_LOGIN_MISSING", "No stored ChatGPT login; sign in again")
        return record

    @property
    def access_token(self) -> str:
        with self._guard:
            if self._token and self._expires - self._clock() > EXPIRY_MARGIN_SECONDS:
                return self._token
            with self.store.locked():
                # Another process may have renewed while this one waited for the lock.
                record = self._record()
                if record["access_expires_at"] - self._clock() <= EXPIRY_MARGIN_SECONDS:
                    record = renew(record, request=self._request, clock=self._clock)
                    self.store.save(record)
            self._token, self._expires = record["access_token"], record["access_expires_at"]
            return self._token

    def renew_now(self) -> None:
        """Force one renewal (the keep-signed-in check): proves that this account and client accept the refresh grant."""
        with self._guard, self.store.locked():
            record = renew(self._record(), request=self._request, clock=self._clock)
            self.store.save(record)
            self._token, self._expires = record["access_token"], record["access_expires_at"]

    def describe(self) -> dict:
        """Facts without secrets: how old the login is and when it ends."""
        record = self._record()
        now = self._clock()
        return {"signed_in_hours_ago": round((now - record["login_at"]) / 3600, 1),
                "login_valid_for_hours": round((record["login_at"] + record["max_age_days"] * 86400 - now) / 3600, 1),
                "max_age_days": record["max_age_days"], "access_token_valid_for_minutes": round(max(0.0, record["access_expires_at"] - now) / 60)}

    def __repr__(self) -> str:
        return "RefreshingPlanCredential(<hidden>)"


def default_directory() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "SQBF" / "plan-login"


def build_record(form: dict, tokens: dict, subject: str, scope: str, *, max_age_days: int, now: float) -> dict:
    """The record to store after a browser login; `refresh_token` must have been issued (scope offline_access)."""
    refresh = tokens.get("refresh_token")
    if not isinstance(refresh, str) or not refresh:
        raise PlanAuthorizationError("PLAN_NO_REFRESH_TOKEN", "OpenAI did not issue a refresh token; the login cannot be kept")
    record = {"version": STORE_VERSION, "refresh_token": refresh, "access_token": tokens["access_token"], "client_id": form["client_id"],
              "subject": subject, "scope": scope, "login_at": now, "access_expires_at": access_expiry(tokens, now), "max_age_days": max_age_days}
    _validate(record)
    return record

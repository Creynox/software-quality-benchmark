# BLE session renewal: BLOCKED_SESSION / NO-GO

## Verified state

SQBF began at local/remote commit `12f83762e4a6529b6c5abd17c10d80bbca5f4210`.
Status/worktrees/fetch and ff-only pull confirmed agreement; the existing dirty
and detached worktrees were preserved. Only the dedicated SQBF worktree changed.

BLE 5080 still listens on 127.0.0.1 from PID 54268, started 2026-10-12 23:38:10
Europe/Berlin. Executable: the existing sqbf-lab01-fixture worktree's BLE.Web.exe.
DLL reports `1.0.0+c51ea2229b3513aa59e659774fe8ce44cdd81859`, SHA-256
`d0109a37a06f91aff137a27f26433f6dbc6696f28db21514e7f63cc97c13b2d4`.
Fixture worktree HEAD remains `fb933961099a6dd6da301998365d22ccb6921857`.
Assembly metadata is not a reproducible-build proof. No restart/configuration
change or intervention on the normal 5059/5433 instance occurred.

The old stored state restores to `/login` (HTTP 200), not an authenticated home.
Its persistent cookies expired at 2026-10-13 18:53:13 Europe/Berlin. Cookie host
127.0.0.1 and path `/` match the target. BLE configures eight-hour sliding cookie
expiration. Expiration is proven; no revocation cause is asserted. The old file's
SHA-256 remained unchanged. No cookie/password/token value was printed.

## Login attempt and concrete blocker

The original manual session command could not receive terminal Enter in this
execution environment. A user-confirmation helper was opened but never saved
state. The user then explicitly authorized using the previously AI-created
benchmark account rather than manually entering unknown credentials. That
pending helper and its own browser tree were closed.

Existing credentials were located in a local, current-user-only DPAPI file.
No password reset, account creation or access grant was performed. A credential
loader issue caused by inherited PowerShell 7 PSModulePath was corrected before
any login request, without exposing decrypted values.

Exactly one automated login attempt followed. It failed to reach the expected
authenticated home; no new session was saved (command exit 1). Independent
account evidence still shows the previous successful login time, 08:53:12 UTC.
A harmless diagnostic using synthetic password input, **without submitting the
form**, reproduced the username being cleared during sequential input fills.

The harness now sets username/password together and requests normal form
submission in one browser turn. Native form validation and server password
authentication are retained. This correction passes a real synthetic-browser
input-reset canary but **has not been retried on BLE**. In accordance with the
stop instruction, no second login attempt or benchmark retry was made.

## Implemented safeguards

- `session --credentials <local-DPAPI-file> --username <exact-test-account>`:
  explicitly authorized loopback-only automatic login, one attempt, no fallback.
  Credential ACL must be protected and allow only the current Windows user;
  password decryption happens in a captured pipe, never command arguments/logs.
- New state is reserved without overwriting, with current-user-only Windows
  file ACL applied **before** cookie data is written (0600 on other systems).
- `session-check --scenario ... --url ... --storage-state ... --output ...`:
  two new contexts, home/product/reload checks, visible search/empty state,
  same-origin request guard and existing event protection, no dispatched input.
  Results contain paths/statuses, no cookies, query strings or exception text.
- `preflight --storage-state ...` performs that model-free restoration check.
  Plain preflight remains configuration validation and doctor file presence
  remains explicitly unverified.
- The subscription run path now requires session restoration **before** OAuth,
  model catalog lookup or compatibility inference. It stops with exit 2 for a
  stale session. The check never independently asserts account identity.

Automatic session verification is now performed for each released subscription
run. Renewal is an explicit separate command using protected credentials; it
does not silently retry failed logins or start a benchmark.

## Independent identity/data evidence

Exact isolated container/database/volume/55432 binding was verified before DB
reads. Existing `sqbf_oracle_ro` before/after snapshots prove all ten protected
table counts and hashes unchanged. It lacks identity/scope table SELECT rights;
those tables were inspected through the existing local database account inside
an explicit READ ONLY transaction, without granting privileges or writing.

`sqbf-laborleitung` is active, non-admin, belongs to the expected synthetic
tenant, has active Laborleiter/products.manage authorization, one active
Enzberg plant scope and one tenant scope, zero active global scopes. Enzberg is
active and belongs to the expected tenant. This verifies the fixture identity,
**not a successful new authenticated session**. A future successful login
normally updates LastLoginAtUtc; this is an application login side effect,
not product/sample/report fixture provisioning.

## Tests and completion

`D:\Entwicklung\Benchmark\.venv\Scripts\python.exe -m unittest discover -s tests -v`
passed **81/81**, zero skipped, exit 0. Includes expired-state redirect, missing
file, expected UI, reload/new-context invalidation, credential identity/error
redaction, input-reset browser canary, no-save/no-retry on login failure,
preserved old files, and no OAuth/inference on stale-session run precheck.

Old live session-check: BLOCKED_SESSION, `/login`; expected CLI return 2.
Independent protected DB comparison and old file hash comparison: unchanged.
New session: absent. Model calls: 0. CORE-SMOKE-01 retries: 0.
Local evidence/logs: `D:\Temp\sqbf-session-refresh-20261013` (current-user-only).

**NO-GO / BLOCKED_SESSION.** Reproducible fresh-session restoration, authenticated
rights and reload checks remain unproven. No new pilot is recommended yet.
Smallest next step: explicitly release one corrected automatic login and its
model-free restoration/identity checks. No GitHub Actions, merge or DB reset.

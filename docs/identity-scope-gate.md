# Independent identity and scope gate — Issue #17

## Result, 2026-10-13

**GO for the repaired model-free safety gate.** The existing signed session and
current Enzberg authorization independently passed the real local gate. No
OAuth, model calls, live benchmark, login renewal or database mutation occurred.
The complete live CORE-SMOKE-01 workflow remains unaccepted; PR #10 stays Draft.

## Explicit controller access and security boundary

`sqbf_oracle_ro` stays SELECT-only on its existing protected tables. No grants,
roles, views, stored functions, schema or BLE configuration were changed.

The scope reader deliberately reuses the **already authorized fixture controller**
path documented in BLE's `scripts/fixtures/lab01/Provision-Lab01Fixture.ps1`:
local Docker socket, role `ble_benchmark`, exact isolated database. This is an
explicit configured access path, never a retry/fallback after Oracle failure.
Its database role has broad privileges; it is not misrepresented as a newly
restricted DB role. The trusted controller's fixed query runs in REPEATABLE READ
READ ONLY, uses a five-second statement timeout, pg_catalog search path and
ROLLBACK. PostgreSQL blocks writes in this transaction. This boundary protects
against accidental mutation; it does not sandbox a compromised trusted controller.

Before the role is used, Docker/container ID/image/volume/database/loopback 55432
and the distinct protected 5433 container are verified. Process inspection binds
5080's current listener to the explicitly supplied application content root;
assembly revision/hash and build-file timestamp are recorded. No credentials
are extracted from container environment or passed on the command line.

The audited projection is `projects/ble-elva/tools/identity-scope.sql`, pinned by
a normalized-text SHA-256 in the fixture. It selects only fixed account IDs,
names and booleans/counters. No passwords, stamps, hashes, emails, tokens or
arbitrary identity fields are selected. Parameters use psql quoted variables;
commands use subprocess argument arrays, no shell interpolation.

The controller-only .NET helper independently authenticates the existing cookie
using ASP.NET's purpose-bound Data Protection ticket format and the checked
application discriminator. Key generation is disabled. Cookie/key contents and
claim collections never leave the helper; only validity, account ID/name and
expiry enter the captured controller pipe. Current user/tenant/role/permission/
scope state is read separately from PostgreSQL and bound to that signed account.
Two fresh authenticated browser contexts and reloads additionally verify server
acceptance. UI display alone cannot satisfy identity proof.

Exactly one active expected Plant scope, one expected Tenant scope, zero Global
scopes and no other active scope are required, alongside active non-admin account,
active tenant, active Laborleiter role and active products.manage permission.
Missing/contradictory evidence returns fixed `BLOCKED_SCOPE_VERIFICATION`; no
automatic retry, credentials, external error text or raw query output is reported.

CLI `run` enforces this gate **before OAuth/catalog/compatibility inference**.
Controller settings/query/session data are not added to model IPC or prompts;
executor and reviewer still have no database, keyring, shell or file tools.
Runtime/session/schema/operator changes must pass the gate again at execution.

## Build and model-free check

Use an explicit local directory outside Git; intermediate/build files contain no
session data. Run from the SQBF worktree:

```powershell
dotnet build projects/ble-elva/tools/identity-check/IdentityCheck.csproj `
  --output D:\Temp\sqbf-scope-gate-20261013\verifier `
  -p:BaseIntermediateOutputPath=D:\Temp\sqbf-scope-gate-20261013\obj\ --nologo

D:\Entwicklung\Benchmark\.venv\Scripts\python.exe -m sqbf.cli scope-check `
  --scenario projects/ble-elva/scenarios/core-smoke-01.json `
  --url http://127.0.0.1:5080/ `
  --storage-state D:\Temp\sqbf-session-once-20261013\ble-session-refreshed.json `
  --identity-application-root D:\Entwicklung\BLE-worktrees\sqbf-lab01-fixture\src\BLE.Web `
  --identity-verifier D:\Temp\sqbf-scope-gate-20261013\verifier\IdentityCheck.dll
```

Optional `--output` exclusively reserves a new private file before JSON contents.
Old sessions/files cannot be overwritten by that output path. Gate exit is 0 for
SCOPE_VERIFIED, 2 for BLOCKED_SCOPE_VERIFICATION. Local source/root parameters
are trusted operator inputs; no model can configure or invoke the scope reader.
The helper is currently for this Windows/.NET 8 fixture's cookie setup; unsupported
or changed Data Protection configurations fail closed rather than guessing keys.

## Acceptance evidence

- `python -m unittest discover -s tests -v`: **110/110 PASS, no skips, exit 0**
  using the existing project venv (10.274 seconds). Seventeen new tests cover
  correct account, wrong/inactive user/tenant, missing role/permission, wrong or
  extra Plant/Tenant/other scope, Global/admin rejection, invalid signature/session,
  unavailable SELECT, incorrect DB/role/transaction, modified projection,
  no implicit privileged fallback/retry, sanitized canaries, model IPC separation
  and CLI prevention of OAuth/inference/runner on gate failure.
- .NET build: exit 0, zero warnings/errors. Real `scope-check`: exit 0,
  `SCOPE_VERIFIED`, every check true; no new login.
- Runtime: PID 54268, assembly-reported
  `1.0.0+c51ea2229b3513aa59e659774fe8ce44cdd81859`, DLL SHA-256
  `d0109a37a06f91aff137a27f26433f6dbc6696f28db21514e7f63cc97c13b2d4`.
  Assembly metadata is not reproducible-build proof; fixture HEAD is separate.
- Independent SELECT-only `sqbf_oracle_ro` before/after snapshots match exact
  isolation identity and all ten protected table counts/hashes. Zero changes.
- Private evidence: `D:/Temp/sqbf-scope-gate-20261013/evidence/`; test log:
  `D:/Temp/sqbf-scope-gate-tests.log`. Old worktrees/sessions unchanged.

The former BLOCKED_SCOPE_VERIFICATION is resolved for the checked fixture.
A newly ordered single pilot can use the documented existing provider path,
including its separate interactive OAuth requirement. No live success, reviewer
scores or populated-data filtering proof is inferred from this safety-gate repair.

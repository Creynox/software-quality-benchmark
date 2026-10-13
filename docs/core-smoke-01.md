# CORE-SMOKE-01: bounded subscription-only read-only pilot

The existing `sqbf run` command now accepts `chatgpt_plan` for the executor and
analyst. CORE-SMOKE-01 is the prepared project profile for that path.
Legacy metered API modes remain blocked. Tokens stay in process memory and IPC
pipes; no OAuth token is stored in a file, command argument, event, or report.
The same separately authorized account is used throughout one pilot, without
signing in for every screenshot. The controller first checks its live catalog
and performs one synthetic reviewer image/JSON compatibility request.

```powershell
python -m sqbf.cli run --scenario projects/ble-elva/scenarios/core-smoke-01.json `
  --url http://127.0.0.1:5080/ --software-version <verified-running-build> `
  --executor-provider chatgpt_plan --executor-model gpt-6-luna `
  --analyst-provider chatgpt_plan --analyst-model gpt-6.1-sol `
  --storage-state <existing-local-laborleitung-session> --fixture-ready --headless
```

## Enforced boundaries

BLE URLs, navigation/search selectors, empty-state text and request paths are
configured only in `projects/ble-elva/scenarios/core-smoke-01.json`. Protected
table names and independently measured expected counts are configured in the
project fixture. The new generic guard/loop/snapshot code does not embed them.
Scenario URL and fixture identity must agree; incomplete policies or unsafe SQL
identifiers are rejected. The blank project template remains unchanged.

- At most 300 seconds for the pilot, including model waits, browser operations,
  reviewer and independent snapshots. A supervisor reserves 30 seconds for
  after verification; the browser/reviewer subprocess receives the remaining
  time. Each model subprocess is additionally limited to 30 seconds. OAuth and
  the one reviewer compatibility test are separate prerequisite phases.
- At most 10 UI actions and 12 model calls inside the pilot (one reserved for
  the reviewer). No retries or extensions, no model/provider fallback.
- On Windows the actual interpreter is started suspended, assigned to a job
  before resuming, then the entire owned job is terminated on timeout. The
  existing venv's import paths are retained. This avoids venv launcher processes
  escaping the job. On Unix the owned process group is terminated.
- A controller-only DOM hit test allows the visible product-navigation link
  and product search input. Typing is limited to the released task query; keys
  are limited to selection/deletion/Enter while that search field is focused.
  Everything else is denied before input dispatch. A capture-phase event guard
  additionally rejects all other control events and every form submission.
- Requests are limited to the exact 5080 origin, approved read-only pages and
  static assets. POST is only permitted for Blazor's circuit transport, which
  is necessary even for reading. This is **not** a blanket read-only database
  permission for the web app: safety rests on the enforced event/action
  contract, confirmed read-only handlers and independent data verification.
- No DOM, selectors, source, credentials, database data or Oracle result is
  included in model inputs. Executor receives one current screenshot, the task
  and its own visible action history. Reviewer receives up to three selected
  screenshots, task, public action history, duration and first observation.

## Independent Oracle and archive

The parent controller verifies the isolated container ID, image, database,
volume and 127.0.0.1:55432 mapping, and independently distinguishes the protected
5433 container. It uses the **existing** `sqbf_oracle_ro` account through the
container's local PostgreSQL socket, checking identity, read-only transaction,
no elevated/create rights and no public table/column write privileges. No
passwords, role changes, grants or resets are required.

Repeatable-read SELECT snapshots hash complete rows in ten protected tables:
products, both sample tables, reports, product/norm assignments, standards,
versions, plants and both classification tables. Before/after identities,
counts and hashes must match. Separate controller observations verify rendered
search text, the empty-state label and the final cleared filter, each associated
with a hashed screenshot. Model/reviewer completion alone cannot give Oracle
PASS. Hashing is deterministic PostgreSQL MD5 over sorted complete row JSON;
it detects accidental changes, not adversarial cryptographic tampering.

Every run archives `run.json`, `report.md`, `scores.json`, `findings.json`,
`events.json`, `evidence.json` with PNG SHA-256 hashes, and before/after Oracle
records. Technical result, Oracle result, UX verdict/scores and completion
status remain distinct. No screenshots or session files are committed.

```powershell
python -m sqbf.cli list-runs --test-id CORE-SMOKE-01 --date 2026-10-13
python -m sqbf.cli list-runs --role luna --result GO --min-score 3
```

The empty fixture has zero products. This can prove entering/resetting the
search and displaying an empty state; it **cannot prove filtering populated
data**. The UI has no dedicated reset button, so the visible search field must
be cleared. That information is not passed as an extra hint to the executor.

## Pre-pilot verification, 2026-10-13

- All 62 local tests passed, exit 0, including actual Windows process-tree
  termination, hard model waits, action/call budgets, invalid-action stopping,
  mock archive/Oracle runs, and a real synthetic-browser write-button canary.
- The first process-tree test failed. Investigation showed an interpreter
  launched via the Windows venv redirector could escape the job. The fix uses
  the actual interpreter with the venv import paths and suspended startup; the
  descendant termination regression then passed. No live inference was made
  during these failures.
- Existing local session reaches the authenticated product route. The exact
  account name is not exposed in BLE's current user menu; it is the previously
  provisioned Laborleitung session, reused unchanged. A controller-only attempt
  to target “Neues Produkt” was denied without clicking it. Guarded navigation
  loads with no blocked assets and all ten DB snapshots unchanged.
- Running process PID 54268 started 2026-10-12 23:38:10 from the fixture
  directory. Loaded DLL was last written 23:29:56, before process start.
  Its assembly reports `1.0.0+c51ea2229b3513aa59e659774fe8ce44cdd81859`, SHA-256
  `d0109a37a06f91aff137a27f26433f6dbc6696f28db21514e7f63cc97c13b2d4`.
  Fixture source worktree HEAD is separately `fb933961...`; the manifest's older
  `90b6d58...` source declaration is not treated as runtime proof. Assembly
  revision metadata is recorded as reported, not a reproducible-build claim.
  The product-list source is unchanged between the reported assembly revision
  and the fixture HEAD; its permitted load/search handlers do not save records.

Live completion is recorded separately after the single authorized pilot.

## Earlier completion: PARTIAL GO / BLOCKED_USER_AUTHORIZATION

The first launch on source commit `04cad1ea7c84237133e7ca0c71166ebce4b2c446`
opened the separate SQBF account-selection page at approximately 14:10 UTC.
No callback arrived within five minutes; the process stopped with the sanitized
authorization timeout, **exit 1**. No token exchange, model catalog request,
reviewer compatibility inference or benchmark was performed. There is no Run-ID,
UX score or benchmark PASS to report. The earlier provider-image test remains a
separate completed test and is not counted as this benchmark.

The CLI now handles that condition with `BLOCKED_USER_AUTHORIZATION`, **exit 2**,
without a traceback or starting an inference/runner; this is covered by mocks.
After the timeout, the profile details were moved out of the generic core and
the final suite contains **65/65 tests passed, no skipped, exit 0**. Guarded live
preflight is independently rechecked against the unchanged fixture; it is not
reported as a KI benchmark.

The smallest next step is a fresh interactive SQBF authorization followed by
one reviewer compatibility test and exactly one CORE-SMOKE-01 pilot. There is no
automatic login retry loop. Portfolio expansion from #16 remains gated on the
actual multiagent pilot's GO.

## Actual pilot completion, 2026-10-13: NO-GO

The fresh, separately authorized SQBF login completed successfully. The live
account catalog allowed `gpt-6-luna` and `gpt-6.1-sol`. The single synthetic
reviewer compatibility request passed image interpretation and strict JSON
output with `gpt-6.1-sol`: 143 input, 19 output, 162 total tokens. No tools were
offered, no API key was used, and bearer tokens remained in process memory.

Exactly one pilot was attempted on SQBF commit
`2116fc867c0cd619deeecde12abb9714a2e7c848`:

- Run-ID: `f9b0f20a-39ed-4694-a888-e53dbc3e858c`.
- Start: 2026-10-13 19:38:01 Europe/Berlin; duration: 2.83 seconds.
- Technical result: FAIL; executor status: ERROR.
- UI actions: 0/10; pilot model calls: 0/12. The prerequisite synthetic
  reviewer request above is separate from the pilot call counter.
- No pilot screenshot was captured and no UI task step completed. No UX
  scores or reviewer verdict exist; none are inferred from the synthetic test.
- Independent before/after snapshots match for the exact isolated database,
  identity, all ten protected table counts and all ten row hashes.
  `database_unchanged=true`. Overall Oracle FAIL reflects missing search,
  cleared-filter and completion evidence, not an observed database change.
- The command tool reported exit code 1. No automatic retry followed.

The event log records a fail-closed RuntimeError before the first screenshot.
A separate controller-only diagnostic repeated the initial page load, without
model calls or UI interactions: the same stored BLE session resolves `5080/`
to `/login` (HTTP 200, no blocked requests). The pilot rejects this path as an
unapproved page/session. The formerly usable session is currently
unauthenticated; its precise expiry/revocation cause was not established.

Local archive:
`D:\Temp\sqbf-core-smoke-runs\f9b0f20a-39ed-4694-a888-e53dbc3e858c`.
It contains run/report/scores/findings/events/evidence and before/after Oracle
JSON files, and is searchable in the local `index.jsonl`. Empty evidence,
scores and findings accurately represent this aborted attempt. The prerequisite
reviewer compatibility result is retained in `run.json`.

**Completion: NO-GO.** The earlier 65/65 local tests passed at the tested source
commit; they do not establish a valid current BLE session or a successful
workflow. The smallest next step is a fresh authorized Laborleitung session in
the isolated 5080 instance, verified immediately before a separately released
pilot. No further pilot was run. Portfolio implementation from #16 remains
gated on actual GO. No database writes/resets, BLE code changes, GitHub Actions,
main changes or merge were performed.

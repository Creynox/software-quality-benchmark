# NSN014 calibration contract — 2026-10-15

## PO decisions implemented

- Active suite v0.3: twelve tasks ending at evaluation and available PDF output.
- Release, signature and delivery are excluded from this active series. If PDF
  needs release, record that dependency as a finding; never bypass a control.
- Four distinct functional accounts: laboratory lead, laboratory staff, WPK and
  plant lead. WPK uses its existing separate Laborleiter account; plant uses
  Viewer. No new privileges or roles are granted.
- Separate task/session for each working actor; an independent reviewer assesses
  evidence. Reviewer judgement is not a laboratory release or database proof.
- Historical v0.1/v0.2 and actual previous runs remain unchanged.

## Limits and accounting

The initial task marks are 600 seconds and 60 actions. Crossing them is recorded
without ending a task or assigning a product FAIL. They can later be calibrated
per task from observed runs. They are not a validated human performance baseline.

The provisional global safety ceiling is 7,200 seconds and 1,000 model requests
across executor and reviewer. One request can contain many input/output tokens;
1,000 requests is not 1,000 tokens and is not the intended amount to consume.
No reliable consumption estimate exists for the full series yet. Usage must be
measured rather than inferred from a subscription or fabricated from call counts.

`sqbf.calibration` provides controller-only reservations, per-actor token totals,
unknown-usage counts, total elapsed/model wait/other elapsed time, and per-task
mark exceedances. Failed requests count; no retry or overlapping requests are
allowed by the accounting bridge. Only numeric accounting fields are retained.
`ask_calibrated` reuses the existing isolated tool-less worker and subscription
provider enforcement. Model responses still have the existing individual worker
timeout. Safety and permission guards remain independent mandatory gates.

Hard resource stops are INCONCLUSIVE, not product failure. The suite aggregator
rejects PASS or FAIL carrying these stop reasons. CORE and LAB budgets are
unchanged. This module alone does not make the twelve pending stage adapters
executable; no live suite command has been enabled by this change.

## Local verification

- Project venv: `D:\Entwicklung\Benchmark\.venv\Scripts\python.exe`.
- `python -m unittest discover -s tests -p test_calibration.py -v`:
  **11 tests, PASS, exit 0**; synthetic/mock requests only.
- `python -m unittest discover -s tests -v`:
  **212 tests, 20.551 seconds, PASS, exit 0**.
- Tests cover soft marks, deadline during response wait, executor/reviewer
  request counting, incomplete token telemetry, failed calls without retry,
  provider rejection, resource-result classification, task/actor mapping and
  unchanged historical pilot limits.
- A new private v0.3 fixture manifest binds the unchanged fixture/dataset to the
  updated suite hash. Original manifest and sessions are retained.
- Model-free real fixture check: **exit 1 / BLOCKED_SUITE_FIXTURE / SESSION_FAILED**.
  Separate staff session check: **BLOCKED_SESSION / UNEXPECTED_PAGE**, first
  context's home request redirected to `/login` with HTTP 200. This is evidence
  that the saved session is currently unusable; it does not prove whether it
  expired or was invalidated. Identity/scope checks were not reached.
- No login, model request, benchmark, source mutation, database reset, Actions,
  OAuth operation or merge was performed by this change.

## Completion and next work

**PARTIAL GO for setup; no live readiness claim.** Contract and accounting tests
pass. Actual stage adapters, task-specific write guards, measurement/PDF Oracles
and complete orchestration/reporting remain to implement and test. Before any
future run, sessions and all independent gates must pass again. The earlier
fixture acceptance must not be reused as proof of a currently authenticated user.

Private evidence files are under `D:\Temp\sqbf-nsn014-implementation-20261014`
and `D:\Temp\sqbf-nsn014-fixture-20261014`. They include the full test log,
new manifest and current acceptance report; credentials/cookies are not copied
to this report or GitHub.

# NSN014 start fixture acceptance — 2026-10-15

## Accepted scope

PO start state: products and plan prepared; the agent creates probes and replays
recorded measurements. Separate lead/staff/WPK/plant accounts reuse unchanged
Laborleiter/Mitarbeiter/Laborleiter/Viewer roles. Norm certification excluded.

New owned Web **5082**, PostgreSQL **55434**, Docker volume and private content
root. Actual binary commit **c51ea2229b3513aa59e659774fe8ce44cdd81859**;
SHA-256 `d0109a37a06f91aff137a27f26433f6dbc6696f28db21514e7f63cc97c13b2d4`.
This accepted build is distinct from the fixture worktree HEAD. Seeding, background
WPK scheduling, Sentry and external weather/geodata providers are disabled.

Prepared counts: 10 products, 1 plan, 10 positions, 25 source norm assignments,
16 standards/versions, 1 synthetic customer/project, **zero probes/LIMS/reports**.
Golden remains at 15 standards/versions: one existing DIN13242 parent/version
snapshot was copied into the new copy from the normal source, not invented or
updated. Actual Create UI requires customer/project: SQBF Enzberg / SQBF NSN014
supplies synthetic context. Samples are plant-owned; lab ownership is separate.

## Independent acceptance

`suite-fixture-check`: exit0, **FIXTURE_GATES_VERIFIED**. Four actors restore in
two new browser contexts with navigation/reload; independent signed identity,
non-admin role, exact existing permissions, tenant and Enzberg scopes pass.
Fixed credential-free controller projection uses READ ONLY/ROLLBACK. Oracle
has no writes or SELECT on Identity/data-scope tables. Models see none of this.
Protected/golden snapshots unchanged; original-source queries only READ ONLY.

## Preparation corrections

- PostgreSQL temporary socket readiness preceded final TCP. First role command
  did not execute. Inspection proved the new copy empty; guarded completion
  restored it. Readiness now requires TCP. No reset/recreation.
- Historical Asphaltsplitt16/32 is currently inactive: retain ten plan items,
  while default active list has nine. Context, not yet a measured defect verdict.
- Names also occur in detail panel: session checker now uses a unique table row.
- Three new accounts' first login attempts failed. Generated credentials verified
  internally; each then passed one corrected stable-form login with one guarded
  POST and redacted 302/fields-match diagnostics. Initial cause not captured;
  hydration timing is a hypothesis. No benchmark retry. Automatic login now waits
  for network stability by default. No secrets exposed.

## Guard and Oracle

Receipt guard restricts fields/values and controls, forbids browser shortcuts,
and latches one save in native sessionStorage plus mandatory controller state.
Mock/native-browser regressions pass; full Runner integration remains pending.
Read-only Oracle verifies exact codes, owner/tenant/product, date, customer/project,
plan linkage and Probe-ID/LIMS FK. Extra/duplicate/orphan/missing rows fail.
Real before-phase verifies zero probes; after-phase PASS has synthetic test
evidence only. No probe saved. Create form inspected without clicking its save.

Dotnet helper/verifier builds: exit0, zero warnings/errors. Full local Python
suite: **201 tests, 23.274s, exit0**, including the final origin guard, stable-login and evidence
aggregation adjustments. A complete valid measurement can contain application
FAIL results: `measurement_status=COMPLETE_VALID` remains distinct from task
outcomes; unsupported/unverified trials never count as valid application failures.
Auth messages in test output are mocks. No model/OAuth/live benchmark operation.

## Overall status

**PARTIAL GO**: fixture/persona gates accepted. Remaining: stage Runner adapters,
measurement persistence checks, bounded orchestration and measured acceptance.
PO budgets and release/signature/local-delivery scope are pending. No Actions,
merge, source-data update or historical-session/run modification.

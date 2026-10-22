# Issue #18: technical repair and local acceptance

## Scope and result

The repair was implemented from `6e52565973f563ffa123495ceab6cddb4a7ed408` in
the existing dedicated SQBF feature worktree. Git status/worktrees/fetch/ff-only
pull verified that baseline. Existing dirty/detached worktrees, sessions and
historical run artifacts were preserved. No BLE code, DB, model login or live
benchmark was used for this repair. No research, Actions, main change or merge.

**GO for the locally tested technical repair.** A new real end-to-end benchmark
has not been performed; Issue #17's successful multiagent workflow remains open.
The historical fifth action cannot be recovered from the old run's artifacts.
The mock uses an unsupported shortcut to reproduce the failure class; it does
not prove the exact cause of run `28db660c-2faa-49bb-90b8-894ad2ca9cab`.

## Changes

1. Fixed action-validation codes replace arbitrary error strings. Before
   validation, `action_received` records only an allowlisted action/key label;
   unsupported labels become `REDACTED`. `action_rejected` retains the turn and
   fixed error code. No rejected raw JSON, reason, typed text or arbitrary key
   is persisted. Stop and no-retry behavior remain enforced.
2. `SEARCH_KEYS` is the single canonical list for the read-only JSON key enum,
   executor protocol and focused-search guard. The global validator remains
   stricter than unrestricted browser keyboard access. `ControlOrMeta+A`,
   `Backspace`, `Delete`, `Enter` are permitted only in the approved search
   field. Aliases and compound shortcuts are rejected, not translated.
3. Monotonic measurements wrap each bounded executor/reviewer call, including
   failed/timeout calls. Started/finished events retain stage and measured
   duration. A normally returned worker supplies measured model-wait totals;
   parent wallclock minus model wait yields non-model runner/supervisor/oracle
   time. Hard worker termination marks complete wait/active durations unknown
   and retains completed-call durations only as a lower bound. Missing report
   times display “nicht gemessen” instead of fabricated zero/full wallclock.
4. `Evidence` establishes and verifies current-user-only Windows directory ACLs
   before the first artifact write. Worker attachment independently verifies
   those ACLs before browser/model execution. Inheritance grants owner-only
   access to generated screenshots/events/reports/oracles. POSIX requires 0700
   owner-only directories. The registry reserves a new protected file before
   content write and atomic replacement (0600 on POSIX). Permission failure
   stops without an artifact payload, Oracle or model dispatch. Existing
   artifact directories and old index files are not modified by this repair.

## Local regression evidence

Command, using the existing project venv:

```powershell
D:\Entwicklung\Benchmark\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**93/93 PASS, no skipped tests, exit 0**, including the existing 81 regressions.
Log: `D:\Temp\sqbf-issue18-tests.log`.

New local tests establish:

- Four mocked actions, fifth unsupported key: `KEY_NOT_ALLOWED`, redacted key,
  no fifth UI dispatch, no sixth model call, no reviewer or retry, no canary
  secret in any generated JSON.
- Canonical select/delete flow and reviewer complete with unchanged focused
  guards; schema/prompt/validator/guard use the same canonical protocol.
- Deterministic fake clock: five two-second mocked calls measure 10 seconds
  model wait and 12.6 seconds worker wallclock; parent case reports 14 seconds
  total = 10 seconds model + 4 seconds non-model overhead. Reviewer and timeout
  durations are included. These are test measurements, not real model latency.
- Hard-worker abort retains only a measured lower bound and reports unknown
  complete durations. Missing timing values never default to zero.
- Private Windows ACLs are inspected on real temporary artifact directories,
  first screenshots and registry replacement. Failure gates prevent artifact
  contents, browser, Oracle/model calls; no other user's permissions are
  weakened. Synthetic browser/process tests remain offline.

## Historical live evidence and PR status

The old PR description's “no real BLE session” claim is obsolete. Two actual
CORE-SMOKE-01 attempts are documented in Issue #17/PR #10:

- `f9b0f20a-39ed-4694-a888-e53dbc3e858c`: stopped at expired BLE session,
  0 UI actions/0 pilot model calls, 2.83 seconds, NO-GO.
- `28db660c-2faa-49bb-90b8-894ad2ca9cab`: 4 UI actions/5 Luna calls,
  25.90 seconds, search/empty evidence present, validation stop before reset,
  no workflow reviewer, protected DB unchanged, NO-GO.

The fresh-session and provider compatibility proofs exist separately. No
complete real workflow, successful filter reset, workflow reviewer score or
production readiness is inferred from this mock repair. PR #10 stays Draft.

Next step: review the repair/test evidence and decide on a new explicit single
CORE-SMOKE-01 execution order under the standing PO authorization. This repair
does not automatically start or schedule that run.

# Regular BLE benchmark setup — 2026-10-14

Status: **IN PROGRESS / BLOCKED_DATA_REVIEW**, not a completed benchmark environment.

## PO scope and reference

The PO requested a complete Enzberg test series including laboratory workflow,
WPK and multiple functional personas. Use one clearly defined existing plan with
original measurements; do not invent raw measurements or substitute synthetic
values without explicit authorization.

W25 was absent from the inspected `ble` / `ble_dev_clone` sources. NSN 018,
05.06.2026, was selected. The initial choice of its nine database positions was
subsequently corrected by the PO: this week uses SP 2/8, SP 8/16 and KSM
Abmagerung; not BS 0/1, BS 1/2 or KSM Kost. The visible original plan has ten
positions. The original database is preserved and its mismatch is evidence,
not a reason to silently change source records.

The current NSN014 suite is a **draft contract**. All fourteen stages remain
`pending`; neither a case catalog nor a successful contract check constitutes
runtime acceptance. The PO's preference is an example already entered personally
in BLE. The PO subsequently selected an already recorded earlier plan for joint
comparison. NSN014 (08.05.2026) is now the active candidate; NSN018 is retained
as a superseded reference investigation. No re-entry or synthetic substitute
was requested for the new candidate.

## Verified data findings

Read-only, bounded PostgreSQL transactions inspected the explicitly identified
normal source container and selected plan. No source writes, resets or migrations
were executed. The normal source is not a benchmark execution target.

- NSN018 has nine linked samples, five `Teilweise` and four `Neu`, without
  release/sign-off. Plan status `Abgeschlossen` does not establish lab completion.
- No NSN018 Kornform masses, sand-equivalent or boiling results were found in
  the workspace tables, nor legacy STS tests or linked `lims_sample` records.
- The older `lims_sieblinie_ergebnis` / `lims_sieblinie_punkt` tables contain two
  NSN018 skeletons with null initial masses and `NichtBerechenbar`. These tables
  must not be confused with the current runtime's newer sieve table names.
- Enzberg Kornform raw rows exist for dates 06.02.–13.05.2026. Lack of values
  for NSN018 is not evidence that all original database measurements are absent.
- Candidate NSN014 (08.05.2026) has ten samples marked `Vollstaendig`, ten sieve
  initial masses, fourteen particle-shape fraction rows, one sand-equivalent row,
  four boiling rows and eleven report entries. Its STS has six actual mass pairs
  (`DataOrigin.Real`). It matches the original ten-position plan, and the six raw STS mass ratios
  round to the six visible report percentages. It is not yet an approved oracle:
  sand-equivalent repetition 2 differs (DB h1 12.1, report 12.2); original unit
  confirmation is pending. Main sieve partial points are placeholders. Correct FK traversal through
  `lims_sample.probe_id` finds two actual LIMS partial series (268.5 g each);
  their five summed masses exactly match the original sheet. An initial lookup
  incorrectly equated Probe-ID and LIMS-Sample-ID; corrected before acceptance.
  Metadata marks partial-sieve Completed while other work items remain Pending.
  Preserve these source distinctions instead of treating status as proof.
  Latest PO decision: stored DB inputs are authoritative; do not replace the
  different sand-equivalent repetition with paper data or convert its unresolved
  physical unit automatically.

Stored STS assignment uses TL SoB-StB 2004/2007; the report names TL SoB 20.
This is an open edition mismatch, not proved equivalence and not permission to
create a replacement norm or change source assignments.

Original PDF copies, hashes, visual renderings and constrained database
projections remain in a private evidence directory outside Git. Hidden/stale PDF
text is not accepted as a visible measurement. Missing values remain unknown,
not zero. The NSN018 STS report includes an oversize warning and `mdv = jein`;
blanket conformity/release must not be inferred from its summary.

## Implemented in this setup step

- Generic `sqbf.cli suite-check --suite ... --dataset ...`, with zero browser,
  authentication, model or database operations and controlled exit code 2 for
  missing/invalid/unreviewed contracts.
- Versioned suite identities, ordered explicit prerequisites, per-case bounds,
  subscription-only provider, no automatic retry, physical simulation and no
  real delivery constraints.
- Dataset approval tied to its canonical content hash; empty/missing inputs,
  missing expectations and unresolved questions cannot be approved by a flag.
  Mismatched dataset identity or position set blocks the suite.
- Exact result aggregation: missing/pending cases stay in the denominator;
  `INVALID` is distinct from product `FAIL`; `PASS` requires independent technical
  and oracle gates plus the literal boolean evidence confirmation. No arbitrary
  normalized score is created.
- Comparison identity holds suite, data, evaluator versions, viewport and browser
  fixed while allowing target builds to differ.
- Populated-fixture session checking requires an explicit expected product list,
  rejects the empty state, checks two fresh browser contexts and reloads. Original
  CORE empty-state behavior remains the default. This is UI restoration evidence,
  **not** independent signed identity or authorization evidence.

## Local validation

Project venv: `D:\Entwicklung\Benchmark\.venv\Scripts\python.exe`.

```powershell
python -m unittest discover -s tests -v
python -m sqbf.cli suite-check --suite projects/ble-elva/suites/enzberg-nsn014-v0.1.json --dataset <private-candidate.json>
```

Full suite: **158 tests, 35.542 s, exit 0**. Includes suite safety, exact
aggregation, generator records, strict evidence boolean, incomplete data,
approval invalidation, dataset mismatch, CLI redaction and populated/empty
session regression cases. The unreviewed NSN014 candidate correctly produces
`BLOCKED_SETUP / BLOCKED_DATA_REVIEW`, exit 2. Independent profile arithmetic checks mean-of-two-ratios sand equivalent,
combined-fraction particle shape and rejection of missing/impossible inputs.
Neither those calculations nor a report label establishes norm conformity.
No actual model or OAuth operation
was performed; mocked authorization messages from tests are not live operations.

## Remaining implementation and acceptance

1. Settle the actual recorded reference plan, verify original raw inputs and
   approve expected rounding, units, conformity/hold decisions and recipe mapping.
2. Build a separate reproducible suite fixture from a controlled projection:
   products/standard snapshots, customer/project, ten plan positions and distinct
   benchmark identities. Never run the executor against the normal source.
3. Verify populated-session and per-persona signed scope gates. Functional WPK/
   plant personas are not automatically distinct existing BLE security roles.
4. Implement and test stage-specific write guards (including autosave), independent
   persistence oracles, role checks and local report/delivery sink. Current LAB01
   single-product guards are not a safe general workflow guard.
5. Complete bounded orchestration and actual end-to-end acceptance, preserving
   immutable historical CORE/LAB artifacts and avoiding automatic retries.

No live benchmark, no merge, no GitHub Actions and no claim of full readiness.

## Historical PO clarification: physical sand-equivalent unit (superseded)

On 2026-10-14 the PO confirmed that the stored height 12.2 means 12.2 cm.
The existing BLE page labels the direct `SandHeightMm` / `SuspensionHeightMm`
values as mm and forwards them without conversion. Preserve the legacy source
rows unchanged. The new fixture/oracle projection must explicitly convert cm
to mm: repetition A 95/122 mm, repetition B 96/121 mm, mean of individual
ratios 78.6038477%. Paper repetition 2 is not substituted. This initial clarification was subsequently retracted; see the current evidence below. Norm context, release expectations and runnable stage gates remain
open; this is not full suite readiness.

The independent conversion helper rejects unknown units, preserves the source
dictionaries and both repetitions, and proves ratio invariance in local tests.

Unit follow-up validation: full project-venv suite **160 tests, 35.465 s, exit 0**.
Unknown source units fail closed; cm/mm equivalence, exact 95/122 and 96/121
projections, two-repetition retention and source immutability are covered.

## Historical correction: source unit temporarily unconfirmed

The PO subsequently withdrew certainty about cm. The uploaded primary document
DIN EN 933-8:2015-07 was inspected directly: section 6.5 specifies a metric ruler,
section 8.5 (printed page 14 / PDF page 16) records both heights to the nearest mm.
Section 9 specifies individual ratios to one decimal and the mean rounded to a
whole number. Method units do not establish the historical entry convention.

Accordingly the active profile now declares UNCONFIRMED and forbids conversion.
The earlier factor-ten projection is a proposal only; source rows remain unchanged.
The ratio is invariant when both heights use the same scale, so the stored
percentage cannot independently settle cm versus mm. No live run or DB write.
Future standard updates must use the available uploaded editions and verified
applicability; the 2004/2007 versus TL SoB-StB 20 mismatch remains documented.

See [unit evidence](sand-equivalent-unit-evidence.md). Last code test result
remains 160 tests, exit 0; this correction changes metadata/documentation only.

## Current PO reconfirmation

The PO reconfirmed original cm entries after the measurement endpoints were
explained. The active unit contract is cm -> mm (factor 10), retaining A 95/122
and B 96/121 mm. The norm specifies the target unit; the PO identifies the
historical entry convention. This resolves the unit blocker only. No production
rows changed and no normative release or full-suite approval is inferred.

## Reference preparation implementation — 2026-10-14

Implemented `sqbf.cli reference-project`, a pure controller-side projection of
all ten recorded positions. New private output is reserved exclusively before
writing, cannot overwrite a prior file and is rejected inside a Git worktree.
Source and unit-decision SHA-256 bind the output to reviewed input versions.
Credentials, identity/source row IDs and stored calculated verdicts are omitted.

Original raw sieve, wash, shape, boiling, actual partial-series/preparation and
repeated SÄ readings survive. SÄ is projected from confirmed cm to mm, retaining
both repetitions. Missing SQL aggregates remain explicitly unrecorded; they do
not become synthetic measurements or automatically non-applicable modules.
Independent arithmetic proposals remain separate from conformity/release.
The pure comparison blocks missing, extra, duplicate or changed measurement
records, and emits mismatch identifiers only. It is not yet a DB persistence
adapter and is not exposed to the screenshot Executor/Reviewer.

`session-check --expected-products <private-name-array.json>` now supports the
populated-fixture UI contract. Empty fixture checking is still the default.
Malformed expectations stop before opening a browser. Session-check output is
now also a new private file, never an overwrite. Neither mode proves identity;
the independent signed identity/role/scope gate remains mandatory.

### Local evidence

- Full project-venv tests: `python -m unittest discover -s tests -v`;
  **171 tests, 19.562 seconds, exit 0**.
- Actual ten-position projection: exit 0, PREPARATION_ONLY; zero DB writes/model calls.
- Golden fixture independently identified on loopback 55432: before/after
  snapshots identical; products/samples/LIMS/reports/assignments remain zero,
  standards/versions remain 15. Source port 5433 was not used in this step.
- No OAuth or live benchmark operation; printed auth messages in tests are mocks.

### Next dependency

The PO is being asked whether to reproduce the historical DB standard context
with the edition mismatch recorded and normative release held, or first update
only the new isolated fixture using verified available editions. No original
standard assignment is modified. Full suite stays BLOCKED_DATA_REVIEW; no stage
is marked implemented solely because projection/session helpers are tested.
Remaining work: populated disposable fixture, per-role gates, stage write guards,
DB persistence adapters and bounded workflow/report acceptance.

## Current PO scope: UX/UI/process stress, not normative certification

The PO explicitly selected the currently entered DB data and existing standard
assignments unchanged. Active contract: `enzberg-nsn014-v0.2.json`. The private
source-replay dataset is approved for this limited purpose with content-bound
SHA-256; this is not approval of normative conformity, mathematical perfection
of historical stored outputs, role/runtime gates or actual full-suite readiness.

No norm update is required before these tests. Assessment/release/WPK/report
cases observe software workflow, controls, feedback, persistence and gaps. A
release interaction in a disposable test fixture is not a real-world normative
release. An application FAIL is a valid, useful result with independent evidence;
we must not fix the product during its measured test. Safety/session failure is
BLOCKED; harness failure is INVALID. No automatic retries or unbounded load.

Missing functionality belongs to application findings once a safe test adapter
exists, whereas an unimplemented adapter remains pending and cannot invent a
finding. Independent fixture checkpoints should cover later stages safely when
an earlier product failure prevents the end-to-end path; each missing prerequisite
must remain explicit. No direct DB access for executor/reviewer.

The old normative-choice question is resolved. Full suite-check correctly still
returns BLOCKED_SETUP for 14 pending test adapters, with DATASET_APPROVED for
source replay. Next implementation dependency is the separate populated fixture
and safe stage/role/persistence adapters, not further norm correction.

Scope validation: full project-venv suite **173 tests, 20.251s, exit 0**.
Actual UX-source projection exit 0; suite-check exit 2 (correct pending adapter
block), with DATASET_APPROVED, 14 pending cases and zero model calls/DB writes.
Verified isolated target schema read-only: 118 selected column definitions,
including actual product/tenant/material/classification fields. No Identity or
credential table contents selected. This metadata supports upcoming fixture
population without guessed schemas. No source5433 operation or DB mutation.

## Start fixture accepted — 2026-10-15

See [NSN014 fixture acceptance](nsn014-fixture-acceptance.md): new Web5082/PG55434,
ten products/positions, zero probes and four independently verified actor sessions.
Receipt guard and Oracle have local regressions; full stage Runner integration
remains pending. No regular-suite live run yet.

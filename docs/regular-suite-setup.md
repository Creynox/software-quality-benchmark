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

The current NSN018 suite is a **draft contract**. All fourteen stages remain
`pending`; neither a case catalog nor a successful contract check constitutes
runtime acceptance. The PO's preference is an example already entered personally
in BLE. A switch to a more fully recorded earlier plan or manual completion of
NSN018 is pending the PO's data decision.

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
  (`DataOrigin.Real`). This is a candidate for verification, not an approved
  complete oracle: raw presence/status alone does not establish correctness.

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
python -m sqbf.cli suite-check --suite projects/ble-elva/suites/enzberg-nsn018-v0.1.json --dataset <private-candidate.json>
```

Full suite: **154 tests, 35.724 s, exit 0**. Includes suite safety, exact
aggregation, generator records, strict evidence boolean, incomplete data,
approval invalidation, dataset mismatch, CLI redaction and populated/empty
session regression cases. The unreviewed NSN018 candidate correctly produces
`BLOCKED_SETUP / BLOCKED_DATA_REVIEW`, exit 2. No actual model or OAuth operation
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

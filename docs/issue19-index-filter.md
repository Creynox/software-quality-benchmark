# Issue #19 — exact Run-Index verdict filtering

## Repair and acceptance

**GO.** `sqbf.cli list-runs` previously applied substring comparison to every
text field, including the structured result. Therefore GO also matched NO-GO
and PARTIAL GO. One pure shared `sqbf.registry.filter_runs` now uses exact,
case-sensitive comparison for result and run identifier. No other registry
filter implementation was found. No historical verdict or manifest is rewritten.

Test ID, software version and date intentionally retain case-sensitive substring
matching. Persona/executor/reviewer role search remains case-insensitive substring
matching; score filtering is unchanged. All supplied filters combine with AND.
The CLI additionally exposes `--run-id` for exact lookup of existing immutable
identifiers; this option was absent before the repair. The old record identity
and independent ID lookup semantics are preserved, not falsely described as an
existing CLI flag. Unknown/partial result strings cannot match another verdict.

## Offline regression evidence

Existing venv command:

```powershell
D:\Entwicklung\Benchmark\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**119/119 PASS, zero skipped, exit 0**, 10.847 seconds. Nine new regression tests
use synthetic GO/NO-GO/PARTIAL GO records: disjoint exact verdicts, combined
scenario/date/result filters, retained free-text/role semantics, exact ID lookup,
unknown/partial/case-mismatched results, no inflated pass count or derived rate,
unmodified source records/files, CLI flags and missing-index behavior. Existing
110 tests pass. No aggregation feature was added; the synthetic derived pass
count is one out of three rather than all three substring matches.

## Existing real index — read only

Commands run with the existing venv, same output/test/date filters and each exact
verdict; all exit 0:

```powershell
python -m sqbf.cli list-runs --output D:\Temp\sqbf-core-smoke-runs `
  --test-id CORE-SMOKE-01 --date 2026-10-13 --result GO
```

- GO: only `04bd06b3-f868-4390-b7d6-3df67e9cb85f`.
- NO-GO: only `28db660c-2faa-49bb-90b8-894ad2ca9cab` and
  `f9b0f20a-39ed-4694-a888-e53dbc3e858c`.
- PARTIAL GO: no existing real record; synthetic coverage passes.
- SHA256 before/after comparison: **all 44 existing run/index files unchanged**.

Private completion evidence: `D:/Temp/sqbf-issue19-20261013/`, including tests.log,
real-index-check.json and artifact-hashes-before.json. No live benchmark, model
call, OAuth, DB connection/change, Actions/main/merge or run regeneration occurred.

## Independent Issue #17 acceptance

Issue #17's actual single-run evidence already satisfies its bounded scope:
six valid visible actions, complete search/reset, separate actual Sol review,
objective unchanged-data Oracle, role/provider/build identity and local searchable
archive. Issue #19 was a separate result-query defect, not a failed live run.
It neither changes historical GO nor requires another pilot. No native Project
items exist on #17/#19; no fictitious Project status is claimed. Formal completed
issue state can be recorded independently; PR #10 remains Draft as requested.

Next step: review PR #10's accumulated implementation and acceptance evidence.
Any additional benchmark or populated-data fixture work needs a separate scoped
order; this repair does not expand the benchmark suite.

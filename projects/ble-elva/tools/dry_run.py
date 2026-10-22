"""Modelless dry run, and rehearsal with a Claude executor, of the complete NSN014 suite code path on a disposable scratch fixture.

Everything a live run executes is real here: persona scope checks, the stage runners, both guards (event script and controller
check), the transport policy, the side-effect contract per stage, the independent Oracles and the final gates. Only the models are
replaced: the executor by a scripted stand-in that acts through the same strict JSON actions (scripted_executor.py), or in a rehearsal
by a Claude model through the local Claude Code CLI (claude_executor.py), and the reviewer by a fixed neutral review.

Why it exists: live run 413f7abe lost ten of twelve stages to guard defects (menu entry not recognised, a primary page action not
permitted, one rejection ends the task) that an earlier dry run could not see, because it bypassed the guards. Run this before every
live run, on a fresh scratch clone (suite-fixture-clone --purpose scratch); it refuses any other fixture because it writes. A rehearsal
adds what a script never does (half-saved entries, wrong clicks, give-ups): live run 824fa661 lost its report stage to such a state.

Both write the same run documents as a live run (run.json, cases.json, accounting.json, completion report, scorecard, points report), labelled
DRY_RUN or REHEARSAL, so the reporting path is exercised before every live run. Neither is ever a benchmark result.

A rejected scripted action is a finding about the guards, not about BLE: the script only ever does what a careful user may do.
"""
import json
from pathlib import Path
from unittest.mock import patch

from sqbf.artifact_privacy import check_private_directory
from sqbf.calibration import SuiteBudget
from sqbf.models import Scenario
from sqbf.reporting import Evidence, now_iso
from sqbf.suites import validate_suite, canonical_hash

from . import inspection_runner, measurement_runner, regular_runner as rr, stage_effects
from .scripted_executor import ScriptedExecutor
from .stage_support import REVIEW_SCHEMA

NEUTRAL_REVIEW = {'verdict': 'INCONCLUSIVE', 'reason': 'scripted dry run, no review', 'scores': dict.fromkeys(
    ('findability', 'clarity', 'task_progress', 'error_recovery'), None), 'findings': []}
KIND_LABELS = {'DRY_RUN': 'skriptierter Trockenlauf', 'REHEARSAL': 'Probelauf'}


class DryRunRefused(RuntimeError):
    pass


def require_scratch(fixture):
    """The dry run writes (plan samples, entries, reports): only a disposable scratch clone may be used, never a fixture of a run."""
    clone = fixture['suite_copy'].get('clone') or {}
    if clone.get('purpose') != 'scratch':
        raise DryRunRefused('NOT_A_SCRATCH_FIXTURE')
    if (Path(fixture['suite_copy']['application_root']).parent / 'benchmark-consumed.json').exists():
        raise DryRunRefused('FIXTURE_ALREADY_CLAIMED')


class _Spy:
    """Transparent proxy that remembers the page the runner currently drives (the scripted executor reads its DOM for coordinates)."""

    def __init__(self, inner, holder):
        self._inner, self._holder = inner, holder

    def __getattr__(self, name):
        return getattr(self._inner, name)


class _SpyContext(_Spy):
    def new_page(self):
        page = self._inner.new_page()
        self._holder['page'] = page
        return page


class _SpyBrowser(_Spy):
    def new_context(self, **kwargs):
        return _SpyContext(self._inner.new_context(**kwargs), self._holder)


def _neutral_review(ask, reviewer, prompt, images, budget, evidence, **context):
    return dict(NEUTRAL_REVIEW), None


def summarize(records, manifest, actions, *, kind='DRY_RUN'):
    cases = []
    gaps = []
    for record in records:
        positions = record.get('positions', [])
        rejected = list(record.get('rejected_actions', [])) + [r for p in positions for r in p.get('rejected_actions', [])]
        item = {'case_id': record['case_id'], 'result': record.get('result'), 'reason': record.get('reason') or record.get('stop_reason'),
                'rejected_scripted_actions': rejected, 'side_effect_findings': record.get('side_effect_findings', []),
                'audit_only_changes': record.get('audit_only_changes', []), 'tasks': len(positions) or 1}
        if record.get('position_results'):
            item['position_results'] = [(p['position_id'], p['result'], p.get('class')) for p in record['position_results']]
            item['outcomes'] = [{k: p.get(k) for k in ('position_id', 'kind', 'status', 'fields_required', 'fields_entered', 'fields_offered',
                                                        'fields_not_offered', 'offered_entered', 'fully_entered', 'test_order_created', 'executor_error_code')} for p in positions]
        cases.append(item)
        gaps += [dict(r, case_id=record['case_id']) for r in rejected]
    final = {k: (v['status'] if isinstance(v, dict) else v) for k, v in manifest.get('final_oracles', {}).items()
             if k in ('receipt', 'measurements', 'allocations', 'reports', 'calculations')}
    final['static_fixture_unchanged'] = manifest.get('final_oracles', {}).get('static_fixture_unchanged')
    final['static_fixture_audit_only_scope'] = manifest.get('final_oracles', {}).get('static_fixture_audit_only_scope')
    harness_stops = [c['case_id'] for c in cases if c['result'] in ('INVALID', 'BLOCKED') or c.get('reason') == 'STATIC_FIXTURE_CHANGED']
    if kind == 'REHEARSAL':
        # A model makes mistakes the guards rightly refuse: rejections are measurements here, only harness stops are findings.
        status = 'REHEARSAL_COMPLETED' if not harness_stops else 'REHEARSAL_FOUND_HARNESS_STOPS'
    else:
        status = 'DRY_RUN_COMPLETED' if not harness_stops and not gaps else 'DRY_RUN_FOUND_GUARD_OR_HARNESS_GAPS'
    return {'status': status, 'kind': kind, 'model_calls': manifest.get('model_calls', 0) if kind == 'REHEARSAL' else 0,
            'scripted_actions': len(actions) if kind == 'DRY_RUN' else 0, 'cases': cases,
            'guard_coverage_gaps': gaps if kind == 'DRY_RUN' else [], 'rejected_actions': len(gaps),
            'harness_stops': harness_stops, 'final_oracles': final,
            'note': 'A rejected scripted action is a guard gap, not a BLE finding. Allocation and shape differences for positions whose approved '
                    'fields BLE does not offer are expected (APPROVED_FIELDS_NOT_PRESENT_ON_PAGE). A rehearsal is never a benchmark result.'}


def run_manifest(kind, run_id, suite, dataset, fixture, projection, allocation, records, accounting, *, executor_model, source,
                 scoped_baseline, contract_sha256, browser_version, started_at):
    """The manifest a live run would write, for a dry run or a rehearsal: same statuses, hashes and accounting, labelled with its kind."""
    summary = rr.aggregate(suite, records)
    critical = any(r.get('technical_gate') == 'BLOCKED' for r in records)
    manifest = {'run_id': run_id, 'run_kind': kind, 'scenario_id': suite['suite_id'], 'scenario_version': suite['version'],
                'software_version': fixture['suite_copy']['runtime']['assembly'].split('+')[-1], 'fixture_id': fixture['fixture_id'],
                'started_at': started_at, 'persona': 'multi-role', 'executor_model': executor_model,
                'analyst_model': 'kein Reviewer (neutrale Antwort)', 'provider': 'claude_cli' if kind == 'REHEARSAL' else 'scripted',
                'scoring_version': rr.SCORING_VERSION, 'rubric_version': rr.RUBRIC_VERSION, 'review_schema_sha256': canonical_hash(REVIEW_SCHEMA),
                'executor_instructions_sha256': rr.instructions_hash(), 'guard_rules_sha256': rr.guard_rules_hash(),
                'sqbf_commit': source['commit'], 'sqbf_source_clean': source['clean'],
                'suite_sha256': canonical_hash(suite), 'dataset_sha256': canonical_hash(dataset),
                'reference_projection_sha256': canonical_hash(projection), 'allocation_reference_sha256': canonical_hash(allocation),
                'protected_scoped_baseline': scoped_baseline, 'side_effect_contract_sha256': contract_sha256,
                'prepared_state_sha256': fixture['suite_copy']['prepared_state_sha256'], 'viewport': {'width': 1280, 'height': 800},
                'locale': 'de-DE', 'timezone': 'Europe/Berlin', 'browser_version': browser_version,
                'resource_policy': suite['resource_policy'], 'budget_approval': {'status': 'NOT_REQUIRED_' + kind},
                'provider_probe': {'status': 'NOT_REQUIRED_' + kind}, 'execution_started': True,
                'model_calls': accounting['model_calls'], 'accounting': accounting, 'summary': summary,
                'technical_status': 'INVALID' if summary['measurement_status'] == 'INVALID' else 'BLOCKED' if critical else 'COMPLETED',
                'functional_status': summary['result'], 'measurement_status': summary['measurement_status'],
                'verdict': 'GO' if summary['result'] == 'PASS' else 'PARTIAL GO' if summary['result'] == 'INCOMPLETE' else 'NO-GO'}
    if accounting.get('stop_reason') and summary['measurement_status'] != 'INVALID':
        manifest.update(technical_status='RESOURCE_STOP', functional_status='INCONCLUSIVE', verdict='PARTIAL GO', stop_reason=accounting['stop_reason'])
    return manifest


def run_dry(suite, dataset, fixture, projection, allocation, folder, *, headed=False, faults=None, executor=None):
    """Dry run with the scripted executor, or a rehearsal when `executor` is given (a ClaudeCliExecutor)."""
    from playwright.sync_api import sync_playwright
    require_scratch(fixture)
    validate_suite(suite)
    kind = 'REHEARSAL' if executor is not None else 'DRY_RUN'
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    check_private_directory(folder, protect=True)
    source = rr.source_state()
    started_at = now_iso()
    contract = stage_effects.load_contract(rr.CASE_IDS)
    scoped_baseline = rr.collect_scoped_hashes(fixture, stage_effects.allowances(contract, fixture))
    budget = SuiteBudget(suite['resource_policy'], on_change=lambda accounting: rr.atomic_json(folder / 'accounting.json', accounting))
    policy = Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json', fixture['target_url']).read_only_policy
    holder = {'page': None, 'case': None}
    if executor is None:
        executor = ScriptedExecutor(lambda: holder['page'], lambda: holder['case'], faults)
    tracker = {'tables': fixture['suite_copy']['prepared_tables'], 'previous': None}
    downloads = folder / 'browser-downloads'
    downloads.mkdir()
    check_private_directory(downloads, protect=True)
    browser_version = None
    with sync_playwright() as p, patch.object(measurement_runner, 'ask_calibrated', executor), patch.object(inspection_runner, 'ask_calibrated', executor), \
            patch.object(measurement_runner, 'ask_review', _neutral_review), patch.object(inspection_runner, 'ask_review', _neutral_review):
        browser = p.chromium.launch(headless=not headed, downloads_path=str(downloads))
        try:
            browser_version = browser.version
            spy = _SpyBrowser(browser, holder)

            def stage(case):
                holder['case'] = case['case_id']

                def run_case():
                    return rr.dispatch(case, spy, fixture, dataset, projection, allocation, policy, object(), object(), budget,
                                       Evidence(folder / case['case_id']))
                return rr.guarded_stage(fixture, contract, case['case_id'], tracker, run_case)

            def write(records, accounting):
                rr.atomic_json(folder / 'cases.json', records)
                rr.atomic_json(folder / 'accounting.json', accounting)
            records = rr.execute_cases(suite, fixture, budget, stage, write=write)
        finally:
            browser.close()
    accounting = budget.report()
    model = getattr(executor, 'model', 'scripted')
    manifest = run_manifest(kind, folder.name, suite, dataset, fixture, projection, allocation, records, accounting, executor_model=model,
                            source=source, scoped_baseline=scoped_baseline, contract_sha256=stage_effects.contract_hash(contract),
                            browser_version=browser_version, started_at=started_at)
    rr.finalise_oracles(manifest, {'records': records}, fixture, dataset, projection, allocation, rr.snapshot(fixture, enforce_counts=False))
    manifest.update(case_matrix=rr.case_matrix(records), ux_summary=rr.ux_summary(records), completed_at=now_iso())
    rr.atomic_json(folder / 'cases.json', records)
    rr.atomic_json(folder / 'accounting.json', accounting)
    rr.write_run_documents(folder, manifest, records)
    report = summarize(records, manifest, getattr(executor, 'log', []), kind=kind)
    report['executor_faults_injected'] = {str(k): v for k, v in sorted((faults or {}).items())}
    report['executor'] = executor.summary() if hasattr(executor, 'summary') else {'kind': 'scripted', 'actions': len(getattr(executor, 'log', []))}
    report['points'] = manifest.get('report_spec')
    (folder / 'dry-run-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return report

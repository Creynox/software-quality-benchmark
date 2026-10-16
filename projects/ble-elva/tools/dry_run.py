"""Modelless dry run of the complete NSN014 suite code path on a disposable scratch fixture.

Everything a live run executes is real here: persona scope checks, the stage runners, both guards (event script and controller
check), the transport policy, the side-effect contract per stage, the independent Oracles and the final gates. Only the models are
replaced: the executor by a scripted stand-in that acts through the same strict JSON actions (scripted_executor.py), the reviewer by
a fixed neutral review. It makes no model request and needs no OAuth.

Why it exists: live run 413f7abe lost ten of twelve stages to guard defects (menu entry not recognised, a primary page action not
permitted, one rejection ends the task) that an earlier dry run could not see, because it bypassed the guards. Run this before every
live run, on a fresh scratch clone (suite-fixture-clone --purpose scratch); it refuses any other fixture because it writes.

A rejected scripted action is a finding about the guards, not about BLE: the script only ever does what a careful user may do.
"""
import json
from pathlib import Path
from unittest.mock import patch

from sqbf.artifact_privacy import check_private_directory
from sqbf.calibration import SuiteBudget
from sqbf.models import Scenario
from sqbf.reporting import Evidence
from sqbf.suites import validate_suite

from . import inspection_runner, measurement_runner, regular_runner as rr, stage_effects
from .scripted_executor import ScriptedExecutor

NEUTRAL_REVIEW = {'verdict': 'INCONCLUSIVE', 'reason': 'scripted dry run, no review', 'scores': dict.fromkeys(
    ('findability', 'clarity', 'task_progress', 'error_recovery'), None), 'findings': []}


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


def summarize(records, manifest, actions):
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
                                                        'fields_not_offered', 'offered_entered', 'fully_entered', 'test_order_created')} for p in positions]
        cases.append(item)
        gaps += [dict(r, case_id=record['case_id']) for r in rejected]
    final = {k: (v['status'] if isinstance(v, dict) else v) for k, v in manifest.get('final_oracles', {}).items()
             if k in ('receipt', 'measurements', 'allocations', 'reports', 'calculations')}
    final['static_fixture_unchanged'] = manifest.get('final_oracles', {}).get('static_fixture_unchanged')
    final['static_fixture_audit_only_scope'] = manifest.get('final_oracles', {}).get('static_fixture_audit_only_scope')
    harness_stops = [c['case_id'] for c in cases if c['result'] in ('INVALID', 'BLOCKED') or c.get('reason') == 'STATIC_FIXTURE_CHANGED']
    return {'status': 'DRY_RUN_COMPLETED' if not harness_stops and not gaps else 'DRY_RUN_FOUND_GUARD_OR_HARNESS_GAPS',
            'model_calls': 0, 'scripted_actions': len(actions), 'cases': cases, 'guard_coverage_gaps': gaps,
            'harness_stops': harness_stops, 'final_oracles': final,
            'note': 'A rejected scripted action is a guard gap, not a BLE finding. Allocation and shape differences for positions whose approved '
                    'fields BLE does not offer are expected (APPROVED_FIELDS_NOT_PRESENT_ON_PAGE).'}


def run_dry(suite, dataset, fixture, projection, allocation, folder, *, headed=False):
    from playwright.sync_api import sync_playwright
    require_scratch(fixture)
    validate_suite(suite)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    check_private_directory(folder, protect=True)
    contract = stage_effects.load_contract(rr.CASE_IDS)
    scoped_baseline = rr.collect_scoped_hashes(fixture, stage_effects.allowances(contract, fixture))
    budget = SuiteBudget(suite['resource_policy'])
    policy = Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json', fixture['target_url']).read_only_policy
    holder = {'page': None, 'case': None}
    executor = ScriptedExecutor(lambda: holder['page'], lambda: holder['case'])
    tracker = {'tables': fixture['suite_copy']['prepared_tables'], 'previous': None}
    downloads = folder / 'browser-downloads'
    downloads.mkdir()
    check_private_directory(downloads, protect=True)
    with sync_playwright() as p, patch.object(measurement_runner, 'ask_calibrated', executor), patch.object(inspection_runner, 'ask_calibrated', executor), \
            patch.object(measurement_runner, 'ask_review', _neutral_review), patch.object(inspection_runner, 'ask_review', _neutral_review):
        browser = p.chromium.launch(headless=not headed, downloads_path=str(downloads))
        try:
            spy = _SpyBrowser(browser, holder)

            def stage(case):
                holder['case'] = case['case_id']

                def run_case():
                    return rr.dispatch(case, spy, fixture, dataset, projection, allocation, policy, object(), object(), budget,
                                       Evidence(folder / case['case_id']))
                return rr.guarded_stage(fixture, contract, case['case_id'], tracker, run_case)
            records = rr.execute_cases(suite, fixture, budget, stage)
        finally:
            browser.close()
    manifest = {'verdict': 'NO-GO', 'protected_scoped_baseline': scoped_baseline, 'side_effect_contract_sha256': stage_effects.contract_hash(contract)}
    rr.finalise_oracles(manifest, {'records': records}, fixture, dataset, projection, allocation, rr.snapshot(fixture, enforce_counts=False))
    report = summarize(records, manifest, executor.log)
    (folder / 'dry-run-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return report

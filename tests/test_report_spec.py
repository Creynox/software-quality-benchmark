import copy
import importlib
import json
from pathlib import Path
import tempfile
import unittest

from sqbf.cli import main

module = importlib.import_module('projects.ble-elva.tools.report_spec')
runner = importlib.import_module('projects.ble-elva.tools.regular_runner')
GOLDEN = Path(__file__).parent / 'golden' / ('nsn014-punktebericht-%s.md' % module.load_spec()['spec_version'])

# The definition may only change together with a new version: an edit of the specification file without a new entry here fails.
PINNED_SPEC_SHA256 = {'1.0.0': '9adbd93d93c2404965fe27c5525a6a1c835e4b7b8a3e7cfaabb02549a7987f3d',
                      '1.1.0': '7419a3d08b743a0707d20b4f671d7fc1733c38e0ca363256f42443ac77ca9291',
                      '1.2.0': 'b1496795f0022867198426769e0a9112c303b364e6d6780c30fb7f88280d5a4e',
                      '1.3.0': 'd2b2b7608a61833a9dc77aceb1c176a7ca6733bccf97ded5951d5b7345931c6b'}


def manifest(**extra):
    base = {'run_id': 'run-1', 'scenario_id': 'ENZBERG-NSN014', 'scenario_version': '0.4.1', 'scoring_version': 'nsn014-objective-v1', 'rubric_version': 'nsn014-ux-rubric-v1',
            'verdict': 'PARTIAL GO', 'technical_status': 'COMPLETED', 'functional_status': 'INCOMPLETE', 'measurement_status': 'INCOMPLETE', 'stop_reason': None,
            'executor_model': 'exec', 'analyst_model': 'rev', 'sqbf_commit': 'abc', 'software_version': 'ble', 'started_at': '2026-10-19T10:00:00Z',
            'completed_at': '2026-10-19T11:00:00Z', 'model_calls': 10, 'suite_sha256': 's', 'dataset_sha256': 'd', 'reference_projection_sha256': 'p',
            'allocation_reference_sha256': 'a', 'executor_instructions_sha256': 'i', 'guard_rules_sha256': 'g', 'review_schema_sha256': 'r',
            'viewport': {'width': 1280, 'height': 800}, 'browser_version': '1.0',
            'accounting': {'elapsed_seconds': 600.4, 'model_wait_seconds': 300.5,
                           'actors': {'executor': {'model_calls': 8, 'tokens': {'total_tokens': {'known_sum': 1000, 'unknown_calls': 1}}},
                                      'reviewer': {'model_calls': 2, 'tokens': {'total_tokens': {'known_sum': 500, 'unknown_calls': 0}}}}}}
    base.update(extra)
    return base


def every_stage(result='PASS', position_result='PASS'):
    spec = module.load_spec()
    records = []
    for stage in spec['stage_order']:
        record = {'case_id': stage, 'result': result}
        if stage in spec['check_catalogue']['positions']:
            record['position_results'] = [{'position_id': p, 'result': position_result, 'class': None if position_result == 'PASS' else 'EXECUTOR_REPORTED_BLOCKED'}
                                          for p in spec['check_catalogue']['positions'][stage]]
        records.append(record)
    return records


def effort(**extra):
    base = {'actions': 10, 'scrolls': 2, 'clicks': 3, 'typed': 4, 'keys': 1, 'waits': 0, 'rejected': 0, 'scrolls_after_last_entry': 1}
    base.update(extra)
    return base


def review(verdict='PASS', scores=(3, 4, 5, None), findings=()):
    return {'verdict': verdict, 'reason': '', 'scores': dict(zip(('findability', 'clarity', 'task_progress', 'error_recovery'), scores)), 'findings': list(findings)}


def build(m=None, records=None, rows=(), reviews=()):
    return module.build_scorecard(m or manifest(), records if records is not None else every_stage(), list(rows), list(reviews))


def criteria_records():
    """Every stage passed except SIEVE P02 (blocked after a rejected entry, Oracle deviation) and RECEIPT (data right, model gave up)."""
    records = every_stage()
    by_stage = {r['case_id']: r for r in records}
    receipt = by_stage['NSN014-RECEIPT']
    receipt.update(result='INCONCLUSIVE', reason='EXECUTOR_REPORTED_BLOCKED', status='BLOCKED', effort=effort(rejected=1),
                   rejected_actions=[{'error_code': 'INSPECTION_ACTION_SCOPE_DENIED', 'action': 'click', 'target': {'label': 'Plan öffnen'}}],
                   oracle={'status': 'PASS', 'sample_count': 10})
    sieve = by_stage['NSN014-SIEVE']
    sieve['result'] = 'INCONCLUSIVE'
    sieve['position_results'][1].update(result='INCOMPLETE', **{'class': 'EXECUTOR_REPORTED_BLOCKED'})
    sieve['positions'] = [
        {'position_id': 'P01', 'kind': 'sieve', 'status': 'DONE', 'module_reached': True, 'fields_required': 2, 'fields_entered': 1,
         'save_status': 'NOT_SAVED_PARTIAL_ENTRY', 'effort': effort(), 'rejected_actions': []},
        {'position_id': 'P02', 'kind': 'sieve', 'status': 'BLOCKED', 'module_reached': True, 'fields_required': 4, 'fields_entered': 2,
         'save_status': 'NOT_SAVED_PARTIAL_ENTRY', 'effort': effort(rejected=1),
         'rejected_actions': [{'error_code': 'MEASUREMENT_ACTION_SCOPE_DENIED', 'action': 'type', 'target': {'label': 'Rückstand 2 mm'},
                               'detail': {'reason': 'NO_APPROVED_FIELD_FOCUSED', 'typed_chars': 3}}]}]
    sieve['oracle'] = {'status': 'FAIL', 'components': [{'status': 'FAIL', 'checks': 20, 'mismatches': [{'position_id': 'P02', 'kind': 'sieves'}]}]}
    return records


def accounting_with_sieve_task():
    base = manifest()['accounting']
    return dict(base, tasks=[{'case_id': 'NSN014-SIEVE', 'elapsed_seconds': 700.4, 'actions': 70, 'observation_marks': {'seconds': 600, 'actions': 60},
                              'time_mark_exceeded': True, 'action_mark_exceeded': True}])


class ReportSpecTests(unittest.TestCase):
    def test_the_definition_is_consistent_versioned_and_pinned(self):
        spec = module.load_spec()
        self.assertEqual(module.validate_spec(spec), [])
        self.assertEqual(len(module.catalogue(spec)), 46)
        self.assertRegex(spec['spec_version'], r'^\d+\.\d+\.\d+$')
        self.assertEqual(spec['changelog'][-1]['version'], spec['spec_version'], 'the newest changelog entry names the current version')
        self.assertIn(spec['spec_version'], PINNED_SPEC_SHA256, 'a new version needs its own pinned hash')
        self.assertEqual(module.spec_sha256(), PINNED_SPEC_SHA256[spec['spec_version']], 'the definition changed without a new version')
        self.assertEqual(build()['spec_sha256'], module.spec_sha256())

    def test_the_scorecard_has_exactly_the_keys_of_the_definition_and_the_whole_catalogue(self):
        card = build()
        self.assertEqual(list(card), module.load_spec()['scorecard_keys'])
        self.assertEqual(module.scorecard_problems(card), [])
        self.assertEqual(len(card['checks']), 46)
        broken = copy.deepcopy(card)
        broken['points']['points'] += 1
        self.assertIn('POINTS', module.scorecard_problems(broken))
        broken = copy.deepcopy(card)
        broken['checks'].pop()
        self.assertIn('CATALOGUE', module.scorecard_problems(broken))
        broken = copy.deepcopy(card)
        broken['extra'] = 1
        self.assertIn('SCORECARD_KEYS', module.scorecard_problems(broken))

    def test_a_complete_pass_is_46_points_and_the_only_way_to_pass_the_run(self):
        card = build(manifest(verdict='GO'))
        self.assertEqual(card['points'], {'points': 46, 'max_points': 46})
        self.assertEqual(card['result'], {'run_result': 'BESTANDEN', 'bestanden': True, 'reasons': ['CHECKS_PASSED=46']})
        self.assertEqual((card['rates']['points_percent'], card['rates']['coverage_percent'], card['rates']['pass_rate_of_decided_percent']), (100.0, 100.0, 100.0))
        # All checks passed but the verdict of the run is not GO: no pass, and the contradiction is reported.
        card = build(manifest(verdict='NO-GO'))
        self.assertEqual(card['result']['run_result'], 'UNVOLLSTAENDIG')
        self.assertEqual(card['consistency']['counts']['ALL_PASSED_WITHOUT_GO'], 1)
        # A GO verdict with an open check is a contradiction as well.
        card = build(manifest(verdict='GO'), every_stage('PASS', 'INCOMPLETE'))
        self.assertEqual(card['consistency']['counts']['VERDICT_GO_WITH_OPEN_CHECK'], 1)

    def test_status_origin_and_points_follow_the_fixed_rules(self):
        records = [{'case_id': 'NSN014-PLAN', 'result': 'PASS'},
                   {'case_id': 'NSN014-RECEIPT', 'result': 'FAIL', 'fail_classes': ['RECEIPT_MISMATCH']},
                   {'case_id': 'NSN014-PREPARATION', 'result': 'FAIL', 'position_results': [
                       {'position_id': 'P01', 'result': 'PASS', 'class': None}, {'position_id': 'P02', 'result': 'FAIL', 'class': 'PERSISTED_VALUE_DEVIATION'},
                       {'position_id': 'P03', 'result': 'INCOMPLETE', 'class': 'EXECUTOR_REPORTED_BLOCKED'}, {'position_id': 'P04', 'result': 'INCOMPLETE', 'class': 'EXECUTOR_REQUEST_FAILED'},
                       {'position_id': 'P05', 'result': 'INCOMPLETE', 'class': 'DERIVED_VALUE_UPSTREAM_INCOMPLETE'}, {'position_id': 'P06', 'result': 'INCOMPLETE', 'class': 'SOMETHING_NEW'}]},
                   {'case_id': 'NSN014-SIEVE', 'result': 'INVALID', 'reason': 'INSPECTION_RUNNER_ERROR'},
                   {'case_id': 'NSN014-SHAPE', 'result': 'INCONCLUSIVE', 'stop_reason': 'EXECUTOR_UNAVAILABLE_AFTER_REPEATED_FAILURES'},
                   {'case_id': 'NSN014-BOILING', 'result': 'NOT_RUN', 'reason': 'UPSTREAM_CRITICAL_STOP'}]
        checks = {c['id']: c for c in build(manifest(), records)['checks']}
        self.assertEqual((checks['NSN014-PLAN']['status'], checks['NSN014-PLAN']['origin']), ('PASSED', None))
        self.assertEqual((checks['NSN014-RECEIPT']['status'], checks['NSN014-RECEIPT']['origin']), ('FAILED', 'BLE-ABWEICHUNG'))
        self.assertEqual(checks['NSN014-PREPARATION/P01']['status'], 'PASSED')
        self.assertEqual((checks['NSN014-PREPARATION/P02']['status'], checks['NSN014-PREPARATION/P02']['origin']), ('FAILED', 'BLE-ABWEICHUNG'))
        self.assertEqual((checks['NSN014-PREPARATION/P03']['status'], checks['NSN014-PREPARATION/P03']['origin']), ('NOT_DECIDED', 'MODELL'))
        self.assertEqual(checks['NSN014-PREPARATION/P04']['origin'], 'PROVIDER')
        self.assertEqual(checks['NSN014-PREPARATION/P05']['origin'], 'VORSTUFE')
        self.assertEqual(checks['NSN014-PREPARATION/P06']['origin'], 'UNKLAR')
        self.assertEqual(checks['NSN014-PREPARATION/P07'], {'id': 'NSN014-PREPARATION/P07', 'stage': 'NSN014-PREPARATION', 'position': 'P07', 'status': 'NOT_DECIDED', 'origin': 'UNKLAR', 'detail': None,
                                                            'criteria': {'tasks': [], 'values': None}})
        self.assertEqual({checks['NSN014-SIEVE/P%02d' % i]['status'] for i in range(1, 11)}, {'INVALID'})
        self.assertEqual(checks['NSN014-SIEVE/P01']['origin'], 'UNGUELTIG')
        self.assertEqual((checks['NSN014-SHAPE/P01']['status'], checks['NSN014-SHAPE/P01']['origin']), ('NOT_DECIDED', 'PROVIDER'))
        self.assertEqual({c['status'] for c in build(manifest(), records)['checks'] if c['stage'] in ('NSN014-BOILING', 'NSN014-SE', 'NSN014-REPORT')}, {'NOT_RUN'})
        card = build(manifest(), records)
        self.assertEqual(card['points']['points'], 2)
        self.assertEqual(sum(card['counts'][s] for s in module.load_spec()['status_order']), 46)
        self.assertEqual(sum(card['origins'].values()), 46 - card['counts']['PASSED'])

    def test_criteria_and_stage_time_come_only_from_recorded_tasks_the_oracle_and_the_accounting(self):
        records = criteria_records()
        card = build(manifest(accounting=accounting_with_sieve_task()), records)
        checks = {c['id']: c for c in card['checks']}
        passed, open_ = checks['NSN014-SIEVE/P01']['criteria'], checks['NSN014-SIEVE/P02']['criteria']
        self.assertEqual(passed['values'], 'MATCH', 'a passed check has matching values by definition')
        self.assertEqual(passed['tasks'][0]['entered'], [1, 2])
        self.assertEqual(open_['values'], 'MISMATCH', 'the Oracle lists P02 with a deviation')
        self.assertEqual(open_['tasks'], [{'kind': 'sieve', 'finished': 'BLOCKED', 'reached': True, 'entered': [2, 4], 'saved': 'NOT_SAVED_PARTIAL_ENTRY',
                                           'actions': 10, 'scrolls': 2, 'scrolls_after_last_entry': 1,
                                           'rejected': [{'code': 'MEASUREMENT_ACTION_SCOPE_DENIED', 'action': 'type', 'label': 'Rückstand 2 mm',
                                                         'reason': 'NO_APPROVED_FIELD_FOCUSED'}]}])
        self.assertNotIn('typed', json.dumps(card['checks']), 'never a typed text or its length')
        self.assertEqual(checks['NSN014-SIEVE/P03']['criteria'], {'tasks': [], 'values': 'MATCH'})
        receipt = checks['NSN014-RECEIPT']['criteria']
        self.assertEqual((receipt['values'], receipt['tasks'][0]['finished']), ('MATCH', 'BLOCKED'), 'right data, but the model gave up')
        self.assertEqual(checks['NSN014-PLAN']['criteria'], {'tasks': [], 'values': 'MATCH'}, 'passed without recorded tasks')
        times = {s['stage']: s['time'] for s in card['stages']}
        self.assertEqual(times['NSN014-SIEVE'], {'seconds': 700, 'actions': 70, 'mark_seconds': 600, 'mark_actions': 60, 'over_time_mark': True,
                                                 'over_action_mark': True})
        self.assertIsNone(times['NSN014-PLAN'], 'not recorded is not zero')
        self.assertEqual(card['points']['points'], 44, 'criteria never change a point: only RECEIPT and SIEVE P02 are open')

    def test_a_blocked_stage_names_its_reason_as_critical_stop_and_a_suite_oracle_fault_is_attributed_to_the_suite(self):
        # Live run 824fa661: the report stage was blocked by the calculation oracle (REPORT_ORACLE_UNAVAILABLE), RIGHTS was not run.
        records = every_stage('INCONCLUSIVE', 'INCOMPLETE')
        records[10] = {'case_id': 'NSN014-REPORT', 'result': 'BLOCKED', 'reason': 'REPORT_ORACLE_UNAVAILABLE'}
        records[11] = {'case_id': 'NSN014-RIGHTS', 'result': 'NOT_RUN', 'reason': 'UPSTREAM_CRITICAL_STOP', 'upstream_reason': 'REPORT_ORACLE_UNAVAILABLE'}
        card = build(manifest(technical_status='BLOCKED'), records)
        self.assertEqual(card['run']['critical_stop'], 'NSN014-REPORT: REPORT_ORACLE_UNAVAILABLE')
        report_checks = [c for c in card['checks'] if c['stage'] == 'NSN014-REPORT']
        self.assertEqual({(c['status'], c['origin'], c['detail']) for c in report_checks}, {('NOT_DECIDED', 'SUITE', 'REPORT_ORACLE_UNAVAILABLE')})
        self.assertEqual(card['origins']['SUITE'], 10)
        self.assertEqual(card['result']['run_result'], 'ABGEBROCHEN')
        text = '\n'.join(module.render(card))
        self.assertIn('| Technischer Status | BLOCKED |', text);self.assertIn('| Kritischer Stopp | NSN014-REPORT: REPORT\\_ORACLE\\_UNAVAILABLE |', text)
        self.assertIsNone(build()['run']['critical_stop'])
        self.assertIn('| Kritischer Stopp | — |', '\n'.join(module.render(build())))

    def test_the_run_result_follows_the_fixed_order(self):
        invalid_and_failed = every_stage()
        invalid_and_failed[2]['result'] = 'INVALID'
        invalid_and_failed[3]['position_results'][0]['result'] = 'FAIL'
        self.assertEqual(build(records=invalid_and_failed)['result']['run_result'], 'UNGUELTIG')
        self.assertEqual(build(manifest(technical_status='INVALID'))['result']['run_result'], 'UNGUELTIG')
        failed = every_stage()
        failed[3]['position_results'][0]['result'] = 'FAIL'
        failed[-1]['result'] = 'NOT_RUN'
        self.assertEqual(build(records=failed)['result']['run_result'], 'NICHT_BESTANDEN', 'a proven deviation outweighs an abort')
        self.assertEqual(build(manifest(stop_reason='SUITE_TIME_CEILING'))['result']['run_result'], 'ABGEBROCHEN')
        self.assertEqual(build(manifest(technical_status='RESOURCE_STOP'))['result']['run_result'], 'ABGEBROCHEN')
        self.assertEqual(build(records=[])['result']['run_result'], 'ABGEBROCHEN')
        self.assertEqual(build(records=[])['points'], {'points': 0, 'max_points': 46})
        self.assertEqual(build(manifest(), every_stage('INCONCLUSIVE', 'INCOMPLETE'))['result']['run_result'], 'UNVOLLSTAENDIG')
        # A stage that failed without a failed check is a deviation, not a silent pass.
        stage_fail = every_stage()
        stage_fail[3]['result'] = 'FAIL'
        card = build(manifest(verdict='GO'), stage_fail)
        self.assertEqual(card['result']['run_result'], 'NICHT_BESTANDEN')
        self.assertEqual(card['consistency']['counts']['STAGE_FAIL_WITHOUT_FAILED_CHECK'], 1)

    def test_catalogue_duplicates_and_unknown_results_are_reported_never_counted(self):
        records = every_stage() + [{'case_id': 'NSN014-PLAN', 'result': 'FAIL'}, {'case_id': 'NSN014-EXTRA', 'result': 'PASS'}]
        records[2]['position_results'].append({'position_id': 'P99', 'result': 'PASS', 'class': None})
        records[1]['result'] = 'SOMETHING'
        card = build(manifest(verdict='GO'), records)
        counts = card['consistency']['counts']
        self.assertEqual((counts['DUPLICATE_RECORD'], counts['CATALOGUE_MISMATCH'], counts['UNKNOWN_RESULT']), (1, 2, 1))
        self.assertEqual(card['points']['max_points'], 46)
        self.assertEqual(card['points']['points'], 45, 'the duplicate record is ignored; the unknown result is not decided')
        self.assertNotEqual(card['result']['run_result'], 'BESTANDEN')
        measured = every_stage()
        measured[3]['position_results'] = measured[3]['position_results'][:5]
        self.assertEqual(build(manifest(verdict='GO'), measured)['consistency']['counts']['STAGE_PASS_WITH_OPEN_CHECK'], 1)

    def test_percentages_are_rounded_half_up_to_one_decimal(self):
        self.assertEqual([module._pct(1, 8), module._pct(1, 16), module._pct(1, 3), module._pct(2, 3), module._pct(0, 5), module._pct(5, 5)], [12.5, 6.3, 33.3, 66.7, 0.0, 100.0])
        self.assertIsNone(module._pct(0, 0))
        self.assertEqual(module._mean([1, 2]), 1.5)
        self.assertEqual(module._mean([1, 1, 2]), 1.3)
        self.assertIsNone(module._mean([]))
        card = build(manifest(), every_stage('INCONCLUSIVE', 'PASS'))
        self.assertEqual(card['points']['points'], 40)
        self.assertEqual(card['rates']['points_percent'], 87.0)

    def test_operating_measurements_are_summed_from_the_rows_only(self):
        rows = [{'case': 'SIEVE', 'position': 'P01', 'kind': 'sieve', 'reached': 'ja', 'status': 'DONE', 'origin': '—', 'effort': effort(), 'save': 'SAVED'},
                {'case': 'SIEVE', 'position': 'P02', 'kind': 'sieve', 'reached': 'nein', 'status': 'BLOCKED', 'origin': 'MODELL', 'effort': effort(scrolls=5, scrolls_after_last_entry=None), 'save': 'NOT_SAVED_AFTER_ENTRY'},
                {'case': 'PLAN', 'position': 'Stufe', 'kind': '—', 'reached': '—', 'status': 'DONE', 'origin': '—', 'effort': effort(), 'save': '—'}]
        op = build(rows=rows)['operating']
        self.assertEqual(op['tasks_measured'], 3)
        self.assertEqual(op['totals']['scrolls'], 9);self.assertEqual(op['totals']['scrolls_after_last_entry'], 2);self.assertEqual(op['totals']['actions'], 30)
        self.assertEqual(op['saves']['SAVED'], 1);self.assertEqual(op['saves']['NOT_SAVED_AFTER_ENTRY'], 1);self.assertEqual(op['saves']['NOT_APPLICABLE'], 1)
        self.assertEqual(op['modules_reached'], {'ja': 1, 'nein': 1, 'unbekannt': 1})
        self.assertEqual(op['save_rate_percent'], 50.0)
        empty = build()['operating']
        self.assertEqual(empty['tasks_measured'], 0)
        self.assertEqual({v for v in empty['totals'].values()} | {v for v in empty['saves'].values()} | {v for v in empty['modules_reached'].values()} | {empty['save_rate_percent']}, {None},
                         'an unmeasured run shows no value instead of a zero that looks like a measurement')
        self.assertIn('| Aktionen | — |', '\n'.join(module.render(build())))

    def test_reviewer_observations_are_counted_and_never_change_points_or_result(self):
        finding = {'category': 'UX_IMPROVEMENT', 'severity': 'major', 'observed': 'x', 'expected': 'y', 'suggestion': 'z', 'evidence': '1'}
        reviews = [review('PASS', (3, 4, 5, None), [finding]), review('FAIL', (1, 2, None, 3), [finding, dict(finding, category='BLE_DEFECT_CANDIDATE', severity='critical')]),
                   review('INCONCLUSIVE', (None, None, None, None))]
        plain = build(manifest(verdict='GO'))
        observed = build(manifest(verdict='GO'), reviews=reviews)
        for key in ('result', 'points', 'counts', 'rates', 'checks', 'origins'):
            self.assertEqual(observed[key], plain[key])
        rv = observed['reviewer_observations']
        self.assertEqual((rv['reviews'], rv['verdicts']), (3, {'PASS': 1, 'FAIL': 1, 'INCONCLUSIVE': 1}))
        self.assertEqual(rv['scores']['findability'], {'n': 2, 'min': 1, 'mean': 2.0, 'max': 3})
        self.assertEqual(rv['scores']['error_recovery'], {'n': 1, 'min': 3, 'mean': 3.0, 'max': 3})
        self.assertEqual(rv['findings']['UX_IMPROVEMENT']['major'], 2);self.assertEqual(rv['findings']['BLE_DEFECT_CANDIDATE']['critical'], 1)
        errors = every_stage()
        errors[0]['review_error'] = 'REVIEW_FAILED'
        self.assertEqual(build(records=errors)['reviewer_observations']['review_errors'], 1)

    def test_the_report_is_rendered_from_the_scorecard_only_in_the_fixed_section_order(self):
        card = build(manifest(), every_stage('INCONCLUSIVE', 'INCOMPLETE'), reviews=[review()])
        text = '\n'.join(module.render(card))
        spec = module.load_spec()
        headings = [f'## {s["id"]}. {s["title"]}' for s in spec['sections']]
        positions = [text.index(h) for h in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual([line for line in text.splitlines() if line.startswith('## ')], headings, 'no further sections')
        self.assertEqual(text, '\n'.join(module.render(copy.deepcopy(card))))
        self.assertIn(f"Prüfsumme der Punktekarte (SHA256): {module.canonical_hash(card)}", text)
        self.assertEqual(text.count('| NSN014-'), 12 + 46, 'twelve stage rows in section 2 and one row per check in section 4')
        hostile = '\n'.join(module.render(build(manifest(run_id='<script>[x](y)|`z`'))))
        self.assertNotIn('<script>', hostile);self.assertNotIn('[x](y)', hostile)

    def test_the_rendered_report_equals_the_golden_file_of_this_version(self):
        records = every_stage('INCONCLUSIVE', 'INCOMPLETE')
        records[0]['result'] = 'PASS'
        records[2]['position_results'][0].update(result='PASS', **{'class': None})
        records[3]['position_results'][1].update(result='FAIL', **{'class': 'PERSISTED_VALUE_DEVIATION'})
        records[-1]['result'] = 'NOT_RUN'
        rows = [{'case': 'SIEVE', 'position': 'P01', 'kind': 'sieve', 'reached': 'ja', 'status': 'DONE', 'origin': '—', 'effort': effort(), 'save': 'SAVED'}]
        card = build(manifest(stop_reason='SUITE_TIME_CEILING'), records, rows, [review('PASS', (3, 4, 5, None))])
        text = '\n'.join(module.render(card)) + '\n'
        if not GOLDEN.exists():
            GOLDEN.parent.mkdir(exist_ok=True)
            GOLDEN.write_text(text, encoding='utf-8', newline='')
        self.assertEqual(text, GOLDEN.read_text(encoding='utf-8'), 'the layout or the wording changed: that needs a new version of the specification and a new golden file')

    def test_two_scorecards_are_comparable_only_under_equal_conditions(self):
        first = build(manifest(), every_stage('INCONCLUSIVE', 'INCOMPLETE'))
        better = every_stage('INCONCLUSIVE', 'INCOMPLETE')
        better[2]['position_results'][0].update(result='PASS', **{'class': None})
        second = build(manifest(run_id='run-2'), better)
        result = module.compare(first, second)
        self.assertTrue(result['comparable']);self.assertEqual(result['differing_keys'], [])
        self.assertEqual((result['points_a'], result['points_b'], result['delta_points'], result['delta_points_percent']), (0, 1, 1, 2.2))
        self.assertEqual(result['checks_changed'], [{'id': 'NSN014-PREPARATION/P01', 'a': 'NOT_DECIDED', 'b': 'PASSED'}])
        other = build(manifest(run_id='run-3', executor_instructions_sha256='other'), better)
        result = module.compare(first, other)
        self.assertFalse(result['comparable']);self.assertEqual(result['differing_keys'], ['executor_instructions_sha256'])
        # Not recorded is not equal: two runs without an instruction hash cannot prove the same wording (runs 5 and 6).
        unknown_a = build(manifest(run_id='run-5', executor_instructions_sha256=None))
        unknown_b = build(manifest(run_id='run-6', executor_instructions_sha256=None))
        result = module.compare(unknown_a, unknown_b)
        self.assertFalse(result['comparable']);self.assertEqual(result['differing_keys'], ['executor_instructions_sha256'])

    def test_the_cli_scores_a_recorded_run_without_a_model_and_never_overwrites(self):
        records = every_stage('INCONCLUSIVE', 'INCOMPLETE')
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            run.mkdir()
            (run / 'run.json').write_text(json.dumps(manifest()), encoding='utf-8')
            (run / 'cases.json').write_text(json.dumps(records), encoding='utf-8')
            self.assertEqual(main(['suite-score', '--run', str(run)]), 0)
            first = (run / 'punktebericht.md').read_text(encoding='utf-8')
            self.assertTrue(first.startswith('# NSN014 Punktebericht'))
            self.assertEqual(json.loads((run / 'scorecard.json').read_text(encoding='utf-8'))['points'], {'points': 0, 'max_points': 46})
            self.assertEqual(main(['suite-score', '--run', str(run)]), 0, 'the same data give the same files')
            (run / 'punktebericht.md').write_text('edited', encoding='utf-8')
            self.assertEqual(main(['suite-score', '--run', str(run)]), 2, 'a differing existing file is reported, not overwritten')
            self.assertEqual((run / 'punktebericht.md').read_text(encoding='utf-8'), 'edited')
            self.assertEqual(main(['suite-score', '--run', str(Path(tmp) / 'missing')]), 2)

    def test_the_cli_keeps_a_scorecard_of_another_version_and_writes_versioned_files_next_to_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            run.mkdir()
            (run / 'run.json').write_text(json.dumps(manifest()), encoding='utf-8')
            (run / 'cases.json').write_text(json.dumps(every_stage('INCONCLUSIVE', 'INCOMPLETE')), encoding='utf-8')
            (run / 'scorecard.json').write_text(json.dumps({'spec_version': '0.9.0'}), encoding='utf-8')
            (run / 'punktebericht.md').write_text('older version', encoding='utf-8')
            version = module.load_spec()['spec_version']
            self.assertEqual(main(['suite-score', '--run', str(run)]), 0)
            self.assertEqual((run / 'punktebericht.md').read_text(encoding='utf-8'), 'older version')
            self.assertEqual(json.loads((run / f'scorecard-{version}.json').read_text(encoding='utf-8'))['spec_version'], version)
            self.assertTrue((run / f'punktebericht-{version}.md').read_text(encoding='utf-8').startswith('# NSN014 Punktebericht'))
            self.assertEqual(main(['suite-score', '--run', str(run)]), 0, 'the versioned files are identical when scored again')


if __name__ == '__main__':
    unittest.main()

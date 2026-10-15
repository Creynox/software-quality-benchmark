import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sqbf.bounded import Budget, LabBudget
from sqbf.calibration import ResourceStop, SuiteBudget, ask_calibrated, validate_policy
from sqbf.suites import aggregate, validate_suite


def policy():
    return {'mode': 'calibration', 'hard_seconds': 7200, 'hard_model_calls': 1000,
            'limit_result': 'INCONCLUSIVE', 'automatic_retry': False,
            'task_marks_are_hard_limits': False}


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.budget = SuiteBudget(policy(), clock=lambda: self.now)
        self.case = {'case_id': 'receipt', 'observation_marks': {'seconds': 600, 'actions': 60}}
        self.budget.start_task(self.case)

    def test_marks_observe_instead_of_stopping_task(self):
        self.now = 601
        for _ in range(61): self.budget.action()
        report = self.budget.report()
        self.assertTrue(report['tasks'][0]['time_mark_exceeded'])
        self.assertTrue(report['tasks'][0]['action_mark_exceeded'])
        self.assertIsNone(report['resource_result'])
        self.assertEqual(self.budget.remaining(), 6599)

    def test_calls_and_tokens_separate_actors_and_unknowns(self):
        first = self.budget.claim('executor'); self.now = 7
        self.budget.complete_call(first, {'input_tokens': 100, 'output_tokens': 30, 'secret': 'excluded'})
        self.now = 9
        second = self.budget.claim('reviewer'); self.now = 12
        self.budget.complete_call(second, {'total_tokens': 40})
        third = self.budget.claim('executor'); self.now = 17
        self.budget.complete_call(third)  # Failed call still consumed a reservation.
        report = self.budget.report()
        self.assertEqual(report['model_calls'], 3)
        self.assertEqual(report['model_wait_seconds'], 15)
        self.assertEqual(report['non_model_elapsed_seconds'], 2)
        inputs = report['actors']['executor']['tokens']['input_tokens']
        self.assertEqual(inputs, {'known_sum': 100, 'unknown_calls': 1, 'complete_total': None})
        self.assertEqual(report['actors']['reviewer']['tokens']['total_tokens']['complete_total'], 40)
        self.assertNotIn('secret', json.dumps(report))

    def test_global_call_limit_includes_reviewer_no_retry_after_stop(self):
        self.budget.policy['hard_model_calls'] = 2
        for actor in ('executor', 'reviewer'):
            self.budget.complete_call(self.budget.claim(actor))
        with self.assertRaises(ResourceStop): self.budget.claim()
        with self.assertRaises(ResourceStop): self.budget.action()
        self.assertEqual(self.budget.report()['resource_result'], 'INCONCLUSIVE')
        self.assertEqual(self.budget.calls, 2)

    def test_waiting_counts_towards_suite_deadline(self):
        ticket = self.budget.claim(); self.now = 7200
        with self.assertRaises(ResourceStop): self.budget.complete_call(ticket)
        self.assertEqual(self.budget.report()['stop_reason'], 'SUITE_TIME_CEILING')
        with self.assertRaises(ResourceStop): self.budget.remaining()

    def test_report_detects_elapsed_deadline_and_no_task_retry(self):
        self.budget.finish_task()
        with self.assertRaises(ValueError): self.budget.start_task(self.case)
        self.now = 7201
        self.assertEqual(self.budget.report()['resource_result'], 'INCONCLUSIVE')

    def test_bad_tokens_are_unknown_not_zero(self):
        ticket = self.budget.claim()
        self.budget.complete_call(ticket, {'input_tokens': True, 'output_tokens': -1, 'total_tokens': 3.5})
        for token in self.budget.report()['actors']['executor']['tokens'].values():
            self.assertIsNone(token['complete_total'])
            self.assertEqual(token['unknown_calls'], 1)

    def test_no_overlap_or_duplicate_completion(self):
        ticket = self.budget.claim()
        with self.assertRaises(ValueError): self.budget.claim('reviewer')
        with self.assertRaises(ValueError): self.budget.finish_task()
        self.budget.complete_call(ticket)
        with self.assertRaises(ValueError): self.budget.complete_call(ticket)
        with self.assertRaises(ValueError): self.budget.complete_call(-1)

    def test_no_relaxation_of_existing_pilot_limits(self):
        with self.assertRaises(ValueError): Budget(seconds=301)
        with self.assertRaises(ValueError): Budget(calls=13)
        with self.assertRaises(ValueError): LabBudget(seconds=1501, calls=2)
        with self.assertRaises(ValueError): LabBudget(seconds=1500, calls=153)
        for key, value in [('hard_seconds', 7201), ('hard_model_calls', 1001),
                           ('hard_seconds', True), ('automatic_retry', True),
                           ('task_marks_are_hard_limits', True), ('limit_result', 'FAIL')]:
            invalid = policy(); invalid[key] = value
            with self.assertRaises(ValueError): validate_policy(invalid)

    def test_worker_bridge_accounts_success_and_failure_without_retry(self):
        def worker(mode, payload, timeout):
            self.assertEqual(mode, 'model')
            self.assertEqual(set(payload), {'provider', 'prompt', 'images'})
            self.assertEqual(timeout, 30)
            self.now += 4
            return {'data': {'action': 'done'}, 'usage': {'input_tokens': 20}}
        with patch('sqbf.bounded.model_spec', return_value={'mock': True}), patch('sqbf.bounded.invoke_worker', side_effect=worker) as call:
            result = ask_calibrated(object(), 'visible task', b'fake image', self.budget, 'executor')
            self.assertEqual(result.data, {'action': 'done'})
            call.assert_called_once()
        with patch('sqbf.bounded.model_spec', return_value={'mock': True}), patch('sqbf.bounded.invoke_worker', side_effect=RuntimeError('mock failure')) as call:
            with self.assertRaises(RuntimeError):
                ask_calibrated(object(), 'visible task', b'fake image', self.budget, 'reviewer')
            call.assert_called_once()
        report = self.budget.report()
        self.assertEqual(report['model_calls'], 2)
        self.assertEqual(report['model_wait_seconds'], 4)
        self.assertIsNone(report['actors']['reviewer']['tokens']['input_tokens']['complete_total'])

    def test_unsupported_provider_stops_before_request(self):
        with self.assertRaises(ValueError):
            ask_calibrated(object(), 'task', b'image', self.budget, 'executor')
        self.assertEqual(self.budget.calls, 0)

    def test_v03_scope_personas_and_no_fabricated_readiness(self):
        suite = json.loads(Path('projects/ble-elva/suites/enzberg-nsn014-v0.3.json').read_text(encoding='utf-8'))
        validate_suite(suite)
        self.assertEqual(len(suite['cases']), 12)
        self.assertEqual(set(suite['personas']), {'laboratory_lead', 'laboratory_staff', 'wpk_lead', 'plant_lead'})
        self.assertFalse({'NSN014-RELEASE', 'NSN014-DELIVERY'} & {c['case_id'] for c in suite['cases']})
        self.assertTrue(all(c['implementation'] == 'pending' for c in suite['cases']))
        self.assertEqual(aggregate(suite, [])['measurement_status'], 'INCOMPLETE')
        record = {'case_id': suite['cases'][0]['case_id'], 'result': 'FAIL', 'stop_reason': 'SUITE_CALL_CEILING'}
        with self.assertRaises(ValueError): aggregate(suite, [record])
        record['result'] = 'INCONCLUSIVE'
        self.assertEqual(aggregate(suite, [record])['result'], 'INCOMPLETE')
        invalid = copy.deepcopy(suite); invalid['cases'][0]['persona'] = 'unprovisioned'
        with self.assertRaises(ValueError): validate_suite(invalid)
        invalid = copy.deepcopy(suite); invalid['cases'][0]['max_actions'] = 60
        with self.assertRaises(ValueError): validate_suite(invalid)

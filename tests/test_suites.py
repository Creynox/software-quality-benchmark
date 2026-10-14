import copy
import json
from pathlib import Path
import tempfile
import unittest

from sqbf.suites import aggregate, canonical_hash, check_dataset, comparison_key, suite_check, validate_suite


def suite():
    return {'schema_version': 1, 'suite_id': 'TEST', 'version': '1', 'dataset_id': 'NSN018',
            'required_position_ids': ['1'],
            'provider': 'chatgpt_plan', 'automatic_retry': False,
            'physical_operations': 'simulated', 'real_delivery': False,
            'cases': [{'case_id': key, 'persona': 'laboratory', 'task': 'synthetic task',
                       'oracle_contract': 'independent read-only', 'fixture_contract': 'isolated',
                       'expected': 'persisted result', 'implementation': 'implemented',
                       'depends_on': [] if key == 'A' else ['A'],
                       'max_minutes': 5, 'max_actions': 10, 'max_model_calls': 12}
                      for key in ('A', 'B')]}


def record(key, result='PASS'):
    return {'case_id': key, 'result': result, 'technical_gate': 'PASS',
            'oracle_gate': 'PASS', 'evidence_verified': True}


class SuiteTests(unittest.TestCase):
    def test_current_ux_stress_contract_excludes_norm_certification_without_readiness_shortcut(self):
        path = Path('projects/ble-elva/suites/enzberg-nsn014-v0.2.json')
        contract = validate_suite(json.loads(path.read_text(encoding='utf-8')))
        self.assertFalse(contract['normative_conformity_scoring'])
        self.assertFalse(contract['automatic_retry'])
        self.assertTrue(all(case['implementation'] == 'pending' for case in contract['cases']))
        for scoring in (True, None, 'false'):
            invalid = copy.deepcopy(contract); invalid['normative_conformity_scoring'] = scoring
            with self.assertRaises(ValueError): validate_suite(invalid)
        implemented = copy.deepcopy(contract)
        for case in implemented['cases']: case['implementation'] = 'implemented'
        records = [record(case['case_id'], 'FAIL') for case in implemented['cases']]
        result = aggregate(implemented, records)
        self.assertEqual(result['valid_cases'], 14)
        self.assertEqual(result['result'], 'FAIL')
        self.assertIsNone(result['score'])

    def test_ux_source_approval_is_not_normative_approval(self):
        data = {'schema_version': 1, 'dataset_id': 'UX', 'benchmark_purpose': 'ux_ui_process_stress',
                'normative_conformity_scoring': False, 'positions': [
                    {'position_id': '1', 'input_status': 'verified', 'inputs': {'mass_g': 10},
                     'expected_status': 'verified', 'expected': {'raw_persistence': 10}}]}
        data['approval'] = {'status': 'approved', 'approved_by': 'PO', 'approved_at': '2026-10-14',
                            'scope': 'UX_UI_PROCESS_SOURCE_REPLAY', 'content_sha256': canonical_hash(data)}
        self.assertEqual(check_dataset(data)['status'], 'DATASET_APPROVED')
        data['approval']['scope'] = 'NORMATIVE_CERTIFICATION'
        self.assertEqual(check_dataset(data)['status'], 'BLOCKED_DATA_REVIEW')

    def test_contract_requires_explicit_safety_boundaries(self):
        for field, value in [('automatic_retry', True), ('provider', 'openai'),
                             ('physical_operations', 'real'), ('real_delivery', True)]:
            value_suite = suite(); value_suite[field] = value
            with self.assertRaises(ValueError): validate_suite(value_suite)

    def test_case_identity_dependencies_and_limits(self):
        for field, value in [('case_id', 'A'), ('depends_on', ['B']),
                             ('max_actions', 151), ('max_minutes', True), ('max_model_calls', 0)]:
            value_suite = suite(); value_suite['cases'][1][field] = value
            with self.assertRaises(ValueError): validate_suite(value_suite)

    def test_dataset_approval_bound_to_actual_content(self):
        dataset = {'schema_version': 1, 'dataset_id': 'NSN018', 'positions': [
            {'position_id': '1', 'input_status': 'verified', 'inputs': {'mass_g': 10},
             'expected_status': 'verified', 'expected': {'retained_g': 10}}]}
        self.assertEqual(check_dataset(dataset)['status'], 'BLOCKED_DATA_REVIEW')
        dataset['approval'] = {'status': 'approved', 'approved_by': 'PO',
                               'approved_at': '2026-10-14', 'content_sha256': canonical_hash(dataset)}
        self.assertEqual(check_dataset(dataset)['status'], 'DATASET_APPROVED')
        dataset['positions'][0]['inputs']['mass_g'] = 11
        self.assertEqual(check_dataset(dataset)['status'], 'BLOCKED_DATA_REVIEW')

    def test_missing_measurements_cannot_be_approved_by_flag(self):
        dataset = {'schema_version': 1, 'dataset_id': 'NSN018', 'positions': []}
        dataset['approval'] = {'status': 'approved', 'approved_by': 'PO',
                               'approved_at': '2026-10-14', 'content_sha256': canonical_hash(dataset)}
        self.assertEqual(check_dataset(dataset)['status'], 'BLOCKED_DATA_REVIEW')

    def test_missing_and_pending_cases_never_pass(self):
        value_suite = suite()
        self.assertEqual(aggregate(value_suite, [record('A')])['result'], 'INCOMPLETE')
        value_suite['cases'][1]['implementation'] = 'pending'
        with self.assertRaises(ValueError): aggregate(value_suite, [record('A'), record('B')])
        result = aggregate(value_suite, [record('A'), record('B', 'NOT_IMPLEMENTED')])
        self.assertEqual(result['coverage'], {'valid': 1, 'required': 2})

    def test_pass_needs_exact_independent_evidence(self):
        for field, value in [('technical_gate', 'BLOCKED'), ('oracle_gate', 'FAIL'),
                             ('evidence_verified', 'yes'), ('evidence_verified', 1)]:
            entry = record('A'); entry[field] = value
            with self.assertRaises(ValueError): aggregate(suite(), [entry])

    def test_exact_results_unknown_and_duplicate_records(self):
        for entries in ([record('A', 'NO-PASS')], [record('X')], [record('A'), record('A')]):
            with self.assertRaises(ValueError): aggregate(suite(), entries)
        self.assertEqual(aggregate(suite(), [record('A'), record('B')])['result'], 'PASS')
        result = aggregate(suite(), [record('A'), record('B', 'FAIL')])
        self.assertEqual(result['result'], 'FAIL')
        self.assertEqual(result['counts']['PASS'], 1)

    def test_invalid_is_not_a_product_failure_or_valid_coverage(self):
        result = aggregate(suite(), (r for r in [record('A', 'INVALID'), record('B', 'FAIL')]))
        self.assertEqual(result['result'], 'INVALID')
        self.assertEqual(result['coverage']['valid'], 1)
        self.assertIsNone(result['score'])

    def test_comparison_inputs_are_fixed(self):
        args = (suite(), 'dataset-hash', 'executor-version', 'reviewer-version', [1280, 720], 'chromium')
        first = comparison_key(*args)
        changed = copy.deepcopy(args); changed[0]['version'] = '2'
        self.assertNotEqual(first, comparison_key(*changed))

    def test_contract_check_is_not_runtime_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'suite.json'
            path.write_text(json.dumps(suite()), encoding='utf-8')
            result = suite_check(path)
            self.assertEqual(result['status'], 'BLOCKED_SETUP')
            self.assertEqual(result['model_calls'], 0)
            self.assertEqual(result['database_writes'], 0)

    def test_cli_contract_check_blocks_unreviewed_dataset(self):
        from sqbf.cli import main
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'suite.json'
            path.write_text(json.dumps(suite()), encoding='utf-8')
            with patch('builtins.print'):
                self.assertEqual(main(['suite-check', '--suite', str(path)]), 2)

    def test_cli_invalid_file_is_controlled_without_data_disclosure(self):
        from sqbf.cli import main
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'suite.json'
            path.write_text('{"secret_canary":', encoding='utf-8')
            with patch('builtins.print') as output:
                self.assertEqual(main(['suite-check', '--suite', str(path)]), 2)
            self.assertNotIn('secret_canary', str(output.call_args))

    def test_approved_complete_contract_and_dataset_identity(self):
        dataset = {'schema_version': 1, 'dataset_id': 'NSN018', 'positions': [
            {'position_id': '1', 'input_status': 'verified', 'inputs': {'mass_g': 10},
             'expected_status': 'verified', 'expected': {'retained_g': 10}}]}
        dataset['approval'] = {'status': 'approved', 'approved_by': 'PO',
                               'approved_at': '2026-10-14', 'content_sha256': canonical_hash(dataset)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'suite.json'
            path.write_text(json.dumps(suite()), encoding='utf-8')
            self.assertEqual(suite_check(path, dataset)['status'], 'CONTRACT_READY')
            wrong = suite(); wrong['dataset_id'] = 'OTHER'
            path.write_text(json.dumps(wrong), encoding='utf-8')
            self.assertEqual(suite_check(path, dataset)['status'], 'BLOCKED_SETUP')
            wrong['dataset_id'] = 'NSN018'; wrong['required_position_ids'] = ['1', '2']
            path.write_text(json.dumps(wrong), encoding='utf-8')
            self.assertEqual(suite_check(path, dataset)['dataset']['status'], 'BLOCKED_POSITION_MISMATCH')

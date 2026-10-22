import copy
import importlib
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

projection = importlib.import_module('projects.ble-elva.tools.reference_projection')


def contracts():
    heights = [{'sand_height': 9.5, 'suspension_height': 12.2},
               {'sand_height': 9.6, 'suspension_height': 12.1}]
    unit = {'status': 'CONFIRMED_SOURCE_UNIT', 'conversion_authorized': True,
            'original_unit': 'cm', 'target_unit': 'mm', 'decision_by': 'PO',
            'decision_date': '2026-10-14', 'source_repetitions': heights}
    source = {'schema_version': 1, 'dataset_id': 'synthetic', 'positions': [
        {'position_id': 'P01', 'product': 'Synthetic stone', 'inputs': {
            'product': 'Synthetic stone', 'sample_code': 'TEST01', 'plan_date': '2026-05-08',
            'wash': [], 'shape': [{'fraction': '8 mm', 'total_g': 80, 'poor_g': 8.6, 'origin': 0}],
            'boiling': [{'initial_g': 600, 'final_g': 600, 'marl_g': 3.8, 'origin': 0}],
            'sieves': [{'input_g': 100, 'split_mm': None, 'partial_input_g': None, 'origin': 0,
                        'points': [{'sieve_mm': 2, 'retained_g': 50, 'partial': False}]}],
            'sand': [{'sand_height_mm': 9.55, 'suspension_height_mm': 12.15}],
            'derived_and_repetitions': [{'sample': 'TEST01', 'module': 'AGGREGATE_SAND_EQUIVALENT',
                'repetitions': [{'sortOrder': i + 1, 'sandHeightMm': h['sand_height'],
                                'suspensionHeightMm': h['suspension_height']} for i, h in enumerate(heights)]}],
            'password': 'SYNTHETIC_CANARY_DO_NOT_EXPORT', 'sample_id': 'private-row-id'}}]}
    suite = {'schema_version': 1, 'suite_id': 'SYNTHETIC', 'version': '1', 'dataset_id': 'synthetic',
        'required_position_ids': ['P01'], 'reference': {'sampling_date': '2026-05-08'},
        'provider': 'chatgpt_plan', 'automatic_retry': False, 'physical_operations': 'simulated',
        'real_delivery': False, 'cases': [{'case_id': 'C1', 'persona': 'staff', 'task': 'test',
            'oracle_contract': 'read-only', 'fixture_contract': 'new clone', 'expected': 'raw values',
            'implementation': 'pending', 'depends_on': [], 'max_minutes': 5,
            'max_actions': 10, 'max_model_calls': 12}]}
    return source, suite, unit


class ReferenceProjectionTests(unittest.TestCase):
    def test_explicit_units_repetitions_and_independent_rounding(self):
        source, suite, unit = contracts()
        original = copy.deepcopy(source)
        output = projection.project_reference(source, suite, unit)
        self.assertEqual(source, original)
        p = output['positions'][0]
        self.assertEqual(p['measurements']['sand'], [
            {'sand_height': '95', 'suspension_height': '122'},
            {'sand_height': '96', 'suspension_height': '121'}])
        self.assertEqual(p['arithmetic_proposals']['sand_individual_percent_1dp'], ['77.9', '79.3'])
        self.assertEqual(p['arithmetic_proposals']['sand_reported_integer'], '79')
        self.assertEqual(output['status'], 'PREPARATION_ONLY')
        self.assertFalse(output['dataset_approved'])
        self.assertFalse(output['normative_release'])
        self.assertEqual(output['database_writes'], 0)
        self.assertNotIn('SYNTHETIC_CANARY_DO_NOT_EXPORT', str(output))
        self.assertNotIn('private-row-id', str(output))

    def test_unit_decision_missing_or_changed_blocks(self):
        for change in ({'original_unit': 'UNCONFIRMED'}, {'conversion_authorized': False},
                       {'status': 'proposal'}, {'decision_by': ''}, {'source_repetitions': []}):
            with self.subTest(change=change):
                source, suite, unit = contracts(); unit.update(change)
                with self.assertRaises(ValueError): projection.project_reference(source, suite, unit)

    def test_actual_repetitions_required_no_mean_fallback(self):
        source, suite, unit = contracts()
        source['positions'][0]['inputs']['derived_and_repetitions'] = []
        with self.assertRaises(ValueError): projection.project_reference(source, suite, unit)

    def test_exact_position_sample_and_date_relations(self):
        for change in ('extra', 'duplicate', 'wrong_sample', 'wrong_date', 'wrong_dataset'):
            with self.subTest(change=change):
                source, suite, unit = contracts()
                row = source['positions'][0]
                if change == 'extra': suite['required_position_ids'].append('P02')
                if change == 'duplicate': source['positions'].append(copy.deepcopy(row))
                if change == 'wrong_sample': row['inputs']['derived_and_repetitions'][0]['sample'] = 'OTHER'
                if change == 'wrong_date': row['inputs']['plan_date'] = '2026-06-05'
                if change == 'wrong_dataset': source['dataset_id'] = 'OTHER'
                with self.assertRaises(ValueError): projection.project_reference(source, suite, unit)

    def test_invalid_or_synthetic_masses_block(self):
        for change in ({'origin': 1}, {'poor_g': 81}, {'total_g': None}, {'poor_g': 'NaN'}):
            source, suite, unit = contracts()
            source['positions'][0]['inputs']['shape'][0].update(change)
            with self.assertRaises(ValueError): projection.project_reference(source, suite, unit)

    def test_null_aggregate_stays_unrecorded_without_fabrication(self):
        source, suite, unit = contracts()
        source['positions'][0]['inputs']['shape'] = None
        output = projection.project_reference(source, suite, unit)['positions'][0]
        self.assertEqual(output['measurements']['shape'], [])
        self.assertIn('shape', output['unrecorded_modules'])
        self.assertNotIn('shape_percent_unrounded', output['arithmetic_proposals'])

    def test_numeric_representation_and_partial_raw_inputs_survive(self):
        source, suite, unit = contracts()
        source['positions'][0]['inputs']['derived_and_repetitions'].append({
            'sample': 'TEST01', 'taken_mass': 560, 'dried_mass': 557.900024,
            'series': [{'initial_mass': 268.5, 'dried_mass': 268.5,
                        'points': [{'mm': 2, 'pan': False, 'mass': 114.2},
                                   {'mm': 0, 'pan': True, 'mass': .4}]}]})
        source['positions'][0]['inputs']['derived_and_repetitions'].append({
            'sample': 'TEST01', 'module': 'AGGREGATE_MARL_CONTENT',
            'repetitions': [{'sortOrder': 1, 'kochzeitMin': 120,
                             'einwaageVorKochen': 600, 'rueckwaageNachKochen': 600}]})
        output = projection.project_reference(source, suite, unit)['positions'][0]['measurements']
        self.assertEqual(output['preparation'][0]['dry_g'], '557.900024')
        self.assertEqual(output['partial_series'][0]['points'][1],
                         {'sieve_mm': '0', 'pan': True, 'retained_g': '0.4'})
        self.assertEqual(output['boiling_repetitions'][0]['minutes'], '120')
        self.assertEqual(projection._n('600.000'), projection._n(600))
        self.assertEqual(projection._n('-0.0'), '0')

    def test_source_changes_invalidate_hash_and_comparison(self):
        source, suite, unit = contracts()
        before = projection.project_reference(source, suite, unit)
        source['positions'][0]['inputs']['shape'][0]['poor_g'] = 8.7
        after = projection.project_reference(source, suite, unit)
        self.assertNotEqual(before['source_sha256'], after['source_sha256'])
        result = projection.compare_measurements(before, after)
        self.assertEqual(result['reason'], 'MEASUREMENT_MISMATCH')
        self.assertEqual(result['positions'], ['P01'])
        self.assertNotIn('8.7', str(result))

    def test_comparison_cannot_accept_missing_extra_or_duplicate_rows(self):
        expected = projection.project_reference(*contracts())
        self.assertEqual(projection.compare_measurements(expected, copy.deepcopy(expected))['status'],
                         'REFERENCE_MEASUREMENTS_MATCH')
        for change in ('missing', 'extra', 'duplicate', 'field', 'dataset'):
            actual = copy.deepcopy(expected)
            if change == 'missing': actual['positions'] = []
            if change in ('extra', 'duplicate'):
                actual['positions'].append(copy.deepcopy(actual['positions'][0]))
                if change == 'extra': actual['positions'][-1]['position_id'] = 'P02'
            if change == 'field': del actual['positions'][0]['measurements']
            if change == 'dataset': actual['dataset_id'] = 'OTHER'
            self.assertEqual(projection.compare_measurements(expected, actual)['status'],
                             'BLOCKED_REFERENCE_COMPARISON')

    def test_cli_private_output_and_no_overwrite_or_sensitive_stdout(self):
        from sqbf.cli import main
        with TemporaryDirectory() as directory:
            root = Path(directory)
            args = ['reference-project']
            for name, value in zip(('dataset', 'suite', 'unit-decision'), contracts()):
                file = root / (name + '.json')
                file.write_text(json.dumps(value), encoding='utf-8')
                args.extend(['--' + name, str(file)])
            output = root / 'projection.json'; args.extend(['--output', str(output)])
            with patch('builtins.print') as stdout:
                self.assertEqual(main(args), 0)
                self.assertNotIn('Synthetic stone', str(stdout.call_args))
                self.assertNotIn('SYNTHETIC_CANARY', str(stdout.call_args))
            before = output.read_bytes()
            with patch('builtins.print'):
                self.assertEqual(main(args), 2)
            self.assertEqual(output.read_bytes(), before)

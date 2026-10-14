import copy
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sqbf.suites import canonical_hash
from test_suite_fixture import owned_fixture

module = importlib.import_module('projects.ble-elva.tools.suite_acceptance')


def contracts():
    suite = json.loads(Path('projects/ble-elva/suites/enzberg-nsn014-v0.2.json').read_text(encoding='utf-8'))
    dataset = {'schema_version': 1, 'dataset_id': suite['dataset_id'], 'positions': [
        {'position_id': key, 'input_status': 'verified', 'inputs': {'test': 1},
         'expected_status': 'verified', 'expected': {'test': 1}} for key in suite['required_position_ids']]}
    dataset['approval'] = {'status': 'approved', 'approved_by': 'PO', 'approved_at': '2026-10-15',
                           'content_sha256': canonical_hash(dataset)}
    fixture = owned_fixture()
    fixture['suite_copy'].update(dataset_sha256=dataset['approval']['content_sha256'], suite_sha256=canonical_hash(suite))
    fixture['personas'] = {key: {'storage_state': key + '-private.json'} for key in
                           ('laboratory_lead', 'laboratory_staff', 'wpk_lead', 'plant_lead')}
    fixture['identity_verifier'] = 'private-controller-verifier.dll'
    fixture['active_list_expected_products'] = ['synthetic product']
    fixture['read_only_oracle']['expected_counts'].update(workspace_products=10, sampling_plans=1,
        sampling_plan_items=10, customers=1, projects=1)
    snapshot = {'tables': {key: {'count': value, 'hash': 'fixed'}
                           for key, value in fixture['read_only_oracle']['expected_counts'].items()}}
    return fixture, suite, dataset, snapshot


class SuiteAcceptanceTests(unittest.TestCase):
    def test_four_actor_restore_scope_and_unchanged_snapshot_required(self):
        fixture, suite, dataset, snapshot = contracts()
        with patch.object(module, 'snapshot', return_value=snapshot), \
             patch.object(module, 'check_session', return_value={'status': 'SESSION_RESTORED'}) as session, \
             patch.object(module, 'check_persona', return_value={'status': 'PERSONA_SCOPE_VERIFIED'}) as scope:
            result = module.check_fixture(fixture, suite, dataset)
        self.assertEqual(result['status'], 'FIXTURE_GATES_VERIFIED')
        self.assertEqual(session.call_count, 4); self.assertEqual(scope.call_count, 4)
        self.assertEqual(result['model_calls'], 0); self.assertEqual(result['database_writes'], 0)
        self.assertIn('not test-adapter readiness', result['limitations'][0])

    def test_changed_contract_blocks_before_db_or_browser(self):
        fixture, suite, dataset, _ = contracts(); suite['version'] = 'changed'
        with patch.object(module, 'snapshot') as oracle, patch.object(module, 'check_session') as browser:
            self.assertEqual(module.check_fixture(fixture, suite, dataset)['reason'], 'SOURCE_OR_SUITE_CHANGED')
        oracle.assert_not_called(); browser.assert_not_called()

    def test_expired_session_or_missing_scope_stops_without_login_retry(self):
        fixture, suite, dataset, snapshot = contracts()
        with patch.object(module, 'snapshot', return_value=snapshot), \
             patch.object(module, 'check_session', return_value={'status': 'BLOCKED_SESSION'}) as session, \
             patch.object(module, 'check_persona') as scope:
            self.assertEqual(module.check_fixture(fixture, suite, dataset)['reason'], 'SESSION_FAILED')
        session.assert_called_once(); scope.assert_not_called()
        with patch.object(module, 'snapshot', return_value=snapshot), \
             patch.object(module, 'check_session', return_value={'status': 'SESSION_RESTORED'}) as session, \
             patch.object(module, 'check_persona', return_value={'status': 'BLOCKED_SCOPE_VERIFICATION'}) as scope:
            self.assertEqual(module.check_fixture(fixture, suite, dataset)['reason'], 'SCOPE_FAILED')
        session.assert_called_once(); scope.assert_called_once()

    def test_data_mutation_or_measured_samples_in_start_state_block(self):
        fixture, suite, dataset, before = contracts(); after=copy.deepcopy(before)
        after['tables']['workspace_products']['hash'] = 'changed'
        with patch.object(module, 'snapshot', side_effect=[before, after]), \
             patch.object(module, 'check_session', return_value={'status': 'SESSION_RESTORED'}), \
             patch.object(module, 'check_persona', return_value={'status': 'PERSONA_SCOPE_VERIFIED'}):
            self.assertEqual(module.check_fixture(fixture, suite, dataset)['reason'], 'PROTECTED_DATA_CHANGED')
        fixture['read_only_oracle']['expected_counts']['samples'] = 1
        with patch.object(module, 'snapshot') as oracle:
            self.assertEqual(module.check_fixture(fixture, suite, dataset)['reason'], 'START_STATE_MISMATCH')
        oracle.assert_not_called()

    def test_missing_read_rights_return_controlled_block(self):
        fixture, suite, dataset, _ = contracts()
        with patch.object(module, 'snapshot', side_effect=RuntimeError('SYNTHETIC_CANARY')):
            result = module.check_fixture(fixture, suite, dataset)
        self.assertEqual(result['reason'], 'EVIDENCE_UNAVAILABLE')
        self.assertNotIn('SYNTHETIC_CANARY', str(result))

import copy
import importlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID

from sqbf.suites import canonical_hash

fixture_module = importlib.import_module('projects.ble-elva.tools.suite_fixture')
scope_module = importlib.import_module('projects.ble-elva.tools.persona_scope')


def owned_fixture():
    fixture = json.loads(Path('projects/ble-elva/fixtures/enzberg-product-core-v0.2.json').read_text(encoding='utf-8'))
    fixture['target_url'] = 'http://127.0.0.1:5082/'
    fixture['database'].update(container='sqbf-nsn014-0123456789ab', name='sqbf_nsn014_0123456789ab',
        volume='sqbf-nsn014-0123456789ab-data', host_port=55434, container_id='a' * 64)
    fixture['suite_copy'] = {'disposable': True, 'never_reset': True, 'golden_sha256': 'b' * 64,
                            'source_database': 'ble_benchmark_20261012', 'stage': 'container_created'}
    return fixture


def prepared_contracts():
    fixture = owned_fixture()
    products, positions, items, assignments = [], [], [], []
    for i in range(1, 11):
        key = str(UUID(int=i))
        products.append({'id': key, 'name': 'Synthetic ' + str(i), 'material_class_id': 'class', 'product_type_id': 'type'})
        positions.append({'position_id': 'P' + str(i), 'product': 'Synthetic ' + str(i),
                          'input_status': 'verified', 'inputs': {'product_id': key},
                          'expected_status': 'verified', 'expected': {'raw': i}})
        items.append({'sampling_plan_id': 'plan', 'product_id': key, 'rezept_version_id': None})
        assignments.append({'product_id': key, 'norm_version_id': 'version'})
    dataset = {'schema_version': 1, 'dataset_id': 'synthetic', 'positions': positions}
    dataset['approval'] = {'status': 'approved', 'approved_by': 'PO', 'approved_at': '2026-10-15',
                           'content_sha256': canonical_hash(dataset)}
    context = {'products': products, 'plan': [{'id': 'plan'}], 'items': items,
               'assignments': assignments, 'versions': [], 'existing_standard_parents': []}
    available = {'classes': [{'id': 'class', 'active': True}], 'types': [{'id': 'type', 'active': True}],
                 'versions': [{'id': 'version'}], 'standard_ids': []}
    return context, dataset, fixture, available


class SuiteFixtureTests(unittest.TestCase):
    def test_target_refuses_normal_golden_and_old_lab_ports(self):
        fixture_module.validate_target(owned_fixture())
        for change in ({'host_port': 5433}, {'host_port': 55432}, {'host_port': 55433},
                       {'container': 'ble-postgres'}, {'container_id': 'short'}, {'volume': 'other'}):
            fixture = owned_fixture(); fixture['database'].update(change)
            with self.assertRaises(ValueError): fixture_module.validate_target(fixture)

    def test_plan_compiler_has_atomic_empty_target_guard_and_no_samples_or_reset(self):
        context, dataset, fixture, available = prepared_contracts()
        original = copy.deepcopy(context)
        sql, mapping = fixture_module.compile_prepared_plan(context, dataset, fixture, available)
        self.assertEqual(context, original)
        self.assertTrue(sql.startswith('BEGIN;'))
        self.assertTrue(sql.endswith('COMMIT;'))
        self.assertEqual(sql.count('INSERT INTO workspace_products '), 10)
        self.assertEqual(sql.count('INSERT INTO sampling_plan_items '), 10)
        self.assertIn('TARGET_NOT_EMPTY', sql)
        for forbidden in ('INSERT INTO samples ', 'INSERT INTO lims_sample ', 'DELETE ', 'TRUNCATE ', 'DROP '):
            self.assertNotIn(forbidden, sql)
        self.assertTrue(set(mapping['products']).isdisjoint(mapping['products'].values()))

    def test_missing_classification_recipe_or_wrong_product_blocks(self):
        for change in ('class', 'recipe', 'duplicate', 'name', 'assignment'):
            args = list(prepared_contracts()); context, _, _, available = args
            if change == 'class': available['classes'][0]['active'] = False
            if change == 'recipe': context['items'][0]['rezept_version_id'] = 'unverified'
            if change == 'duplicate': context['items'][1]['product_id'] = context['items'][0]['product_id']
            if change == 'name': context['products'][0]['name'] = 'Changed'
            if change == 'assignment': context['assignments'][0]['product_id'] = 'unexpected'
            with self.assertRaises(ValueError): fixture_module.compile_prepared_plan(*args)

    def test_exact_existing_norm_parent_required_no_inferred_edition(self):
        args = list(prepared_contracts()); context, _, _, available = args
        available['versions'] = []
        context['versions'] = [{'id': 'version', 'norm_id': 'existing-parent', 'previous_version_id': None}]
        with self.assertRaises(ValueError): fixture_module.compile_prepared_plan(*args)
        context['existing_standard_parents'] = [{'id': 'existing-parent', 'number': 'Existing source only'}]
        sql, _ = fixture_module.compile_prepared_plan(*args)
        self.assertEqual(sql.count('INSERT INTO norm_standards '), 1)

    def test_operation_exception_is_redacted(self):
        error = subprocess.CalledProcessError(1, ['canary'], stderr='SYNTHETIC_SECRET_CANARY')
        with patch.object(fixture_module.subprocess, 'run', side_effect=error):
            with self.assertRaises(RuntimeError) as caught: fixture_module._command(['safe'])
        self.assertNotIn('SYNTHETIC_SECRET_CANARY', str(caught.exception))

    def test_nonempty_recovery_is_blocked_without_second_command_or_credentials(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.json'; path.write_text(json.dumps(owned_fixture()))
            source = json.loads(Path('projects/ble-elva/fixtures/enzberg-product-core-v0.2.json').read_text())
            with patch.object(fixture_module, 'verify_docker_identity', return_value={'container_id': 'a'*64}), \
                 patch.object(fixture_module, '_command', return_value=SimpleNamespace(stdout=b'1\n0\n')) as command, \
                 patch.object(fixture_module, 'load_credentials') as credential:
                with self.assertRaises(ValueError): fixture_module.complete_inspected_empty_copy(path, source)
                command.assert_called_once(); credential.assert_not_called()


class PersonaScopeTests(unittest.TestCase):
    def data(self, role='Mitarbeiter'):
        fixture = owned_fixture()
        actor = {'username': 'sqbf-labormitarbeiter', 'user_id': str(UUID(int=100)),
                 'tenant_id': fixture['fixture_data']['tenant_id'], 'plant_id': fixture['fixture_data']['plant_id'],
                 'role': role, 'allowed_permissions': ['products.view', 'samples.create']}
        ticket = {'valid': True, 'username': actor['username'], 'user_id': actor['user_id']}
        scope = {'username': actor['username'], 'user_id': actor['user_id'], 'users': 1,
                 'active': True, 'admin': False, 'tenant_id': actor['tenant_id'], 'tenant_active': True,
                 'roles': [role], 'permissions': actor['allowed_permissions'][:], 'plant_valid': True,
                 'read_only': 'on', 'database': fixture['database']['name'], 'role': fixture['database']['bootstrap_user'],
                 'scopes': [{'type': 'Plant', 'key': actor['plant_id'], 'tenant_id': actor['tenant_id'],
                             'plant_id': actor['plant_id'], 'customer_id': None, 'laboratory_id': None},
                            {'type': 'Tenant', 'key': actor['tenant_id'], 'tenant_id': actor['tenant_id'],
                             'plant_id': None, 'customer_id': None, 'laboratory_id': None}]}
        return ticket, scope, actor, fixture

    def test_existing_nonadmin_roles_pass(self):
        for role in ('Laborleiter', 'Mitarbeiter', 'Viewer'):
            self.assertEqual(scope_module.evaluate_persona(*self.data(role))['status'], 'PERSONA_SCOPE_VERIFIED')

    def test_wrong_user_tenant_inactive_permissions_roles_and_global_scope_block(self):
        for field, value in (('username', 'wrong'), ('tenant_id', 'wrong'), ('active', False),
                             ('admin', True), ('roles', []), ('roles', ['Mitarbeiter', 'Admin']),
                             ('permissions', []), ('permissions', ['products.view', 'samples.create', 'system.manage']),
                             ('read_only', 'off'), ('users', True), ('plant_valid', False)):
            args = list(self.data()); args[1][field] = value
            self.assertEqual(scope_module.evaluate_persona(*args)['status'], 'BLOCKED_SCOPE_VERIFICATION')
        args = list(self.data()); args[1]['scopes'].append({'type': 'Global'})
        self.assertEqual(scope_module.evaluate_persona(*args)['status'], 'BLOCKED_SCOPE_VERIFICATION')

    def test_invalid_signature_or_extra_plant_and_no_sensitive_output(self):
        args = list(self.data()); args[0]['valid'] = False; args[1]['password_hash'] = 'HARMLESS_CANARY'
        result = scope_module.evaluate_persona(*args)
        self.assertEqual(result['status'], 'BLOCKED_SCOPE_VERIFICATION')
        self.assertNotIn('HARMLESS_CANARY', json.dumps(result))
        args = list(self.data()); args[1]['scopes'][0]['key'] = str(UUID(int=999))
        self.assertEqual(scope_module.evaluate_persona(*args)['status'], 'BLOCKED_SCOPE_VERIFICATION')

    def test_projection_never_selects_credential_fields_and_rolls_back(self):
        sql = scope_module.PROJECTION.read_text(encoding='utf-8').lower()
        self.assertIn('read only', sql); self.assertIn('rollback;', sql)
        for forbidden in ('password_hash', 'security_stamp', 'concurrency_stamp', 'insert ', 'update ', 'grant '):
            self.assertNotIn(forbidden, sql)

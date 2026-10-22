import importlib
import json
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from test_suite_fixture import owned_fixture

module = importlib.import_module('projects.ble-elva.tools.protected_oracle')


class ProtectedOracleTests(unittest.TestCase):
    def run_collect(self, tables, *, rows=None, identity=None):
        fixture = owned_fixture();fixture['database'].update(oracle_role='sqbf_oracle_ro')
        calls = []
        def run(command, **kwargs):
            calls.append((command, kwargs['input']))
            ident = identity or {'database': fixture['database']['name'], 'role': 'sqbf_oracle_ro', 'read_only': 'on'}
            body = rows if rows is not None else [{'table': t, 'count': 1, 'hash': 'h-' + t} for t in sorted(set(tables))]
            return CompletedProcess(command, 0, stdout='\n'.join(json.dumps(x) for x in [ident] + body) + '\n')
        with patch.object(module, 'verify_docker_identity', return_value={'container_id': 'c' * 64}):
            return module.collect_normalized_hashes(fixture, tables, run=run), calls, fixture

    def test_hashes_exclude_exactly_the_audit_columns_and_use_the_select_only_role(self):
        result, calls, fixture = self.run_collect(['sampling_plans', 'workspace_products'])
        self.assertEqual(result, {'sampling_plans': {'count': 1, 'hash': 'h-sampling_plans'}, 'workspace_products': {'count': 1, 'hash': 'h-workspace_products'}})
        command, sql = calls[0]
        self.assertIn('sqbf_oracle_ro', command);self.assertIn('READ ONLY', sql);self.assertTrue(sql.rstrip().endswith('ROLLBACK;'))
        self.assertEqual(sql.count("ARRAY['updated_at','updated_by']"), 4)
        self.assertNotRegex(sql, r'(?i)\b(insert|update\s+public|delete|drop|truncate|create)\b')
        self.assertEqual(module.AUDIT_COLUMNS, ('updated_at', 'updated_by'))

    def test_unsafe_identifiers_and_identity_mismatches_are_refused(self):
        for tables in ([], ['a; drop table x'], ['Samples'], ['samples", "x']):
            with self.assertRaises(ValueError):self.run_collect(tables)
        with self.assertRaises(ValueError):self.run_collect(['samples'], identity={'database': 'x', 'role': 'y', 'read_only': 'off'})
        with self.assertRaises(ValueError):self.run_collect(['samples'], rows=[])

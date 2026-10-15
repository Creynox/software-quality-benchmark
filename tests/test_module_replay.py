import importlib
import json
import re
import unittest
from subprocess import CompletedProcess
from uuid import NAMESPACE_URL, UUID, uuid5

module = importlib.import_module('projects.ble-elva.tools.module_replay')

SRC_PRODUCT, NEW_PRODUCT = str(UUID(int=1)), str(UUID(int=2))
CATALOG = {'AGGREGATE_SIEVE_ANALYSIS': str(UUID(int=900)), 'AGGREGATE_SHAPE_INDEX': str(UUID(int=901))}
SOURCE_ROWS = [{'id': str(UUID(int=10)), 'product_id': SRC_PRODUCT, 'module_code': 'AGGREGATE_SIEVE_ANALYSIS', 'is_mandatory': True,
                'is_default_active': True, 'comment': "it's a comment", 'default_config_json': '{"a":1}'},
               {'id': str(UUID(int=11)), 'product_id': SRC_PRODUCT, 'module_code': 'AGGREGATE_SHAPE_INDEX', 'is_mandatory': False,
                'is_default_active': True, 'comment': None, 'default_config_json': None}]


class PlanTests(unittest.TestCase):
    def test_rows_are_mapped_deterministically_and_copied_unchanged(self):
        planned = module.plan_rows(SOURCE_ROWS, {SRC_PRODUCT: NEW_PRODUCT}, CATALOG)
        self.assertEqual(planned[0]['id'], str(uuid5(NAMESPACE_URL, 'sqbf-nsn014/lims_product_test_modules/' + SOURCE_ROWS[0]['id'])))
        self.assertEqual([(r['product_id'], r['test_module_id']) for r in planned],
                         [(NEW_PRODUCT, CATALOG['AGGREGATE_SIEVE_ANALYSIS']), (NEW_PRODUCT, CATALOG['AGGREGATE_SHAPE_INDEX'])])
        self.assertEqual({k: planned[0][k] for k in ('is_mandatory', 'is_default_active', 'comment', 'default_config_json')},
                         {k: SOURCE_ROWS[0][k] for k in ('is_mandatory', 'is_default_active', 'comment', 'default_config_json')})
        self.assertEqual(planned, module.plan_rows(SOURCE_ROWS, {SRC_PRODUCT: NEW_PRODUCT}, CATALOG))

    def test_unknown_product_module_code_or_duplicates_are_refused(self):
        with self.assertRaises(module.ReplayError):module.plan_rows(SOURCE_ROWS, {}, CATALOG)
        with self.assertRaises(module.ReplayError):module.plan_rows(SOURCE_ROWS, {SRC_PRODUCT: NEW_PRODUCT}, {'AGGREGATE_SIEVE_ANALYSIS': CATALOG['AGGREGATE_SIEVE_ANALYSIS']})
        with self.assertRaises(module.ReplayError):module.plan_rows(SOURCE_ROWS * 2, {SRC_PRODUCT: NEW_PRODUCT}, CATALOG)

    def test_insert_statement_is_guarded_escaped_and_touches_only_the_activation_table(self):
        planned = module.plan_rows(SOURCE_ROWS, {SRC_PRODUCT: NEW_PRODUCT}, CATALOG)
        sql = module.insert_sql(planned)
        self.assertIn("TARGET_NOT_EMPTY", sql);self.assertIn("ROWCOUNT_MISMATCH", sql);self.assertIn("it''s a comment", sql)
        self.assertEqual(re.findall(r'(?i)\b(insert into|update|delete from|truncate|drop|alter)\b[^;]{0,40}', sql)[0], 'INSERT INTO')
        self.assertEqual(len(re.findall(r'(?i)\binsert into\b', sql)), 1);self.assertNotRegex(sql, r'(?i)\b(delete|truncate|drop|alter)\b')
        self.assertIn('public.lims_product_test_modules', sql)
        bad = dict(planned[0], product_id="x'; DROP TABLE y;--")
        with self.assertRaises(module.ReplayError):module.insert_sql([bad])
        self.assertTrue(sql.startswith('BEGIN;') and sql.rstrip().endswith('COMMIT;'))


class CollectTests(unittest.TestCase):
    def test_source_query_is_read_only_scoped_to_the_given_products_and_rejects_bad_ids(self):
        seen = []
        def run(command, **kwargs):
            seen.append((command, kwargs['input']))
            return CompletedProcess(command, 0, stdout=json.dumps(SOURCE_ROWS) + '\n')
        rows = module.collect_source_modules([SRC_PRODUCT], run=run)
        command, sql = seen[0]
        self.assertEqual(rows, SOURCE_ROWS);self.assertIn('ble-postgres', command);self.assertIn('BEGIN TRANSACTION READ ONLY', sql)
        self.assertTrue(sql.rstrip().endswith('ROLLBACK;'));self.assertIn("'" + SRC_PRODUCT + "'", sql)
        for bad in ([], ["x') OR 1=1 --"], ['']):
            with self.assertRaises(module.ReplayError):module.collect_source_modules(bad, run=run)

    def test_replay_reports_counts_by_module_without_values(self):
        fixture = {'suite_copy': {'mapping': {'products': {SRC_PRODUCT: NEW_PRODUCT}}},
                   'database': {'container': 'c', 'bootstrap_user': 'u', 'name': 'n'}}
        calls = []
        def run(command, **kwargs):
            body = kwargs['input'];calls.append(body)
            if 'lims_test_modules' in body and 'json_object_agg' in body:return CompletedProcess(command, 0, stdout=json.dumps(CATALOG) + '\n')
            if 'json_agg' in body:return CompletedProcess(command, 0, stdout=json.dumps(SOURCE_ROWS) + '\n')
            return CompletedProcess(command, 0, stdout='')
        evidence = module.replay(fixture, run=run)
        self.assertEqual((evidence['rows'], evidence['per_module'], evidence['with_default_config']),
                         (2, {'AGGREGATE_SHAPE_INDEX': 1, 'AGGREGATE_SIEVE_ANALYSIS': 1}, 1))
        self.assertNotIn('comment', json.dumps(evidence));self.assertTrue(calls[-1].startswith('BEGIN;'))
        with self.assertRaises(module.ReplayError):
            module.replay(fixture, run=lambda command, **kw: CompletedProcess(command, 0, stdout='[]\n' if 'json_agg' in kw['input'] else json.dumps(CATALOG) + '\n'))

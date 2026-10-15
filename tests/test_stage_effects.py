import copy
import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from test_regular_runner import BASE_TABLES, PLAN, scoped, static_fixture

effects = importlib.import_module('projects.ble-elva.tools.stage_effects')
runner = importlib.import_module('projects.ble-elva.tools.regular_runner')
oracle = importlib.import_module('projects.ble-elva.tools.protected_oracle')
probe = importlib.import_module('projects.ble-elva.tools.side_effect_probe')

CASES = runner.CASE_IDS
READ_ONLY = {'NSN014-RECEIPT', 'NSN014-ASSESS', 'NSN014-WPK', 'NSN014-ANALYSIS', 'NSN014-RIGHTS'}


def contract():
    return effects.load_contract(CASES)


class ContractFileTests(unittest.TestCase):
    def test_the_contract_covers_exactly_the_twelve_stages_and_names_the_dry_run_footprint(self):
        c = contract()
        self.assertEqual(set(c['stages']), CASES);self.assertEqual(len(c['stages']), 12)
        self.assertEqual({k for k, v in c['stages'].items() if v['mode'] == 'read_only'}, READ_ONLY)
        for case in READ_ONLY:self.assertEqual(c['stages'][case]['tables'], [])
        # Observed in the dry run: the first saved result and the partial sieve start write the lazy module and LIMS rows.
        self.assertIn('lims_probe_test_modules', c['stages']['NSN014-PREPARATION']['tables'])
        self.assertTrue({'lims_customer', 'lims_product', 'lims_project', 'lims_sample'} <= set(c['stages']['NSN014-SIEVE']['tables']))
        self.assertEqual(c['stages']['NSN014-REPORT']['tables'], ['ble_reports', 'workspace_probe_report_entries'])
        self.assertEqual(len(effects.contract_hash(c)), 64)

    def test_exactly_one_audit_only_allowance_for_one_stage_table_row_and_two_columns(self):
        c = contract()
        self.assertEqual(c['audit_only_allowances'], [{'case_id': 'NSN014-PLAN', 'table': 'sampling_plans', 'target': 'plan_id',
                                                       'columns': ['updated_at', 'updated_by'], 'max_rows': 1,
                                                       'action': c['audit_only_allowances'][0]['action'], 'evidence': c['audit_only_allowances'][0]['evidence']}])
        f = static_fixture()
        resolved = effects.allowances(c, f)
        self.assertEqual([(a['case_id'], a['table'], a['ids']) for a in resolved], [('NSN014-PLAN', 'sampling_plans', [PLAN])])
        self.assertEqual(effects.allowances(c, f, 'NSN014-PLAN')[0]['ids'], [PLAN])
        for other in CASES - {'NSN014-PLAN'}:self.assertEqual(effects.allowances(c, f, other), [])

    def test_invalid_contracts_are_refused(self):
        def broken(change):
            c = contract();change(c)
            with self.assertRaises(effects.ContractError):effects.validate_contract(c, CASES)
        broken(lambda c: c.update(schema_version='x'))
        broken(lambda c: c.update(audit_columns=['updated_at']))
        broken(lambda c: c['stages'].pop('NSN014-SE'))
        broken(lambda c: c['stages'].update(extra=dict(mode='read_only', tables=[])))
        broken(lambda c: c['stages']['NSN014-SE'].update(mode='maybe'))
        broken(lambda c: c['stages']['NSN014-RECEIPT'].update(tables=['samples']))
        broken(lambda c: c['stages']['NSN014-SE'].update(tables=['samples; DROP TABLE samples']))
        broken(lambda c: c['stages']['NSN014-SE'].update(tables=['samples', 'samples']))
        for allowance in (dict(case_id='NSN014-RECEIPT'), dict(table='workspace_products'), dict(columns=['updated_at', 'name']), dict(columns=[]),
                          dict(target='id'), dict(max_rows=0), dict(max_rows=11), dict(max_rows=True)):
            broken(lambda c, a=allowance: c['audit_only_allowances'][0].update(a))
        broken(lambda c: c['audit_only_allowances'].append(dict(c['audit_only_allowances'][0])))

    def test_a_missing_or_unreadable_contract_file_is_an_error_not_a_default(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(OSError):effects.load_contract(CASES, Path(directory) / 'missing.json')
            bad = Path(directory) / 'bad.json';bad.write_text('{not json', encoding='utf-8')
            with self.assertRaises(ValueError):effects.load_contract(CASES, bad)


class ScopedComparisonTests(unittest.TestCase):
    ALLOW = dict(max_rows=1)

    def test_only_an_unchanged_target_and_unchanged_other_rows_are_audit_only(self):
        self.assertTrue(effects.scoped_equal(scoped(), scoped(), self.ALLOW))
        for after in (scoped(target='x'), scoped(rest='x'), scoped(rest_count=1), scoped(target_count=0), scoped(target_count=2)):
            self.assertFalse(effects.scoped_equal(scoped(), after, self.ALLOW), after)
        self.assertFalse(effects.scoped_equal(None, scoped(), self.ALLOW));self.assertFalse(effects.scoped_equal(scoped(), None, self.ALLOW))
        self.assertFalse(effects.scoped_equal({'target_count': 1}, {'target_count': 1}, self.ALLOW))

    def test_protected_delta_tolerates_nothing_without_an_allowance_for_that_table(self):
        mutable = runner.MUTABLE_TABLES
        base = copy.deepcopy(BASE_TABLES)
        stamped = dict(copy.deepcopy(BASE_TABLES), sampling_plans={'count': 1, 'hash': 's'})
        allowance = dict(table='sampling_plans', columns=['updated_at', 'updated_by'], max_rows=1, ids=[PLAN])
        ok = effects.protected_delta(base, stamped, [allowance], {'sampling_plans': scoped()}, {'sampling_plans': scoped()}, mutable=mutable)
        self.assertEqual((ok['unchanged'], ok['audit_only']), (True, [{'table': 'sampling_plans', 'rows': 1, 'columns': ['updated_at', 'updated_by']}]))
        for resolved in ([], [dict(allowance, table='workspace_products')]):
            bad = effects.protected_delta(base, stamped, resolved, {'sampling_plans': scoped()}, {'sampling_plans': scoped()}, mutable=mutable)
            self.assertEqual((bad['unchanged'], bad['changed_tables']), (False, ['sampling_plans']))
        both = dict(stamped, workspace_products={'count': 10, 'hash': 'other'})
        result = effects.protected_delta(base, both, [allowance], {'sampling_plans': scoped()}, {'sampling_plans': scoped()}, mutable=mutable)
        self.assertEqual((result['changed_tables'], [a['table'] for a in result['audit_only']]), (['workspace_products'], ['sampling_plans']))
        self.assertFalse(effects.protected_delta(base, {'samples': base['samples']}, [allowance], {}, {}, mutable=mutable)['unchanged'])
        # Mutable benchmark tables are never judged here.
        self.assertTrue(effects.protected_delta(base, dict(base, samples={'count': 9, 'hash': 'z'}), [], {}, {}, mutable=mutable)['unchanged'])


class FindingTests(unittest.TestCase):
    PROTECTED = {'sampling_plans', 'workspace_products'}

    def all_tables(self, **changed):
        before = {'samples': {'count': 0, 'hash': 'a'}, 'lims_probe_test_modules': {'count': 0, 'hash': 'm'}, 'ble_reports': {'count': 0, 'hash': 'r'},
                  'sampling_plans': {'count': 1, 'hash': 'p'}, 'identity_users': {'count': 4, 'hash': 'u'}}
        after = dict(before, **changed)
        return before, after

    def test_a_write_outside_the_listed_tables_of_a_write_stage_is_a_finding_not_a_stop(self):
        before, after = self.all_tables(identity_users={'count': 4, 'hash': 'changed'}, lims_probe_test_modules={'count': 3, 'hash': 'n'})
        out = effects.findings(contract(), 'NSN014-PREPARATION', before, after, protected=self.PROTECTED)
        self.assertEqual(out, [{'code': 'UNEXPECTED_TABLE_WRITE', 'table': 'identity_users'}])

    def test_every_change_in_a_read_only_stage_is_reported(self):
        before, after = self.all_tables(samples={'count': 1, 'hash': 'b'}, lims_probe_test_modules={'count': 1, 'hash': 'x'})
        out = effects.findings(contract(), 'NSN014-RECEIPT', before, after, protected=self.PROTECTED)
        self.assertEqual(out, [{'code': 'WRITE_IN_READ_ONLY_STAGE', 'table': 'lims_probe_test_modules'}, {'code': 'WRITE_IN_READ_ONLY_STAGE', 'table': 'samples'}])

    def test_protected_tables_are_left_to_the_hard_gate_and_unchanged_runs_have_no_findings(self):
        before, after = self.all_tables(sampling_plans={'count': 1, 'hash': 'stamped'})
        self.assertEqual(effects.findings(contract(), 'NSN014-RECEIPT', before, after, protected=self.PROTECTED), [])
        self.assertEqual(effects.findings(contract(), 'NSN014-SE', before, dict(before), protected=self.PROTECTED), [])
        self.assertEqual(effects.findings(contract(), 'NSN014-SE', before, {'samples': before['samples']}, protected=self.PROTECTED),
                         [{'code': 'TABLE_SET_CHANGED', 'table': None}])

    def test_external_changes_between_stages_are_named(self):
        before, after = self.all_tables(identity_users={'count': 5, 'hash': 'c'})
        self.assertEqual(effects.external_changes(None, before), []);self.assertEqual(effects.external_changes(before, dict(before)), [])
        self.assertEqual(effects.external_changes(before, after), ['identity_users'])
        self.assertEqual(effects.external_changes(before, {'samples': before['samples']}), ['TABLE_SET_CHANGED'])


def capture_sequence(states):
    """A capture() stand-in that returns the prepared states one after the other."""
    queue = list(states)
    return lambda fixture, resolved: queue.pop(0)


def state(tables=None, all_=None, plan_scope=None):
    t = copy.deepcopy(BASE_TABLES);t.update(tables or {})
    return {'tables': t, 'all': all_ or {'x': {'count': 0, 'hash': 'x'}}, 'scoped': {'sampling_plans': plan_scope or scoped()}}


class GuardedStageTests(unittest.TestCase):
    def run_stage(self, case, states, tracker=None, outcome=None):
        f = static_fixture();c = contract()
        tracker = tracker or {'tables': copy.deepcopy(BASE_TABLES), 'previous': None}
        called = []
        def run_case():
            called.append(case);return outcome or {'result': 'PASS', 'technical_gate': 'PASS'}
        result = runner.guarded_stage(f, c, case, tracker, run_case, capture=capture_sequence(states))
        return result, tracker, called

    def test_plan_stage_with_the_audit_stamp_on_the_plan_row_passes_and_records_the_scope(self):
        stamped = state({'sampling_plans': {'count': 1, 'hash': 'stamped'}, 'samples': {'count': 10, 'hash': 's'}})
        result, tracker, called = self.run_stage('NSN014-PLAN', [state(), stamped])
        self.assertEqual((result['result'], result['audit_only_changes'], result['technical_gate']), ('PASS', ['sampling_plans'], 'PASS'))
        self.assertEqual(result['audit_only_scope'], [{'table': 'sampling_plans', 'rows': 1, 'columns': ['updated_at', 'updated_by']}])
        self.assertEqual(tracker['tables'], stamped['tables']);self.assertEqual(result['side_effect_findings'], [])
        self.assertEqual(called, ['NSN014-PLAN']);self.assertIn('stage_wall_seconds', result)

    def test_the_same_stamp_in_any_other_stage_is_an_invalid_harness_stop(self):
        # RECEIPT starts from the stamped state (end of PLAN) and must not stamp again: nothing is allowed there.
        stamped = copy.deepcopy(BASE_TABLES);stamped['sampling_plans'] = {'count': 1, 'hash': 'stamped'}
        restamped = copy.deepcopy(BASE_TABLES);restamped['sampling_plans'] = {'count': 1, 'hash': 'stamped-again'}
        result, tracker, _ = self.run_stage('NSN014-RECEIPT', [state(stamped), state(restamped)], tracker={'tables': stamped, 'previous': None})
        self.assertEqual((result['result'], result['technical_gate'], result['reason'], result['changed_tables']),
                         ('INVALID', 'INVALID', 'STATIC_FIXTURE_CHANGED', ['sampling_plans']))

    def test_a_stamp_on_another_row_or_a_second_changed_column_set_in_the_plan_stage_is_not_covered(self):
        for plan_scope in (scoped(rest='other', rest_count=1), scoped(target='changed-content'), scoped(target_count=0)):
            stamped = state({'sampling_plans': {'count': 1, 'hash': 'stamped'}}, plan_scope=plan_scope)
            result, _, _ = self.run_stage('NSN014-PLAN', [state(), stamped])
            self.assertEqual((result['result'], result['changed_tables']), ('INVALID', ['sampling_plans']), plan_scope)

    def test_a_changed_protected_table_in_a_write_stage_stops_the_suite_even_if_the_stage_lists_other_tables(self):
        result, _, _ = self.run_stage('NSN014-PREPARATION', [state(), state({'workspace_products': {'count': 10, 'hash': 'edited'}})])
        self.assertEqual((result['result'], result['reason'], result['changed_tables']), ('INVALID', 'STATIC_FIXTURE_CHANGED', ['workspace_products']))

    def test_unlisted_tables_are_findings_and_the_result_is_kept(self):
        after_all = {'x': {'count': 0, 'hash': 'x'}, 'lims_probe_test_modules': {'count': 2, 'hash': 'm'}, 'identity_users': {'count': 4, 'hash': 'new'}}
        before_all = {'x': {'count': 0, 'hash': 'x'}, 'lims_probe_test_modules': {'count': 0, 'hash': 'm0'}, 'identity_users': {'count': 4, 'hash': 'old'}}
        result, _, _ = self.run_stage('NSN014-PREPARATION', [state(all_=before_all), state(all_=after_all)])
        self.assertEqual((result['result'], result['technical_gate']), ('PASS', 'PASS'))
        self.assertEqual(result['side_effect_findings'], [{'code': 'UNEXPECTED_TABLE_WRITE', 'table': 'identity_users'}])
        result, _, _ = self.run_stage('NSN014-WPK', [state(all_=before_all), state(all_=after_all)])
        self.assertEqual([f['code'] for f in result['side_effect_findings']], ['WRITE_IN_READ_ONLY_STAGE', 'WRITE_IN_READ_ONLY_STAGE'])
        self.assertEqual(result['result'], 'PASS')

    def test_a_stage_never_starts_from_a_state_other_than_the_end_of_the_previous_one(self):
        edited = state({'workspace_products': {'count': 10, 'hash': 'edited-between-stages'}})
        result, tracker, called = self.run_stage('NSN014-SHAPE', [edited])
        self.assertEqual((result['result'], result['technical_gate'], result['reason'], result['changed_tables']),
                         ('BLOCKED', 'BLOCKED', 'STATIC_FIXTURE_CHANGED', ['workspace_products']))
        self.assertEqual(called, [])  # the stage did not run
        self.assertEqual(tracker['tables'], BASE_TABLES)

    def test_external_writes_between_stages_in_unprotected_tables_are_recorded(self):
        first = state(all_={'a': {'count': 1, 'hash': '1'}})
        second_start = state(all_={'a': {'count': 1, 'hash': 'external'}})
        tracker = {'tables': copy.deepcopy(BASE_TABLES), 'previous': first}
        result, _, _ = self.run_stage('NSN014-SE', [second_start, second_start], tracker=tracker)
        self.assertEqual(result['external_changes_before_stage'], ['a'])


class CollectorTests(unittest.TestCase):
    def fixture(self):
        f = static_fixture();f['database'] = {'container': 'c', 'name': 'db', 'oracle_role': 'sqbf_oracle_ro'};return f

    def run_with(self, stdout, resolved):
        sent = []
        def run(args, **kwargs):
            sent.append((args, kwargs.get('input')));return MagicMock(stdout=stdout, returncode=0)
        with patch.object(oracle, 'validate_target'), patch.object(oracle, 'verify_docker_identity', return_value={'container_id': 'cid'}):
            return oracle.collect_scoped_hashes(self.fixture(), resolved, run=run), sent

    def test_scoped_hashes_are_read_only_select_only_and_keyed_by_table(self):
        identity = json.dumps({'database': 'db', 'role': 'sqbf_oracle_ro', 'read_only': 'on'})
        row = json.dumps({'table': 'sampling_plans', 'target_count': 1, 'target_hash': 't', 'rest_count': 0, 'rest_hash': 'r'})
        result, sent = self.run_with(identity + '\n' + row + '\n', [dict(table='sampling_plans', ids=[PLAN])])
        self.assertEqual(result, {'sampling_plans': {'target_count': 1, 'target_hash': 't', 'rest_count': 0, 'rest_hash': 'r'}})
        args, sql = sent[0]
        self.assertEqual((args[args.index('-U') + 1], args[args.index('-d') + 1]), ('sqbf_oracle_ro', 'db'))
        self.assertIn('READ ONLY', sql);self.assertIn(PLAN, sql);self.assertIn('FROM public.sampling_plans', sql)
        for forbidden in ('INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'GRANT'):self.assertNotIn(forbidden, sql)

    def test_unsafe_identifiers_wrong_identity_or_a_missing_row_are_refused(self):
        for bad in (dict(table='sampling_plans; DROP', ids=[PLAN]), dict(table='sampling_plans', ids=["x'); DROP"]), dict(table='sampling_plans', ids=[])):
            with self.assertRaises(ValueError):self.run_with('', [bad])
        identity = json.dumps({'database': 'other', 'role': 'sqbf_oracle_ro', 'read_only': 'on'})
        with self.assertRaises(ValueError):self.run_with(identity + '\n{}\n', [dict(table='sampling_plans', ids=[PLAN])])
        self.assertEqual(self.run_with('', [])[0], {})

    def test_all_public_tables_are_hashed_with_the_controller_role_read_only(self):
        calls = []
        def run(args, **kwargs):
            calls.append(kwargs['input'])
            if len(calls) == 1:
                return MagicMock(stdout="SELECT json_build_object('table','a','count',count(*),'hash','h') FROM public.a x;\n", returncode=0)
            return MagicMock(stdout='{"table":"a","count":2,"hash":"h"}\n', returncode=0)
        self.assertEqual(probe.table_hashes(run, 'c', 'ctrl', 'db'), {'a': {'count': 2, 'hash': 'h'}})
        self.assertTrue(all('READ ONLY' in sql and sql.rstrip().endswith('ROLLBACK;') for sql in calls))
        with self.assertRaises(ValueError):
            probe.table_hashes(lambda *a, **k: MagicMock(stdout='{"table":"Bad;Name","count":1,"hash":"h"}\n', returncode=0)
                               if 'json_build' not in k['input'] else MagicMock(stdout='x', returncode=0), 'c', 'u', 'd')


if __name__ == '__main__':
    unittest.main()

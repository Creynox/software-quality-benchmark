import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch
from uuid import UUID

from sqbf.suites import canonical_hash
from test_suite_fixture import owned_fixture

module = importlib.import_module('projects.ble-elva.tools.fixture_clone')

PRODUCT = str(UUID(int=106))
OTHER_TABLES = ('samples', 'lims_sample', 'ble_reports', 'sqbf_measurement_inputs_v1', 'sqbf_allocation_inputs_v1')
BASE = {name: {'count': 0, 'hash': 'e' * 32} for name in OTHER_TABLES}
BASE.update(workspace_products={'count': 10, 'hash': 'a' * 32}, norm_versions={'count': 16, 'hash': 'b' * 32})
MODULES_BEFORE = {'count': 0, 'hash': 'm0'}
MODULES_AFTER = {'count': 51, 'hash': 'm1'}
ROW = {'id': PRODUCT, 'name': 'Synthetic product six', 'is_active': False, 'use_area': 'Asphalt'}


def source(runtime_root):
    f = owned_fixture()
    f['database'].update(bootstrap_user='ble_benchmark', oracle_role='sqbf_oracle_ro', image='postgres:16')
    f['personas'] = {k: {'username': 'u-' + k, 'storage_state': 'old-' + k, 'credential_file': 'cred-' + k, 'gates_verified': True}
                     for k in ('laboratory_lead', 'laboratory_staff', 'wpk_lead', 'plant_lead')}
    f['identity_scope_check'] = {'executable': 'BLE.Web.exe', 'assembly': 'BLE.Web.dll'}
    f['active_list_expected_products'] = ['Betonsplitt', 'asphalt']
    f['suite_copy'].update(stage='persona_sessions_verified', measured_samples_preseeded=False, prepared_tables=copy.deepcopy(BASE),
                           prepared_state_sha256=canonical_hash(BASE), mapping={'positions': {'P06': PRODUCT}, 'products': {'src-product': PRODUCT}},
                           runtime={'assembly': 'asm', 'sha256': 's' * 64}, application_root=str(runtime_root), web_pid=4242,
                           suite_sha256='f' * 64)
    f['suite_copy']['budget_approval'] = None
    del f['suite_copy']['budget_approval']
    f['read_only_oracle'] = {'expected_counts': {name: value['count'] for name, value in BASE.items()}}
    return f


def replay(docker):
    docker.replayed = True;docker.log.append('replay')
    return {'table': 'lims_product_test_modules', 'rows': 51, 'per_module': {'AGGREGATE_SIEVE_ANALYSIS': 10}}


class FakeDocker:
    """Minimal docker/psql double that records every command in order."""

    def __init__(self, source_container, corrupt_clone=False, exit_code=0, checksum_mismatch=False, row_active=False):
        self.source, self.log, self.updated = source_container, [], False
        self.corrupt_clone, self.exit_code, self.checksum_mismatch = corrupt_clone, exit_code, checksum_mismatch
        self.row_active = row_active
        self.encodings = []
        self.ids, self.status = {}, {}
        self.replayed = False

    def __call__(self, args, input=None, capture_output=True, text=True, timeout=None, encoding=None, errors=None):
        self.encodings.append((args[0], encoding, errors))
        self.log.append('taskkill' if args[0] == 'taskkill' else ' '.join(args[:3]))
        ok = lambda out='': CompletedProcess(args, 0, stdout=out)
        if args[0] == 'taskkill' or args[:3] == ['docker', 'volume', 'create']:
            return ok()
        if args[:2] == ['docker', 'stop']:
            return ok()
        if args[:2] == ['docker', 'inspect']:
            return ok(json.dumps([{'Id': self.ids.get(args[2], 'a' * 64), 'Name': '/' + args[2],
                                   'State': {'Status': self.status.get(args[2], 'exited'), 'ExitCode': self.exit_code}}]))
        if args[:3] == ['docker', 'run', '--rm']:
            return ok('1' * 64 + '  -\n' + ('2' if self.checksum_mismatch else '1') * 64 + '  -\n')
        if args[:3] == ['docker', 'run', '-d']:
            return ok('c' * 64 + '\n')
        if 'pg_isready' in args:
            return ok()
        container = args[args.index('-i') + 1]
        if 'FROM pg_tables' in input:
            return ok('SELECT 1;\n')
        if 'ALTER DATABASE' in input:
            self.log.append('rename')
            return ok()
        if 'to_jsonb(p)' in input:
            row = dict(ROW, is_active=True) if self.updated else dict(ROW, is_active=self.row_active)
            return ok(json.dumps(row) + '\n')
        if 'UPDATE public.workspace_products' in input:
            self.updated = True;self.log.append('update')
            return ok()
        tables = copy.deepcopy(BASE)
        tables['lims_product_test_modules'] = dict(MODULES_AFTER if self.replayed and container != self.source else MODULES_BEFORE)
        if self.updated and container != self.source:
            tables['workspace_products']['hash'] = 'd' * 32
        if self.corrupt_clone and container != self.source:
            tables['norm_versions']['hash'] = '0' * 32
        return ok('\n'.join(json.dumps({'table': t, 'count': v['count'], 'hash': v['hash']}) for t, v in tables.items()) + '\n')


class PureFunctionTests(unittest.TestCase):
    def test_diff_helpers_and_override_statement(self):
        self.assertEqual(module.changed_tables(BASE, dict(BASE, norm_versions={'count': 16, 'hash': 'x'})), ['norm_versions'])
        with self.assertRaises(module.CloneError):module.changed_tables(BASE, {})
        self.assertEqual(module.column_diff({'a': 1, 'b': 2}, {'a': 1, 'b': 3, 'c': 4}), {'b': {'from': 2, 'to': 3}, 'c': {'from': None, 'to': 4}})
        sql = module.override_sql(PRODUCT)
        self.assertIn("is_active = true WHERE id = '" + PRODUCT + "'::uuid AND is_active = false", sql);self.assertIn('ROW_COUNT', sql)
        self.assertEqual(sql.count('UPDATE'), 1);self.assertNotRegex(sql, r'(?i)\b(delete|insert|drop|truncate)\b')
        for bad in ("x'; DROP TABLE a;--", '', PRODUCT + "'"):
            with self.assertRaises(module.CloneError):module.override_sql(bad)

    def test_new_identity_matches_the_fixture_naming_contract(self):
        identity = module.new_identity({})
        self.assertRegex(identity['container'], r'sqbf-nsn014-[a-f0-9]{12}')
        self.assertEqual((identity['database'], identity['volume']), (identity['container'].replace('-', '_'), identity['container'] + '-data'))
        self.assertNotEqual(identity['container'], module.new_identity({})['container'])

    def test_manifest_changes_only_identity_baseline_override_and_session_state(self):
        with tempfile.TemporaryDirectory() as folder:
            src = source(folder);identity = module.new_identity(src)
            prepared = copy.deepcopy(BASE);prepared['workspace_products'] = {'count': 10, 'hash': 'd' * 32}
            evidence = {'override': {'product_name': 'Asphaltsplitt X'}, 'source_fixture_id': src['fixture_id']}
            new = module.build_manifest(src, identity, 'c' * 64, Path(folder) / 'new-runtime', prepared, evidence)
        self.assertEqual({k for k in set(src) | set(new) if src.get(k) != new.get(k)},
                         {'database', 'fixture_id', 'fixture_version', 'status', 'suite_copy', 'active_list_expected_products',
                          'personas', 'session_preparation'})
        self.assertEqual({k for k in set(src['suite_copy']) | set(new['suite_copy']) if src['suite_copy'].get(k) != new['suite_copy'].get(k)},
                         {'prepared_tables', 'prepared_state_sha256', 'application_root', 'stage', 'web_pid', 'clone'})
        self.assertEqual(new['suite_copy']['prepared_state_sha256'], canonical_hash(prepared))
        self.assertEqual(new['active_list_expected_products'], ['asphalt', 'Asphaltsplitt X', 'Betonsplitt'])
        self.assertTrue(all(a['gates_verified'] is False for a in new['personas'].values()))
        self.assertNotIn('budget_approval', new['suite_copy']);self.assertNotIn('web_pid', new['suite_copy'])
        for key in ('mapping', 'suite_sha256', 'runtime', 'measurement_reference_sha256'):
            self.assertEqual(new['suite_copy'].get(key), src['suite_copy'].get(key))

    def test_web_environment_drops_foreign_credentials_and_connection_overrides(self):
        env = module.web_environment({'PATH': 'p', 'OPENAI_API_KEY': 'k', 'ConnectionStrings__X': 'c', 'DataProtection__Keys': 'd'}, 'Host=h')
        self.assertEqual((env['PATH'], env['ConnectionStrings__DefaultConnection'], env['Ble__DisableStartupSeeding']), ('p', 'Host=h', 'true'))
        self.assertNotIn('OPENAI_API_KEY', env);self.assertNotIn('ConnectionStrings__X', env);self.assertNotIn('DataProtection__Keys', env)


class PreflightTests(unittest.TestCase):
    def check(self, **overrides):
        with tempfile.TemporaryDirectory() as folder:
            f = source(folder)
            args = dict(runtime_fn=lambda *a: {'pid': 4242, 'assembly': 'asm', 'sha256': 's' * 64},
                        snapshot_fn=lambda *a, **k: {'tables': copy.deepcopy(BASE)}, docker_fn=lambda *a: None)
            mutate = overrides.pop('mutate', None)
            if mutate:mutate(f)
            args.update(overrides)
            return module.preflight(f, None, **args)

    def test_unchanged_source_with_the_recorded_web_process_passes(self):
        self.assertEqual(self.check()['pid'], 4242)

    def test_changed_dirty_or_foreign_sources_are_refused(self):
        changed = copy.deepcopy(BASE);changed['workspace_products']['hash'] = 'z'
        dirty = copy.deepcopy(BASE);dirty['samples']['count'] = 1
        cases = [({'snapshot_fn': lambda *a, **k: {'tables': changed}}, 'SOURCE_NOT_IN_PREPARED_STATE'),
                 ({'snapshot_fn': lambda *a, **k: {'tables': dirty}}, 'SOURCE_NOT_IN_PREPARED_STATE'),
                 ({'runtime_fn': lambda *a: {'pid': 1, 'assembly': 'asm', 'sha256': 's' * 64}}, 'WEB_PROCESS_NOT_THE_RECORDED_ONE'),
                 ({'runtime_fn': lambda *a: {'pid': 4242, 'assembly': 'asm', 'sha256': 'other'}}, 'WEB_PROCESS_NOT_THE_RECORDED_ONE'),
                 ({'mutate': lambda f: f['suite_copy'].update(stage='web_started')}, 'SOURCE_STAGE_NOT_ACCEPTED'),
                 ({'mutate': lambda f: f['suite_copy'].update(prepared_state_sha256='0' * 64)}, 'PREPARED_HASH_MISMATCH')]
        for overrides, reason in cases:
            with self.assertRaises(module.CloneError, msg=reason) as caught:self.check(**overrides)
            self.assertEqual(caught.exception.reason, reason)


class CloneFlowTests(unittest.TestCase):
    def run_clone(self, **fake):
        folder = tempfile.mkdtemp()
        runtime = Path(folder) / 'old-runtime';runtime.mkdir()
        src = source(runtime);path = Path(folder) / 'source.json';path.write_text(json.dumps(src), encoding='utf-8')
        docker = FakeDocker(src['database']['container'], **fake)
        process = MagicMock();process.pid = 5151
        state = {'tables': copy.deepcopy(BASE)}
        def snap(fixture, **kwargs):
            tables = copy.deepcopy(BASE)
            if fixture['database']['container'] != src['database']['container'] and docker.updated:
                tables['workspace_products'] = {'count': 10, 'hash': 'd' * 32}
            if 'lims_product_test_modules' in fixture['read_only_oracle']['expected_counts']:
                tables['lims_product_test_modules'] = dict(MODULES_AFTER)
            return {'tables': tables}
        runtime_info = {'pid': 4242, 'assembly': 'asm', 'sha256': 's' * 64}
        def runtime_fn(url, root, config, **kwargs):
            return dict(runtime_info, pid=5151 if Path(root).parent.name == 'clone-out' else 4242)
        output = Path(folder) / 'clone-out'
        with patch.object(module, 'snapshot', side_effect=snap), patch.object(module, 'verify_docker_identity'), \
             patch.object(module, 'verify_runtime', side_effect=runtime_fn), \
             patch.object(module, 'load_credentials', return_value={'username': 'u', 'password': 'p'}), \
             patch.object(module, 'check_private_directory'), patch.object(module.shutil, 'copytree', side_effect=lambda a, b, **k: Path(b).mkdir()), \
             patch.object(module.module_replay, 'replay', side_effect=lambda fixture, run=None: replay(docker)):
            popen = MagicMock(return_value=process)
            try:
                result = module.clone_fixture(path, 'controller.dpapi', output, run=docker, popen=popen, sleep=lambda s: None, environ={'PATH': 'p'})
            except module.CloneError as error:
                result = error
        return result, docker, output, src, popen

    def test_phases_run_in_a_safe_order_and_produce_a_verified_manifest(self):
        result, docker, output, src, popen = self.run_clone()
        self.assertIsInstance(result, Path, result)
        order = [entry for entry in docker.log if entry in ('taskkill', 'docker stop -t', 'docker volume create', 'docker run --rm', 'docker run -d', 'rename', 'update', 'replay')]
        self.assertEqual(order, ['taskkill', 'docker stop -t', 'docker volume create', 'docker run --rm', 'docker run -d', 'rename', 'update', 'replay'])
        manifest = json.loads(result.read_text(encoding='utf-8'))
        self.assertEqual((manifest['suite_copy']['web_pid'], manifest['database']['container_id']), (5151, 'c' * 64))
        self.assertNotEqual(manifest['database']['container'], src['database']['container'])
        override = manifest['suite_copy']['clone']['override']
        self.assertEqual((override['changed_tables'], override['changed_columns'], override['other_tables_identical']),
                         (['workspace_products'], ['is_active'], True))
        self.assertEqual(manifest['suite_copy']['prepared_tables']['workspace_products']['hash'], 'd' * 32)
        self.assertEqual({t for t in BASE if manifest['suite_copy']['prepared_tables'][t] != BASE[t]}, {'workspace_products'})
        self.assertEqual(manifest['suite_copy']['prepared_state_sha256'], canonical_hash(manifest['suite_copy']['prepared_tables']))
        phases = [p['phase'] for p in json.loads((output / 'clone-state.json').read_text(encoding='utf-8'))['phases']]
        self.assertEqual(phases, ['source_hashed', 'source_stopped', 'volume_cloned', 'container_started',
                                  'clone_verified_identical', 'override_applied', 'modules_replayed', 'web_started'])
        self.assertEqual(manifest['suite_copy']['clone']['all_changed_tables'], ['lims_product_test_modules', 'workspace_products'])
        self.assertEqual(manifest['read_only_oracle']['expected_counts']['lims_product_test_modules'], 51)
        self.assertEqual(manifest['suite_copy']['prepared_tables']['lims_product_test_modules'], MODULES_AFTER)
        self.assertEqual(manifest['suite_copy']['clone']['module_replay']['rows'], 51)
        self.assertEqual(popen.call_args.kwargs['env']['ConnectionStrings__DefaultConnection'].count('Database=' + manifest['database']['name']), 1)
        self.assertFalse(any('workspace_products' in str(c) and 'DELETE' in str(c) for c in docker.log))
        self.assertTrue(all(enc == 'utf-8' for _, enc, _ in docker.encodings))
        self.assertEqual({err for tool, _, err in docker.encodings if tool == 'taskkill'}, {'replace'})
        self.assertEqual({err for tool, _, err in docker.encodings if tool == 'docker'} - {'replace'}, {'strict'})

    def test_a_clone_that_differs_from_the_source_is_never_modified(self):
        result, docker, _, _, _ = self.run_clone(corrupt_clone=True)
        self.assertIsInstance(result, module.CloneError);self.assertEqual(result.phase, 'verify')
        self.assertIn('norm_versions', result.reason);self.assertNotIn('update', docker.log)

    def test_unclean_source_stop_or_volume_checksum_mismatch_stop_before_any_new_container(self):
        result, docker, _, _, _ = self.run_clone(exit_code=137)
        self.assertEqual((result.phase, result.reason), ('stop_source', 'NOT_CLEANLY_STOPPED'));self.assertNotIn('docker volume create', docker.log)
        result, docker, _, _, _ = self.run_clone(checksum_mismatch=True)
        self.assertEqual((result.phase, result.reason), ('volume', 'COPY_CHECKSUM_MISMATCH'));self.assertNotIn('docker run -d', docker.log)

    def test_an_already_active_product_stops_the_override(self):
        result, docker, _, _, _ = self.run_clone(row_active=True)
        self.assertEqual((result.phase, result.reason), ('override', 'PRODUCT_NOT_INACTIVE'));self.assertNotIn('update', docker.log)


class CloneCommandTests(unittest.TestCase):
    def test_default_is_a_read_only_preflight_and_only_execute_clones(self):
        from sqbf.cli import main
        with tempfile.TemporaryDirectory() as folder:
            src = source(Path(folder) / 'rt');path = Path(folder) / 'source.json';path.write_text(json.dumps(src), encoding='utf-8')
            args = ['suite-fixture-clone', '--source-fixture', str(path), '--controller-credentials', 'c', '--output-dir', str(Path(folder) / 'out')]
            with patch.object(module, 'preflight', return_value={'pid': 4242}) as preflight, patch.object(module, 'clone_fixture') as clone:
                self.assertEqual(main(args), 0)
                clone.assert_not_called();preflight.assert_called_once()
                clone.return_value = Path('manifest.json')
                self.assertEqual(main(args + ['--execute']), 0);clone.assert_called_once()
            with patch.object(module, 'clone_fixture', side_effect=module.CloneError('volume', 'COPY_CHECKSUM_MISMATCH')):
                self.assertEqual(main(args + ['--execute']), 2)


class StoppedSourceCloneTests(unittest.TestCase):
    TREE = '1' * 64

    def run_stopped(self, *, expected=TREE, occupant_pid=7777, source_status='exited', checksum_mismatch=False, with_occupant=True):
        folder = tempfile.mkdtemp()
        runtime = Path(folder) / 'old-runtime';runtime.mkdir()
        src = source(runtime);src['database'].update(container_id='a' * 64)
        src_path = Path(folder) / 'source.json';src_path.write_text(json.dumps(src), encoding='utf-8')
        occ = source(Path(folder) / 'occ-runtime');occ['database'].update(container='sqbf-nsn014-fedcba987654', name='sqbf_nsn014_fedcba987654',
                                                                         volume='sqbf-nsn014-fedcba987654-data', container_id='b' * 64)
        occ['suite_copy']['web_pid'] = 7777;occ['fixture_id'] = 'occupant-fixture'
        occ_path = Path(folder) / 'occupant.json';occ_path.write_text(json.dumps(occ), encoding='utf-8')
        docker = FakeDocker(src['database']['container'], checksum_mismatch=checksum_mismatch)
        docker.ids = {src['database']['container']: 'a' * 64, occ['database']['container']: 'b' * 64}
        docker.status = {src['database']['container']: source_status}
        process = MagicMock();process.pid = 5151
        def snap(fixture, **kwargs):
            tables = copy.deepcopy(BASE)
            if fixture['database']['container'] != src['database']['container'] and docker.updated:
                tables['workspace_products'] = {'count': 10, 'hash': 'd' * 32}
            if 'lims_product_test_modules' in fixture['read_only_oracle']['expected_counts']:
                tables['lims_product_test_modules'] = dict(MODULES_AFTER)
            return {'tables': tables}
        def runtime_fn(url, root, config, **kwargs):
            return {'pid': 5151 if Path(root).parent.name == 'out' else occupant_pid, 'assembly': 'asm', 'sha256': 's' * 64}
        output = Path(folder) / 'out'
        with patch.object(module, 'snapshot', side_effect=snap), patch.object(module, 'verify_docker_identity'), \
             patch.object(module, 'verify_runtime', side_effect=runtime_fn), \
             patch.object(module, 'load_credentials', return_value={'username': 'u', 'password': 'p'}), \
             patch.object(module, 'check_private_directory'), patch.object(module.shutil, 'copytree', side_effect=lambda a, b, **k: Path(b).mkdir()), \
             patch.object(module.module_replay, 'replay', side_effect=lambda fixture, run=None: replay(docker)):
            try:
                result = module.clone_fixture(src_path, 'c.dpapi', output, run=docker, popen=MagicMock(return_value=process), sleep=lambda s: None,
                                              environ={'PATH': 'p'}, source_stopped=True, expected_tree_sha256=expected,
                                              occupant_path=occ_path if with_occupant else None, purpose='scratch')
            except module.CloneError as error:
                result = error
        return result, docker, output

    def test_stopped_source_is_copied_verified_and_only_then_is_the_occupant_stopped(self):
        result, docker, output = self.run_stopped()
        self.assertIsInstance(result, Path, result)
        order = [e for e in docker.log if e in ('docker volume create', 'docker run --rm', 'taskkill', 'docker stop -t', 'docker run -d', 'rename', 'update')]
        self.assertEqual(order, ['docker volume create', 'docker run --rm', 'taskkill', 'docker stop -t', 'docker run -d', 'rename', 'update'])
        phases = [p['phase'] for p in json.loads((output / 'clone-state.json').read_text(encoding='utf-8'))['phases']]
        self.assertEqual(phases, ['volume_cloned', 'occupant_stopped', 'container_started', 'clone_verified_identical', 'override_applied',
                                  'modules_replayed', 'web_started'])
        manifest = json.loads(result.read_text(encoding='utf-8'));evidence = manifest['suite_copy']['clone']
        self.assertEqual((evidence['source_started_for_clone'], evidence['occupant_stopped'], evidence['purpose']), (False, 'occupant-fixture', 'scratch'))
        self.assertEqual(evidence['override']['changed_tables'], ['workspace_products'])

    def test_a_changed_source_volume_stops_before_anything_running_is_touched(self):
        result, docker, _ = self.run_stopped(expected='9' * 64)
        self.assertEqual((result.phase, result.reason), ('volume', 'SOURCE_VOLUME_CHANGED_SINCE_IT_WAS_STOPPED'))
        self.assertNotIn('taskkill', docker.log);self.assertNotIn('docker run -d', docker.log)

    def test_a_running_source_or_a_foreign_occupant_is_refused(self):
        result, docker, _ = self.run_stopped(source_status='running')
        self.assertEqual((result.phase, result.reason), ('preflight', 'SOURCE_NOT_A_CLEANLY_STOPPED_CONTAINER'));self.assertNotIn('docker volume create', docker.log)
        result, docker, _ = self.run_stopped(occupant_pid=1)
        self.assertEqual((result.phase, result.reason), ('stop_occupant', 'WEB_PROCESS_NOT_THE_RECORDED_ONE'))
        self.assertNotIn('taskkill', docker.log);self.assertNotIn('docker run -d', docker.log)

    def test_plan_only_preflight_for_a_stopped_source_never_starts_anything(self):
        folder = tempfile.mkdtemp();src = source(Path(folder) / 'rt');src['database'].update(container_id='a' * 64)
        path = Path(folder) / 's.json';path.write_text(json.dumps(src), encoding='utf-8')
        docker = FakeDocker(src['database']['container']);docker.ids = {src['database']['container']: 'a' * 64}
        report = module.plan_clone(path, run=docker, source_stopped=True)
        self.assertEqual((report['status'], report['source_state'], report['database_writes']), ('CLONE_PREFLIGHT_PASSED', 'stopped, never started', 0))
        self.assertEqual(docker.log, ['docker inspect ' + src['database']['container']])


class SessionSeedTests(unittest.TestCase):
    def test_new_copy_points_at_the_newest_session_files_of_the_occupant(self):
        with tempfile.TemporaryDirectory() as folder:
            src = source(folder);identity = module.new_identity(src)
            seed = {name: 'newest-' + name for name in src['personas']}
            new = module.build_manifest(src, identity, 'c' * 64, Path(folder) / 'rt', copy.deepcopy(BASE),
                                        {'override': {'product_name': 'X'}, 'source_fixture_id': 'f'}, session_seed=seed)
            plain = module.build_manifest(src, identity, 'c' * 64, Path(folder) / 'rt', copy.deepcopy(BASE),
                                          {'override': {'product_name': 'X'}, 'source_fixture_id': 'f'})
        self.assertTrue(all(new['personas'][n]['storage_state'] == 'newest-' + n for n in src['personas']))
        self.assertTrue(all(plain['personas'][n]['storage_state'] == src['personas'][n]['storage_state'] for n in src['personas']))

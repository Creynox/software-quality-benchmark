import hashlib
import importlib
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from sqbf.cli import main

module = importlib.import_module('projects.ble-elva.tools.pipeline')
SUITE = 'projects/ble-elva/suites/enzberg-nsn014-v0.4.1.json'


class Done:
    def __init__(self, stdout='', returncode=0):
        self.stdout, self.returncode = stdout, returncode


def fake_run(containers='', netstat='', docker_ok=True):
    def run(args, **kwargs):
        if args[:2] == ['docker', 'info']:
            return Done('28.5', 0 if docker_ok else 1)
        if args[:2] == ['docker', 'ps']:
            return Done(containers)
        if args[0] == 'netstat':
            return Done(netstat)
        raise AssertionError(args)
    return run


class Machine:
    """A temporary layout of fixture folders, dossiers, runs and probes."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        self.config = {'suite': SUITE, 'dataset': 'd.json', 'projection': 'p.json', 'allocations': 'a.json', 'golden_source': 'g.json',
                       'golden_tree_sha256': 'f' * 64, 'controller_credentials': 'c.json', 'fixtures_root': str(self.root),
                       'dossiers_root': str(self.root / 'dossiers'), 'runs_root': str(self.root / 'runs'), 'probes_root': str(self.root / 'probes'),
                       'executor_model': 'gpt-6-luna', 'reviewer_model': 'gpt-6.1-sol', 'rehearsal_model': 'claude-haiku-5-5'}

    def fixture(self, name, *, container, web_pid, mtime=None, consumed=False):
        folder = self.root / ('sqbf-nsn014-' + name)
        folder.mkdir()
        personas = {}
        for persona in module.SESSION_PERSONAS:
            state = folder / f'{persona}-session.json'
            state.write_text(json.dumps({'cookies': [], 'persona': persona, 'name': name}), encoding='utf-8')
            if mtime:
                os.utime(state, (mtime, mtime))
            personas[persona] = {'storage_state': str(state), 'username': persona}
        manifest = {'fixture_id': name, 'database': {'container': container}, 'personas': personas,
                    'suite_copy': {'web_pid': web_pid, 'application_root': str(folder / 'runtime')}}
        path = folder / 'fixture-clone.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        if consumed:
            (folder / 'benchmark-consumed.json').write_text('{}', encoding='utf-8')
        return path


NETSTAT = """
  Proto  Lokale Adresse         Remoteadresse          Status           PID
  TCP    127.0.0.1:5082         0.0.0.0:0              ABHÖREN          4711
  TCP    127.0.0.1:55434        0.0.0.0:0              ABHÖREN          999
"""


class PipelineTests(unittest.TestCase):
    def test_the_configuration_lives_outside_the_repository_and_must_be_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(module.config_path({'LOCALAPPDATA': tmp}), Path(tmp) / 'SQBF' / 'nsn014-pipeline.json')
            with self.assertRaises(module.PipelineError) as caught:
                module.load_config(Path(tmp) / 'missing.json')
            self.assertEqual(caught.exception.code, 'CONFIG_MISSING')
            path = Path(tmp) / 'c.json'
            path.write_text(json.dumps({'suite': SUITE}), encoding='utf-8')
            with self.assertRaises(module.PipelineError) as caught:
                module.load_config(path)
            self.assertEqual(caught.exception.code, 'CONFIG_INCOMPLETE')
        example = json.loads(Path('projects/ble-elva/pipeline.example.json').read_text(encoding='utf-8'))
        self.assertEqual(set(module.CONFIG_KEYS) - set(example), set(), 'the template names every key')
        self.assertNotIn('D:/Temp', json.dumps(example), 'no private paths in the public template')

    def test_the_port_holder_is_the_manifest_whose_container_runs_and_whose_web_listens(self):
        self.assertEqual(module.listening_pid(5082, fake_run(netstat=NETSTAT)), 4711, 'the localised state column is ignored')
        self.assertIsNone(module.listening_pid(5083, fake_run(netstat=NETSTAT)))
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            machine.fixture('old', container='sqbf-nsn014-old', web_pid=1)
            holder = machine.fixture('current', container='sqbf-nsn014-current', web_pid=4711)
            run = fake_run(containers='sqbf-nsn014-current\t127.0.0.1:55434->5432/tcp\nother\t', netstat=NETSTAT)
            state = module.ports_state(machine.config, run)
            self.assertEqual(state['occupant'], str(holder));self.assertFalse(state['free'])
            stray = module.ports_state(machine.config, fake_run(containers='', netstat=NETSTAT))
            self.assertIsNone(stray['occupant'], 'a web process without its container is not a known holder')
            free = module.ports_state(machine.config, fake_run(containers='', netstat=''))
            self.assertTrue(free['free'])

    def test_the_session_seed_is_the_newest_set_not_yet_used_for_a_renewal(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            older = machine.fixture('older', container='x', web_pid=1, mtime=1_000_000)
            newer = machine.fixture('newer', container='y', web_pid=2, mtime=2_000_000)
            self.assertEqual(module.session_seed(machine.config), newer)
            state = Path(json.loads(newer.read_text(encoding='utf-8'))['personas']['plant_lead']['storage_state'])
            key = hashlib.sha256(state.read_bytes()).hexdigest()
            (state.parent / f'login-attempt-plant_lead-{key}.json').write_text('{}', encoding='utf-8')
            self.assertEqual(module.session_seed(machine.config), older, 'a file renewed once is never used as seed again')

    def test_the_dossier_records_every_step_and_names_the_next_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            dossier = module.Dossier(machine.config, 'lauf-09')
            self.assertEqual(dossier.next_step(), 'dry_run_clean')
            dossier.record('dry_run_clean', 'PASSED')
            dossier.record('dry_run_faults', 'FAILED', error='X')
            again = module.Dossier(machine.config, 'lauf-09')
            self.assertEqual(again.next_step(), 'dry_run_faults', 'a failed step stays the next step')
            self.assertEqual([item[0] for item in module.checklist(again)], ['dry_run_clean', 'dry_run_faults', 'fixture', 'probe', 'approval', 'run'])
            again.start('rehearsal')
            with self.assertRaises(module.PipelineError):
                again.start('rehearsal')
            self.assertIn('rehearsal', [item[0] for item in module.checklist(again)])
            for bad in ('', '../x', 'a/b', 'c:d'):
                with self.assertRaises(module.PipelineError):
                    module.Dossier(machine.config, bad)

    def test_a_step_left_running_by_a_dead_process_is_noted_as_aborted_and_may_start_again(self):
        # Dossier lauf-09 (2026-10-21): the process was killed mid-run and left the step RUNNING without a finish.
        self.assertTrue(module.process_alive(os.getpid()))
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            dossier = module.Dossier(machine.config, 'lauf-09')
            dossier.data['steps']['dry_run_clean'] = {'status': 'RUNNING', 'started_at': 't', 'pid': 424242}
            dossier.start('dry_run_clean', alive=lambda pid: False)
            self.assertEqual(dossier.step('dry_run_clean')['pid'], os.getpid())
            self.assertEqual((dossier.data['history'][0]['status'], dossier.data['history'][0]['pid']), ('ABORTED', 424242))
            with self.assertRaises(module.PipelineError) as caught:
                dossier.start('dry_run_clean', alive=lambda pid: True)
            self.assertEqual(caught.exception.code, 'STEP_ALREADY_RUNNING')

    def test_a_stray_own_container_on_55434_without_its_web_is_stopped_before_the_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            stopped, seen = [], {}

            def run(args, **kwargs):
                if args[:2] == ['docker', 'stop']:
                    stopped.append(args[-1])
                    return Done('')
                return fake_run(containers='sqbf-nsn014-left\t127.0.0.1:55434->5432/tcp\nother-db\t127.0.0.1:5433->5432/tcp', netstat='')(args, **kwargs)

            def clone(source, credentials, output, **kwargs):
                seen.update(kwargs)
                Path(output).mkdir(parents=True)
                return Path(output) / 'fixture-clone.json'
            dossier = module.Dossier(machine.config, 'lauf-09')
            module.clone_with_sessions(machine.config, dossier, 'scratch-clean', 'scratch', clone=clone,
                                       sessions=lambda *a: {'status': 'SESSIONS_VERIFIED'}, run=run)
            self.assertEqual(stopped, ['sqbf-nsn014-left'], 'only our own container, never another database')
            self.assertIsNone(seen['occupant_path'])
            self.assertEqual(dossier.data['history'][0]['event'], 'stray_container_stopped')

    def test_prepare_runs_the_dry_runs_and_the_rehearsal_in_order_keeps_passed_steps_and_stops_at_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            dossier = module.Dossier(machine.config, 'lauf-09')
            calls = []

            def step(config, dossier_, **options):
                key = 'rehearsal' if options.get('rehearsal_model') else 'dry_run_faults' if options.get('faults') else 'dry_run_clean'
                calls.append(key)
                return dossier_.record(key, 'FAILED' if key == 'dry_run_faults' and len(calls) == 2 else module.DONE[key])
            first = module.prepare(machine.config, dossier, rehearse=True, step=step)
            self.assertEqual(calls, ['dry_run_clean', 'dry_run_faults'], 'a failed step ends the preparation')
            self.assertEqual(first['dry_run_faults']['status'], 'FAILED')
            second = module.prepare(machine.config, dossier, rehearse=True, step=step)
            self.assertEqual(calls, ['dry_run_clean', 'dry_run_faults', 'dry_run_faults', 'rehearsal'], 'a passed step is not repeated')
            self.assertEqual({k: v['status'] for k, v in second.items()}, {'dry_run_clean': 'PASSED', 'dry_run_faults': 'PASSED', 'rehearsal': 'RECORDED'})

    def test_a_clone_stops_the_recorded_holder_and_seeds_the_newest_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            holder = machine.fixture('current', container='sqbf-nsn014-current', web_pid=4711, mtime=2_000_000)
            calls = {}

            def clone(source, credentials, output, **kwargs):
                calls.update(kwargs, source=source, output=output)
                Path(output).mkdir(parents=True)
                path = Path(output) / 'fixture-clone.json'
                path.write_text('{}', encoding='utf-8')
                return path

            def sessions(fixture, output, report):
                Path(output).write_text('{}', encoding='utf-8')
                return {'status': 'SESSIONS_VERIFIED'}
            run = fake_run(containers='sqbf-nsn014-current\t127.0.0.1:55434->5432/tcp', netstat=NETSTAT)
            dossier = module.Dossier(machine.config, 'lauf-09')
            prepared = module.clone_with_sessions(machine.config, dossier, 'scratch-clean', 'scratch', clone=clone, sessions=sessions, run=run)
            self.assertEqual(prepared, dossier.path / 'scratch-clean' / 'fixture-sessions.json')
            self.assertEqual((calls['occupant_path'], calls['session_seed_path'], calls['purpose']), (str(holder), str(holder), 'scratch'))
            self.assertTrue(calls['source_stopped']);self.assertEqual(calls['expected_tree_sha256'], 'f' * 64)
            with self.assertRaises(module.PipelineError) as caught:
                module.clone_with_sessions(machine.config, dossier, 'x', 'scratch', clone=clone, sessions=sessions, run=fake_run(netstat=NETSTAT))
            self.assertEqual(caught.exception.code, 'PORT_5082_HELD_BY_UNKNOWN_PROCESS')
            with self.assertRaises(module.PipelineError) as caught:
                module.clone_with_sessions(machine.config, dossier, 'y', 'scratch', clone=clone, sessions=sessions, run=fake_run(docker_ok=False))
            self.assertEqual(caught.exception.code, 'DOCKER_NOT_READY')

    def test_dry_runs_rehearsal_and_fixture_record_their_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            dossier = module.Dossier(machine.config, 'lauf-09')
            prepared = Path(tmp) / 'prepared.json'
            with patch.object(module, 'clone_with_sessions', return_value=prepared), patch.object(module, '_inputs', return_value=('s', 'd', 'f', 'p', 'a')):
                seen = {}

                def run_dry(*inputs, faults=None, executor=None):
                    seen.update(faults=faults, executor=executor)
                    status = 'REHEARSAL_COMPLETED' if executor else 'DRY_RUN_COMPLETED'
                    return {'status': status, 'points': {'points': 3}, 'harness_stops': [], 'rejected_actions': 0}
                self.assertEqual(module.dry_run(machine.config, dossier, run_dry=run_dry)['status'], 'PASSED')
                self.assertIsNone(seen['faults'])
                self.assertEqual(module.dry_run(machine.config, dossier, faults=True, run_dry=run_dry)['status'], 'PASSED')
                self.assertEqual(seen['faults'], module.DEFAULT_FAULTS)
                entry = module.dry_run(machine.config, dossier, rehearsal_model='claude-haiku-5-5', run_dry=run_dry, executor_factory=lambda model: ('executor', model))
                self.assertEqual(entry['status'], 'RECORDED');self.assertEqual(seen['executor'], ('executor', 'claude-haiku-5-5'))
                broken = module.dry_run(machine.config, dossier, run_dry=lambda *a, **k: {'status': 'DRY_RUN_FOUND_GUARD_OR_HARNESS_GAPS'})
                self.assertEqual(broken['status'], 'FAILED')
                ready = lambda *a, **k: {'status': 'BLOCKED_SUITE_READINESS', 'reason': 'BUDGET_APPROVAL_MISSING', 'other_gates': 'PASSED'}
                self.assertEqual(module.fixture(machine.config, dossier, ready=ready)['status'], 'READY')
                blocked = lambda *a, **k: {'status': 'BLOCKED_SUITE_READINESS', 'reason': 'ACTIVE_RUNTIME_MISMATCH'}
                self.assertEqual(module.fixture(machine.config, dossier, ready=blocked)['readiness_reason'], 'ACTIVE_RUNTIME_MISMATCH')
            with patch.object(module, 'clone_with_sessions', side_effect=module.PipelineError('DOCKER_NOT_READY', 'start')):
                failed = module.dry_run(machine.config, dossier)
            self.assertEqual((failed['status'], failed['error']), ('FAILED', 'DOCKER_NOT_READY'))

    def test_the_approval_is_written_only_with_the_po_statement_on_a_ready_fixture_and_a_clean_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            dossier = module.Dossier(machine.config, 'lauf-09')
            prepared = dossier.path / 'fixture' / 'fixture-sessions.json'
            prepared.parent.mkdir(parents=True)
            prepared.write_text(json.dumps({'suite_copy': {'application_root': str(prepared.parent / 'runtime')}}), encoding='utf-8')
            clean = {'commit': 'a' * 40, 'clean': True}
            with self.assertRaises(module.PipelineError) as caught:
                module.approve(machine.config, dossier, 'ja', source=clean)
            self.assertEqual(caught.exception.code, 'STATEMENT_REQUIRED')
            with self.assertRaises(module.PipelineError) as caught:
                module.approve(machine.config, dossier, 'ja starte mit lauf 9', source=clean)
            self.assertEqual(caught.exception.code, 'FIXTURE_NOT_READY')
            dossier.record('fixture', 'READY', fixture=str(prepared))
            with self.assertRaises(module.PipelineError) as caught:
                module.approve(machine.config, dossier, 'ja starte mit lauf 9', source={'commit': 'a' * 40, 'clean': False})
            self.assertEqual(caught.exception.code, 'SOURCE_NOT_CLEAN')
            entry = module.approve(machine.config, dossier, 'ja starte mit lauf 9', source=clean, approved_at='2026-10-21')
            approval = json.loads(Path(entry['fixture']).read_text(encoding='utf-8'))['suite_copy']['budget_approval']
            suite = json.loads(Path(SUITE).read_text(encoding='utf-8'))
            self.assertEqual((approval['approved_by'], approval['runs_approved'], approval['approved_commit']), ('PO', 1, 'a' * 40))
            self.assertEqual((approval['hard_model_calls'], approval['profile']), (suite['resource_policy']['hard_model_calls'], suite['resource_policy']['profile']))
            self.assertEqual(approval['statement'], 'ja starte mit lauf 9')
            with self.assertRaises(module.PipelineError) as caught:
                module.approve(machine.config, dossier, 'ja starte mit lauf 9', source=clean)
            self.assertEqual(caught.exception.code, 'APPROVAL_FILE_EXISTS')

    def test_the_live_run_needs_every_earlier_step_and_runs_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            dossier = module.Dossier(machine.config, 'lauf-09')
            with self.assertRaises(module.PipelineError) as caught:
                module.run(machine.config, dossier)
            self.assertEqual(caught.exception.code, 'STEP_MISSING')
            for key in ('dry_run_clean', 'dry_run_faults', 'fixture', 'probe', 'approval'):
                dossier.record(key, module.DONE[key], fixture='f.json', path='probe.json')
            with patch.object(module, '_inputs', return_value=('s', 'd', 'f', 'p', 'a')):
                entry = module.run(machine.config, dossier, ready=lambda *a, **k: {'status': 'BLOCKED_SUITE_READINESS', 'reason': 'FIXTURE_ALREADY_CLAIMED'})
                self.assertEqual((entry['status'], entry['reasons']), ('NOT_READY', ['FIXTURE_ALREADY_CLAIMED']))
                calls = []

                def run_suite(*inputs, **kwargs):
                    calls.append(kwargs)
                    return {'status': 'SUITE_RUN_RECORDED', 'run_id': 'r9', 'path': None, 'verdict': 'PARTIAL GO', 'technical_status': 'COMPLETED'}
                entry = module.run(machine.config, dossier, ready=lambda *a, **k: {'status': 'READY_FOR_SINGLE_SUITE_RUN'}, run_suite=run_suite)
                self.assertEqual((entry['status'], entry['run_id']), ('RECORDED', 'r9'))
                self.assertEqual(calls[0]['provider_probe'], 'probe.json')
                with self.assertRaises(module.PipelineError) as caught:
                    module.run(machine.config, dossier, ready=lambda *a, **k: {'status': 'READY_FOR_SINGLE_SUITE_RUN'}, run_suite=run_suite)
                self.assertEqual(caught.exception.code, 'RUN_ALREADY_STARTED')
                self.assertEqual(len(calls), 1)
            self.assertIsNone(module.Dossier(machine.config, 'lauf-09').next_step())

    def test_the_probe_is_valid_only_when_passed_fresh_and_from_this_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            Path(machine.config['probes_root']).mkdir()
            clock = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
            path = Path(machine.config['probes_root']) / 'provider-probe-1.json'
            path.write_text(json.dumps({'verdict': 'PROBE_PASS', 'created_at': (clock - timedelta(hours=2)).isoformat(), 'sqbf_commit': 'abc'}), encoding='utf-8')
            self.assertTrue(module.probe_state(machine.config, 'abc', clock)['valid'])
            self.assertFalse(module.probe_state(machine.config, 'def', clock)['valid'])
            self.assertFalse(module.probe_state(machine.config, 'abc', clock + timedelta(hours=11))['valid'])
            self.assertIsNone(module.probe_state(dict(machine.config, probes_root=str(Path(tmp) / 'none')), 'abc', clock))

    def test_status_text_and_cli_guidance(self):
        facts = {'docker': True, 'ports': {'occupant': 'x.json', 'free': False, 'web_pid': 1}, 'source': {'commit': 'abc1234', 'clean': True},
                 'probe': None, 'session_seed': 'x.json',
                 'dossier': {'name': 'lauf-09', 'path': 'p', 'checklist': [('dry_run_clean', 'Trockenlauf sauber', 'PASSED', True),
                                                                            ('dry_run_faults', 'Trockenlauf mit Fehlerinjektion', 'OFFEN', False)]},
                 'next': {'step': 'dry_run_faults', 'label': 'Trockenlauf mit Fehlerinjektion', 'command': 'python -m sqbf.cli nsn014 dry-run-faults --name lauf-09'}}
        text = module.render_status(facts)
        self.assertIn('[x] Trockenlauf sauber: PASSED', text);self.assertIn('[ ] Trockenlauf mit Fehlerinjektion: OFFEN', text)
        self.assertIn('Nächster Schritt: Trockenlauf mit Fehlerinjektion → python -m sqbf.cli nsn014 dry-run-faults --name lauf-09', text)
        with tempfile.TemporaryDirectory() as tmp:
            machine = Machine(tmp)
            config = Path(tmp) / 'config.json'
            config.write_text(json.dumps(machine.config), encoding='utf-8')
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(['nsn014', 'fixture', '--config', str(config)]), 2)
            self.assertIn('BLOCKED_NSN014: NAME_REQUIRED', out.getvalue())
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(['nsn014', 'status', '--config', str(Path(tmp) / 'missing.json')]), 2)
            self.assertIn('CONFIG_MISSING', out.getvalue())


if __name__ == '__main__':
    unittest.main()

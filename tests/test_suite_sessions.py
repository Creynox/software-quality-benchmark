import copy
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_suite_fixture import owned_fixture

module = importlib.import_module('projects.ble-elva.tools.suite_sessions')


class SuiteSessionsTests(unittest.TestCase):
    def fixture(self, directory):
        value = owned_fixture()
        value['suite_copy'].update(application_root='owned-root', runtime={'assembly': 'build', 'sha256': 'hash'})
        value['identity_scope_check'] = {}; value['identity_verifier'] = 'verifier'
        value['active_list_expected_products'] = ['synthetic']
        value['personas'] = {}
        for key in ('laboratory_lead','laboratory_staff','wpk_lead','plant_lead'):
            p = Path(directory) / (key + '.json'); p.write_text(key)
            names = {'laboratory_lead': 'sqbf-laborleitung', 'laboratory_staff': 'sqbf-labormitarbeiter',
                     'wpk_lead': 'sqbf-wpk', 'plant_lead': 'sqbf-werkleitung'}
            credential=Path(directory)/('credentials-'+key);credential.touch()
            value['personas'][key] = {'storage_state': str(p), 'credential_file': str(credential), 'username': names[key]}
        return value

    def invoke(self, directory, fixture, sessions, *, login_error=False, scope='PERSONA_SCOPE_VERIFIED'):
        with patch.object(module,'check_private_directory'), patch.object(module,'verify_docker_identity'), \
             patch.object(module,'verify_runtime',return_value={'assembly':'build','sha256':'hash'}), \
             patch.object(module,'snapshot',return_value={'fixed':'state'}), \
             patch.object(module,'check_session',side_effect=sessions), \
             patch.object(module,'save_session',side_effect=RuntimeError('secret text') if login_error else None) as login, \
             patch.object(module,'check_persona',return_value={'status':scope}):
            result, output = module.prepare_sessions(fixture, directory)
        return result, output, login

    def test_valid_sessions_never_login(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory); original = copy.deepcopy(fixture)
            result, output, login = self.invoke(directory, fixture, [{'status':'SESSION_RESTORED'}] * 4)
        self.assertEqual(result['status'], 'SESSIONS_VERIFIED'); login.assert_not_called()
        self.assertEqual(fixture, original); self.assertEqual(result['model_calls'], 0)

    def test_one_login_and_independent_check_for_expired_actor(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory)
            sessions=[{'status':'BLOCKED_SESSION','reason':'UNEXPECTED_PAGE','checks':[{'path':'/login'}]}]
            sessions += [{'status':'SESSION_RESTORED'}] * 4
            result, output, login = self.invoke(directory, fixture, sessions)
            self.assertTrue(Path(fixture['personas']['laboratory_lead']['storage_state']).is_file())
        self.assertEqual(result['status'], 'SESSIONS_VERIFIED'); login.assert_called_once()
        self.assertEqual(result['login_attempts'], 1)
        self.assertNotEqual(output['personas']['laboratory_lead']['storage_state'], fixture['personas']['laboratory_lead']['storage_state'])

    def test_failed_login_is_durably_not_retried(self):
        stale={'status':'BLOCKED_SESSION','reason':'UNEXPECTED_PAGE','checks':[{'path':'/login'}]}
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory)
            first, _, login = self.invoke(directory, fixture, [stale], login_error=True)
            second, _, repeat = self.invoke(directory, fixture, [stale])
        login.assert_called_once(); repeat.assert_not_called()
        self.assertEqual(first['status'], 'BLOCKED_SESSION'); self.assertEqual(second['status'], 'BLOCKED_SESSION')
        self.assertNotIn('secret text', str(first))

    def test_ui_failure_not_treated_as_expired_session_and_scope_failure_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory)
            result, _, login=self.invoke(directory, fixture, [{'status':'BLOCKED_SESSION','reason':'MISSING_EXPECTED_UI'}])
            login.assert_not_called(); self.assertEqual(result['reason'],'SESSION_FAILURE_NOT_LOGIN_REDIRECT')
            result, _, login=self.invoke(directory, fixture, [{'status':'SESSION_RESTORED'}], scope='BLOCKED_SCOPE_VERIFICATION')
            login.assert_not_called(); self.assertEqual(result['reason'],'IDENTITY_SCOPE_FAILED')

    def test_relative_paths_resolve_from_manifest_not_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); fixture=self.fixture(directory)
            for actor in fixture['personas'].values():
                for key in ('credential_file','storage_state'): actor[key]=Path(actor[key]).name
            source=root/'fixture.json';source.write_text(json.dumps(fixture))
            with patch.object(module,'prepare_sessions',return_value=({'status':'SESSIONS_VERIFIED'},fixture)) as prepare:
                module.write_prepared_sessions(source,root/'new.json',root/'report.json')
            supplied=prepare.call_args.args[0]
            for actor in supplied['personas'].values():
                for key in ('credential_file','storage_state'):
                    self.assertTrue(Path(actor[key]).is_absolute()); self.assertEqual(Path(actor[key]).parent,root)

    def test_missing_credentials_do_not_reserve_or_attempt_login(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=self.fixture(directory); fixture['personas']['laboratory_lead']['credential_file']='nonexistent-private-file'
            stale={'status':'BLOCKED_SESSION','reason':'UNEXPECTED_PAGE','checks':[{'path':'/login'}]}
            result,_,login=self.invoke(directory,fixture,[stale])
            self.assertEqual(result['login_attempts'],0);login.assert_not_called()
            self.assertEqual(list(Path(directory).glob('login-attempt-*')),[])

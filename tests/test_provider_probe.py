import importlib
import json
import struct
import tempfile
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqbf.calibration import ResourceStop
from sqbf.cli import main
from sqbf.providers import ModelResponse

module = importlib.import_module('projects.ble-elva.tools.provider_probe')
support = importlib.import_module('projects.ble-elva.tools.stage_support')
runner = importlib.import_module('projects.ble-elva.tools.regular_runner')

SUITE = 'projects/ble-elva/suites/enzberg-nsn014-v0.4.1.json'
GOOD_ACTION = {'action': 'done', 'x': None, 'y': None, 'text': None, 'key': None, 'amount': None, 'seconds': None, 'reason': 'probe'}
GOOD_REVIEW = {'verdict': 'INCONCLUSIVE', 'reason': 'probe', 'scores': {'findability': 3, 'clarity': None, 'task_progress': 3,
               'error_recovery': None}, 'findings': [{'category': 'UNCLEAR', 'severity': 'info', 'observed': 'probe',
               'expected': 'probe', 'suggestion': 'probe', 'evidence': 'probe'}]}


def suite():
    return json.loads(Path(SUITE).read_text(encoding='utf-8'))


class Failure(RuntimeError):
    def __init__(self, code):
        super().__init__('provider text that must never be stored')
        self.code = code


class SyntheticImageTests(unittest.TestCase):
    def test_png_is_valid_small_and_contains_no_application_content(self):
        png = module.synthetic_png()
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'));self.assertLess(len(png), 50_000)
        width, height = struct.unpack('>II', png[16:24]);self.assertEqual((width, height), (320, 200))
        end = png.index(b'IDAT');length = struct.unpack('>I', png[end - 4:end])[0]
        pixels = zlib.decompress(png[end + 4:end + 4 + length]);self.assertEqual(len(pixels), 200 * (1 + 320 * 3))
        self.assertEqual(png, module.synthetic_png())

    def test_schema_contracts_are_the_suites_own(self):
        hashes = module.schema_hashes()
        self.assertEqual(support.executor_schema()['properties']['key']['enum'], [None, 'ControlOrMeta+A', 'Backspace', 'Delete', 'Tab', 'Escape'])
        self.assertNotEqual(hashes['executor_schema_sha256'], hashes['reviewer_schema_sha256'])


class RunProbeTests(unittest.TestCase):
    def run_probe(self, answers):
        calls = []

        def ask(model, prompt, images, budget, actor):
            calls.append((actor, prompt, images))
            ticket = budget.claim(actor)
            try:
                answer = answers[actor]
                if isinstance(answer, Exception):raise answer
                budget.complete_call(ticket, {'input_tokens': 5, 'output_tokens': 2, 'total_tokens': 7})
                return ModelResponse(answer, {})
            except Exception:
                if budget.requests[ticket]['finished'] is None:budget.complete_call(ticket, None)
                raise
        results, count = module.run_probe('exec', 'rev', ask=ask)
        return results, count, calls

    def test_both_schemas_accepted_is_a_pass_with_exactly_two_requests(self):
        results, count, calls = self.run_probe({'executor': GOOD_ACTION, 'reviewer': GOOD_REVIEW})
        self.assertEqual((count, [c[0] for c in calls]), (2, ['executor', 'reviewer']))
        self.assertEqual(module.probe_verdict(results), 'PROBE_PASS')
        self.assertEqual(results['executor']['usage']['total_tokens'], 7);self.assertEqual(len(calls[0][2]), 1)
        self.assertIn('nsn014-ux-rubric-v1', calls[1][1]);self.assertNotIn('private', (calls[0][1] + calls[1][1]).lower())

    def test_reviewer_failure_is_one_fixed_code_without_retry_and_blocks_the_verdict(self):
        results, count, calls = self.run_probe({'executor': GOOD_ACTION, 'reviewer': Failure('PROVIDER_HTTP_400')})
        self.assertEqual((count, len(calls)), (2, 2))
        self.assertEqual((results['reviewer']['status'], results['reviewer']['error_code']), ('FAILED', 'PROVIDER_HTTP_400'))
        self.assertEqual(module.probe_verdict(results), 'PROBE_FAILED')
        self.assertNotIn('provider text', json.dumps(results))
        results, _, _ = self.run_probe({'executor': RuntimeError('x'), 'reviewer': GOOD_REVIEW})
        self.assertEqual((results['executor']['error_code'], module.probe_verdict(results)), ('PROBE_REQUEST_FAILED', 'PROBE_FAILED'))

    def test_schema_valid_but_content_invalid_answers_fail_the_probe(self):
        bad_review = dict(GOOD_REVIEW, scores=dict(GOOD_REVIEW['scores'], clarity=9))
        results, _, _ = self.run_probe({'executor': dict(GOOD_ACTION, action='click'), 'reviewer': bad_review})
        self.assertEqual((results['executor']['status'], results['reviewer']['status']), ('RESPONSE_INVALID', 'RESPONSE_INVALID'))


class ProbeCommandTests(unittest.TestCase):
    def test_default_is_plan_only_without_oauth_or_model(self):
        with patch.object(module, 'run_probe') as run, patch('sqbf.plan_login.authorize') as oauth:
            report = module.provider_probe(suite(), 'unused', 'gpt-6-luna', 'gpt-6.1-sol')
        run.assert_not_called();oauth.assert_not_called()
        self.assertEqual((report['status'], report['model_calls'], report['requests']), ('PROBE_PLAN_ONLY', 0, 2))
        self.assertEqual(module.provider_probe(suite(), 'x', 'other', 'gpt-6.1-sol')['status'], 'BLOCKED_MODEL_SELECTION')

    def test_execute_records_a_private_result_without_prompts_images_or_tokens(self):
        with tempfile.TemporaryDirectory() as folder, patch('sqbf.plan_login._load_host'), \
             patch('sqbf.plan_login.authorize', return_value=MagicMock()) as oauth, \
             patch('sqbf.plan_login.catalog', return_value=['gpt-6-luna', 'gpt-6.1-sol']), \
             patch('sqbf.providers.ChatGPTPlanModel'), patch.object(module, 'check_private_directory'), \
             patch.object(module, 'create_private_file'), patch.dict('os.environ', {'LOCALAPPDATA': folder}), \
             patch.object(module, 'run_probe', return_value=({'executor': {'status': 'OK', 'error_code': None},
                                                              'reviewer': {'status': 'OK', 'error_code': None}}, 2)):
            report = module.provider_probe(suite(), str(Path(folder) / 'probes'), 'gpt-6-luna', 'gpt-6.1-sol', execute=True)
            stored = json.loads(Path(report['path']).read_text(encoding='utf-8'))
        oauth.assert_called_once()
        self.assertEqual((report['verdict'], stored['model_calls'], stored['kind']), ('PROBE_PASS', 2, module.PROBE_KIND))
        self.assertEqual(len(stored['sqbf_commit']), 40)
        for secret in ('access_token', 'Synthetic provider compatibility probe', 'iVBOR', 'base64', 'Bearer'):
            self.assertNotIn(secret, json.dumps(stored))

    def test_unavailable_model_stops_before_any_request(self):
        with tempfile.TemporaryDirectory() as folder, patch('sqbf.plan_login._load_host'), patch('sqbf.plan_login.authorize'), \
             patch('sqbf.plan_login.catalog', return_value=['gpt-6-luna']), patch.object(module, 'check_private_directory'), \
             patch.dict('os.environ', {'LOCALAPPDATA': folder}), patch.object(module, 'run_probe') as run:
            report = module.provider_probe(suite(), str(Path(folder) / 'p'), 'gpt-6-luna', 'gpt-6.1-sol', execute=True)
        run.assert_not_called();self.assertEqual((report['status'], report['model_calls']), ('BLOCKED_MODEL_UNAVAILABLE', 0))

    def test_cli_without_execute_makes_no_calls_and_with_failed_verdict_exits_nonzero(self):
        self.assertEqual(main(['suite-provider-probe', '--suite', SUITE]), 0)
        with patch.object(runner, 'provider_probe', return_value={'status': 'PROBE_RECORDED', 'verdict': 'PROBE_FAILED'}):
            self.assertEqual(main(['suite-provider-probe', '--suite', SUITE, '--execute']), 2)


class ReadinessProbeTests(unittest.TestCase):
    def record(self, folder, **changes):
        hashes = module.schema_hashes()
        value = {'kind': module.PROBE_KIND, 'executor_model': 'gpt-6-luna', 'reviewer_model': 'gpt-6.1-sol', **hashes,
                 'created_at': datetime.now(timezone.utc).isoformat(), 'verdict': 'PROBE_PASS',
                 'results': {'executor': {'status': 'OK', 'error_code': None}, 'reviewer': {'status': 'OK', 'error_code': None}}}
        value.update(changes)
        path = Path(folder) / 'probe.json';path.write_text(json.dumps(value), encoding='utf-8');return str(path)

    def test_probe_states(self):
        self.assertEqual(module.evaluate_probe(None, 'gpt-6-luna', 'gpt-6.1-sol'), {'status': 'NOT_PROBED', 'ux_layer_assured': False})
        with tempfile.TemporaryDirectory() as folder:
            ok = module.evaluate_probe(self.record(folder), 'gpt-6-luna', 'gpt-6.1-sol')
            self.assertEqual((ok['status'], ok['ux_layer_assured']), ('PROBE_PASSED', True))
            failed = module.evaluate_probe(self.record(folder, verdict='PROBE_FAILED', results={
                'executor': {'status': 'OK', 'error_code': None}, 'reviewer': {'status': 'FAILED', 'error_code': 'PROVIDER_HTTP_400'}}),
                'gpt-6-luna', 'gpt-6.1-sol')
            self.assertEqual((failed['status'], failed['codes']['reviewer'], failed['ux_layer_assured']), ('PROBE_FAILED', 'PROVIDER_HTTP_400', False))
            stale = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
            for changes in ({'created_at': stale}, {'reviewer_schema_sha256': '0' * 64}, {'executor_model': 'other'},
                            {'kind': 'other'}, {'created_at': 'garbage'}, {'created_at': datetime.now().isoformat()}):
                self.assertEqual(module.evaluate_probe(self.record(folder, **changes), 'gpt-6-luna', 'gpt-6.1-sol')['status'],
                                 'PROBE_NOT_CURRENT', changes)
            self.assertEqual(module.evaluate_probe(self.record(folder, verdict='PROBE_PASS', results={
                'executor': {'status': 'OK'}, 'reviewer': {'status': 'RESPONSE_INVALID'}}), 'gpt-6-luna', 'gpt-6.1-sol')['status'],
                'PROBE_FAILED')
            self.assertEqual(module.evaluate_probe(str(Path(folder) / 'missing.json'), 'gpt-6-luna', 'gpt-6.1-sol')['status'], 'PROBE_NOT_CURRENT')

import importlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

module = importlib.import_module('projects.ble-elva.tools.claude_executor')
support = importlib.import_module('projects.ble-elva.tools.stage_support')


class Done:
    def __init__(self, stdout='', returncode=0):
        self.stdout, self.returncode, self.stderr = stdout, returncode, ''


def result_line(**extra):
    base = {'type': 'result', 'subtype': 'success', 'is_error': False, 'api_error_status': None,
            'structured_output': {'action': 'click', 'x': 10, 'y': 20, 'text': None, 'key': None, 'amount': None, 'seconds': None, 'reason': 'open'},
            'usage': {'input_tokens': 4, 'cache_creation_input_tokens': 2000, 'cache_read_input_tokens': 100, 'output_tokens': 50}}
    base.update(extra)
    return json.dumps(base)


class Budget:
    def __init__(self):
        self.claims, self.completed = [], []

    def claim(self, actor):
        self.claims.append(actor)
        return len(self.claims) - 1

    def complete_call(self, ticket, usage):
        self.completed.append((ticket, usage))


class ClaudeExecutorTests(unittest.TestCase):
    def executor(self, stdout='', returncode=0, error=None):
        calls = []

        def run(args, **kwargs):
            calls.append((args, kwargs))
            if error:
                raise error
            return Done(stdout, returncode)
        return module.ClaudeCliExecutor('claude-haiku-5-5', run=run, executable='C:/claude.exe'), calls

    def test_the_model_sees_only_the_task_text_and_the_screenshots_without_tools_or_project_context(self):
        executor, calls = self.executor('{"type":"system"}\n' + result_line())
        data, usage = executor.ask('Task: open Kornform', b'\x89PNG')
        args, kwargs = calls[0]
        self.assertEqual(args[0], 'C:/claude.exe')
        for flag, value in (('--model', 'claude-haiku-5-5'), ('--tools', ''), ('--setting-sources', ''), ('--input-format', 'stream-json')):
            self.assertEqual(args[args.index(flag) + 1], value)
        for flag in ('-p', '--strict-mcp-config', '--no-session-persistence', '--json-schema', '--system-prompt'):
            self.assertIn(flag, args)
        self.assertEqual(json.loads(args[args.index('--json-schema') + 1]), support.executor_schema())
        message = json.loads(kwargs['input'])
        content = message['message']['content']
        self.assertEqual([c['type'] for c in content], ['text', 'image'], 'task text first, then the screenshot, as the benchmark executor gets it')
        self.assertEqual(content[0]['text'], 'Task: open Kornform')
        self.assertTrue(Path(kwargs['cwd']).name.startswith('sqbf-claude-'), 'an empty working directory, never the repository')
        self.assertFalse(Path(kwargs['cwd']).exists(), 'the working directory is removed after the request')
        self.assertEqual(data['action'], 'click')
        self.assertEqual(usage, {'input_tokens': 2104, 'output_tokens': 50, 'total_tokens': 2154})
        self.assertEqual(executor.log[0]['status'], 'OK')

    def test_failures_carry_a_fixed_code_and_never_model_text(self):
        cases = [(self.executor('no json at all'), 'CLAUDE_CLI_NO_RESULT'),
                 (self.executor('', returncode=3), 'CLAUDE_CLI_EXIT_3'),
                 (self.executor(result_line(is_error=True, subtype='error_during_execution', api_error_status=429)), 'CLAUDE_CLI_RATE_LIMITED'),
                 (self.executor(result_line(is_error=True, subtype='error_during_execution', api_error_status=500)), 'CLAUDE_CLI_API_ERROR_500'),
                 (self.executor(result_line(structured_output=None)), 'CLAUDE_CLI_NO_STRUCTURED_OUTPUT'),
                 (self.executor(error=subprocess.TimeoutExpired('claude', 120)), 'CLAUDE_CLI_TIMEOUT'),
                 (self.executor(error=FileNotFoundError()), 'CLAUDE_CLI_NOT_STARTED')]
        for (executor, _), code in cases:
            with self.assertRaises(module.ClaudeCliFailed) as caught:
                executor.ask('task', b'png')
            self.assertEqual(caught.exception.code, code)
            self.assertEqual(executor.log[-1]['error_code'], code)
        executor, _ = self.executor(result_line())
        for images in ([], [b'1', b'2', b'3', b'4'], [b'x' * (module.MAX_IMAGE_BYTES + 1)], ['text']):
            with self.assertRaises(module.ClaudeCliFailed):
                executor.ask('task', images)
        self.assertEqual(executor.summary()['failed_by_code'], {})

    def test_requests_are_accounted_in_the_suite_budget_and_the_reviewer_stays_neutral(self):
        executor, calls = self.executor(result_line())
        budget = Budget()
        response = executor(object(), 'task', [b'png'], budget, 'executor')
        self.assertEqual(response.data['action'], 'click')
        self.assertEqual(budget.claims, ['executor'])
        self.assertEqual(budget.completed, [(0, {'input_tokens': 2104, 'output_tokens': 50, 'total_tokens': 2154})])
        review = executor(object(), 'review', [b'png'], budget, 'reviewer')
        self.assertEqual(review.data['verdict'], 'INCONCLUSIVE')
        self.assertEqual(len(calls), 1, 'no model request for the reviewer')
        failing, _ = self.executor('nothing')
        with self.assertRaises(module.ClaudeCliFailed):
            failing(object(), 'task', b'png', budget, 'executor')
        self.assertEqual(budget.completed[-1], (1, None), 'a failed request is completed in the accounting too')
        self.assertEqual(executor.summary()['requests'], 1)

    def test_a_failed_request_ends_only_the_task_with_its_code(self):
        class Evidence:
            def __init__(self):
                self.events = []

            def event(self, kind, **data):
                self.events.append((kind, data))
        failing, _ = self.executor(result_line(is_error=True, subtype='error_during_execution', api_error_status=429))
        budget, evidence = Budget(), Evidence()
        with self.assertRaises(support.ExecutorRequestFailed) as caught:
            support.ask_executor(failing, object(), 'task', b'png', budget, evidence)
        self.assertEqual(str(caught.exception), 'CLAUDE_CLI_RATE_LIMITED')
        self.assertEqual(evidence.events[-1][1]['error_code'], 'CLAUDE_CLI_RATE_LIMITED')

    def test_the_real_executable_is_found_behind_the_npm_shim(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim = Path(tmp) / 'claude.cmd'
            shim.write_text('@echo off', encoding='utf-8')
            exe = Path(tmp) / 'node_modules' / '@anthropic-ai' / 'claude-code' / 'bin' / 'claude.exe'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'MZ')
            self.assertEqual(module.cli_path({}, which=lambda name: str(shim)), str(exe))
            self.assertEqual(module.cli_path({'SQBF_CLAUDE_CLI': str(exe)}, which=lambda name: None), str(exe))
            with self.assertRaises(module.ClaudeCliFailed):
                module.cli_path({}, which=lambda name: None)
            with self.assertRaises(module.ClaudeCliFailed):
                module.cli_path({}, which=lambda name: str(Path(tmp) / 'other' / 'claude.cmd'))


if __name__ == '__main__':
    unittest.main()

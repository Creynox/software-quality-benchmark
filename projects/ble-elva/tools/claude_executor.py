"""A Claude model as the executor of a rehearsal (Probelauf), through the locally signed-in Claude Code CLI (PO decision 2026-10-21).

A rehearsal runs the complete dry-run path (real guards, side-effect contract per stage, independent Oracles, points report) on a disposable
scratch clone; only the executor is a Claude model (default Haiku 5.5) instead of the script. It shows where the tasks are hard for a model and
where the harness breaks on states a script never produces (live run 824fa661 lost its report stage to a half-saved entry). It is never a
benchmark result: the ChatGPT plan stays the only provider of a scored run (regular_runner.run_suite), and a rehearsal is labelled as such in
every report.

The model gets what the benchmark executor gets: one user message with the task text, then one to three screenshots, and the strict action
schema. The CLI runs with no tools, no MCP servers, no settings or project files, no session persistence and in an empty working directory, so
the model sees nothing but the screenshot and the task. It uses the Claude Code login of this Windows user; no API key is read or stored.
"""
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from sqbf.providers import ModelResponse

from .stage_support import DIMENSIONS, executor_schema

DEFAULT_MODEL = 'claude-haiku-5-5'
SYSTEM_PROMPT = ('You operate a web application in a usability test. Follow the task and the instructions in the user message and answer only '
                 'with the requested JSON action.')
NEUTRAL_REVIEW = {'verdict': 'INCONCLUSIVE', 'reason': 'rehearsal without reviewer', 'scores': dict.fromkeys(DIMENSIONS, None), 'findings': []}
MAX_IMAGES = 3
MAX_IMAGE_BYTES = 2_000_000


class ClaudeCliFailed(RuntimeError):
    """A failed request; `code` is recorded by ask_executor as the reason of the incomplete task (never the model text)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def cli_path(environ=None, which=shutil.which):
    """The real claude.exe: the npm shim (claude.cmd) cannot be started without cmd.exe, which would break the quoting of the JSON schema."""
    environ = os.environ if environ is None else environ
    configured = environ.get('SQBF_CLAUDE_CLI')
    candidates = [Path(configured)] if configured else []
    shim = which('claude')
    if shim:
        shim = Path(shim)
        candidates += [shim.parent / 'node_modules' / '@anthropic-ai' / 'claude-code' / 'bin' / 'claude.exe', shim]
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() == '.exe':
            return str(candidate)
    raise ClaudeCliFailed('CLAUDE_CLI_NOT_FOUND')


def _usage(result):
    usage = result.get('usage') or {}
    known = [usage.get(k) for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')]
    if not all(type(v) is int or v is None for v in known) or type(usage.get('output_tokens')) is not int:
        return {}
    prompt = sum(v for v in known if v)
    return {'input_tokens': prompt, 'output_tokens': usage['output_tokens'], 'total_tokens': prompt + usage['output_tokens']}


class ClaudeCliExecutor:
    """Callable with the signature of calibration.ask_calibrated: (model, prompt, images, budget, role) -> ModelResponse."""

    def __init__(self, model=DEFAULT_MODEL, *, schema=None, timeout=120, run=subprocess.run, executable=None):
        self.model = model
        self.schema = schema or executor_schema()
        self.timeout = timeout
        self.run = run
        self.executable = executable
        self.log = []  # per request: seconds, status, error code, tokens; never model text

    def command(self):
        return [self.executable or cli_path(), '-p', '--model', self.model, '--input-format', 'stream-json', '--output-format', 'stream-json',
                '--verbose', '--json-schema', json.dumps(self.schema, separators=(',', ':')), '--tools', '', '--strict-mcp-config',
                '--setting-sources', '', '--no-session-persistence', '--system-prompt', SYSTEM_PROMPT]

    @staticmethod
    def message(prompt, images):
        images = images if isinstance(images, list) else [images]
        if not 1 <= len(images) <= MAX_IMAGES or any(not isinstance(png, bytes) or len(png) > MAX_IMAGE_BYTES for png in images):
            raise ClaudeCliFailed('CLAUDE_CLI_IMAGE_LIMIT')
        content = [{'type': 'text', 'text': prompt}] + [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': base64.b64encode(png).decode('ascii')}} for png in images]
        return json.dumps({'type': 'user', 'message': {'role': 'user', 'content': content}}) + '\n'

    def ask(self, prompt, images):
        payload = self.message(prompt, images)
        started = time.monotonic()
        entry = {'status': 'FAILED', 'error_code': None, 'seconds': None, 'usage': {}}
        self.log.append(entry)
        try:
            with tempfile.TemporaryDirectory(prefix='sqbf-claude-') as cwd:
                try:
                    done = self.run(self.command(), input=payload, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                    cwd=cwd, timeout=self.timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                except subprocess.TimeoutExpired:
                    raise ClaudeCliFailed('CLAUDE_CLI_TIMEOUT') from None
                except OSError:
                    raise ClaudeCliFailed('CLAUDE_CLI_NOT_STARTED') from None
            result = None
            for line in (done.stdout or '').splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict) and item.get('type') == 'result':
                    result = item
            if result is None:
                raise ClaudeCliFailed('CLAUDE_CLI_NO_RESULT' if done.returncode == 0 else 'CLAUDE_CLI_EXIT_' + str(done.returncode))
            if result.get('is_error') or result.get('subtype') != 'success':
                status = result.get('api_error_status')
                raise ClaudeCliFailed('CLAUDE_CLI_RATE_LIMITED' if status == 429 else 'CLAUDE_CLI_API_ERROR_' + str(status) if status else 'CLAUDE_CLI_ERROR')
            data = result.get('structured_output')
            if not isinstance(data, dict):
                raise ClaudeCliFailed('CLAUDE_CLI_NO_STRUCTURED_OUTPUT')
            usage = _usage(result)
            entry.update(status='OK', usage=usage)
            return data, usage
        except ClaudeCliFailed as error:
            entry['error_code'] = error.code
            raise
        finally:
            entry['seconds'] = round(time.monotonic() - started, 3)

    def __call__(self, model, prompt, images, budget, role):
        if role != 'executor':
            return ModelResponse(json.loads(json.dumps(NEUTRAL_REVIEW)), {})
        ticket = budget.claim('executor')
        usage = None
        try:
            data, usage = self.ask(prompt, images)
            return ModelResponse(data, usage)
        finally:
            budget.complete_call(ticket, usage)

    def summary(self):
        ok = [e for e in self.log if e['status'] == 'OK']
        codes = {}
        for entry in self.log:
            if entry['error_code']:
                codes[entry['error_code']] = codes.get(entry['error_code'], 0) + 1
        return {'kind': 'claude_cli', 'model': self.model, 'requests': len(self.log), 'succeeded': len(ok), 'failed_by_code': codes,
                'seconds_total': round(sum(e['seconds'] or 0 for e in self.log), 1),
                'tokens_total': sum(e['usage'].get('total_tokens', 0) for e in ok)}

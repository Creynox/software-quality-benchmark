"""Two synthetic provider requests that prove the suite's response schemas are accepted.

Live run 3d9c2706 lost its first stage to a reviewer request that failed after 2.7 s. The
executor and reviewer schemas are the only provider-facing contracts the suite adds, and no
offline test can show that the provider accepts them. This probe sends exactly one request
per schema (no retry) with a generated synthetic image: no application data, no private
screenshots, no credentials. It prints and stores fixed diagnostic codes only.
"""
import json
import struct
import subprocess
import time
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqbf.artifact_privacy import check_private_directory, create_private_file
from sqbf.calibration import ResourceStop, SuiteBudget, ask_calibrated
from sqbf.models import ActionValidationError, validate_action
from sqbf.suites import canonical_hash
from .stage_support import REVIEW_SCHEMA, RUBRIC_VERSION, SCORING_VERSION, executor_schema, review_prompt, valid_review

PROBE_KIND = 'nsn014-provider-probe-v1'
PROBE_MODELS = ('gpt-6-luna', 'gpt-6.1-sol')
PROBE_MAX_AGE = timedelta(hours=12)
PROBE_POLICY = {'mode': 'calibration', 'hard_seconds': 300, 'hard_model_calls': 2, 'limit_result': 'INCONCLUSIVE',
                'automatic_retry': False, 'task_marks_are_hard_limits': False}
EXECUTOR_PROMPT = ('Synthetic provider compatibility probe. The image only shows colored blocks; there is no application, '
                   'task or data. Return exactly one strict JSON UI action: action "done", reason "probe", all other fields null.')
REVIEWER_INTRO = ('Synthetic provider compatibility probe. The image only shows colored blocks; there is no application '
                  'or workflow to judge. Return the configured strict review schema with verdict INCONCLUSIVE, '
                  'findability 3, clarity null, task_progress 3, error_recovery null and exactly one finding with '
                  'category UNCLEAR, severity info and the text "probe" for observed, expected, suggestion and evidence.')
PALETTE = ((200, 40, 40), (40, 160, 60), (50, 80, 200), (230, 200, 40))


def synthetic_png(width=320, height=200):
    """Generated colored blocks; contains no text, no application content."""
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend(PALETTE[(x * 4 // width + y * 3 // height * 4) % len(PALETTE)])
        rows.append(bytes(row))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))


def schema_hashes():
    return {'executor_schema_sha256': canonical_hash(executor_schema()), 'reviewer_schema_sha256': canonical_hash(REVIEW_SCHEMA)}


def _valid_action(data):
    try:
        action = {k: v for k, v in data.items() if v is not None}
        validate_action(action, 1280, 800)
        return True
    except (ActionValidationError, AttributeError, TypeError):
        return False


def run_probe(executor, reviewer, *, ask=ask_calibrated, clock=time.monotonic):
    """At most two requests, each once. Returns per-actor results with fixed codes only."""
    budget = SuiteBudget(PROBE_POLICY, clock=clock)
    budget.start_task({'case_id': 'PROVIDER-PROBE', 'observation_marks': {'seconds': 120, 'actions': 2}})
    png = synthetic_png()
    results = {}
    for actor, model, prompt, validate in (
            ('executor', executor, EXECUTOR_PROMPT, _valid_action),
            ('reviewer', reviewer, review_prompt(REVIEWER_INTRO, '\n' + json.dumps({'visible_actions': [], 'synthetic': True})), valid_review)):
        try:
            response = ask(model, prompt, [png], budget, actor)
            results[actor] = {'status': 'OK' if validate(response.data) else 'RESPONSE_INVALID', 'error_code': None}
        except ResourceStop:
            results[actor] = {'status': 'NOT_RUN', 'error_code': 'RESOURCE_STOP'}
            break
        except Exception as error:
            results[actor] = {'status': 'FAILED', 'error_code': getattr(error, 'code', None) or 'PROBE_REQUEST_FAILED'}
    report = budget.report()
    for index, request in enumerate(report['requests']):
        results[request['actor']].update(elapsed_seconds=round(request['elapsed_seconds'], 3), usage=request['usage'])
    return results, report['model_calls']


def probe_verdict(results):
    return 'PROBE_PASS' if all(results.get(a, {}).get('status') == 'OK' for a in ('executor', 'reviewer')) else 'PROBE_FAILED'


def provider_probe(suite, output, executor_id, reviewer_id, *, execute=False):
    """Plan only by default; --execute performs fresh OAuth and exactly two requests."""
    if (executor_id, reviewer_id) != PROBE_MODELS:
        return {'status': 'BLOCKED_MODEL_SELECTION', 'model_calls': 0}
    plan = {'kind': PROBE_KIND, 'executor_model': executor_id, 'reviewer_model': reviewer_id, 'requests': 2,
            'scoring_version': SCORING_VERSION, 'rubric_version': RUBRIC_VERSION, 'suite_version': suite['version'],
            **schema_hashes(), 'data': 'generated synthetic image only; no application data, credentials or private files'}
    if not execute:
        return dict(plan, status='PROBE_PLAN_ONLY', model_calls=0)
    output = Path(output).resolve()
    if any((p / '.git').exists() for p in output.parents):
        raise ValueError('Artifacts must remain outside Git')
    if not output.exists():
        output.mkdir(parents=True)
        check_private_directory(output, protect=True)
    else:
        check_private_directory(output)
    from sqbf.plan_login import _load_host, authorize_or_reuse, catalog
    from sqbf.providers import ChatGPTPlanModel
    import os
    credential = authorize_or_reuse(_load_host(Path(os.environ['LOCALAPPDATA']) / 'SQBF' / 'plan-login'))
    available = catalog(credential)
    if executor_id not in available or reviewer_id not in available:
        return dict(plan, status='BLOCKED_MODEL_UNAVAILABLE', model_calls=0, catalog_has_models=False)
    executor = ChatGPTPlanModel(executor_id, credential, executor_schema())
    reviewer = ChatGPTPlanModel(reviewer_id, credential, REVIEW_SCHEMA)
    results, calls = run_probe(executor, reviewer)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    record = dict(plan, status='PROBE_RECORDED', verdict=probe_verdict(results), results=results, model_calls=calls,
                  created_at=datetime.now(timezone.utc).isoformat(), sqbf_commit=commit, catalog_has_models=True)
    path = output / ('provider-probe-' + uuid4().hex + '.json')
    create_private_file(path)
    path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    return dict(record, path=str(path))


def evaluate_probe(path, executor_id, reviewer_id, *, now=None):
    """Readiness view of a stored probe. NOT_PROBED is allowed; a failed or stale probe is not."""
    if path is None:
        return {'status': 'NOT_PROBED', 'ux_layer_assured': False}
    try:
        record = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        created = datetime.fromisoformat(record['created_at'])
        current = schema_hashes()
        bound = (record.get('kind') == PROBE_KIND and record.get('executor_model') == executor_id
                 and record.get('reviewer_model') == reviewer_id
                 and all(record.get(k) == v for k, v in current.items()))
        if not bound or created.tzinfo is None or (now or datetime.now(timezone.utc)) - created > PROBE_MAX_AGE:
            return {'status': 'PROBE_NOT_CURRENT', 'ux_layer_assured': False}
        verdict = record['verdict']
        codes = {a: record['results'][a].get('error_code') or record['results'][a]['status'] for a in ('executor', 'reviewer')}
        if verdict == 'PROBE_PASS' and all(record['results'][a]['status'] == 'OK' for a in codes):
            return {'status': 'PROBE_PASSED', 'ux_layer_assured': True, 'created_at': record['created_at']}
        return {'status': 'PROBE_FAILED', 'ux_layer_assured': False, 'codes': codes}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {'status': 'PROBE_NOT_CURRENT', 'ux_layer_assured': False}

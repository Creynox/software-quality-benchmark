"""Repeatable, model-free acceptance of prepared fixture/persona gates only."""
import json
from pathlib import Path

from sqbf.artifact_privacy import create_private_file
from sqbf.models import Scenario
from sqbf.no_write_oracle import snapshot
from sqbf.session_check import check_session
from sqbf.suites import check_dataset, canonical_hash, validate_suite
from .persona_scope import check_persona
from .suite_fixture import validate_target


def check_fixture(fixture, suite, dataset):
    result = {'status': 'BLOCKED_SUITE_FIXTURE', 'model_calls': 0, 'database_writes': 0, 'actors': {},
              'limitations': ['Fixture acceptance is not test-adapter readiness or a measured benchmark.']}
    try:
        validate_target(fixture); validate_suite(suite)
        review = check_dataset(dataset)
        if (review['status'] != 'DATASET_APPROVED' or review['content_sha256'] != fixture['suite_copy']['dataset_sha256']
                or canonical_hash(suite) != fixture['suite_copy']['suite_sha256']
                or dataset['dataset_id'] != suite['dataset_id']
                or {row['position_id'] for row in dataset['positions']} != set(suite['required_position_ids'])):
            return dict(result, reason='SOURCE_OR_SUITE_CHANGED')
        if set(fixture['personas']) != {'laboratory_lead', 'laboratory_staff', 'wpk_lead', 'plant_lead'}:
            return dict(result, reason='PERSONA_SET_MISMATCH')
        counts = fixture['read_only_oracle']['expected_counts']
        project_count=2 if fixture['suite_copy'].get('receipt_entrypoint')=='plan_replenish_once' else 1
        if any(counts.get(key) != value for key, value in {'workspace_products': 10, 'sampling_plans': 1,
                 'sampling_plan_items': 10, 'samples': 0, 'lims_sample': 0, 'ble_reports': 0,
                 'customers': 1, 'projects': project_count}.items()):
            return dict(result, reason='START_STATE_MISMATCH')
        before = snapshot(fixture)
        pinned=fixture['suite_copy'].get('prepared_state_sha256')
        if ((suite.get('resource_policy') is not None and not pinned)
                or (pinned and canonical_hash(before['tables'])!=pinned)):
            return dict(result,reason='PREPARED_CONTENT_CHANGED_OR_UNPINNED')
        policy = Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json', fixture['target_url']).read_only_policy
        for persona, actor in fixture['personas'].items():
            session = check_session(fixture['target_url'], actor['storage_state'], policy,
                                    expected_products=fixture['active_list_expected_products'])
            actor_result = {'session': session['status'], 'identity_scope': 'NOT_CHECKED'}
            result['actors'][persona] = actor_result
            if session['status'] != 'SESSION_RESTORED':
                return dict(result, reason='SESSION_FAILED')
            scope = check_persona(fixture, persona, actor['storage_state'], fixture['identity_verifier'])
            actor_result['identity_scope'] = scope['status']
            if scope['status'] != 'PERSONA_SCOPE_VERIFIED':
                return dict(result, reason='SCOPE_FAILED')
        after = snapshot(fixture)
        if after != before:
            return dict(result, reason='PROTECTED_DATA_CHANGED')
        result.update(status='FIXTURE_GATES_VERIFIED', protected_data_unchanged=True,
                      database_endpoint='127.0.0.1:55434', web_url=fixture['target_url'],
                      counts={key: row['count'] for key, row in after['tables'].items()})
        return result
    except Exception:
        return dict(result, reason='EVIDENCE_UNAVAILABLE')


def write_acceptance(fixture_path, suite_path, dataset_path, output):
    fixture, suite, dataset = [json.loads(Path(path).read_text(encoding='utf-8-sig'))
                              for path in (fixture_path, suite_path, dataset_path)]
    report = check_fixture(fixture, suite, dataset)
    output = Path(output); create_private_file(output)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report

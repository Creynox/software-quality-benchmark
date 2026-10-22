"""Model-free controller session renewal; one guarded login per stale file.

Never called by an executor. Failed attempts are durable and never retried by
this command. Existing session files and fixture manifests remain unchanged.
"""
import copy
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from sqbf.artifact_privacy import create_private_file, check_private_directory
from sqbf.cli import save_session
from sqbf.models import Scenario
from sqbf.no_write_oracle import snapshot
from sqbf.oracle import verify_docker_identity
from sqbf.scope_check import verify_runtime
from sqbf.session_check import check_session
from .persona_scope import check_persona
from .suite_fixture import validate_target


def prepare_sessions(fixture, directory):
    result = {'status': 'BLOCKED_SESSION', 'actors': {}, 'model_calls': 0,
              'benchmark_started': False, 'login_attempts': 0}
    output = copy.deepcopy(fixture)
    try:
        validate_target(fixture)
        names = {'laboratory_lead': 'sqbf-laborleitung', 'laboratory_staff': 'sqbf-labormitarbeiter',
                 'wpk_lead': 'sqbf-wpk', 'plant_lead': 'sqbf-werkleitung'}
        if set(fixture['personas']) != set(names) or any(fixture['personas'][k]['username'] != v for k,v in names.items()):
            return dict(result, reason='PERSONA_SET_MISMATCH'), output
        directory = Path(directory).resolve(strict=True)
        check_private_directory(directory)
        if any((p / '.git').exists() for p in directory.parents):
            raise ValueError()
        verify_docker_identity(fixture)
        runtime = verify_runtime(fixture['target_url'], fixture['suite_copy']['application_root'],
                                 fixture['identity_scope_check'])
        pinned = fixture['suite_copy']['runtime']
        if any(runtime[k] != pinned[k] for k in ('assembly', 'sha256')):
            return dict(result, reason='RUNTIME_MISMATCH'), output
        before = snapshot(fixture)
        policy = Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json',
                               fixture['target_url']).read_only_policy
        for persona in ('laboratory_lead', 'laboratory_staff', 'wpk_lead', 'plant_lead'):
            actor = output['personas'][persona]
            session = check_session(fixture['target_url'], actor['storage_state'], policy,
                                    expected_products=fixture['active_list_expected_products'])
            item = {'login_attempts': 0, 'session': session['status'], 'scope': 'NOT_CHECKED'}
            result['actors'][persona] = item
            if session['status'] != 'SESSION_RESTORED':
                # Only a demonstrated login redirect permits renewal. Browser,
                # connection and UI-contract failures are not login failures.
                if session.get('reason') != 'UNEXPECTED_PAGE' or not session.get('checks') or session['checks'][-1].get('path') != '/login':
                    return dict(result, reason='SESSION_FAILURE_NOT_LOGIN_REDIRECT'), output
                old = Path(actor['storage_state']).resolve(strict=True)
                check_private_directory(old.parent)
                Path(actor['credential_file']).resolve(strict=True)
                key = hashlib.sha256(old.read_bytes()).hexdigest()
                marker = old.parent / ('login-attempt-' + persona + '-' + key + '.json')
                create_private_file(marker)  # Existing marker blocks another POST.
                marker.write_text(json.dumps({'status': 'ATTEMPT_RESERVED', 'persona': persona}), encoding='utf-8')
                fresh = directory / (persona + '-session-' + uuid4().hex + '.json')
                diagnostic = directory / (fresh.stem + '-login-check.json')
                item['login_attempts'] = 1
                result['login_attempts'] += 1
                save_session(fixture['target_url'], fresh, actor['credential_file'],
                             actor['username'], diagnostic_output=diagnostic)
                actor['storage_state'] = str(fresh)
                session = check_session(fixture['target_url'], fresh, policy,
                                        expected_products=fixture['active_list_expected_products'])
                item['session'] = session['status']
            if session['status'] != 'SESSION_RESTORED':
                return dict(result, reason='RENEWED_SESSION_INVALID'), output
            scope = check_persona(output, persona, actor['storage_state'], fixture['identity_verifier'])
            item['scope'] = scope['status']
            if scope['status'] != 'PERSONA_SCOPE_VERIFIED':
                return dict(result, reason='IDENTITY_SCOPE_FAILED'), output
            actor['gates_verified'] = True
        after = snapshot(fixture)
        if after != before:
            return dict(result, reason='PROTECTED_DATA_CHANGED'), output
        return dict(result, status='SESSIONS_VERIFIED', protected_data_unchanged=True), output
    except Exception:
        return dict(result, reason='RENEWAL_FAILED_NO_RETRY'), output


def write_prepared_sessions(fixture_path, output_path, report_path):
    output_path, report_path = Path(output_path), Path(report_path)
    # Output and report ACLs are enforced before login, including error paths.
    create_private_file(output_path)
    create_private_file(report_path)
    fixture_path = Path(fixture_path).resolve(strict=True)
    fixture = json.loads(fixture_path.read_text(encoding='utf-8-sig'))
    for actor in fixture['personas'].values():
        for key in ('credential_file', 'storage_state'):
            p = Path(actor[key])
            actor[key] = str(p if p.is_absolute() else fixture_path.parent / p)
    result, prepared = prepare_sessions(fixture, output_path.parent)
    prepared['session_preparation'] = result
    output_path.write_text(json.dumps(prepared, indent=2), encoding='utf-8')
    report_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result

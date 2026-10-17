"""Independent signed identity/exact-role/exact-scope gate for suite actors.

Uses the already authorized fixture controller in READ ONLY/ROLLBACK, never an
Oracle privilege fallback. No credential/hash columns queried; models see none
of its inputs. UI reachability remains a separate mandatory gate.
"""
import json
import hashlib
from pathlib import Path
import subprocess
from uuid import UUID

from sqbf.oracle import verify_docker_identity
from sqbf.scope_check import verify_runtime
from .suite_fixture import validate_target

PROJECTION = Path(__file__).with_name('persona-scope.sql')


def evaluate_persona(ticket, scope, actor, fixture):
    """Emit booleans only, never signed claims, DB records or permissions."""
    expected_scopes = [{'type': 'Plant', 'key': actor['plant_id'], 'tenant_id': actor['tenant_id'],
        'plant_id': actor['plant_id'], 'customer_id': None, 'laboratory_id': None},
        {'type': 'Tenant', 'key': actor['tenant_id'], 'tenant_id': actor['tenant_id'],
         'plant_id': None, 'customer_id': None, 'laboratory_id': None}]
    checks = {
        'signed_session': ticket.get('valid') is True,
        'account': ticket.get('username') == scope.get('username') == actor['username']
                   and ticket.get('user_id') == scope.get('user_id') == actor['user_id']
                   and type(scope.get('users')) is int and scope['users'] == 1,
        'active_non_admin': scope.get('active') is True and scope.get('admin') is False,
        'tenant': scope.get('tenant_id') == actor['tenant_id'] and scope.get('tenant_active') is True,
        'exact_role': scope.get('roles') == [actor['role']] and actor['role'] in ('Laborleiter', 'Mitarbeiter', 'Viewer'),
        'exact_permissions': isinstance(scope.get('permissions'), list)
            and sorted(scope['permissions']) == sorted(actor['allowed_permissions']),
        'plant': scope.get('plant_valid') is True,
        'exact_scope_no_global': scope.get('scopes') == expected_scopes,
        'verified_controller_read_only': scope.get('read_only') == 'on'
            and scope.get('database') == fixture['database']['name']
            and scope.get('role') == fixture['database']['bootstrap_user'],
    }
    return {'status': 'PERSONA_SCOPE_VERIFIED' if all(checks.values()) else 'BLOCKED_SCOPE_VERIFICATION',
            'checks': checks, 'model_calls': 0, 'database_writes': 0}


def check_persona(fixture, persona, storage_state, verifier, *, run=subprocess.run):
    blocked = {'status': 'BLOCKED_SCOPE_VERIFICATION', 'model_calls': 0, 'database_writes': 0}
    try:
        validate_target(fixture)
        actor = fixture['personas'][persona]
        for key in ('user_id', 'tenant_id', 'plant_id'):
            if str(UUID(actor[key])) != actor[key]: raise ValueError()
        if actor['username'] not in ('sqbf-laborleitung', 'sqbf-labormitarbeiter', 'sqbf-wpk', 'sqbf-werkleitung'):
            raise ValueError()
        identity = verify_docker_identity(fixture, run=run)
        root = fixture['suite_copy']['application_root']
        runtime = verify_runtime(fixture['target_url'], root, fixture['identity_scope_check'], run=run)
        expected = fixture['suite_copy']['runtime']
        if runtime['sha256'] != expected['sha256'] or runtime['assembly'] != expected['assembly']:
            return dict(blocked, reason='BUILD_MISMATCH')
        ticket_result = run(['dotnet', str(Path(verifier).resolve(strict=True))],
            input=json.dumps({'storage_state': str(Path(storage_state).resolve(strict=True)), 'application_root': root}),
            capture_output=True, text=True, check=True, timeout=15)
        ticket = json.loads(ticket_result.stdout)
        if ticket.get('valid') is not True:
            return dict(blocked, reason='SIGNED_SESSION_INVALID')
        sql = PROJECTION.read_text(encoding='utf-8')
        if hashlib.sha256(sql.encode()).hexdigest() != fixture['persona_projection_sha256']:
            return dict(blocked, reason='PROJECTION_MISMATCH')
        cmd = ['docker', 'exec', '-i', identity['container_id'], 'psql', '-X', '-q', '-At',
               '-U', fixture['database']['bootstrap_user'], '-d', fixture['database']['name'], '-v', 'ON_ERROR_STOP=1']
        parameters = {'username': actor['username'], 'tenant_id': actor['tenant_id'], 'plant_id': actor['plant_id'],
                      'plant_name': fixture['fixture_data']['plant_name'], 'site_number': fixture['fixture_data']['site_number']}
        for key, value in parameters.items(): cmd.extend(['-v', key + '=' + value])
        result = run(cmd, input=sql, capture_output=True, text=True, check=True, timeout=10)
        scope = json.loads(result.stdout)
        return evaluate_persona(ticket, scope, actor, fixture)
    except Exception:
        return dict(blocked, reason='EVIDENCE_UNAVAILABLE')

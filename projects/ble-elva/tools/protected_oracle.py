"""Audit-aware comparison of protected tables (live run 45eb301f).

BLE's own, sanctioned write actions stamp audit columns on rows they touch: the plan-wide
sample creation updates sampling_plans.updated_at/updated_by. The static-fixture gate must
still stop any substantive change of protected data, so a table that differs from its
prepared baseline is compared again with the audit columns removed. Only an audit-only
difference is tolerated, and it is reported, never hidden.
"""
import json
import re
import subprocess

from sqbf.oracle import verify_docker_identity
from .suite_fixture import validate_target

AUDIT_COLUMNS = ('updated_at', 'updated_by')
TABLE = re.compile(r'[a-z][a-z0-9_]*')


UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def collect_scoped_hashes(fixture, resolved, *, run=subprocess.run):
    """Per allowance table: target rows (audit columns excluded) and all other rows (nothing excluded), each with count and hash.
    SELECT-only role, READ ONLY, rolled back. Lets the gate tell an audit stamp on the target row from any other change."""
    validate_target(fixture)
    if not resolved:
        return {}
    audit = 'ARRAY[' + ','.join("'" + column + "'" for column in AUDIT_COLUMNS) + ']'
    target = verify_docker_identity(fixture, run=run)
    db = fixture['database']
    statements = ['BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;', "SET LOCAL statement_timeout='5s';",
                  "SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));"]
    for allowance in resolved:
        name, ids = allowance['table'], allowance['ids']
        if not TABLE.fullmatch(name) or not ids or any(not UUID_PATTERN.fullmatch(i) for i in ids):
            raise ValueError('Safe allowance table and row identifiers required')
        wanted = "t.id = ANY(ARRAY[" + ','.join("'" + i + "'" for i in ids) + "]::uuid[])"
        statements.append(
            "SELECT json_build_object('table','" + name + "','target_count',count(*) FILTER (WHERE " + wanted + "),"
            "'target_hash',md5(coalesce(string_agg((to_jsonb(t) - " + audit + ")::text,E'\\n' ORDER BY (to_jsonb(t) - " + audit + ")::text) FILTER (WHERE " + wanted + "),'')),"
            "'rest_count',count(*) FILTER (WHERE NOT " + wanted + "),"
            "'rest_hash',md5(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text) FILTER (WHERE NOT " + wanted + "),''))) FROM public." + name + " t;")
    statements.append('ROLLBACK;')
    result = run(['docker', 'exec', '-i', target['container_id'], 'psql', '-X', '-q', '-At', '-U', db['oracle_role'],
                  '-d', db['name'], '-v', 'ON_ERROR_STOP=1'], input='\n'.join(statements), capture_output=True, text=True,
                 encoding='utf-8', check=True, timeout=20)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    if rows[0] != {'database': db['name'], 'role': db['oracle_role'], 'read_only': 'on'} or len(rows) != len(resolved) + 1:
        raise ValueError('Read-only Oracle identity mismatch')
    return {row['table']: {k: v for k, v in row.items() if k != 'table'} for row in rows[1:]}


def collect_normalized_hashes(fixture, tables, *, run=subprocess.run):
    """Count and content hash per table, audit columns excluded. SELECT-only role, READ ONLY, rolled back."""
    validate_target(fixture)
    names = sorted(set(tables))
    if not names or any(not TABLE.fullmatch(name) for name in names):
        raise ValueError('Safe protected table identifiers required')
    target = verify_docker_identity(fixture, run=run)
    db = fixture['database']
    audit = 'ARRAY[' + ','.join("'" + column + "'" for column in AUDIT_COLUMNS) + ']'
    statements = ['BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;', "SET LOCAL statement_timeout='5s';",
                  "SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));"]
    for name in names:
        statements.append(
            "SELECT json_build_object('table','" + name + "','count',count(*),'hash',md5(coalesce(string_agg((to_jsonb(t) - " + audit
            + ")::text,E'\\n' ORDER BY (to_jsonb(t) - " + audit + ")::text),''))) FROM public." + name + " t;")
    statements.append('ROLLBACK;')
    result = run(['docker', 'exec', '-i', target['container_id'], 'psql', '-X', '-q', '-At', '-U', db['oracle_role'],
                  '-d', db['name'], '-v', 'ON_ERROR_STOP=1'], input='\n'.join(statements), capture_output=True, text=True,
                 encoding='utf-8', check=True, timeout=20)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    if rows[0] != {'database': db['name'], 'role': db['oracle_role'], 'read_only': 'on'} or len(rows) != len(names) + 1:
        raise ValueError('Read-only Oracle identity mismatch')
    return {row['table']: {'count': row['count'], 'hash': row['hash']} for row in rows[1:]}

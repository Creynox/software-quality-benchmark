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

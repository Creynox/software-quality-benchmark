"""Row- and column-level database diff for modelless dry runs on a disposable fixture copy.

Live run 45eb301f lost its first stage to an undocumented but harmless audit stamp. This module
measures, per stage action, exactly which rows and columns of which tables BLE changes, so the
allowed side effects can be written down as a contract instead of being discovered in a live run.
Read-only: the controller role runs READ ONLY transactions that are rolled back; values are
never stored, only per-column hashes. Never run against a fixture that is meant for a benchmark.
"""
import json
import re
import subprocess

AUDIT_COLUMNS = ('updated_at', 'updated_by')
LIST_TABLES_SQL = "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
TABLE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


def _psql(run, container, user, database, sql, *, timeout=120):
    result = run(['docker', 'exec', '-i', container, 'psql', '-X', '-q', '-At', '-U', user, '-d', database, '-v', 'ON_ERROR_STOP=1'],
                 input='BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n' + sql.rstrip().rstrip(';') + ';\nROLLBACK;', capture_output=True,
                 text=True, encoding='utf-8', timeout=timeout)
    if result.returncode != 0:
        # The first stderr line names the failing statement class (syntax, missing column), never row values.
        raise RuntimeError('psql failed: ' + ((result.stderr or '').strip().splitlines() or [''])[0][:160])
    return result.stdout


def table_names(run, container, user, database):
    names = _psql(run, container, user, database, LIST_TABLES_SQL).split()
    if not names or any(not TABLE.fullmatch(name) for name in names):
        raise ValueError('Unexpected table identifiers')
    return names


TABLE_HASH_SQL = """SELECT string_agg(format('SELECT json_build_object(''table'',%L,''count'',count(*),''hash'',md5(coalesce(
string_agg(to_jsonb(x)::text,E''\\n'' ORDER BY to_jsonb(x)::text),''''))) FROM public.%I x;',tablename,tablename),E'\\n' ORDER BY tablename)
FROM pg_tables WHERE schemaname='public';"""


def table_hashes(run, container, user, database):
    """{table: {count, hash}} of every public table (controller role, READ ONLY, rolled back). Values are never returned."""
    statements = _psql(run, container, user, database, TABLE_HASH_SQL).strip()
    if not statements:
        raise ValueError('No tables')
    rows = [json.loads(line) for line in _psql(run, container, user, database, statements, timeout=120).splitlines() if line.strip()]
    result = {row['table']: {'count': row['count'], 'hash': row['hash']} for row in rows}
    if len(result) != len(rows) or any(not TABLE.fullmatch(name) for name in result):
        raise ValueError('Unexpected table identifiers')
    return result


def snapshot_rows(run, container, user, database, tables=None):
    """{table: {row key: {column: md5(value)}}}. The key is the id column or the row hash if there is none."""
    names = tables or table_names(run, container, user, database)
    statements = []
    for name in names:
        if not TABLE.fullmatch(name):
            raise ValueError('Unsafe table identifier')
        statements.append(
            "SELECT json_build_object('t','" + name + "','r',coalesce(json_object_agg(s.k,s.c),'{}'::json)) FROM ("
            "SELECT coalesce(to_jsonb(t)->>'id',md5(to_jsonb(t)::text)) k,"
            "(SELECT json_object_agg(e.key,md5(e.value::text)) FROM jsonb_each(to_jsonb(t)) e) c FROM public.\"" + name + "\" t) s;")
    output = _psql(run, container, user, database, '\n'.join(statements), timeout=300)
    snapshot = {}
    for line in output.splitlines():
        if line.strip():
            row = json.loads(line)
            snapshot[row['t']] = row['r']
    if set(snapshot) != set(names):
        raise ValueError('Incomplete table snapshot')
    return snapshot


def diff_snapshots(before, after):
    """Per changed table: inserted/deleted row counts and updated rows with their changed column names."""
    if set(before) != set(after):
        raise ValueError('Table set changed')
    changes = {}
    for table in sorted(before):
        old, new = before[table], after[table]
        if old == new:
            continue
        inserted = sorted(set(new) - set(old))
        deleted = sorted(set(old) - set(new))
        updated = []
        for key in sorted(set(old) & set(new)):
            if old[key] != new[key]:
                columns = sorted(c for c in set(old[key]) | set(new[key]) if old[key].get(c) != new[key].get(c))
                updated.append({'key': key, 'columns': columns})
        changes[table] = {'inserted': len(inserted), 'deleted': len(deleted), 'updated': updated, 'inserted_keys': inserted[:20],
                          'rows_before': len(old), 'rows_after': len(new)}
    return changes


def classify_change(change):
    """audit_only: only updated rows whose changed columns are all audit stamps; otherwise substantive."""
    if change['inserted'] or change['deleted']:
        return 'rows_added_or_removed'
    return 'audit_only' if all(set(u['columns']) <= set(AUDIT_COLUMNS) for u in change['updated']) else 'substantive_update'


def summarize(changes):
    """Compact, value-free summary per table for contracts and reports."""
    return {table: {'kind': classify_change(c), 'inserted': c['inserted'], 'deleted': c['deleted'],
                    'updated_rows': len(c['updated']),
                    'updated_columns': sorted({col for u in c['updated'] for col in u['columns']})}
            for table, c in changes.items()}

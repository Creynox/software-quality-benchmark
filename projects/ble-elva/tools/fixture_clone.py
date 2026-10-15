"""Clone an unchanged, single-use NSN014 fixture and apply one documented preparation override.

Live run 3d9c2706 found a plan product that is inactive in the approved source data. The PO
chose a new isolated fixture with exactly that product activated, rather than editing the
consumed one. The clone is a byte copy of the source PostgreSQL volume, so roles, grants,
views, identities and every prepared row are identical; a hash of every public table proves
the copy and, after the override, that exactly one column of one row differs.

Nothing here touches the source data: the source container is stopped (never removed), its
volume, runtime directory, credentials, sessions and consumed lease stay in place. There is
no automatic rollback and no retry; each phase is recorded durably and a failure stops.
Model-free: no OAuth, no provider request, no BLE benchmark action.
"""
import copy
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqbf.artifact_privacy import check_private_directory
from sqbf.no_write_oracle import snapshot
from sqbf.oracle import verify_docker_identity
from sqbf.scope_check import verify_runtime
from sqbf.session_credentials import load_credentials
from sqbf.suites import canonical_hash
from .suite_fixture import validate_target

IDENT = re.compile(r'[a-z][a-z0-9_]{0,62}')
UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
TABLE_HASH_SQL = """SELECT string_agg(format('SELECT json_build_object(''table'',%L,''count'',count(*),''hash'',md5(coalesce(
string_agg(to_jsonb(x)::text,E''\\n'' ORDER BY to_jsonb(x)::text),''''))) FROM public.%I x;',tablename,tablename),E'\\n' ORDER BY tablename)
FROM pg_tables WHERE schemaname='public';"""


class CloneError(RuntimeError):
    def __init__(self, phase, reason):
        super().__init__(phase + ': ' + reason)
        self.phase, self.reason = phase, reason


def _run(run, args, *, phase, input=None, timeout=120):
    result = run(args, input=input, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise CloneError(phase, 'COMMAND_FAILED ' + ' '.join(args[:3]))
    return result.stdout


def _psql(run, container, user, database, sql, *, phase, readonly=True, timeout=60):
    body = ('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n' + sql + '\nROLLBACK;') if readonly else sql
    return _run(run, ['docker', 'exec', '-i', container, 'psql', '-X', '-q', '-At', '-U', user, '-d', database,
                      '-v', 'ON_ERROR_STOP=1'], phase=phase, input=body, timeout=timeout)


def table_hashes(run, container, user, database, *, phase):
    """Count and content hash of every public table (controller role, READ ONLY, rolled back)."""
    statements = _psql(run, container, user, database, TABLE_HASH_SQL, phase=phase).strip()
    if not statements:
        raise CloneError(phase, 'NO_TABLES')
    rows = [json.loads(line) for line in _psql(run, container, user, database, statements, phase=phase, timeout=120).splitlines() if line.strip()]
    result = {row['table']: {'count': row['count'], 'hash': row['hash']} for row in rows}
    if len(result) != len(rows):
        raise CloneError(phase, 'DUPLICATE_TABLE')
    return result


def changed_tables(before, after):
    if set(before) != set(after):
        raise CloneError('verify', 'TABLE_SET_CHANGED')
    return sorted(table for table in before if before[table] != after[table])


def new_identity(source):
    suffix = uuid4().hex[:12]
    name = 'sqbf-nsn014-' + suffix
    return {'suffix': suffix, 'container': name, 'database': name.replace('-', '_'), 'volume': name + '-data',
            'fixture_id': 'nsn014-ux-' + suffix}


def preflight(fixture, run, *, runtime_fn=None, snapshot_fn=None, docker_fn=None):
    # Module-level collaborators are resolved at call time so they stay replaceable.
    runtime_fn, snapshot_fn, docker_fn = runtime_fn or verify_runtime, snapshot_fn or snapshot, docker_fn or verify_docker_identity
    validate_target(fixture)
    copy_ = fixture['suite_copy']
    if copy_.get('stage') != 'persona_sessions_verified' or copy_.get('measured_samples_preseeded') is not False:
        raise CloneError('preflight', 'SOURCE_STAGE_NOT_ACCEPTED')
    baseline = copy_['prepared_tables']
    if canonical_hash(baseline) != copy_['prepared_state_sha256']:
        raise CloneError('preflight', 'PREPARED_HASH_MISMATCH')
    current = snapshot_fn(fixture, enforce_counts=False)['tables']
    if set(current) != set(baseline) or any(current[t] != v for t, v in baseline.items()):
        raise CloneError('preflight', 'SOURCE_NOT_IN_PREPARED_STATE')
    for table in ('samples', 'lims_sample', 'ble_reports', 'sqbf_measurement_inputs_v1', 'sqbf_allocation_inputs_v1'):
        if current[table]['count'] != 0:
            raise CloneError('preflight', 'SOURCE_HAS_BENCHMARK_ROWS')
    docker_fn(fixture)
    runtime = runtime_fn(fixture['target_url'], copy_['application_root'], fixture['identity_scope_check'])
    if runtime['pid'] != copy_['web_pid'] or any(runtime[k] != copy_['runtime'][k] for k in ('assembly', 'sha256')):
        raise CloneError('preflight', 'WEB_PROCESS_NOT_THE_RECORDED_ONE')
    return runtime


def clone_volume(run, source_volume, target_volume, image):
    """Byte copy with a content-checksum comparison; the source mount is read-only."""
    _run(run, ['docker', 'volume', 'create', target_volume], phase='volume')
    script = ('test ! -e /from/postmaster.pid && cp -a /from/. /to/ && '
              "cd /from && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum && "
              "cd /to && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum")
    out = _run(run, ['docker', 'run', '--rm', '--entrypoint', 'sh', '-v', source_volume + ':/from:ro', '-v', target_volume + ':/to',
                     image, '-c', script], phase='volume', timeout=900).split()
    checksums = [token for token in out if re.fullmatch(r'[0-9a-f]{64}', token)]
    if len(checksums) != 2 or checksums[0] != checksums[1]:
        raise CloneError('volume', 'COPY_CHECKSUM_MISMATCH')
    return checksums[0]


def override_sql(product_id):
    if not UUID_PATTERN.fullmatch(product_id):
        raise CloneError('override', 'PRODUCT_ID_INVALID')
    return ("BEGIN;\nDO $$ DECLARE n int; BEGIN\n"
            "UPDATE public.workspace_products SET is_active = true WHERE id = '" + product_id + "'::uuid AND is_active = false;\n"
            "GET DIAGNOSTICS n = ROW_COUNT;\nIF n <> 1 THEN RAISE EXCEPTION 'OVERRIDE_ROWCOUNT_%', n; END IF;\nEND $$;\nCOMMIT;")


def row_json(run, container, user, database, product_id, *, phase):
    if not UUID_PATTERN.fullmatch(product_id):
        raise CloneError(phase, 'PRODUCT_ID_INVALID')
    out = _psql(run, container, user, database, "SELECT to_jsonb(p) FROM public.workspace_products p WHERE p.id = '" + product_id + "'::uuid;", phase=phase)
    rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    if len(rows) != 1:
        raise CloneError(phase, 'PRODUCT_ROW_NOT_UNIQUE')
    return rows[0]


def column_diff(before, after):
    keys = set(before) | set(after)
    return {key: {'from': before.get(key), 'to': after.get(key)} for key in sorted(keys) if before.get(key) != after.get(key)}


def build_manifest(source, identity, container_id, runtime_root, prepared_tables, evidence):
    """New fixture manifest: identity, prepared baseline and override record change; nothing else is invented."""
    fixture = copy.deepcopy(source)
    fixture['database'].update(container=identity['container'], container_id=container_id, name=identity['database'],
                               volume=identity['volume'], host_port=55434, host_binding='127.0.0.1:55434')
    fixture.update(fixture_id=identity['fixture_id'], fixture_version='0.3', status='FIXTURE_CLONE_SESSIONS_PENDING')
    copy_ = fixture['suite_copy']
    copy_.update(prepared_tables=prepared_tables, prepared_state_sha256=canonical_hash(prepared_tables),
                 application_root=str(runtime_root), stage='clone_web_started')
    copy_.pop('web_pid', None)
    copy_['clone'] = evidence
    expected = list(fixture.get('active_list_expected_products', []))
    if evidence['override']['product_name'] not in expected:
        expected.append(evidence['override']['product_name'])
    fixture['active_list_expected_products'] = sorted(expected, key=str.casefold)
    for actor in fixture['personas'].values():
        actor['gates_verified'] = False
    fixture['session_preparation'] = {'status': 'SESSIONS_PENDING', 'model_calls': 0, 'benchmark_started': False}
    return fixture


def web_environment(base_env, connection):
    env = {k: v for k, v in base_env.items() if k.upper() not in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY')
           and not k.lower().startswith(('connectionstrings', 'sentry', 'geoweather', 'wpk__', 'dataprotection'))}
    env.update(ASPNETCORE_ENVIRONMENT='Development', Ble__DisableStartupSeeding='true',
               ConnectionStrings__DefaultConnection=connection, ConnectionStrings__DevelopmentCloneConnection=connection,
               Sentry__Dsn='', Wpk__Scheduler__Enabled='false', DOTNET_CLI_TELEMETRY_OPTOUT='1')
    return env


def clone_fixture(source_path, source_controller_credentials, output_dir, *, product_position='P06',
                  run=subprocess.run, popen=subprocess.Popen, sleep=time.sleep, environ=None):
    """Perform all phases; returns the new manifest path. Stops at the first failed phase."""
    import os
    environ = os.environ if environ is None else environ
    source_path = Path(source_path).resolve(strict=True)
    source = json.loads(source_path.read_text(encoding='utf-8-sig'))
    output = Path(output_dir)
    if any((p / '.git').exists() for p in output.resolve().parents):
        raise CloneError('preflight', 'OUTPUT_INSIDE_GIT')
    if output.exists():
        raise CloneError('preflight', 'OUTPUT_EXISTS')
    runtime = preflight(source, run)
    db = source['database']
    controller = db['bootstrap_user']
    product_id = source['suite_copy']['mapping']['positions'][product_position]
    output.mkdir(parents=True)
    check_private_directory(output, protect=True)
    state = {'phases': [], 'source_fixture_id': source['fixture_id'], 'started_at': datetime.now(timezone.utc).isoformat()}

    def done(phase, **detail):
        state['phases'].append(dict(phase=phase, at=datetime.now(timezone.utc).isoformat(), **detail))
        (output / 'clone-state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')

    before = table_hashes(run, db['container'], controller, db['name'], phase='source_hash')
    done('source_hashed', tables=len(before))
    # The only processes touched are the verified source web process and the source container (stopped, kept).
    _run(run, ['taskkill', '/PID', str(runtime['pid']), '/T', '/F'], phase='stop_web')
    sleep(2)
    _run(run, ['docker', 'stop', '-t', '120', db['container']], phase='stop_source')
    info = json.loads(_run(run, ['docker', 'inspect', db['container']], phase='stop_source'))[0]
    if info['State']['Status'] != 'exited' or info['State']['ExitCode'] != 0:
        raise CloneError('stop_source', 'NOT_CLEANLY_STOPPED')
    done('source_stopped', exit_code=info['State']['ExitCode'])
    identity = new_identity(source)
    volume_checksum = clone_volume(run, db['volume'], identity['volume'], db['image'])
    done('volume_cloned', volume=identity['volume'], tree_sha256=volume_checksum)
    container_id = _run(run, ['docker', 'run', '-d', '--name', identity['container'], '-e', 'POSTGRES_USER=' + controller,
                              '-e', 'POSTGRES_DB=' + identity['database'], '-p', '127.0.0.1:55434:5432',
                              '-v', identity['volume'] + ':/var/lib/postgresql/data', db['image']], phase='new_container').strip()
    for _ in range(120):
        ready = run(['docker', 'exec', container_id, 'pg_isready', '-h', '127.0.0.1', '-U', controller, '-d', 'postgres'],
                    capture_output=True, text=True, timeout=10)
        if ready.returncode == 0:
            break
        sleep(.5)
    else:
        raise CloneError('new_container', 'NOT_READY')
    done('container_started', container=identity['container'])
    if not (IDENT.fullmatch(db['name']) and IDENT.fullmatch(identity['database'])):
        raise CloneError('rename', 'DATABASE_NAME_INVALID')
    _psql(run, container_id, controller, 'postgres', 'ALTER DATABASE ' + db['name'] + ' RENAME TO ' + identity['database'] + ';',
          phase='rename', readonly=False)
    new_fixture = copy.deepcopy(source)
    new_fixture['database'].update(container=identity['container'], container_id=container_id, name=identity['database'],
                                   volume=identity['volume'])
    verify_docker_identity(new_fixture)
    cloned = table_hashes(run, identity['container'], controller, identity['database'], phase='clone_hash')
    if cloned != before:
        raise CloneError('verify', 'CLONE_DIFFERS_FROM_SOURCE ' + ','.join(changed_tables(before, cloned)))
    done('clone_verified_identical', tables=len(cloned))
    row_before = row_json(run, identity['container'], controller, identity['database'], product_id, phase='override')
    if row_before.get('is_active') is not False:
        raise CloneError('override', 'PRODUCT_NOT_INACTIVE')
    statement = override_sql(product_id)
    _psql(run, identity['container'], controller, identity['database'], statement, phase='override', readonly=False)
    row_after = row_json(run, identity['container'], controller, identity['database'], product_id, phase='override')
    after = table_hashes(run, identity['container'], controller, identity['database'], phase='override_hash')
    if changed_tables(before, after) != ['workspace_products'] or set(column_diff(row_before, row_after)) != {'is_active'}:
        raise CloneError('override', 'UNEXPECTED_DIFFERENCE')
    done('override_applied', changed_tables=['workspace_products'], column='is_active')
    prepared = copy.deepcopy(source['suite_copy']['prepared_tables'])
    snap = snapshot(new_fixture, enforce_counts=False)['tables']
    if set(snap) != set(prepared) or [t for t in prepared if snap[t] != prepared[t]] != ['workspace_products']:
        raise CloneError('verify', 'PREPARED_BASELINE_DIFFERENCE')
    prepared['workspace_products'] = snap['workspace_products']
    evidence = {
        'source_fixture_id': source['fixture_id'], 'source_container': db['container'], 'source_volume': db['volume'],
        'source_prepared_state_sha256': source['suite_copy']['prepared_state_sha256'],
        'source_lease': 'retained unchanged in the source fixture directory (consumed by run 3d9c2706-7e58-4979-8515-6fbc6cac9a1e)',
        'volume_tree_sha256': volume_checksum, 'public_tables_compared': len(before),
        'override': {'position_id': product_position, 'product_name': row_before['name'], 'table': 'workspace_products',
                     'column': 'is_active', 'from': False, 'to': True, 'statement_sha256': canonical_hash(statement),
                     'row_sha256_before': canonical_hash(row_before), 'row_sha256_after': canonical_hash(row_after),
                     'changed_tables': ['workspace_products'], 'changed_columns': ['is_active'],
                     'other_tables_identical': True, 'reference_values_changed': False,
                     'reason': 'plan product inactive in approved source data; BLE refuses plan-wide sample creation (run 3d9c2706)'},
        'created_at': datetime.now(timezone.utc).isoformat()}
    runtime_root = output / 'runtime'
    shutil.copytree(Path(source['suite_copy']['application_root']), runtime_root, ignore=shutil.ignore_patterns('logs'))
    manifest = build_manifest(source, identity, container_id, runtime_root, prepared, evidence)
    credential = load_credentials(source_controller_credentials, controller)
    connection = (f"Host=127.0.0.1;Port=55434;Database={identity['database']};Username={credential['username']};"
                  f"Password={credential['password']}")
    with (output / 'web.stdout.log').open('xb') as stdout, (output / 'web.stderr.log').open('xb') as stderr:
        process = popen([str(runtime_root / 'BLE.Web.exe'), '--urls', manifest['target_url'].rstrip('/')], cwd=runtime_root,
                        env=web_environment(environ, connection), stdout=stdout, stderr=stderr,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    for _ in range(120):
        try:
            current = verify_runtime(manifest['target_url'], runtime_root, manifest['identity_scope_check'])
            if current['pid'] == process.pid:
                break
        except Exception:
            pass
        sleep(1)
    else:
        raise CloneError('web', 'NOT_LISTENING')
    if any(current[k] != source['suite_copy']['runtime'][k] for k in ('assembly', 'sha256')):
        raise CloneError('web', 'RUNTIME_BINARY_MISMATCH')
    manifest['suite_copy']['web_pid'] = process.pid
    path = output / 'fixture-clone.json'
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    done('web_started', web_pid=process.pid, manifest=path.name)
    return path


def plan_clone(source_path, *, run=subprocess.run, product_position='P06'):
    """Read-only preflight: proves the source is unchanged and names what would be stopped."""
    source = json.loads(Path(source_path).resolve(strict=True).read_text(encoding='utf-8-sig'))
    runtime = preflight(source, run)
    return {'status': 'CLONE_PREFLIGHT_PASSED', 'model_calls': 0, 'database_writes': 0, 'source_fixture_id': source['fixture_id'],
            'would_stop_web_pid': runtime['pid'], 'would_stop_container': source['database']['container'],
            'override': {'position_id': product_position, 'column': 'workspace_products.is_active', 'to': True},
            'source_retained': ['volume', 'runtime directory', 'credentials', 'sessions', 'consumed lease']}

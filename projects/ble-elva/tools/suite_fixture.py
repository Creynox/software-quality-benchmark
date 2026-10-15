"""Owned, new NSN014 database copies only; no reset, reuse or model access."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import time
from uuid import uuid4

from sqbf.artifact_privacy import create_private_file
from sqbf.no_write_oracle import snapshot
from sqbf.oracle import verify_docker_identity
from sqbf.reporting import Evidence
from sqbf.session_credentials import load_credentials
from sqbf.scope_check import verify_runtime
from sqbf.suites import check_dataset, validate_suite, canonical_hash
from .lab_guard import validate_source


def validate_target(fixture):
    db = fixture['database']
    owned = fixture['suite_copy']
    if (fixture['target_url'] != 'http://127.0.0.1:5082/' or db['host_port'] != 55434
            or not re.fullmatch(r'sqbf-nsn014-[a-f0-9]{12}', db['container'])
            or db['name'] != db['container'].replace('-', '_')
            or db['volume'] != db['container'] + '-data'
            or not re.fullmatch(r'[a-f0-9]{64}', db['container_id'])
            or owned.get('disposable') is not True or owned.get('never_reset') is not True
            or not re.fullmatch(r'[a-f0-9]{64}', owned.get('golden_sha256', ''))
            or owned.get('source_database') != 'ble_benchmark_20261012'):
        raise ValueError('Owned suite copy identity required')


def _command(args, **kwargs):
    try:
        return subprocess.run(args, capture_output=True, check=True, timeout=60, **kwargs)
    except Exception:
        # Never forward process output that might contain credentials.
        raise RuntimeError('SUITE_FIXTURE_OPERATION_FAILED; inspect private state, no retry/reset') from None


def _protect_credentials(directory, filename, username, password):
    script = r"$c=[Console]::In.ReadToEnd()|ConvertFrom-Json;@{username=$c.username;password_dpapi=(ConvertTo-SecureString $c.password -AsPlainText -Force|ConvertFrom-SecureString)}|ConvertTo-Json -Compress"
    protected = _command(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
        input=json.dumps({'username': username, 'password': password}).encode(),
        env={k: v for k, v in os.environ.items() if k.lower() != 'psmodulepath'}).stdout
    path = directory / filename
    create_private_file(path)
    path.write_bytes(protected)


def create_base_copy(source, suite, dataset, output):
    """Copy synthetic golden schema/data; no original business DB dump.

    Restored copies are not run-ready and contain no measured samples. Provision
    state is durable before role/restore operations; failed copies are retained
    for inspection and must never be reused by this function.
    """
    if os.name != 'nt':
        raise ValueError('Windows DPAPI controller required')
    validate_source(source)
    validate_suite(suite)
    if (suite.get('suite_id') != 'ENZBERG-NSN014' or suite.get('version') not in ('0.2','0.3','0.4')
            or suite.get('benchmark_purpose') != 'ux_ui_process_stress'
            or suite['dataset_id'] != dataset['dataset_id']
            or check_dataset(dataset)['status'] != 'DATASET_APPROVED'):
        raise ValueError('Approved UX source-replay contract required')
    for port in (55434, 5082):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))
    before = snapshot(source)
    source_identity = verify_docker_identity(source)
    directory = Path(output)
    if any((p / '.git').exists() for p in directory.resolve().parents):
        raise ValueError('Private fixture must stay outside Git')
    Evidence(directory)
    suffix = uuid4().hex[:12]
    name = 'sqbf-nsn014-' + suffix
    database, volume = name.replace('-', '_'), name + '-data'
    names = _command(['docker', 'ps', '-a', '--format', '{{.Names}}']).stdout.decode().splitlines()
    volumes = _command(['docker', 'volume', 'ls', '--format', '{{.Name}}']).stdout.decode().splitlines()
    if name in names or volume in volumes:
        raise ValueError('Destination already exists')
    dump = _command(['docker', 'exec', source_identity['container_id'], 'pg_dump', '-Fc',
        '-U', source['database']['bootstrap_user'], '-d', source['database']['name']]).stdout
    (directory / 'golden.dump').write_bytes(dump)
    admin_password, oracle_password = secrets.token_hex(32), secrets.token_hex(32)
    _protect_credentials(directory, 'controller-credentials.dpapi.json', source['database']['bootstrap_user'], admin_password)
    _protect_credentials(directory, 'oracle-credentials.dpapi.json', 'sqbf_oracle_ro', oracle_password)
    envfile = directory / 'container.env'
    create_private_file(envfile)
    envfile.write_text('POSTGRES_USER=' + source['database']['bootstrap_user'] + '\nPOSTGRES_DB=' + database
                       + '\nPOSTGRES_PASSWORD=' + admin_password + '\n', encoding='utf-8')
    _command(['docker', 'volume', 'create', volume])
    try:
        result = _command(['docker', 'run', '-d', '--name', name, '--env-file', str(envfile),
            '-p', '127.0.0.1:55434:5432', '-v', volume + ':/var/lib/postgresql/data', source['database']['image']])
    finally:
        envfile.unlink()
    fixture = copy.deepcopy(source)
    fixture['database'].update(container=name, container_id=result.stdout.decode().strip(),
        name=database, volume=volume, host_port=55434, host_binding='127.0.0.1:55434')
    fixture.update(fixture_id='nsn014-ux-' + suffix, target_url='http://127.0.0.1:5082/',
                   status='BASE_COPY_CREATED_NOT_POPULATED', suite_id=suite['suite_id'], suite_version=suite['version'])
    fixture['suite_copy'] = {'source_database': source['database']['name'], 'source_snapshot': before,
        'golden_sha256': hashlib.sha256(dump).hexdigest(), 'disposable': True, 'never_reset': True,
        'dataset_sha256': check_dataset(dataset)['content_sha256'], 'suite_sha256': canonical_hash(suite),
        'stage': 'container_created', 'measured_samples_preseeded': False}
    path = directory / 'fixture.json'
    path.write_text(json.dumps(fixture, indent=2), encoding='utf-8')
    validate_target(fixture)
    for _ in range(30):
        ready = subprocess.run(['docker', 'exec', fixture['database']['container_id'], 'pg_isready',
            '-h', '127.0.0.1', '-U', source['database']['bootstrap_user'], '-d', database], capture_output=True, timeout=5)
        if ready.returncode == 0:
            break
        time.sleep(.5)
    else:
        raise RuntimeError('NEW_SUITE_DB_NOT_READY; no retry/reset')
    target = verify_docker_identity(fixture)
    sql = "CREATE ROLE sqbf_oracle_ro LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD '" + oracle_password + "';"
    _command(['docker', 'exec', '-i', target['container_id'], 'psql', '-X', '-q', '-U',
        source['database']['bootstrap_user'], '-d', database, '-v', 'ON_ERROR_STOP=1'], input=sql.encode())
    _command(['docker', 'exec', '-i', target['container_id'], 'pg_restore', '--exit-on-error', '--no-owner',
        '-U', source['database']['bootstrap_user'], '-d', database], input=dump)
    copied = snapshot(fixture)
    if copied['tables'] != before['tables'] or snapshot(source) != before:
        raise RuntimeError('COPY_OR_SOURCE_MISMATCH; no reset')
    fixture['status'] = 'BASE_COPY_VERIFIED_NOT_POPULATED'
    fixture['suite_copy']['stage'] = 'restored_verified'
    fixture['oracle_credential_file'] = str(directory / 'oracle-credentials.dpapi.json')
    path.write_text(json.dumps(fixture, indent=2), encoding='utf-8')
    return path


def complete_inspected_empty_copy(path, source):
    """Explicit controller recovery of a verified EMPTY new copy, not a retry.

    Docker's initial temporary socket server can be ready before its final TCP
    server. Require no restored table and no Oracle role before any write. If
    anything was partially applied this recovery is forbidden, with no reset.
    """
    path = Path(path)
    fixture = json.loads(path.read_text(encoding='utf-8'))
    validate_source(source); validate_target(fixture)
    if fixture['suite_copy']['stage'] != 'container_created':
        raise ValueError('Inspected empty provisioning stage required')
    identity = verify_docker_identity(fixture)
    db = fixture['database']
    sql = "BEGIN READ ONLY; SELECT count(*) FROM pg_roles WHERE rolname='sqbf_oracle_ro'; SELECT count(*) FROM information_schema.tables WHERE table_schema='public'; ROLLBACK;"
    result = _command(['docker', 'exec', '-i', identity['container_id'], 'psql', '-X', '-q', '-At',
        '-U', db['bootstrap_user'], '-d', db['name'], '-v', 'ON_ERROR_STOP=1'], input=sql.encode())
    if result.stdout.decode().split() != ['0', '0']:
        raise ValueError('Nonempty or partially provisioned target; recovery forbidden')
    dump = (path.parent / 'golden.dump').read_bytes()
    if hashlib.sha256(dump).hexdigest() != fixture['suite_copy']['golden_sha256']:
        raise ValueError('Golden dump changed')
    if snapshot(source) != fixture['suite_copy']['source_snapshot']:
        raise ValueError('Source changed')
    credentials = load_credentials(path.parent / 'oracle-credentials.dpapi.json', 'sqbf_oracle_ro')
    password = credentials['password']
    if not re.fullmatch('[a-f0-9]{64}', password):
        raise ValueError('Unexpected generated credential format')
    sql = "CREATE ROLE sqbf_oracle_ro LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD '" + password + "';"
    _command(['docker', 'exec', '-i', identity['container_id'], 'psql', '-X', '-q', '-U',
        db['bootstrap_user'], '-d', db['name'], '-v', 'ON_ERROR_STOP=1'], input=sql.encode())
    _command(['docker', 'exec', '-i', identity['container_id'], 'pg_restore', '--exit-on-error', '--no-owner',
        '-U', db['bootstrap_user'], '-d', db['name']], input=dump)
    copied = snapshot(fixture)
    if copied['tables'] != fixture['suite_copy']['source_snapshot']['tables'] or snapshot(source) != fixture['suite_copy']['source_snapshot']:
        raise RuntimeError('COPY_OR_SOURCE_MISMATCH; no reset')
    fixture['status'] = 'BASE_COPY_VERIFIED_NOT_POPULATED'
    fixture['suite_copy']['stage'] = 'restored_verified'
    fixture['suite_copy']['provisioning_finding'] = 'Temporary PostgreSQL socket readiness preceded final server; corrected TCP readiness.'
    fixture['oracle_credential_file'] = str(path.parent / 'oracle-credentials.dpapi.json')
    path.write_text(json.dumps(fixture, indent=2), encoding='utf-8')
    return path


def compile_prepared_plan(context, dataset, fixture, available):
    """Compile inserts for ten products/one plan only; no measurement seeding."""
    validate_target(fixture)
    if check_dataset(dataset)['status'] != 'DATASET_APPROVED':
        raise ValueError('Approved source replay required')
    source_products = {row['id']: row for row in context['products']}
    if len(source_products) != 10 or len(context['products']) != 10 or len(context['plan']) != 1 or len(context['items']) != 10:
        raise ValueError('Exact ten-position source context required')
    selected = {p['inputs']['product_id']: p for p in dataset['positions']}
    if set(selected) != set(source_products):
        raise ValueError('Source context differs from approved dataset')
    for key, table in [('material_class_id', 'classes'), ('product_type_id', 'types')]:
        allowed = {row['id'] for row in available[table] if row['active'] is True}
        if any(row[key] not in allowed for row in source_products.values()):
            raise ValueError('Missing/inactive existing classification; no fallback')
    plan = context['plan'][0]
    if any(row['sampling_plan_id'] != plan['id'] or row['product_id'] not in selected
           or row.get('rezept_version_id') is not None for row in context['items']):
        raise ValueError('Wrong plan relation or unsupported recipe reference')
    if len({row['product_id'] for row in context['items']}) != 10:
        raise ValueError('Duplicate plan position')
    available_versions = {row['id'] for row in available['versions']}
    required_versions = {row['norm_version_id'] for row in context['assignments']}
    if any(row['product_id'] not in selected for row in context['assignments']):
        raise ValueError('Unexpected product assignment')
    missing = [row for row in context['versions'] if row['id'] not in available_versions]
    if (required_versions - available_versions != {row['id'] for row in missing}
            or any(row.get('previous_version_id') not in (None, *available_versions) for row in missing)):
        raise ValueError('Incomplete existing standard-version snapshot')
    # New UUIDs avoid any source tenant/product/plan cross-reference.
    mapping = {key: str(uuid4()) for key in selected}
    new_plan_id = str(uuid4())
    tenant, plant = fixture['fixture_data']['tenant_id'], fixture['fixture_data']['plant_id']
    rows = []
    def insert(table, value):
        payload = json.dumps(value, ensure_ascii=False, allow_nan=False).replace("'", "''")
        rows.append("INSERT INTO " + table + " SELECT * FROM json_populate_record(NULL::" + table + ", '" + payload + "'::json);")
    parent_ids = {row['norm_id'] for row in missing} - set(available['standard_ids'])
    parents = context.get('existing_standard_parents', [])
    if parent_ids != {row['id'] for row in parents}:
        raise ValueError('Missing exact existing historical standard parent; no inferred edition')
    for row in parents:
        insert('norm_standards', row)
    for row in missing:
        insert('norm_versions', row)
    for old_id, row in source_products.items():
        if row['name'] != selected[old_id]['product']:
            raise ValueError('Product name changed since source approval')
        product = dict(row)
        product.update(id=mapping[old_id], plant_id=plant, tenant_id=tenant, laboratory_id=None,
                       norm_limit_set_id=None, created_at='2026-10-14T00:00:00Z', updated_at=None,
                       description='Isolated SQBF source-replay product; no original database writes.', tags=None)
        insert('workspace_products', product)
    plan_row = dict(plan)
    plan_row.update(id=new_plan_id, plant_id=plant, tenant_id=tenant, laboratory_id=None,
                    created_by='sqbf-fixture-controller', updated_by=None)
    insert('sampling_plans', plan_row)
    for item in context['items']:
        item = dict(item)
        item.update(id=str(uuid4()), sampling_plan_id=new_plan_id, product_id=mapping[item['product_id']],
                    created_by='sqbf-fixture-controller')
        insert('sampling_plan_items', item)
    for assignment in context['assignments']:
        assignment = dict(assignment)
        assignment.update(id=str(uuid4()), product_id=mapping[assignment['product_id']])
        insert('product_norm_version_assignments', assignment)
    guard = """DO $$ BEGIN
IF (SELECT count(*) FROM workspace_products)<>0 OR (SELECT count(*) FROM sampling_plans)<>0
 OR (SELECT count(*) FROM samples)<>0 OR (SELECT count(*) FROM lims_sample)<>0
 OR (SELECT count(*) FROM ble_reports)<>0 THEN RAISE EXCEPTION 'TARGET_NOT_EMPTY'; END IF;
END $$;"""
    sql = 'BEGIN;\nSET LOCAL statement_timeout=\'10s\';\n' + guard + '\n' + '\n'.join(rows) + '\nCOMMIT;'
    return sql, {'products': mapping, 'plan_id': new_plan_id, 'positions': {
        p['position_id']: mapping[p['inputs']['product_id']] for p in dataset['positions']},
        'expected_products': 10, 'expected_plan_items': 10, 'expected_assignments': len(context['assignments']),
        'copied_existing_version_ids': [row['id'] for row in missing]}


def provision_personas(path, context, password_helper, lead_credential_path):
    """Three new synthetic accounts; existing lead and role matrix unchanged."""
    path = Path(path)
    fixture = json.loads(path.read_text(encoding='utf-8'))
    validate_target(fixture)
    if fixture['suite_copy']['stage'] != 'products_plan_prepared':
        raise ValueError('Prepared suite stage required; no re-provisioning')
    target = verify_docker_identity(fixture)
    database = fixture['database']
    active_roles = {r['name']: r['id'] for r in context['roles'] if r['active'] is True}
    legacy_roles = {r['name']: r['id'] for r in context['identity_roles']}
    tenant, plant = fixture['fixture_data']['tenant_id'], fixture['fixture_data']['plant_id']
    assignments = [('laboratory_staff', 'sqbf-labormitarbeiter', 'Mitarbeiter'),
                   ('wpk_lead', 'sqbf-wpk', 'Laborleiter'), ('plant_lead', 'sqbf-werkleitung', 'Viewer')]
    actors, statements = {}, []
    def insert(table, row):
        payload = json.dumps(row, ensure_ascii=False).replace("'", "''")
        statements.append("INSERT INTO " + table + " SELECT * FROM json_populate_record(NULL::" + table + ", '" + payload + "'::json);")
    for persona, username, role in assignments:
        if role not in active_roles or role not in legacy_roles:
            raise ValueError('Existing active role required; no role/permission seed')
        password = 'S!9' + secrets.token_urlsafe(32)
        result = _command(['dotnet', str(Path(password_helper).resolve(strict=True))],
                          input=json.dumps({'username': username, 'password': password}).encode())
        hashed = json.loads(result.stdout)['password_hash']
        user_id = str(uuid4())
        insert('identity_users', {'id': user_id, 'display_name': 'SQBF ' + persona,
            'user_name': username, 'normalized_user_name': username.upper(), 'email': username + '@example.invalid',
            'normalized_email': (username + '@example.invalid').upper(), 'email_confirmed': True,
            'password_hash': hashed, 'security_stamp': uuid4().hex, 'concurrency_stamp': uuid4().hex,
            'is_admin': False, 'is_active': True, 'tenant_id': tenant, 'phone_number': None,
            'phone_number_confirmed': False, 'two_factor_enabled': False, 'lockout_enabled': True,
            'lockout_end': None, 'access_failed_count': 0, 'last_login_at_utc': None})
        insert('identity_user_roles', {'user_id': user_id, 'role_id': legacy_roles[role]})
        insert('security_user_roles', {'id': str(uuid4()), 'user_id': user_id, 'role_id': active_roles[role],
            'organization_id': None, 'project_id': None, 'is_active': True,
            'created_at': '2026-10-15T00:00:00Z', 'updated_at': None})
        for scope_type, key, plant_id in [('Tenant', tenant, None), ('Plant', plant, plant)]:
            insert('security_user_data_scopes', {'id': str(uuid4()), 'user_id': user_id,
                'scope_type': scope_type, 'scope_key': key, 'tenant_id': tenant, 'werk_id': plant_id,
                'customer_id': None, 'laboratory_id': None, 'granted_by_user_id': None,
                'is_active': True, 'created_at': '2026-10-15T00:00:00Z', 'updated_at': None})
        filename = username + '-credentials.dpapi.json'
        _protect_credentials(path.parent, filename, username, password)
        actors[persona] = {'username': username, 'user_id': user_id, 'role': role,
            'tenant_id': tenant, 'plant_id': plant, 'credential_file': filename,
            'allowed_permissions': sorted(p['permission'] for p in context['permissions'] if p['role'] == role)}
    lead = fixture['fixture_data']
    credentials = load_credentials(lead_credential_path, lead['laboratory_lead_account'])
    filename = 'sqbf-laborleitung-credentials.dpapi.json'
    _protect_credentials(path.parent, filename, credentials['username'], credentials['password'])
    actors['laboratory_lead'] = {'username': lead['laboratory_lead_account'],
        'user_id': lead['laboratory_lead_user_id'], 'role': 'Laborleiter', 'tenant_id': tenant,
        'plant_id': plant, 'credential_file': filename,
        'allowed_permissions': sorted(p['permission'] for p in context['permissions'] if p['role'] == 'Laborleiter')}
    # Guard in the same transaction: any existing account blocks all inserts.
    guard = """DO $$ BEGIN IF EXISTS(SELECT 1 FROM identity_users WHERE user_name IN
('sqbf-labormitarbeiter','sqbf-wpk','sqbf-werkleitung')) THEN RAISE EXCEPTION 'PERSONAS_ALREADY_EXIST'; END IF; END $$;"""
    sql = 'BEGIN;\nSET LOCAL statement_timeout=\'10s\';\n' + guard + '\n' + '\n'.join(statements) + '\nCOMMIT;'
    _command(['docker', 'exec', '-i', target['container_id'], 'psql', '-X', '-q', '-U',
        database['bootstrap_user'], '-d', database['name'], '-v', 'ON_ERROR_STOP=1'], input=sql.encode())
    fixture['personas'] = actors
    fixture['suite_copy']['stage'] = 'personas_provisioned'
    fixture['status'] = 'PRODUCTS_PLAN_PERSONAS_READY_SESSIONS_PENDING'
    path.write_text(json.dumps(fixture, indent=2), encoding='utf-8')
    return actors


def start_suite_web(path, source_root, source_runtime):
    """Separate content root/cookie discriminator; exact accepted binaries."""
    path = Path(path)
    fixture = json.loads(path.read_text(encoding='utf-8'))
    validate_target(fixture)
    if fixture['suite_copy']['stage'] != 'personas_provisioned':
        raise ValueError('Personas must be provisioned; no automatic restart')
    verify_docker_identity(fixture)
    source_root = Path(source_root).resolve(strict=True)
    config = fixture['identity_scope_check']
    current = verify_runtime('http://127.0.0.1:5081/', source_root, config)
    if current['sha256'] != source_runtime['sha256'] or current['assembly'] != source_runtime['assembly']:
        raise ValueError('Accepted source build changed')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 5082))
    runtime = path.parent / 'runtime'
    # Only compiled output and public static assets; never source, sessions,
    # databases, original settings files or authentication key rings.
    shutil.copytree(source_root / Path(config['assembly']).parent, runtime,
                    ignore=shutil.ignore_patterns('appsettings*.json', 'logs'))
    shutil.copytree(source_root / 'wwwroot', runtime / 'wwwroot', dirs_exist_ok=True)
    original_dll = source_root / config['assembly']
    if hashlib.sha256((runtime / 'BLE.Web.dll').read_bytes()).hexdigest() != current['sha256']:
        raise ValueError('Runtime copy changed')
    settings = json.loads((source_root / 'appsettings.json').read_text(encoding='utf-8-sig'))
    settings['Sentry'] = {'Dsn': ''}
    settings.pop('ConnectionStrings', None)
    settings['AllowedHosts'] = '127.0.0.1'
    settings.setdefault('Wpk', {}).setdefault('Scheduler', {})['Enabled'] = False
    weather = settings.setdefault('GeoWeather', {})
    for provider in ('BrightSky', 'OpenMeteo', 'Nominatim', 'Elevation'):
        weather.setdefault(provider, {})['Enabled'] = False
    settings.setdefault('Ble', {})['DisableStartupSeeding'] = True
    (runtime / 'appsettings.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    manifest = runtime / 'BLE.Web.staticwebassets.runtime.json'
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        data['ContentRoots'] = [str(runtime / 'wwwroot') if Path(root).resolve() == (source_root / 'wwwroot').resolve()
                                else root for root in data['ContentRoots']]
        manifest.write_text(json.dumps(data), encoding='utf-8')
    credential = load_credentials(path.parent / 'controller-credentials.dpapi.json', fixture['database']['bootstrap_user'])
    db = fixture['database']
    connection = f"Host=127.0.0.1;Port=55434;Database={db['name']};Username={credential['username']};Password={credential['password']}"
    env = {k: v for k, v in os.environ.items() if k.upper() not in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY')
           and not k.lower().startswith(('connectionstrings', 'sentry', 'geoweather', 'wpk__', 'dataprotection'))}
    env.update(ASPNETCORE_ENVIRONMENT='Development', Ble__DisableStartupSeeding='true',
               ConnectionStrings__DefaultConnection=connection, ConnectionStrings__DevelopmentCloneConnection=connection,
               Sentry__Dsn='', Wpk__Scheduler__Enabled='false', DOTNET_CLI_TELEMETRY_OPTOUT='1')
    with (path.parent / 'web.stdout.log').open('xb') as stdout, (path.parent / 'web.stderr.log').open('xb') as stderr:
        process = subprocess.Popen([str(runtime / 'BLE.Web.exe'), '--urls', fixture['target_url'].rstrip('/')],
            cwd=runtime, env=env, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
    fixture['identity_scope_check'].update(executable='BLE.Web.exe', assembly='BLE.Web.dll')
    fixture['suite_copy'].update(stage='web_started', web_pid=process.pid, application_root=str(runtime),
        runtime=current, isolation_overrides=['startup seeding disabled', 'WPK background scheduler disabled',
                                              'Sentry disabled', 'external geo/weather providers disabled'])
    fixture['status'] = 'WEB_STARTED_SESSIONS_PENDING'
    path.write_text(json.dumps(fixture, indent=2), encoding='utf-8')
    return process.pid


def provision_required_context(path):
    """Prepare only synthetic required customer/project; samples owned by plant.

    Mirrors the actual Create UI's required context. Laboratory ownership is a
    different branch and is not implied by a laboratory employee's role.
    """
    path = Path(path)
    fixture = json.loads(path.read_text(encoding='utf-8'))
    validate_target(fixture)
    if fixture['suite_copy'].get('preparation_context'):
        raise ValueError('Context already provisioned; no re-seed')
    target = verify_docker_identity(fixture)
    tenant, plant = fixture['fixture_data']['tenant_id'], fixture['fixture_data']['plant_id']
    for value in (tenant, plant):
        from uuid import UUID
        if str(UUID(value)) != value: raise ValueError('Canonical fixture IDs required')
    customer, project = str(uuid4()), str(uuid4())
    sql = f"""BEGIN; SET LOCAL statement_timeout='5s';
DO $$ BEGIN IF (SELECT count(*) FROM customers)<>0 OR (SELECT count(*) FROM projects)<>0
 OR (SELECT count(*) FROM samples)<>0 OR (SELECT count(*) FROM lims_sample)<>0
 OR (SELECT count(*) FROM ble_reports)<>0
 OR NOT EXISTS(SELECT 1 FROM workspace_plants WHERE id='{plant}'::uuid AND tenant_id='{tenant}'::uuid
 AND customer_id IS NULL) THEN RAISE EXCEPTION 'CONTEXT_ALREADY_SET_OR_UNEXPECTED'; END IF; END $$;
INSERT INTO customers(id,name,tenant_id,created_at) VALUES('{customer}'::uuid,'SQBF Enzberg','{tenant}'::uuid,now());
INSERT INTO projects(id,customer_id,name,location,created_at) VALUES('{project}'::uuid,'{customer}'::uuid,'SQBF NSN 014','Enzberg',now());
UPDATE workspace_plants SET customer_id='{customer}'::uuid WHERE id='{plant}'::uuid AND tenant_id='{tenant}'::uuid AND customer_id IS NULL;
GRANT SELECT ON customers,projects TO sqbf_oracle_ro;
COMMIT;"""
    db = fixture['database']
    _command(['docker', 'exec', '-i', target['container_id'], 'psql', '-X', '-q', '-U',
              db['bootstrap_user'], '-d', db['name'], '-v', 'ON_ERROR_STOP=1'], input=sql.encode())
    fixture['fixture_data'].update(customer_id=customer, project_id=project)
    fixture['read_only_oracle']['expected_counts'].update(customers=1, projects=1)
    fixture['suite_copy']['preparation_context'] = {'customer': 'SQBF Enzberg', 'project': 'SQBF NSN 014',
        'sample_owner': 'Werk Enzberg', 'real_contacts': False,
        'lab_owner_not_required': 'Laboratory selector applies only to Laboratory-owned samples.'}
    snapshot(fixture)
    path.write_text(json.dumps(fixture, indent=2), encoding='utf-8')
    return path

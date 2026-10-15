"""Replay of existing product configuration into an isolated fixture copy.

Pre-test finding (scratch dry run, 15.10.2026): the fixture had no rows in lims_product_test_modules,
so BLE reported "AGGREGATE_* ist fuer das Produkt nicht aktiv" and locked the measurement forms of
the stages PREPARATION to SE. The source database holds 51 activation rows for the ten plan
products. They are product configuration, not measured data: ids are derived deterministically,
product ids are mapped to the fixture products and the catalog module is mapped by its code (the
catalog ids differ between the source and the golden copy). Rows are copied unchanged otherwise.

A second dry-run finding: the fixture lacked the 37 product-specific rows of workspace_sampling_rules.
BLE builds the allocation cards ("Entnahmen": label, sieve size, target amount) of the sieve page from
them, so PREPARATION offered 2 of 9 approved allocation fields and SHAPE stayed empty ("Bitte zuerst
Entnahmen mit Kornform-Fraktionen anlegen"). They are replayed the same way; the 28 generic rules stay.
Not replayed (documented): product_characteristic_requirements (needs 8 further category rows),
workspace_test_plan_templates (source plant id), recipes and one issue decision.
"""
import json
import re
import subprocess
from uuid import NAMESPACE_URL, UUID, uuid5

UUID_PATTERN = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
TABLE = 'lims_product_test_modules'
RULES_TABLE = 'workspace_sampling_rules'
COLUMNS = ('id', 'product_id', 'test_module_id', 'is_mandatory', 'is_default_active', 'comment', 'default_config_json')


class ReplayError(RuntimeError):
    pass


def _psql(run, container, user, database, sql, *, readonly=True, timeout=120):
    body = ('BEGIN TRANSACTION READ ONLY;\n' + sql.rstrip(';') + ';\nROLLBACK;') if readonly else sql
    result = run(['docker', 'exec', '-i', container, 'psql', '-X', '-q', '-At', '-U', user, '-d', database, '-v', 'ON_ERROR_STOP=1'],
                 input=body, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    if result.returncode != 0:
        raise ReplayError('psql failed')
    return result.stdout


def collect_source_modules(source_product_ids, *, run=subprocess.run, container='ble-postgres', user='claude_dev', database='ble'):
    """READ ONLY: activation rows of the given source products with the catalog code of their module."""
    if not source_product_ids or any(not UUID_PATTERN.fullmatch(i) for i in source_product_ids):
        raise ReplayError('SOURCE_PRODUCT_IDS_INVALID')
    ids = ','.join("'" + i + "'" for i in sorted(source_product_ids))
    out = _psql(run, container, user, database,
                "SELECT coalesce(json_agg(json_build_object('id',p.id,'product_id',p.product_id,'module_code',m.code,'is_mandatory',p.is_mandatory,"
                "'is_default_active',p.is_default_active,'comment',p.comment,'default_config_json',p.default_config_json) ORDER BY m.code,p.id),'[]'::json) "
                "FROM lims_product_test_modules p JOIN lims_test_modules m ON m.id=p.test_module_id WHERE p.product_id IN (" + ids + ")")
    return json.loads(out.strip())


def collect_target_catalog(fixture, *, run=subprocess.run):
    db = fixture['database']
    out = _psql(run, db['container'], db['bootstrap_user'], db['name'], "SELECT coalesce(json_object_agg(code,id),'{}'::json) FROM lims_test_modules")
    return json.loads(out.strip())


def plan_rows(source_rows, product_map, catalog):
    """Rows for the fixture: deterministic new id, mapped product, catalog module by code; nothing else changes."""
    planned = []
    for row in source_rows:
        if row['product_id'] not in product_map:
            raise ReplayError('PRODUCT_NOT_IN_FIXTURE')
        if row['module_code'] not in catalog:
            raise ReplayError('MODULE_CODE_NOT_IN_CATALOG ' + row['module_code'])
        planned.append({'id': str(uuid5(NAMESPACE_URL, 'sqbf-nsn014/' + TABLE + '/' + row['id'])), 'product_id': product_map[row['product_id']],
                        'test_module_id': catalog[row['module_code']], 'is_mandatory': row['is_mandatory'],
                        'is_default_active': row['is_default_active'], 'comment': row['comment'],
                        'default_config_json': row['default_config_json']})
    if len({r['id'] for r in planned}) != len(planned) or len({(r['product_id'], r['test_module_id']) for r in planned}) != len(planned):
        raise ReplayError('DUPLICATE_ACTIVATION')
    return planned


ROLE = re.compile(r'[a-z][a-z0-9_]{0,62}')


def insert_sql(planned, oracle_role):
    if not ROLE.fullmatch(oracle_role):
        raise ReplayError('ORACLE_ROLE_INVALID')
    for row in planned:
        if not (UUID_PATTERN.fullmatch(row['id']) and UUID_PATTERN.fullmatch(row['product_id']) and UUID_PATTERN.fullmatch(row['test_module_id'])):
            raise ReplayError('ID_INVALID')
    payload = json.dumps(planned, ensure_ascii=False, allow_nan=False).replace("'", "''")
    return ("BEGIN;\nDO $$ BEGIN IF (SELECT count(*) FROM public." + TABLE + ")<>0 THEN RAISE EXCEPTION 'TARGET_NOT_EMPTY'; END IF; END $$;\n"
            "INSERT INTO public." + TABLE + " (" + ','.join(COLUMNS) + ") SELECT " + ','.join('r.' + c for c in COLUMNS)
            + " FROM json_populate_recordset(NULL::public." + TABLE + ", '" + payload + "'::json) r;\n"
            "DO $$ BEGIN IF (SELECT count(*) FROM public." + TABLE + ")<>" + str(len(planned)) + " THEN RAISE EXCEPTION 'ROWCOUNT_MISMATCH'; END IF; END $$;\n"
            # The SELECT-only oracle must be able to read the table the protected baseline now covers.
            "GRANT SELECT ON public." + TABLE + " TO " + oracle_role + ";\nCOMMIT;")


def replay(fixture, *, run=subprocess.run):
    """Insert the activation rows into the fixture copy (controller role); returns an evidence record without values."""
    product_map = fixture['suite_copy']['mapping']['products']
    source_rows = collect_source_modules(list(product_map), run=run)
    if not source_rows:
        raise ReplayError('NO_SOURCE_ACTIVATIONS')
    planned = plan_rows(source_rows, product_map, collect_target_catalog(fixture, run=run))
    db = fixture['database']
    _psql(run, db['container'], db['bootstrap_user'], db['name'], insert_sql(planned, db['oracle_role']), readonly=False)
    per_module = {}
    for row in source_rows:
        per_module[row['module_code']] = per_module.get(row['module_code'], 0) + 1
    return {'table': TABLE, 'rows': len(planned), 'per_module': dict(sorted(per_module.items())),
            'with_default_config': sum(1 for r in planned if r['default_config_json']),
            'ids': 'uuid5(sqbf-nsn014/' + TABLE + '/<source id>)', 'product_ids': 'mapped to fixture products',
            'module_ids': 'mapped by catalog code', 'source': 'normal local BLE database, READ ONLY'}


def collect_source_rules(source_product_ids, *, run=subprocess.run, container='ble-postgres', user='claude_dev', database='ble'):
    """READ ONLY: product-specific sampling rules (all columns) of the given source products."""
    if not source_product_ids or any(not UUID_PATTERN.fullmatch(i) for i in source_product_ids):
        raise ReplayError('SOURCE_PRODUCT_IDS_INVALID')
    ids = ','.join("'" + i + "'" for i in sorted(source_product_ids))
    out = _psql(run, container, user, database,
                "SELECT coalesce(json_agg(to_jsonb(r) ORDER BY r.id),'[]'::json) FROM " + RULES_TABLE + " r WHERE r.product_id IN (" + ids + ")")
    return json.loads(out.strip())


def plan_rule_rows(source_rows, product_map, material_class_ids):
    planned = []
    for row in source_rows:
        if row['product_id'] not in product_map:
            raise ReplayError('PRODUCT_NOT_IN_FIXTURE')
        if row.get('material_class_id') and row['material_class_id'] not in material_class_ids:
            raise ReplayError('MATERIAL_CLASS_NOT_IN_FIXTURE')
        planned.append(dict(row, id=str(uuid5(NAMESPACE_URL, 'sqbf-nsn014/' + RULES_TABLE + '/' + row['id'])), product_id=product_map[row['product_id']]))
    if len({r['id'] for r in planned}) != len(planned):
        raise ReplayError('DUPLICATE_RULE')
    return planned


def rules_insert_sql(planned, product_ids, oracle_role):
    if not ROLE.fullmatch(oracle_role):
        raise ReplayError('ORACLE_ROLE_INVALID')
    if any(not (UUID_PATTERN.fullmatch(r['id']) and UUID_PATTERN.fullmatch(r['product_id'])) for r in planned) or any(
            not UUID_PATTERN.fullmatch(i) for i in product_ids):
        raise ReplayError('ID_INVALID')
    listed = ','.join("'" + i + "'" for i in sorted(product_ids))
    payload = json.dumps(planned, ensure_ascii=False, allow_nan=False).replace("'", "''")
    return ("BEGIN;\nDO $$ BEGIN IF (SELECT count(*) FROM public." + RULES_TABLE + " WHERE product_id IN (" + listed + "))<>0 THEN RAISE EXCEPTION 'TARGET_NOT_EMPTY'; END IF; END $$;\n"
            "INSERT INTO public." + RULES_TABLE + " SELECT * FROM json_populate_recordset(NULL::public." + RULES_TABLE + ", '" + payload + "'::json);\n"
            "DO $$ BEGIN IF (SELECT count(*) FROM public." + RULES_TABLE + " WHERE product_id IN (" + listed + "))<>" + str(len(planned)) + " THEN RAISE EXCEPTION 'ROWCOUNT_MISMATCH'; END IF; END $$;\n"
            "GRANT SELECT ON public." + RULES_TABLE + " TO " + oracle_role + ";\nCOMMIT;")


def replay_rules(fixture, *, run=subprocess.run):
    product_map = fixture['suite_copy']['mapping']['products']
    source_rows = collect_source_rules(list(product_map), run=run)
    if not source_rows:
        raise ReplayError('NO_SOURCE_RULES')
    db = fixture['database']
    classes = set(json.loads(_psql(run, db['container'], db['bootstrap_user'], db['name'],
                                   "SELECT coalesce(json_agg(id),'[]'::json) FROM material_classes").strip()))
    planned = plan_rule_rows(source_rows, product_map, classes)
    _psql(run, db['container'], db['bootstrap_user'], db['name'], rules_insert_sql(planned, list(product_map.values()), db['oracle_role']), readonly=False)
    total = int(_psql(run, db['container'], db['bootstrap_user'], db['name'], 'SELECT count(*) FROM ' + RULES_TABLE).strip())
    per_process = {}
    for row in source_rows:
        per_process[row['process_type']] = per_process.get(row['process_type'], 0) + 1
    return {'table': RULES_TABLE, 'rows': len(planned), 'table_rows_after': total, 'per_process_type': dict(sorted(per_process.items())),
            'ids': 'uuid5(sqbf-nsn014/' + RULES_TABLE + '/<source id>)', 'product_ids': 'mapped to fixture products',
            'other_columns': 'unchanged', 'source': 'normal local BLE database, READ ONLY'}


def replay_all(fixture, *, run=subprocess.run):
    """Both configuration replays; evidence per table (no values)."""
    modules = replay(fixture, run=run)
    modules['table_rows_after'] = modules['rows']
    return {'tables': {TABLE: modules, RULES_TABLE: replay_rules(fixture, run=run)}}

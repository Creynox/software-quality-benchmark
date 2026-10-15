"""Read-only independent probe-registration oracle; never run by a model."""
import json
import subprocess

from sqbf.oracle import verify_docker_identity
from .suite_fixture import validate_target


def collect_receipts(fixture, *, run=subprocess.run):
    validate_target(fixture)
    target = verify_docker_identity(fixture, run=run)
    db = fixture['database']
    sql = """BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='5s';
SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));
SELECT json_build_object('kind','samples','rows',(SELECT coalesce(json_agg(json_build_object(
 'id',s.id,'sample_code',s.sample_code,'tenant_id',s.tenant_id,'plant_id',s.plant_id,'laboratory_id',s.laboratory_id,
 'product_id',s.product_id,'customer_id',s.customer_id,'project_id',s.project_id,
 'taken_date',(s.taken_at AT TIME ZONE 'Europe/Berlin')::date,'sampling_plan_item_id',s.sampling_plan_item_id,
 'created_by',s.created_by) ORDER BY s.sample_code),'[]'::json) FROM samples s));
SELECT json_build_object('kind','lims','rows',(SELECT coalesce(json_agg(json_build_object(
 'id',l.id,'probe_id',l.probe_id,'product_id',l.product_id,'project_id',l.project_id) ORDER BY l.id),'[]'::json) FROM lims_sample l));
SELECT json_build_object('kind','plan_items','rows',(SELECT coalesce(json_agg(json_build_object(
 'id',p.id,'product_id',p.product_id,'plan_id',p.sampling_plan_id) ORDER BY p.id),'[]'::json) FROM sampling_plan_items p));
ROLLBACK;"""
    result = run(['docker','exec','-i',target['container_id'],'psql','-X','-q','-At',
        '-U',db['oracle_role'],'-d',db['name'],'-v','ON_ERROR_STOP=1'],
        input=sql,capture_output=True,text=True,check=True,timeout=10)
    rows = list(map(json.loads, result.stdout.splitlines()))
    identity = rows[0]
    if identity != {'database':db['name'],'role':db['oracle_role'],'read_only':'on'}:
        raise ValueError('Read-only Oracle identity mismatch')
    records = {row['kind']:row['rows'] for row in rows[1:]}
    if set(records) != {'samples','lims','plan_items'}:
        raise ValueError('Incomplete receipt projection')
    return records


def verify_receipts(records, dataset, fixture, *, phase):
    """Source-derived inputs and correct probe/LIMS FKs, not a norm verdict."""
    result = {'status':'BLOCKED_RECEIPT_EVIDENCE','model_calls':0,'database_writes':0}
    try:
        validate_target(fixture)
        if phase not in ('before','after','after_plan','after_modules'):
            raise ValueError('Explicit phase required')
        samples, lims, items = [records[key] for key in ('samples','lims','plan_items')]
        expected = {row['inputs']['sample_code']:row for row in dataset['positions']}
        if len(expected) != 10 or len(items) != 10:
            return dict(result, reason='REFERENCE_OR_PLAN_COUNT_MISMATCH')
        item_ids = {row['product_id']:row['id'] for row in items
                    if row['plan_id'] == fixture['suite_copy']['mapping']['plan_id']}
        if len(item_ids) != 10 or set(item_ids) != set(fixture['suite_copy']['mapping']['positions'].values()):
            return dict(result, reason='PLAN_PRODUCT_RELATION_MISMATCH')
        if phase == 'before':
            return dict(result,status='RECEIPT_START_VERIFIED' if not samples and not lims else 'BLOCKED_RECEIPT_EVIDENCE',
                        sample_count=len(samples),lims_count=len(lims))
        actual = {row['sample_code']:row for row in samples}
        if len(actual) != len(samples) or set(actual)-set(expected):
            return dict(result,status='FAIL',reason='EXTRA_OR_DUPLICATE_PROBE',sample_count=len(samples))
        failures, missing = [], []
        for code, source in expected.items():
            key = source['position_id']; row = actual.get(code)
            if row is None:
                missing.append(key); continue
            product = fixture['suite_copy']['mapping']['positions'][key]
            linked = [l for l in lims if l['probe_id'] == row['id']]
            needs_lims=(phase=='after' or phase=='after_modules' and any(
                bool(r.get('series')) for r in source['inputs'].get('derived_and_repetitions',[]) if isinstance(r,dict)))
            valid = (row['tenant_id'] == fixture['fixture_data']['tenant_id']
                and row['plant_id'] == fixture['fixture_data']['plant_id'] and row['laboratory_id'] is None
                and row['product_id'] == product and row['customer_id'] == fixture['fixture_data']['customer_id']
                and row['project_id'] == fixture['fixture_data']['project_id']
                and row['taken_date'] == dataset['reference']['sampling_date']
                and row['sampling_plan_item_id'] == item_ids[product]
                and (len(linked)==1 if needs_lims else len(linked)<=1)
                and all(l['product_id']==product and l['project_id']==fixture['fixture_data']['project_id'] for l in linked))
            if not valid: failures.append(key)
        orphan = any(l['probe_id'] not in {s['id'] for s in samples} for l in lims)
        complete = not missing and not failures and not orphan and len(samples)==10 and (len(lims)==10 if phase=='after' else len(lims)<=10)
        return dict(result,status='PASS' if complete else 'FAIL',sample_count=len(samples),lims_count=len(lims),
                    missing_positions=missing,mismatched_positions=failures,orphan_lims=orphan,
                    limitations=['No normative certification; related module/result persistence is checked by separate stages.'])
    except (KeyError, TypeError, ValueError, AttributeError):
        return dict(result,reason='INCOMPLETE_OR_CONTRADICTORY_PROJECTION')


def collect_plan_products(fixture, *, run=subprocess.run):
    """Flags BLE's sample creation checks per product of the plan; no names, no values."""
    validate_target(fixture)
    target = verify_docker_identity(fixture, run=run)
    db = fixture['database']
    data = fixture['fixture_data']
    sql = """BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='5s';
SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));
SELECT coalesce(json_agg(json_build_object('product_id',p.id,'is_active',p.is_active,
 'use_area_set',p.use_area IS NOT NULL,'product_level_set',p.product_level IS NOT NULL,
 'owner_ok',(p.tenant_id::text='__TENANT__' AND p.plant_id::text='__PLANT__' AND p.laboratory_id IS NULL),
 'standard_assignments',(SELECT count(*) FROM product_norm_version_assignments a WHERE a.product_id=p.id)) ORDER BY p.id),'[]'::json)
FROM workspace_products p WHERE p.id IN (SELECT product_id FROM sampling_plan_items);
ROLLBACK;""".replace('__TENANT__', str(data['tenant_id'])).replace('__PLANT__', str(data['plant_id']))
    result = run(['docker','exec','-i',target['container_id'],'psql','-X','-q','-At',
        '-U',db['oracle_role'],'-d',db['name'],'-v','ON_ERROR_STOP=1'],
        input=sql,capture_output=True,text=True,check=True,timeout=10)
    rows = list(map(json.loads, result.stdout.splitlines()))
    if len(rows) != 2 or rows[0] != {'database':db['name'],'role':db['oracle_role'],'read_only':'on'}:
        raise ValueError('Read-only Oracle identity mismatch')
    return rows[1]


def verify_plan_products(rows, fixture):
    """Every plan product must be one BLE can carry a new sample for (live run 3d9c2706 precondition).

    BLE refuses the whole plan-wide creation if one product is inactive or lacks use area or
    level, so this is a fixture precondition, not product behaviour under test.
    """
    blocked = {'status': 'BLOCKED_PLAN_PRODUCT_EVIDENCE', 'model_calls': 0, 'database_writes': 0}
    try:
        by_product = {row['product_id']: row for row in rows}
        if len(by_product) != len(rows):
            return dict(blocked, reason='DUPLICATE_PRODUCT_ROW')
        issues = []
        for position, product in sorted(fixture['suite_copy']['mapping']['positions'].items()):
            row = by_product.get(product)
            if row is None:
                return dict(blocked, reason='PLAN_PRODUCT_MISSING', position_id=position)
            reasons = [name for name, bad in (
                ('PRODUCT_INACTIVE', row['is_active'] is not True),
                ('USE_AREA_MISSING', row['use_area_set'] is not True),
                ('PRODUCT_LEVEL_MISSING', row['product_level_set'] is not True),
                ('OWNER_SCOPE_MISMATCH', row['owner_ok'] is not True),
                ('NO_STANDARD_ASSIGNMENT', not row['standard_assignments'])) if bad]
            if reasons:
                issues.append({'position_id': position, 'reasons': reasons})
        if len(by_product) != len(fixture['suite_copy']['mapping']['positions']):
            return dict(blocked, reason='UNEXPECTED_PLAN_PRODUCT_COUNT')
        return {'status': 'PLAN_PRODUCTS_BLOCKED' if issues else 'PLAN_PRODUCTS_CREATABLE', 'positions_checked': len(by_product),
                'blocked_positions': issues, 'model_calls': 0, 'database_writes': 0}
    except (KeyError, TypeError, AttributeError):
        return dict(blocked, reason='INCOMPLETE_PLAN_PRODUCT_EVIDENCE')

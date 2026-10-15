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

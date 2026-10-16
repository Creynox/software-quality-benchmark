"""Read-only numeric allocation projection; no source masses are invented."""
import json
import subprocess
from uuid import UUID
from sqbf.suites import canonical_hash
from sqbf.oracle import verify_docker_identity
from sqbf.no_write_oracle import snapshot
from .suite_fixture import validate_target
from .measurement_oracle import _canonical


def view_sql(fixture):
    validate_target(fixture)
    tenant=str(UUID(fixture['fixture_data']['tenant_id']));plant=str(UUID(fixture['fixture_data']['plant_id']))
    return """BEGIN; SET LOCAL statement_timeout='5s';
DO $$ BEGIN IF (SELECT count(*) FROM samples)<>0 OR (SELECT count(*) FROM lims_sample)<>0
THEN RAISE EXCEPTION 'UNUSED_FIXTURE_REQUIRED'; END IF; END $$;
CREATE VIEW public.sqbf_allocation_inputs_v1 AS
SELECT s.sample_code,s.product_id,i.target_process,i.target_sieve_mm,i.actual_amount_g,i.material_source_kind
FROM public.samples s JOIN public.workspace_sampling_info i ON i.sample_id=s.id
WHERE s.tenant_id='__TENANT__'::uuid AND s.plant_id='__PLANT__'::uuid AND i.actual_amount_g IS NOT NULL;
GRANT SELECT ON public.sqbf_allocation_inputs_v1 TO sqbf_oracle_ro; COMMIT;""".replace('__TENANT__',tenant).replace('__PLANT__',plant)


def collect_allocations(fixture, *, run=subprocess.run):
    validate_target(fixture);target=verify_docker_identity(fixture,run=run);db=fixture['database']
    snapshot(fixture,run=run,enforce_counts=False)
    sql="""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL statement_timeout='5s';
SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));
SELECT coalesce(json_agg(json_build_object('sample_code',sample_code,'product_id',product_id,'target_process',target_process,
'target_sieve_mm',target_sieve_mm,'actual_amount_g',actual_amount_g,'material_source_kind',material_source_kind)),'[]'::json)
FROM public.sqbf_allocation_inputs_v1; ROLLBACK;"""
    r=run(['docker','exec','-i',target['container_id'],'psql','-X','-q','-At','-U',db['oracle_role'],'-d',db['name'],
        '-v','ON_ERROR_STOP=1'],input=sql,capture_output=True,text=True,check=True,timeout=10)
    rows=list(map(json.loads,r.stdout.splitlines()))
    if len(rows)!=2 or rows[0]!={'database':db['name'],'role':db['oracle_role'],'read_only':'on'}:raise ValueError()
    return rows[1]


def _value(row):
    return json.dumps(_canonical({k:row[k] for k in ('target_process','target_sieve_mm','actual_amount_g','material_source_kind')}),sort_keys=True)


def prerequisite_gaps(records,projection,allocation_reference,target_process):
    """Positions whose reference allocations of one target process (with a recorded actual amount) are not all persisted exactly as approved.

    Evidence for the classification of derived values, not an Oracle verdict: BLE derives the preparation mass of the partial sieve from the
    allocation of the pan material (target process Siebanalyse), and stores 0 when that allocation was never captured (guarded dry run with
    replayed provider faults, 16.10.2026). A deviation of such a value says nothing about BLE while its input is missing.
    """
    codes={p['sample_code']:p['position_id'] for p in projection['positions']}
    wanted={p['position_id']:sorted(_value(r) for r in p['allocations'] if r['actual_amount_g'] is not None and r['target_process']==target_process)
            for p in allocation_reference['positions']}
    actual={key:[] for key in wanted}
    for row in records:
        key=codes.get(row['sample_code'])
        if key in actual and row['target_process']==target_process:actual[key].append(_value(row))
    return {key for key in wanted if sorted(actual[key])!=wanted[key]}


def verify_allocations(records,projection,allocation_reference,fixture):
    blocked={'status':'BLOCKED_ALLOCATION_EVIDENCE','model_calls':0,'database_writes':0}
    try:
        validate_target(fixture)
        if canonical_hash(allocation_reference)!=fixture['suite_copy']['allocation_reference_sha256']:
            return dict(blocked,reason='ALLOCATION_REFERENCE_CHANGED')
        if canonical_hash(projection)!=fixture['suite_copy']['measurement_reference_sha256']:
            return dict(blocked,reason='MEASUREMENT_REFERENCE_CHANGED')
        positions={p['position_id']:p for p in projection['positions']}
        allocation_positions={p['position_id']:p for p in allocation_reference['positions']}
        if len(positions)!=10 or set(positions)!=set(allocation_positions):raise ValueError()
        codes={p['sample_code']:key for key,p in positions.items()}
        value=_value
        wanted={key:sorted(value(r) for r in p['allocations'] if r['actual_amount_g'] is not None) for key,p in allocation_positions.items()}
        actual={key:[] for key in positions}
        for row in records:
            key=codes[row['sample_code']]
            if row['product_id']!=fixture['suite_copy']['mapping']['positions'][key]:raise ValueError()
            actual[key].append(value(row))
        mismatches=[key for key in positions if sorted(actual[key])!=wanted[key]]
        return {'status':'FAIL' if mismatches else 'PASS','mismatched_positions':mismatches,
                'expected_recorded_allocations':sum(len(v) for v in wanted.values()),'model_calls':0,'database_writes':0}
    except (ValueError,TypeError,KeyError,AttributeError):
        return dict(blocked,reason='INCOMPLETE_OR_WRONG_RELATION')

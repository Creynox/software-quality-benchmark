"""Independent read-only measurement evidence, outside every UI/model process.

The view exposes numeric source inputs and sample relations only. Free-form
metadata, credentials, claims, personnel, notes and computed verdicts are absent.
"""
import json
import subprocess
from decimal import Decimal, InvalidOperation
from uuid import UUID
from sqbf.oracle import verify_docker_identity
from sqbf.suites import canonical_hash
from .suite_fixture import validate_target

VIEW='sqbf_measurement_inputs_v1'
KINDS={'wash','shape','boiling','boiling_repetitions','sand','sieves','preparation','partial_series'}


def view_sql(fixture):
    validate_target(fixture)
    tenant=str(UUID(fixture['fixture_data']['tenant_id']))
    plant=str(UUID(fixture['fixture_data']['plant_id']))
    # All relation names and expressions are repository-owned constants.
    return """BEGIN; SET LOCAL statement_timeout='5s';
DO $$ BEGIN IF (SELECT count(*) FROM samples)<>0 OR (SELECT count(*) FROM lims_sample)<>0
OR (SELECT count(*) FROM ble_reports)<>0 THEN RAISE EXCEPTION 'UNUSED_FIXTURE_REQUIRED'; END IF; END $$;
CREATE VIEW public.sqbf_measurement_inputs_v1 AS
WITH owned AS (SELECT s.id,s.sample_code,s.product_id FROM public.samples s
 WHERE s.tenant_id='__TENANT__'::uuid AND s.plant_id='__PLANT__'::uuid),
facts AS (
 SELECT s.id probe_id,'wash'::text kind,jsonb_build_object(
 'container_g',r.container_mass_g,'container_wet_g',r.container_plus_wet_mass_g,
 'container_dry_g',r.container_plus_dry_mass_g,'container_washed_g',r.container_plus_washed_dry_mass_g) inputs
 FROM owned s JOIN public.lims_agg_uf_fine_tests r ON r.sample_id=s.id
 WHERE r.container_mass_g IS NOT NULL OR r.container_plus_wet_mass_g IS NOT NULL
 OR r.container_plus_dry_mass_g IS NOT NULL OR r.container_plus_washed_dry_mass_g IS NOT NULL
 UNION ALL SELECT s.id,'shape',jsonb_build_object('fraction',i.label,
 'total_g',r.total_weight_g,'poor_g',r.poor_shape_weight_g)
 FROM owned s JOIN public.workspace_particle_shape_fraction_results r ON r.sample_id=s.id
 JOIN public.workspace_sampling_info i ON i.id=r.sampling_info_id AND i.sample_id=s.id
 WHERE r.total_weight_g IS NOT NULL OR r.poor_shape_weight_g IS NOT NULL
 UNION ALL SELECT s.id,'boiling',jsonb_build_object('initial_g',r.weight_before_boiling_g,
 'final_g',r.weight_after_boiling_g,'marl_g',r.damaged_grains_weight_g)
 FROM owned s JOIN public.workspace_boiling_test_results r ON r.sample_id=s.id
 WHERE r.weight_before_boiling_g IS NOT NULL OR r.weight_after_boiling_g IS NOT NULL OR r.damaged_grains_weight_g IS NOT NULL
 UNION ALL SELECT s.id,'boiling_repetitions',jsonb_build_object('order',(rep->>'sortOrder')::int,
 'minutes',(rep->>'kochzeitMin')::numeric,'initial_g',(rep->>'einwaageVorKochen')::numeric,
 'final_g',(rep->>'rueckwaageNachKochen')::numeric)
 FROM owned s JOIN public.workspace_work_items w ON w.sample_id=s.id
 CROSS JOIN LATERAL jsonb_array_elements(w.metadata_json::jsonb->'repetitions') rep
 WHERE w.module_key='AGGREGATE_MARL_CONTENT' AND (rep->>'einwaageVorKochen' IS NOT NULL OR rep->>'rueckwaageNachKochen' IS NOT NULL)
 UNION ALL SELECT s.id,'sand',jsonb_build_object('order',(rep->>'sortOrder')::int,
 'sand_height_mm',(rep->>'sandHeightMm')::numeric,'suspension_height_mm',(rep->>'suspensionHeightMm')::numeric)
 FROM owned s JOIN public.workspace_work_items w ON w.sample_id=s.id
 CROSS JOIN LATERAL jsonb_array_elements(w.metadata_json::jsonb->'repetitions') rep
 WHERE w.module_key='AGGREGATE_SAND_EQUIVALENT' AND (rep->>'sandHeightMm' IS NOT NULL OR rep->>'suspensionHeightMm' IS NOT NULL)
 UNION ALL SELECT s.id,'sieves',jsonb_build_object('input_g',r.input_weight_g,
 'split_mm',r.teilsiebung_split_mm,'partial_input_g',r.teilsiebung_einwaage_g,
 'points',(SELECT coalesce(jsonb_agg(jsonb_build_object('sieve_mm',p.sieve_size_mm,
 'partial',p.is_partial_sieve,'retained_g',p.retained_weight_g) ORDER BY p.sort_order),'[]'::jsonb)
 FROM public.lims_sieblinie_punkt p WHERE p.sieve_analysis_result_id=r.id))
 FROM owned s JOIN public.lims_sieblinie_ergebnis r ON r.sample_id=s.id
 WHERE r.input_weight_g IS NOT NULL
 UNION ALL SELECT s.id,'preparation',jsonb_build_object('taken_g',d.taken_mass,'dry_g',d.dried_mass)
 FROM owned s JOIN public.lims_sample l ON l.probe_id=s.id
 JOIN public.lims_sample_derived_test_step d ON d.sample_id=l.id
 WHERE d.taken_mass IS NOT NULL OR d.dried_mass IS NOT NULL
 UNION ALL SELECT s.id,'partial_series',jsonb_build_object('order',r.series_order,
 'initial_g',r.initial_mass,'dry_g',r.dried_mass,
 'points',(SELECT coalesce(jsonb_agg(jsonb_build_object('sieve_mm',p.sieve_size_mm,
 'pan',p.is_pan,'retained_g',p.residue_mass) ORDER BY p.sort_order),'[]'::jsonb)
 FROM public.lims_sample_derived_sieve_result p WHERE p.result_series_id=r.id))
 FROM owned s JOIN public.lims_sample l ON l.probe_id=s.id
 JOIN public.lims_sample_derived_test_step d ON d.sample_id=l.id
 JOIN public.lims_sample_derived_test_result_series r ON r.sample_derived_test_step_id=d.id
 WHERE r.initial_mass IS NOT NULL OR r.dried_mass IS NOT NULL
)
SELECT s.id probe_id,s.sample_code,s.product_id,f.kind,f.inputs FROM owned s JOIN facts f ON f.probe_id=s.id;
GRANT SELECT ON public.sqbf_measurement_inputs_v1 TO sqbf_oracle_ro;
COMMIT;""".replace('__TENANT__',tenant).replace('__PLANT__',plant)


def collect_inputs(fixture, *, run=subprocess.run):
    validate_target(fixture);target=verify_docker_identity(fixture,run=run);db=fixture['database']
    from sqbf.no_write_oracle import snapshot
    snapshot(fixture,run=run,enforce_counts=False)  # Includes role-wide no-write/no-create/no-bypass checks.
    sql="""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='5s';
SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));
SELECT coalesce(json_agg(json_build_object('sample_code',sample_code,'product_id',product_id,
'kind',kind,'inputs',inputs) ORDER BY sample_code,kind,inputs::text),'[]'::json)
FROM public.sqbf_measurement_inputs_v1;
ROLLBACK;"""
    result=run(['docker','exec','-i',target['container_id'],'psql','-X','-q','-At','-U',db['oracle_role'],
        '-d',db['name'],'-v','ON_ERROR_STOP=1'],input=sql,capture_output=True,text=True,check=True,timeout=10)
    rows=list(map(json.loads,result.stdout.splitlines()))
    if len(rows)!=2 or rows[0]!={'database':db['name'],'role':db['oracle_role'],'read_only':'on'}:
        raise ValueError('Independent read-only measurement identity failed')
    return rows[1]


def _canonical(value):
    if isinstance(value,dict):return {k:_canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,list):return [_canonical(v) for v in value]
    if value is None or type(value) is bool:return value
    try:
        number=Decimal(str(value))
        if not number.is_finite():raise ValueError('Nonfinite input')
        return format(number.normalize(),'f')
    except InvalidOperation:
        if not isinstance(value,str):raise ValueError('Invalid input')
        return value


def verify_inputs(records, projection, fixture, *, kinds):
    """Compare raw inputs only; return identifiers, never the underlying inputs."""
    blocked={'status':'BLOCKED_MEASUREMENT_EVIDENCE','model_calls':0,'database_writes':0}
    try:
        validate_target(fixture)
        if canonical_hash(projection)!=fixture['suite_copy'].get('measurement_reference_sha256'):
            return dict(blocked,reason='REFERENCE_PROJECTION_CHANGED')
        if not isinstance(kinds,(set,list,tuple)) or not kinds or not set(kinds)<=KINDS:
            return dict(blocked,reason='UNKNOWN_MEASUREMENT_SCOPE')
        positions=projection['positions'];codes={r['sample_code']:r for r in positions}
        if len(codes)!=10 or len(positions)!=10:raise ValueError()
        actual={code:{k:[] for k in kinds} for code in codes}
        for row in records:
            code=row['sample_code']
            if code not in codes or row['product_id']!=fixture['suite_copy']['mapping']['positions'][codes[code]['position_id']]:
                return dict(blocked,reason='WRONG_SAMPLE_PRODUCT_RELATION')
            if row['kind'] not in KINDS:raise ValueError()
            if row['kind'] in kinds:actual[code][row['kind']].append(row['inputs'])
        mismatches=[];checked=0
        for code,position in codes.items():
            for kind in kinds:
                expected=position['measurements'][kind]
                found=actual[code][kind]
                # Repetition/series order is meaningful, independent query order isn't.
                if kind in ('sand','partial_series'):
                    found=sorted(found,key=lambda row:row['order'])
                    if len({r['order'] for r in found})!=len(found):raise ValueError()
                    found=[{k:v for k,v in r.items() if k!='order'} for r in found]
                    if kind=='partial_series':
                        # Series A/B must match the original ordered series.
                        expected=list(expected)
                def packed(rows, unordered=True):
                    canonical=[json.dumps(_canonical(row),sort_keys=True) for row in rows]
                    return sorted(canonical) if unordered else canonical
                if packed(expected,kind not in ('sand','partial_series'))!=packed(found,kind not in ('sand','partial_series')):
                    mismatches.append({'position_id':position['position_id'],'kind':kind})
                checked+=1
        return {'status':'FAIL' if mismatches else 'PASS','checks':checked,'mismatches':mismatches,
                'model_calls':0,'database_writes':0,'normative_conformity_scoring':False}
    except (ValueError,TypeError,KeyError,AttributeError):
        return dict(blocked,reason='INCOMPLETE_OR_CONTRADICTORY_INPUTS')

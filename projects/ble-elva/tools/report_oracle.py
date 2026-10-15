"""Non-official report and PDF evidence; never a normative release verdict."""
import json
import subprocess
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from sqbf.oracle import verify_docker_identity
from sqbf.no_write_oracle import snapshot
from sqbf.suites import canonical_hash
from .suite_fixture import validate_target


def collect_reports(fixture, *, run=subprocess.run):
    validate_target(fixture);target=verify_docker_identity(fixture,run=run);db=fixture['database']
    snapshot(fixture,run=run,enforce_counts=False)
    # Project explicit numeric/identity keys only. No full snapshot, notes or actors.
    sql="""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL statement_timeout='5s';
SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));
SELECT coalesce(json_agg(json_build_object('id',id,'probe_id',primary_probe_id,'tenant_id',tenant_id,
'plant_id',plant_id,'laboratory_id',laboratory_id,'is_official',is_official,'status',status,
'snapshot',json_build_object('probe_id',snapshot_json::jsonb->>'probeId','sample_code',snapshot_json::jsonb->>'probencode',
'product',snapshot_json::jsonb->>'produktName','plant',snapshot_json::jsonb->>'werkName',
'is_official',snapshot_json::jsonb->'isOfficial','sieve_input_g',snapshot_json::jsonb#>'{siebanalyse,einwaageProbenmenge}',
'dry_g',snapshot_json::jsonb#>'{ufFine,dryMassGramm}','washed_g',snapshot_json::jsonb#>'{ufFine,washedDryMassGramm}',
'shape_total_g',snapshot_json::jsonb#>'{kornform,einwaageGesamt}','shape_poor_g',snapshot_json::jsonb#>'{kornform,einwaageSchlechtGeformt}',
'boiling_initial_g',snapshot_json::jsonb#>'{kochversuch,einwaageVorKochen}',
'boiling_final_g',snapshot_json::jsonb#>'{kochversuch,rueckwaageNachKochen}',
'sand_a_mm',snapshot_json::jsonb#>'{sandAequivalent,bestimmungASandHeightMm}',
'suspension_a_mm',snapshot_json::jsonb#>'{sandAequivalent,bestimmungASuspensionHeightMm}',
'sand_b_mm',snapshot_json::jsonb#>'{sandAequivalent,bestimmungBSandHeightMm}',
'suspension_b_mm',snapshot_json::jsonb#>'{sandAequivalent,bestimmungBSuspensionHeightMm}'))),'[]'::json)
FROM public.ble_reports; ROLLBACK;"""
    r=run(['docker','exec','-i',target['container_id'],'psql','-X','-q','-At','-U',db['oracle_role'],'-d',db['name'],
        '-v','ON_ERROR_STOP=1'],input=sql,capture_output=True,text=True,check=True,timeout=10)
    rows=list(map(json.loads,r.stdout.splitlines()))
    if len(rows)!=2 or rows[0]!={'database':db['name'],'role':db['oracle_role'],'read_only':'on'}:raise ValueError()
    return rows[1]


def expected_numbers(position):
    raw=position['measurements'];expected={}
    if len(raw['sieves'])==1:expected['sieve_input_g']=raw['sieves'][0]['input_g']
    if len(raw['wash'])==1:
        row=raw['wash'][0]
        expected.update(dry_g=Decimal(row['container_dry_g'])-Decimal(row['container_g']),
                        washed_g=Decimal(row['container_washed_g'])-Decimal(row['container_g']))
    if raw['shape']:
        expected.update(shape_total_g=sum(Decimal(r['total_g']) for r in raw['shape']),
                        shape_poor_g=sum(Decimal(r['poor_g']) for r in raw['shape']))
    if len(raw['boiling'])==1:
        expected.update(boiling_initial_g=raw['boiling'][0]['initial_g'],boiling_final_g=raw['boiling'][0]['final_g'])
    if len(raw['sand'])==2:
        a,b=raw['sand'];expected.update(sand_a_mm=a['sand_height_mm'],suspension_a_mm=a['suspension_height_mm'],
                                       sand_b_mm=b['sand_height_mm'],suspension_b_mm=b['suspension_height_mm'])
    return expected


def verify_reports(records,receipts,projection,fixture,downloads):
    blocked={'status':'BLOCKED_REPORT_EVIDENCE','model_calls':0,'database_writes':0}
    try:
        validate_target(fixture)
        if canonical_hash(projection)!=fixture['suite_copy'].get('measurement_reference_sha256'):
            return dict(blocked,reason='REFERENCE_CHANGED')
        positions={r['sample_code']:r for r in projection['positions']};probes={p['id']:p for p in receipts['samples']}
        if len(positions)!=10 or len(probes)!=len(receipts['samples']):raise ValueError()
        seen=set();failures=[];checked=[]
        for report in records:
            probe=probes[report['probe_id']];position=positions[probe['sample_code']];key=position['position_id']
            if probe['id'] in seen:return dict(blocked,reason='DUPLICATE_OR_UNEXPECTED_REPORT')
            seen.add(probe['id']);snap=report['snapshot']
            files=[d for d in downloads if d['report_id']==report['id']]
            valid=(report['tenant_id']==fixture['fixture_data']['tenant_id'] and report['plant_id']==fixture['fixture_data']['plant_id']
                and report['laboratory_id'] is None and report['is_official'] is False and report['status']=='Draft' and snap['is_official'] is False
                and probe['tenant_id']==fixture['fixture_data']['tenant_id'] and probe['plant_id']==fixture['fixture_data']['plant_id']
                and snap['probe_id']==probe['id'] and snap['sample_code']==probe['sample_code']
                and snap['product']==position['product'] and snap['plant']=='Enzberg'
                and probe['product_id']==fixture['suite_copy']['mapping']['positions'][key]
                and len(files)==1 and files[0].get('pdf_integrity')=='PASS')
            mismatched=[]
            for name,expected in expected_numbers(position).items():
                actual=snap.get(name)
                # Report UI uses up to two decimal places for masses/heights.
                numeric=Decimal(str(actual)) if actual is not None else None
                if numeric is None or not numeric.is_finite() or numeric.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)!=Decimal(str(expected)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP):
                    mismatched.append(name)
            if not valid or mismatched:failures.append({'position_id':key,'numeric_fields':mismatched,'relations_pdf_valid':valid})
            checked.append(key)
        missing=sorted(set(p['position_id'] for p in positions.values())-set(checked))
        unknown_files=any(d['report_id'] not in {r['id'] for r in records} for d in downloads)
        return {'status':'PASS' if not failures and not missing and not unknown_files else 'FAIL',
                'report_count':len(records),'missing_positions':missing,'failures':failures,
                'unexpected_download':unknown_files,'model_calls':0,'database_writes':0,'normative_release':False}
    except (ValueError,TypeError,KeyError,AttributeError,InvalidOperation):
        return dict(blocked,reason='INCOMPLETE_OR_WRONG_REPORT_RELATION')

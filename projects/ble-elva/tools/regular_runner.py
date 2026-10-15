"""NSN014 suite orchestration; no implicit live execution or automatic retry.

Objective case statuses (scoring nsn014-objective-v1): PASS, FAIL, BLOCKED,
INVALID (reported as INVALID_HARNESS), INCONCLUSIVE, NOT_RUN, NOT_IMPLEMENTED.
UX scores (rubric nsn014-ux-rubric-v1) are a separate, provisional layer and never
compensate a safety or data fault. There is no global percentage.
"""
import copy
import importlib.metadata
import json
import os
import subprocess
from pathlib import Path
import time
from uuid import uuid4

from sqbf.artifact_privacy import check_private_directory, create_private_file
from sqbf.bounded import invoke_worker, model_spec, restore_model, BudgetExceeded
from sqbf.calibration import SuiteBudget, ResourceStop
from sqbf.models import Scenario
from sqbf.reporting import Evidence, now_iso, index_run
from sqbf.suites import suite_check, canonical_hash, aggregate, validate_suite, comparison_key
from sqbf.smoke_runner import ACTION_SCHEMA
from sqbf.no_write_oracle import snapshot
from sqbf.scope_check import verify_runtime
from .allocation_oracle import collect_allocations, verify_allocations
from .calculation_oracle import collect_report_calculations, persisted_basis, verify_calculations, expected_calculations
from .measurement_guard import make_contract
from .measurement_oracle import collect_inputs, verify_inputs, KINDS, PERSISTED_NAMES
from .report_oracle import collect_reports, verify_reports, expected_numbers
from .receipt_oracle import collect_receipts, verify_receipts
from .suite_acceptance import check_fixture
from .persona_scope import check_persona
from .measurement_runner import run_measurements, required_saves
from .inspection_runner import run_inspection, run_reports, run_plan_creation, ENTRY_PATHS
from .receipt_contract_check import check_receipt_form, check_entry_routes
from .stage_support import (REVIEW_SCHEMA, SCORING_VERSION, RUBRIC_VERSION, CATEGORIES, SEVERITIES, DIMENSIONS,
                            valid_review)

CASE_KINDS={'NSN014-PREPARATION':['allocations','wash'],'NSN014-SIEVE':['sieve','partial'],
            'NSN014-SHAPE':['shape'],'NSN014-BOILING':['boiling'],'NSN014-SE':['sand']}
READ_CASES={'NSN014-RECEIPT','NSN014-ASSESS','NSN014-WPK','NSN014-ANALYSIS','NSN014-RIGHTS'}
CASE_IDS=READ_CASES|set(CASE_KINDS)|{'NSN014-PLAN','NSN014-REPORT'}
MUTABLE_TABLES={'samples','lims_sample','ble_reports','sqbf_measurement_inputs_v1','sqbf_allocation_inputs_v1'}
REPOSITORY=Path(__file__).resolve().parents[3]
SOURCE_PATHS=('sqbf','projects')
OBJECTIVE_STATUS={'INVALID':'INVALID_HARNESS'}


def objective_status(result):
    return OBJECTIVE_STATUS.get(result,result)


def static_fixture_unchanged(fixture,current):
    baseline=fixture['suite_copy']['prepared_tables']
    if canonical_hash(baseline)!=fixture['suite_copy']['prepared_state_sha256']:return False
    return set(baseline)==set(current['tables']) and all(current['tables'][k]==v for k,v in baseline.items() if k not in MUTABLE_TABLES)


def atomic_json(path,data):
    """Parent is already private; replace avoids a truncated kill-time ledger."""
    path=Path(path);temporary=path.with_name('.'+path.name+'-'+uuid4().hex+'.tmp')
    with temporary.open('x',encoding='utf-8') as output:
        json.dump(data,output,ensure_ascii=False,indent=2)
        output.flush();os.fsync(output.fileno())
    temporary.replace(path)


def load_inputs(suite_path,dataset_path,fixture_path,projection_path,allocation_path):
    paths=[suite_path,dataset_path,fixture_path,projection_path,allocation_path]
    suite,dataset,fixture,projection,allocation=[json.loads(Path(p).read_text(encoding='utf-8-sig')) for p in paths]
    root=Path(fixture_path).resolve(strict=True).parent
    for actor in fixture['personas'].values():
        for key in ('storage_state','credential_file'):
            path=Path(actor[key]);actor[key]=str(path if path.is_absolute() else root/path)
    return suite,dataset,fixture,projection,allocation


def source_state(*,run=subprocess.run):
    """Executed SQBF code must be a commit; local edits would make the run unreproducible."""
    git=['git','-C',str(REPOSITORY)]
    commit=run(git+['rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    changes=run(git+['status','--porcelain','--',*SOURCE_PATHS],capture_output=True,text=True,check=True,timeout=10).stdout
    return {'commit':commit,'clean':not changes.strip(),'checked_paths':list(SOURCE_PATHS)}


def persona_context(suite,fixture):
    """Role and permission set per persona; no user names, IDs or credentials."""
    context={}
    for persona in suite['personas']:
        permissions=sorted(fixture['personas'][persona]['allowed_permissions'])
        context[persona]={'role':fixture['personas'][persona].get('role'),'allowed_permissions':permissions,
                          'permissions_sha256':canonical_hash(permissions),
                          'cases':[c['case_id'] for c in suite['cases'] if c['persona']==persona]}
    return context


def route_probes(suite,fixture):
    """One model-free entry probe per persona and stage entry route."""
    routes={}
    for case in suite['cases']:
        key=case['case_id']
        if key in ENTRY_PATHS:path=ENTRY_PATHS[key](fixture)
        elif key in CASE_KINDS or key=='NSN014-REPORT':path='/samples'
        else:continue  # NSN014-PLAN: native plan form check covers the lead entry.
        routes.setdefault((case['persona'],path),[]).append(key)
    return [(persona,path,stages) for (persona,path),stages in routes.items()]


def _measurement_tasks(case_kinds,projection,allocation):
    allocated={p['position_id']:p['allocations'] for p in allocation['positions']}
    for source in projection['positions']:
        position=dict(source,allocations=allocated[source['position_id']])
        for kind in case_kinds:
            rawkind={'sieve':'sieves','partial':'partial_series'}.get(kind,kind)
            if kind=='allocations':
                if not any(r['actual_amount_g'] is not None for r in position['allocations']):continue
            elif not position['measurements'][rawkind]:continue
            yield position,kind


def stage_contracts(suite,projection,allocation,fixture):
    """Model-free build of every stage contract from the approved reference.

    Builds each measurement field contract, each report expectation and each
    recomputation, and round-trips the reference through the persisted-view
    vocabulary into the measurement Oracle. A schema mismatch here would
    otherwise surface only during a live run, as a controller error or a false FAIL.
    """
    placeholder='00000000-0000-0000-0000-000000000000';step='measurement_contracts'
    try:
        tasks=0
        for key,kinds in CASE_KINDS.items():
            for position,kind in _measurement_tasks(kinds,projection,allocation):
                make_contract(fixture,placeholder,position,kind);tasks+=1
        step='report_expectations'
        for position in projection['positions']:expected_numbers(position)
        step='vocabulary_roundtrip'
        inverse={kind:{v:k for k,v in names.items()} for kind,names in PERSISTED_NAMES.items()}
        records=[]
        for position in projection['positions']:
            product=fixture['suite_copy']['mapping']['positions'][position['position_id']]
            for kind in sorted(KINDS):
                for order,row in enumerate(position['measurements'][kind],start=1):
                    row={inverse.get(kind,{}).get(k,k):v for k,v in row.items()}
                    if kind in ('sand','partial_series'):row=dict(row,order=order)
                    records.append({'sample_code':position['sample_code'],'product_id':product,'kind':kind,'inputs':row})
        roundtrip=verify_inputs(records,projection,fixture,kinds=KINDS)
        if roundtrip['status']!='PASS':return {'status':'BLOCKED_STAGE_CONTRACTS','step':step,'oracle':roundtrip.get('reason') or roundtrip['status']}
        step='recomputation'
        basis=persisted_basis(records)
        computed=sum(len(expected_calculations(measurements)) for measurements in basis.values())
        return {'status':'STAGE_CONTRACTS_VERIFIED','measurement_tasks':tasks,'report_positions':len(projection['positions']),
                'vocabulary_roundtrip':'PASS','roundtrip_checks':roundtrip['checks'],'recomputed_result_groups':computed}
    except (KeyError,ValueError,TypeError,AttributeError) as error:
        return {'status':'BLOCKED_STAGE_CONTRACTS','step':step,'error_type':type(error).__name__}


def estimate_requests(suite,projection,allocation,fixture):
    """Lower bound of model requests for one complete attempt; not a forecast.

    Per measurement module: focus+type per approved field, every required save,
    sample navigation and the terminal action, plus one review. Inspections need at
    least one navigation, a terminal action and one review. Reports need navigation,
    generation, report opening, download, the terminal action, one review and at
    least one PDF review batch per position.
    """
    placeholder='00000000-0000-0000-0000-000000000000'
    per_case={}
    for case in suite['cases']:
        key=case['case_id'];requests=0
        if key in CASE_KINDS:
            for position,kind in _measurement_tasks(CASE_KINDS[key],projection,allocation):
                contract=make_contract(fixture,placeholder,position,kind)
                requests+=2*len(contract['fields'])+max(1,len(required_saves(contract)))+2+1
        elif key=='NSN014-REPORT':requests=len(projection['positions'])*7
        elif key=='NSN014-PLAN':requests=4
        else:requests=3
        per_case[key]=requests
    total=sum(per_case.values());ceiling=suite['resource_policy']['hard_model_calls']
    return {'minimum_model_requests':total,'hard_model_calls':ceiling,'fits_ceiling':total<=ceiling,
            'headroom_ratio':round(ceiling/total,2) if total else None,'per_case':per_case,
            'basis':'lower bound without agent retries, scrolling, dropdowns or navigation detours'}


def check_ready(suite,dataset,fixture,projection,allocation):
    blocked={'status':'BLOCKED_SUITE_READINESS','model_calls':0,'database_writes':0}
    try:
        validate_suite(suite)
        if (suite.get('adapter_contract')!='ENZBERG-NSN014-UX-v1' or suite.get('suite_id')!='ENZBERG-NSN014'
                or {c['case_id'] for c in suite['cases']}!=CASE_IDS
                or any(c['implementation']!='implemented' for c in suite['cases'])):
            return dict(blocked,reason='ADAPTER_COVERAGE_PENDING')
        lease=Path(fixture['suite_copy']['application_root']).parent/'benchmark-consumed.json'
        if lease.exists():return dict(blocked,reason='FIXTURE_ALREADY_CLAIMED')
        source=source_state()
        if not source['clean']:return dict(blocked,reason='SQBF_SOURCE_NOT_COMMITTED',source=source)
        if (fixture['suite_copy'].get('receipt_entrypoint')!='plan_replenish_once'
                or not {'sampling.manage','samples.view'}<=set(fixture['personas']['laboratory_lead']['allowed_permissions'])):
            return dict(blocked,reason='PLAN_WORKFLOW_OR_PERMISSION_UNVERIFIED')
        if (canonical_hash(projection)!=fixture['suite_copy'].get('measurement_reference_sha256')
                or canonical_hash(allocation)!=fixture['suite_copy'].get('allocation_reference_sha256')
                or projection['source_sha256']!=canonical_hash(dataset)
                or allocation['source_dataset_id']!=dataset['dataset_id']
                or {p['position_id'] for p in projection['positions']}!=set(suite['required_position_ids'])
                or {p['position_id'] for p in allocation['positions']}!=set(suite['required_position_ids'])):
            return dict(blocked,reason='REFERENCE_INPUT_CHANGED')
        if fixture['suite_copy'].get('suite_sha256')!=canonical_hash(suite):
            return dict(blocked,reason='SUITE_NOT_BOUND_TO_FIXTURE')
        contracts=stage_contracts(suite,projection,allocation,fixture)
        if contracts['status']!='STAGE_CONTRACTS_VERIFIED':return dict(blocked,reason='STAGE_CONTRACT_BUILD_FAILED',stage_contracts=contracts)
        estimate=estimate_requests(suite,projection,allocation,fixture)
        if not estimate['fits_ceiling']:return dict(blocked,reason='REQUEST_CEILING_BELOW_MINIMUM',request_estimate=estimate)
        dependencies={name:importlib.metadata.version(name) for name in ('playwright','pypdf','PyMuPDF')}
        for table,count in {'product_test_method_derived_steps':20,'product_test_method_input_specs':11,
                'product_test_method_sampling_steps':9,'product_sample_preparation_steps':5,
                'product_original_sample_split_requirements':15}.items():
            if fixture['read_only_oracle']['expected_counts'].get(table)!=count:
                return dict(blocked,reason='METHOD_FIXTURE_INCOMPLETE')
        gates=check_fixture(fixture,suite,dataset)
        if gates['status']!='FIXTURE_GATES_VERIFIED':return dict(blocked,reason='FIXTURE_GATE_FAILED',gates=gates)
        if not static_fixture_unchanged(fixture,snapshot(fixture)):
            return dict(blocked,reason='STATIC_FIXTURE_BASELINE_MISMATCH')
        runtime=verify_runtime(fixture['target_url'],fixture['suite_copy']['application_root'],fixture['identity_scope_check'])
        if any(runtime[k]!=fixture['suite_copy']['runtime'][k] for k in ('assembly','sha256')):
            return dict(blocked,reason='ACTIVE_RUNTIME_MISMATCH')
        start=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='before')
        if (start['status']!='RECEIPT_START_VERIFIED' or collect_inputs(fixture)
                or collect_allocations(fixture) or collect_reports(fixture)):
            return dict(blocked,reason='UNUSED_START_STATE_NOT_VERIFIED')
        policy=Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json',fixture['target_url']).read_only_policy
        form=check_receipt_form(fixture,dataset,policy)
        if form['status']!='RECEIPT_UI_CONTRACT_VERIFIED':return dict(blocked,reason='RECEIPT_UI_CONTRACT_FAILED',form=form)
        routes=check_entry_routes(fixture,policy,route_probes(suite,fixture))
        if routes['status']!='ENTRY_ROUTES_VERIFIED':return dict(blocked,reason='ENTRY_ROUTE_CONTRACT_FAILED',entry_routes=routes)
        return {'status':'READY_FOR_SINGLE_SUITE_RUN','model_calls':0,'database_writes':0,
                'source':source,'scoring_version':SCORING_VERSION,'rubric_version':RUBRIC_VERSION,'stage_contracts':contracts,
                'fixture_gates':gates,'dependencies':dependencies,'native_receipt_form':form,'entry_routes':routes,
                'active_runtime':runtime,'request_estimate':estimate,'persona_context':persona_context(suite,fixture),
                'fresh_subscription_authorization_required_at_execution':True,'current_provider_catalog_checked':False,
                'limitations':['Readiness is not a successful benchmark or proof of defect-free BLE behaviour.',
                               'Request estimate is a lower bound; agent detours can exhaust the ceiling (INCONCLUSIVE).']}
    except Exception:
        return dict(blocked,reason='READINESS_EVIDENCE_UNAVAILABLE')


def dispatch(case,browser,fixture,dataset,projection,allocation,policy,executor,reviewer,budget,evidence):
    key=case['case_id']
    if key=='NSN014-PLAN':return run_plan_creation(browser,fixture,dataset,projection,case,policy,executor,reviewer,budget,evidence)
    if key in CASE_KINDS:
        return run_measurements(browser,fixture,projection,CASE_KINDS[key],policy,executor,reviewer,budget,evidence,
                                allocation_reference=allocation)
    if key in READ_CASES:
        result=run_inspection(browser,fixture,projection,case,policy,executor,reviewer,budget,evidence)
        if key=='NSN014-RECEIPT' and result.get('technical_gate')=='PASS' and not result.get('stop_reason'):
            # Staff sees plan-created samples; LIMS records stay lazy until module work.
            oracle=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='after_plan')
            result.update(oracle=oracle,oracle_gate=oracle['status'])
            if oracle['status'] not in ('PASS','FAIL'):
                result.update(result='BLOCKED',technical_gate='BLOCKED',reason='RECEIPT_ORACLE_UNAVAILABLE')
            elif oracle['status']=='FAIL' and (oracle.get('mismatched_positions') or oracle.get('orphan_lims')
                                               or oracle.get('reason')):
                # The inspection itself is write-free, so this is an inconsistent plan state.
                result.update(result='BLOCKED',technical_gate='BLOCKED',reason='PLAN_STATE_INCONSISTENT')
            elif oracle['status']=='FAIL':
                result.update(result='INCONCLUSIVE',reason='MISSING_PLAN_PREREQUISITE',
                              missing_prerequisites=oracle.get('missing_positions',[]))
        return result
    if key=='NSN014-REPORT':return run_reports(browser,fixture,projection,case,policy,executor,reviewer,budget,evidence)
    raise ValueError('Unknown suite case; no fallback')


def _reviews(record):
    reviews=[record.get('review')]+[r.get('review') for r in record.get('positions',[])]
    reviews+=record.get('pdf_reviews',[])+[review for r in record.get('positions',[]) for review in r.get('pdf_reviews',[])]
    return [r for r in reviews if r is not None]


def _valid_reviewers(record):
    return all(valid_review({k:v for k,v in review.items() if k!='pages'}) for review in _reviews(record))


def execute_cases(suite,fixture,budget,stage,*,write=lambda records,accounting:None,scope_fn=check_persona):
    """One visit per case; failures never trigger a second run or re-login."""
    records=[];stopped=None
    for case in suite['cases']:
        if stopped:
            records.append({'case_id':case['case_id'],'persona':case['persona'],'result':'NOT_RUN',
                            'objective_status':'NOT_RUN','reason':'UPSTREAM_CRITICAL_STOP','upstream_reason':stopped})
            write(records,budget.report());continue
        try:
            budget.start_task(case)
            gate=scope_fn(fixture,case['persona'],fixture['personas'][case['persona']]['storage_state'],fixture['identity_verifier'])
            if gate['status']!='PERSONA_SCOPE_VERIFIED':
                record={'result':'BLOCKED','technical_gate':'BLOCKED','reason':'ACTOR_SCOPE_FAILED'}
            else:record=stage(case)
            if not _valid_reviewers(record):record={'result':'INVALID','technical_gate':'INVALID','reason':'REVIEW_SCHEMA_OR_SCORE_INVALID'}
            record=dict(record,case_id=case['case_id'],persona=case['persona'])
            if (record.get('technical_gate') in ('BLOCKED','INVALID') or record['result']=='INVALID'
                    or record.get('stop_reason') or record.get('critical_stop')):
                stopped=record.get('stop_reason') or record.get('reason') or record['result']
        except ResourceStop:
            stopped=budget.stop_reason;record={'case_id':case['case_id'],'persona':case['persona'],'result':'INCONCLUSIVE',
                                               'technical_gate':'PASS','stop_reason':stopped}
        except Exception:
            stopped='SUITE_CONTROLLER_ERROR';record={'case_id':case['case_id'],'persona':case['persona'],'result':'INVALID',
                                                     'technical_gate':'INVALID','reason':stopped}
        finally:
            if budget.active is not None:budget.finish_task()
        record['objective_status']=objective_status(record['result'])
        records.append(record);write(records,budget.report())
    return records


def browser_suite(payload):
    from playwright.sync_api import sync_playwright
    suite,fixture=payload['suite'],payload['fixture']
    validate_suite(suite)
    root=Path(payload['folder']);check_private_directory(root)
    def checkpoint(accounting):
        atomic_json(root/'accounting.json',accounting)
    budget=SuiteBudget(suite['resource_policy'],on_change=checkpoint)
    executor,reviewer=restore_model(payload['executor']),restore_model(payload['reviewer'])
    downloads=root/'browser-downloads';downloads.mkdir();check_private_directory(downloads,protect=True)
    policy=Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json',fixture['target_url']).read_only_policy
    def write(records,accounting):
        atomic_json(root/'cases.json',records)
        atomic_json(root/'accounting.json',accounting)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=not payload['headed'],downloads_path=str(downloads),timeout=min(15000,budget.remaining()*1000))
        try:
            def stage(case):
                if not static_fixture_unchanged(fixture,snapshot(fixture,enforce_counts=False)):
                    return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'STATIC_FIXTURE_CHANGED'}
                evidence=Evidence(root/case['case_id'])
                started=time.monotonic()
                result=dispatch(case,browser,fixture,payload['dataset'],payload['projection'],payload['allocation'],
                                policy,executor,reviewer,budget,evidence)
                result=dict(result,stage_wall_seconds=round(time.monotonic()-started,3))
                if not static_fixture_unchanged(fixture,snapshot(fixture,enforce_counts=False)):
                    return dict(result,result='INVALID',technical_gate='INVALID',reason='STATIC_FIXTURE_CHANGED')
                return result
            records=execute_cases(suite,fixture,budget,stage,write=write)
            summary=aggregate(suite,records)
            return {'records':records,'summary':summary,'accounting':budget.report(),'browser_version':browser.version}
        finally:browser.close()


def run_suite(suite,dataset,fixture,projection,allocation,output,executor_id,reviewer_id,*,headed=False):
    """Explicit live entry point; preflight precedes browser OAuth or inference."""
    ready=check_ready(suite,dataset,fixture,projection,allocation)
    if (ready['status']!='READY_FOR_SINGLE_SUITE_RUN' and ready.get('reason')=='FIXTURE_GATE_FAILED'
            and ready.get('gates',{}).get('reason')=='SESSION_FAILED'):
        from .suite_sessions import prepare_sessions
        private=Path(fixture['suite_copy']['application_root']).parent;check_private_directory(private)
        prepared=private/('fixture-session-refresh-'+uuid4().hex+'.json')
        report_path=private/('session-refresh-'+uuid4().hex+'.json')
        create_private_file(prepared);create_private_file(report_path)
        session_result,fixture=prepare_sessions(fixture,private)
        prepared.write_text(json.dumps(fixture,indent=2),encoding='utf-8')
        report_path.write_text(json.dumps(session_result,indent=2),encoding='utf-8')
        if session_result['status']!='SESSIONS_VERIFIED':return session_result
        ready=check_ready(suite,dataset,fixture,projection,allocation)
    if ready['status']!='READY_FOR_SINGLE_SUITE_RUN':return ready
    if (executor_id,reviewer_id)!=('gpt-6-luna','gpt-6.1-sol'):
        return {'status':'BLOCKED_MODEL_SELECTION','model_calls':0}
    output=Path(output).resolve()
    if any((p/'.git').exists() for p in output.parents):raise ValueError('Artifacts must remain outside Git')
    if not output.exists():output.mkdir(parents=True);check_private_directory(output,protect=True)
    else:check_private_directory(output)
    evidence=Evidence(output/str(uuid4()))
    manifest={'run_id':evidence.path.name,'scenario_id':suite['suite_id'],'scenario_version':suite['version'],
        'software_version':fixture['suite_copy']['runtime']['assembly'].split('+')[-1],
        'fixture_id':fixture['fixture_id'],'started_at':now_iso(),'persona':'multi-role',
        'persona_context':ready['persona_context'],
        'executor_model':executor_id,'analyst_model':reviewer_id,'provider':'chatgpt_plan',
        'scoring_version':SCORING_VERSION,'rubric_version':RUBRIC_VERSION,'review_schema_sha256':canonical_hash(REVIEW_SCHEMA),
        'sqbf_commit':ready['source']['commit'],'sqbf_source_clean':ready['source']['clean'],
        'suite_sha256':canonical_hash(suite),'dataset_sha256':canonical_hash(dataset),
        'reference_projection_sha256':canonical_hash(projection),'allocation_reference_sha256':canonical_hash(allocation),
        'fixture_manifest_sha256':canonical_hash(fixture),
        'prepared_state_sha256':fixture['suite_copy']['prepared_state_sha256'],
        'environment':ready['dependencies'],'viewport':{'width':1280,'height':800},
        'locale':'de-DE','timezone':'Europe/Berlin',
        'ble_assembly_sha256':fixture['suite_copy']['runtime']['sha256'],
        'active_runtime':ready['active_runtime'],'request_estimate':ready['request_estimate'],
        'verdict':'NO-GO','technical_status':'NOT_STARTED','functional_status':'NOT_RUN','model_calls':0,'execution_started':False}
    (evidence.path/'run.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    result={}
    try:
        from sqbf.plan_login import _load_host, authorize, catalog
        from sqbf.providers import ChatGPTPlanModel
        directory=Path(os.environ['LOCALAPPDATA'])/'SQBF'/'plan-login'
        credential=authorize(_load_host(directory));available=catalog(credential)
        if executor_id not in available or reviewer_id not in available:raise ValueError('MODEL_UNAVAILABLE')
        schema=copy.deepcopy(ACTION_SCHEMA)
        schema['properties']['key']['enum']=[None,'ControlOrMeta+A','Backspace','Delete','Tab','Escape']
        executor=ChatGPTPlanModel(executor_id,credential,schema)
        reviewer=ChatGPTPlanModel(reviewer_id,credential,REVIEW_SCHEMA)
        # A measured write fixture is single-use, including failed/aborted runs.
        # Reserve only after OAuth so a cancelled login does not consume it.
        lease=Path(fixture['suite_copy']['application_root']).parent/'benchmark-consumed.json'
        check_private_directory(lease.parent);create_private_file(lease)
        lease.write_text(json.dumps({'run_id':manifest['run_id'],'suite_sha256':canonical_hash(suite),
                                    'claimed_at':now_iso(),'automatic_retry':False}),encoding='utf-8')
        manifest['started_at']=now_iso();manifest['execution_started']=True;started=time.monotonic()
        result=invoke_worker('regular-suite',{'suite':suite,'dataset':dataset,'fixture':fixture,
            'projection':projection,'allocation':allocation,'folder':str(evidence.path),'headed':headed,
            'executor':model_spec(executor),'reviewer':model_spec(reviewer)},suite['resource_policy']['hard_seconds'])
        summary=result['summary']
        critical=any(r.get('technical_gate')=='BLOCKED' for r in result['records'])
        manifest.update(technical_status='INVALID' if summary['measurement_status']=='INVALID' else 'BLOCKED' if critical else 'COMPLETED',
            functional_status=summary['result'],measurement_status=summary['measurement_status'],
            verdict='GO' if summary['result']=='PASS' else 'PARTIAL GO' if summary['result']=='INCOMPLETE' else 'NO-GO',
            model_calls=result['accounting']['model_calls'],wall_seconds=time.monotonic()-started,
            summary=summary,accounting=result['accounting'],browser_version=result['browser_version'],
            comparison_key=comparison_key(suite,canonical_hash(dataset),executor_id,reviewer_id,
                                          {'width':1280,'height':800},result['browser_version']))
        if result['accounting'].get('stop_reason') and summary['measurement_status']!='INVALID':
            manifest.update(technical_status='RESOURCE_STOP',functional_status='INCONCLUSIVE',verdict='PARTIAL GO',
                            stop_reason=result['accounting']['stop_reason'])
    except BudgetExceeded:
        manifest.update(technical_status='RESOURCE_STOP',functional_status='INCONCLUSIVE',measurement_status='INCOMPLETE',
                        verdict='PARTIAL GO',stop_reason='SUITE_TIME_CEILING',accounting_complete=False)
    except FileExistsError:
        manifest.update(technical_status='BLOCKED',functional_status='NOT_RUN',reason='FIXTURE_ALREADY_CLAIMED')
    except Exception:
        manifest.update(technical_status='BLOCKED_OR_INVALID',functional_status='NOT_CONFIRMED',reason='SUITE_STOPPED_NO_RETRY')
    finally:
        if not result and (evidence.path/'accounting.json').is_file():
            try:
                accounting=json.loads((evidence.path/'accounting.json').read_text(encoding='utf-8'))
                manifest.update(accounting=accounting,model_calls=accounting['model_calls'])
            except Exception:
                manifest.update(accounting_complete=False,model_calls=None)
        if not result and (evidence.path/'cases.json').is_file():
            try:result['records']=json.loads((evidence.path/'cases.json').read_text(encoding='utf-8'))
            except Exception:manifest['case_evidence_complete']=False
        try:
            current=snapshot(fixture,enforce_counts=False)
            if not manifest['execution_started']:
                manifest['post_setup_protected_data_unchanged']=canonical_hash(current['tables'])==fixture['suite_copy']['prepared_state_sha256']
                if not manifest['post_setup_protected_data_unchanged']:
                    manifest.update(verdict='NO-GO',technical_status='INVALID',reason='SETUP_CHANGED_PROTECTED_DATA')
            else:
                finalise_oracles(manifest,result,fixture,dataset,projection,allocation,current)
        except Exception:
            manifest.update(verdict='NO-GO',technical_status='BLOCKED',reason='FINAL_ORACLE_UNAVAILABLE')
        records=result.get('records',[])
        manifest.update(case_matrix=case_matrix(records),ux_summary=ux_summary(records))
        manifest['completed_at']=now_iso()
        # Credentials/tokens never enter persisted manifests or reports.
        (evidence.path/'run.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        (evidence.path/'completion-report.md').write_text(completion_text(manifest,records),encoding='utf-8')
        index_run(output,evidence.path)
    return {'status':'SUITE_RUN_RECORDED','run_id':manifest['run_id'],'verdict':manifest['verdict'],
            'technical_status':manifest['technical_status'],'path':str(evidence.path)}


def finalise_oracles(manifest,result,fixture,dataset,projection,allocation,current):
    receipts=collect_receipts(fixture)
    pdfs=[]
    for record in result.get('records',[]):
        if record['case_id']=='NSN014-REPORT':
            pdfs=record.get('downloads',[]) or [d for p in record.get('positions',[]) for d in p.get('downloads',[])]
    basis=persisted_basis(collect_inputs(fixture))
    final_oracles={'static_fixture_unchanged':static_fixture_unchanged(fixture,current),
        'receipt':verify_receipts(receipts,dataset,fixture,phase='after_modules'),
        'measurements':verify_inputs(collect_inputs(fixture),projection,fixture,kinds=KINDS),
        'allocations':verify_allocations(collect_allocations(fixture),projection,allocation,fixture),
        'reports':verify_reports(collect_reports(fixture),receipts,projection,fixture,pdfs,basis=basis),
        'calculations':verify_calculations(collect_report_calculations(fixture),receipts,basis,fixture)}
    manifest['final_oracles']=final_oracles
    if not final_oracles['static_fixture_unchanged']:
        manifest.update(verdict='NO-GO',technical_status='INVALID',reason='STATIC_FIXTURE_CHANGED')
    if manifest['verdict']=='GO' and any(final_oracles[k]['status']!='PASS'
                                         for k in ('receipt','measurements','allocations','reports','calculations')):
        manifest.update(verdict='NO-GO',functional_status='NOT_CONFIRMED',reason='FINAL_ORACLE_FAILED')


ATTRIBUTION={
    'PASS':'—',
    'FAIL':'BLE: objektive Abweichung durch unabhängige Oracles belegt (fachliche Bestätigung offen)',
    'INVALID':'SQBF/Harness: Messung ungültig, kein BLE-Befund',
    'BLOCKED':'Voraussetzung, Sicherheitsstopp oder Harness: kein BLE-Befund',
    'INCONCLUSIVE':'Nicht entschieden: Agent, Budget oder fehlende Vorstufe',
    'NOT_RUN':'Nicht ausgeführt: vorgelagerter kritischer Stopp',
    'NOT_IMPLEMENTED':'Adapter fehlt',
}
CATEGORY_LABELS={'BLE_DEFECT_CANDIDATE':'BLE-Kandidat (unbestätigt)','UX_IMPROVEMENT':'UX-Verbesserung',
                 'AGENT_DIFFICULTY':'Agentenschwierigkeit','HARNESS_SUSPECTED':'SQBF-Kandidat (unbestätigt)',
                 'UNCLEAR':'Unklar'}


def _findings(record):
    out=[]
    for review in _reviews(record):
        for finding in review.get('findings',[]):
            if isinstance(finding,dict):out.append(finding)
    return out


def case_matrix(records):
    """Machine-readable per-case result; objective status and UX layer side by side."""
    rows=[]
    for record in records:
        scores={name:[] for name in DIMENSIONS}
        for review in _reviews(record):
            for name in DIMENSIONS:
                value=(review.get('scores') or {}).get(name)
                if type(value) is int:scores[name].append(value)
        rows.append({'case_id':record['case_id'],'persona':record.get('persona'),
            'objective_status':objective_status(record['result']),'technical_gate':record.get('technical_gate'),
            'oracle_gate':record.get('oracle_gate'),'reason':record.get('reason') or record.get('stop_reason'),
            'fail_classes':record.get('fail_classes',[]),'position_results':record.get('position_results',[]),
            'missing_prerequisites':record.get('missing_prerequisites',[]),
            'ux_verdict':record.get('ux_verdict','NOT_EVALUATED'),
            'ux_scores':{name:({'n':len(v),'min':min(v),'max':max(v)} if v else 'NOT_EVALUATED') for name,v in scores.items()},
            'stage_wall_seconds':record.get('stage_wall_seconds')})
    return rows


def ux_summary(records):
    counts={category:{severity:0 for severity in SEVERITIES} for category in CATEGORIES}
    for record in records:
        for finding in _findings(record):
            if finding.get('category') in counts and finding.get('severity') in SEVERITIES:
                counts[finding['category']][finding['severity']]+=1
    return {'rubric_version':RUBRIC_VERSION,'finding_counts':counts,'global_score':None,
            'note':'No global percentage; UX never compensates objective faults.'}


def completion_text(manifest,records):
    def text(value):
        value=str(value).replace('\\','\\\\').replace('\n',' ').replace('\r',' ').replace('`',"'")
        for char in ('[',']','!','*','_','#','|'):value=value.replace(char,'\\'+char)
        return value.replace('<','&lt;').replace('>','&gt;')
    accounting=manifest.get('accounting',{})
    lines=['# NSN014 Abschlussbericht','',
        f"- Lauf: {text(manifest['run_id'])}",f"- Gesamtergebnis: {text(manifest['verdict'])}",
        f"- Technischer Status: {text(manifest['technical_status'])}",f"- Funktionaler Status: {text(manifest['functional_status'])}",
        f"- Messstatus: {text(manifest.get('measurement_status','NOT_STARTED'))}",
        f"- Suite: {text(manifest['scenario_id'])} v{text(manifest['scenario_version'])}; Bewertung {text(manifest.get('scoring_version'))}; "
        f"UX-Rubrik {text(manifest.get('rubric_version'))} (vorläufig)",
        f"- SQBF-Commit: {text(manifest['sqbf_commit'])}; BLE-Build: {text(manifest['software_version'])}",
        f"- Executor: {text(manifest['executor_model'])}; Reviewer: {text(manifest['analyst_model'])}",
        f"- Modellanfragen: {text(manifest.get('model_calls',0))}",'']
    if manifest.get('final_oracles'):
        lines+=['Abschließende unabhängige Oracles: '+text({key:value.get('status') if isinstance(value,dict) else value
                                                       for key,value in manifest['final_oracles'].items()}),'']
    matrix=manifest.get('case_matrix') or case_matrix(records)
    lines+=['## Stufenmatrix','','| Stufe | Persona | Objektiver Status | Grund | UX-Urteil |','|---|---|---|---|---|']
    for row in matrix:
        lines.append('| '+' | '.join(text(v) for v in (row['case_id'],row['persona'],row['objective_status'],
                                                       row['reason'] or '—',row['ux_verdict']))+' |')
    passed=[r for r in matrix if r['objective_status']=='PASS']
    failed=[r for r in matrix if r['objective_status']=='FAIL']
    lines+=['','## 1. Was in BLE funktioniert','']
    lines+=['- '+text(r['case_id'])+': objektiv bestanden' for r in passed] or ['- Keine Stufe objektiv bestanden.']
    for row in matrix:
        good=[p['position_id'] for p in row['position_results'] if p['result']=='PASS']
        if good and row['objective_status']!='PASS':lines.append('- '+text(row['case_id'])+': bestandene Positionen '+text(good))
    lines+=['','## 2. Was in BLE nicht funktioniert','']
    lines+=['- '+text(r['case_id'])+': '+text(r['fail_classes'] or r['reason'])+'; Positionen '+
            text([p['position_id'] for p in r['position_results'] if p['result']=='FAIL']) for r in failed] or [
            '- Keine objektiv belegte BLE-Abweichung.']
    lines+=['','## 3. BLE- oder SQBF-Problem','']
    for row in matrix:
        if row['objective_status']!='PASS':
            lines.append('- '+text(row['case_id'])+' ('+text(row['objective_status'])+'): '+
                         text(ATTRIBUTION.get({'INVALID_HARNESS':'INVALID'}.get(row['objective_status'],row['objective_status']),'')))
    summary=manifest.get('ux_summary') or ux_summary(records)
    lines+=['','## 4. UX-Befunde nach Kategorie und Schweregrad','',
            'Reviewer-Befunde sind unbestätigte Beobachtungen; sie ändern keinen objektiven Status.','']
    for category,severities in summary['finding_counts'].items():
        if any(severities.values()):
            lines.append('- '+text(CATEGORY_LABELS[category])+': '+text(', '.join(f'{k} {v}' for k,v in severities.items() if v)))
    priority=[];minor=[]
    for record in records:
        for finding in _findings(record):
            entry=(text(record['case_id'])+' — '+text(CATEGORY_LABELS.get(finding.get('category'),'Unklar'))+' / '
                   +text(finding.get('severity'))+': '+text(finding.get('observed'))+' → erwartet: '+text(finding.get('expected'))
                   +'; Vorschlag: '+text(finding.get('suggestion'))+' (Evidenz: '+text(finding.get('evidence'))+')')
            (priority if finding.get('severity') in ('critical','major') else minor).append(entry)
    lines+=['','## 5. Priorität','',
            'P1 objektive BLE-Abweichungen (fachlich bestätigen, dann BLE-Issue):']
    lines+=['- '+text(r['case_id'])+': '+text(r['fail_classes']) for r in failed] or ['- keine']
    lines+=['P2 Harness-/Voraussetzungsstopps vor einem Retest beheben:']
    lines+=['- '+text(r['case_id'])+': '+text(r['reason']) for r in matrix if r['objective_status'] in ('INVALID_HARNESS','BLOCKED')] or ['- keine']
    lines+=['P3 kritische/major UX-Befunde:']+(['- '+e for e in priority] or ['- keine'])
    lines+=['P4 weitere UX-Befunde (minor/info):']+(['- '+e for e in minor] or ['- keine'])
    lines+=['','## 6. Retest-Benchmark','',
        f"- Vergleichsschlüssel (Suite, Datensatz, Modelle, Viewport, Browser): {text(manifest.get('comparison_key','nicht verfügbar'))}",
        f"- Suite-SHA256: {text(manifest['suite_sha256'])}; Datensatz-SHA256: {text(manifest['dataset_sha256'])}",
        f"- Fixture-Startzustand-SHA256: {text(manifest.get('prepared_state_sha256'))}",
        '- Retest: neue Fixture aus derselben Golden-Basis, gleiche Suite-/Bewertungs-/Rubrik-Version, ein Lauf ohne Retry.',
        '- Verglichen werden objektive Status je Stufe und Position sowie UX-Werte je Dimension; keine globale Prozentzahl.',
        '','## 7. Zeit und Nutzung','',
        f"Controller-Laufzeit (s): {text(accounting.get('elapsed_seconds','unbekannt'))}",
        f"Modell-Wartezeit (s): {text(accounting.get('model_wait_seconds','unbekannt'))}",
        f"Übrige Controller-Zeit (s): {text(accounting.get('non_model_elapsed_seconds','unbekannt'))}",'']
    for actor,usage in accounting.get('actors',{}).items():
        lines.append(f"- {text(actor)}: {text(usage['model_calls'])} Anfragen")
        for key,value in usage['tokens'].items():
            total=value['complete_total'] if value['complete_total'] is not None else 'unbekannt'
            lines.append(f"  - {text(key)}: gesamt {text(total)}; bekannte Summe {text(value['known_sum'])}; ohne Angabe {text(value['unknown_calls'])}")
    lines+=['','## 8. Stufendetails','']
    for record in records:
        lines+=['### '+text(record['case_id']),'',
            f"Status: {text(objective_status(record['result']))}; technisch: {text(record.get('technical_gate','ungeprüft'))}; "
            f"Oracle: {text(record.get('oracle_gate','ungeprüft'))}"]
        if record.get('reason'):lines.append('Grund: '+text(record['reason']))
        if record.get('missing_prerequisites'):lines.append('Fehlende Voraussetzungen: '+text(record['missing_prerequisites']))
        for item in record.get('position_results',[]):
            lines.append('- Position '+text(item['position_id'])+': '+text(item['result'])+(' ('+text(item['class'])+')' if item.get('class') else ''))
        for item in [record]+record.get('positions',[]):
            if item.get('executor_statement'):
                lines.append('- Executor-Aussage (unbestätigt): '+text(item['executor_statement'].get('reason','')))
            review=item.get('review') or {}
            if review:
                lines.append('- Reviewer '+text(item.get('position_id','Stufe'))+': '+text(review.get('verdict'))+'; UX-Werte: '+text(review.get('scores',{})))
            for review in item.get('pdf_reviews',[]):
                lines.append('- PDF-Seiten '+text(review['pages'])+': '+text(review['verdict'])+'; UX-Werte: '+text(review.get('scores',{})))
        lines.append('')
    lines+=['## Evidenz und Interpretation','',
        '- Ereignisse, Screenshots, PDF-Downloads, cases.json, accounting.json und run.json bleiben lokal und privat.',
        '- Objektive Status stammen aus Controller- und unabhängigen Read-only-Oracles; der Reviewer bestimmt sie nicht.',
        '- Harte Sicherheits- oder Datenfehler werden nicht durch UX-Werte kompensiert; es gibt keine Gesamtprozentzahl.',
        '- Berechnungen werden aus persistierten Rohdaten unabhängig nachgerechnet; Teilsiebung/gekoppelte Siebung ist NOT_COVERED.',
        '- KI-Controllerzeit ist keine menschliche Arbeitszeit. Normkonformität und Freigabe sind ausgeschlossen.',
        '- Fehlende Voraussetzungen und Ressourcenstopps bleiben explizit; es gibt keinen automatischen Retry.']
    return '\n'.join(lines)+'\n'

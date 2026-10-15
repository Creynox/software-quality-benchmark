"""NSN014 suite orchestration; no implicit live execution or automatic retry."""
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
from sqbf.suites import suite_check, canonical_hash, aggregate, validate_suite
from sqbf.smoke_runner import ACTION_SCHEMA, REVIEW_SCHEMA
from sqbf.no_write_oracle import snapshot
from sqbf.scope_check import verify_runtime
from .allocation_oracle import collect_allocations, verify_allocations
from .measurement_oracle import collect_inputs, verify_inputs, KINDS
from .report_oracle import collect_reports, verify_reports
from .receipt_oracle import collect_receipts, verify_receipts
from .suite_acceptance import check_fixture
from .persona_scope import check_persona
from .measurement_runner import run_measurements
from .inspection_runner import run_inspection, run_reports,run_plan_creation
from .receipt_contract_check import check_receipt_form

CASE_KINDS={'NSN014-PREPARATION':['allocations','wash'],'NSN014-SIEVE':['sieve','partial'],
            'NSN014-SHAPE':['shape'],'NSN014-BOILING':['boiling'],'NSN014-SE':['sand']}
READ_CASES={'NSN014-RECEIPT','NSN014-ASSESS','NSN014-WPK','NSN014-ANALYSIS','NSN014-RIGHTS'}
CASE_IDS=READ_CASES|set(CASE_KINDS)|{'NSN014-PLAN','NSN014-REPORT'}
MUTABLE_TABLES={'samples','lims_sample','ble_reports','sqbf_measurement_inputs_v1','sqbf_allocation_inputs_v1'}


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
        return {'status':'READY_FOR_SINGLE_SUITE_RUN','model_calls':0,'database_writes':0,
                'fixture_gates':gates,'dependencies':dependencies,'native_receipt_form':form,'active_runtime':runtime,
                'fresh_subscription_authorization_required_at_execution':True,'current_provider_catalog_checked':False,
                'limitations':['Readiness is not a successful benchmark or proof of defect-free BLE behaviour.']}
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
            oracle=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='after_plan')
            result.update(oracle=oracle,oracle_gate=oracle['status'])
            if oracle['status']!='PASS':result['result']='INCONCLUSIVE' if oracle.get('missing_positions') else 'BLOCKED'
        return result
    if key=='NSN014-REPORT':return run_reports(browser,fixture,projection,case,policy,executor,reviewer,budget,evidence)
    raise ValueError('Unknown suite case; no fallback')


def _valid_reviewers(record):
    reviews=[record.get('review')]+[r.get('review') for r in record.get('positions',[])]
    reviews+=record.get('pdf_reviews',[])+[review for r in record.get('positions',[]) for review in r.get('pdf_reviews',[])]
    for review in (r for r in reviews if r is not None):
        if (review.get('verdict') not in ('PASS','FAIL','INCONCLUSIVE') or not isinstance(review.get('scores'),dict)
                or set(review['scores'])!={'findability','clarity','task_progress','error_recovery'}
                or any(type(v) is not int or not 0<=v<=5 for v in review['scores'].values())):
            return False
    return True


def execute_cases(suite,fixture,budget,stage,*,write=lambda records,accounting:None,scope_fn=check_persona):
    """One visit per case; failures never trigger a second run or re-login."""
    records=[];stopped=None
    for case in suite['cases']:
        if stopped:
            records.append({'case_id':case['case_id'],'result':'BLOCKED','technical_gate':'BLOCKED',
                            'reason':'UPSTREAM_CRITICAL_STOP','upstream_reason':stopped})
            write(records,budget.report());continue
        try:
            budget.start_task(case)
            gate=scope_fn(fixture,case['persona'],fixture['personas'][case['persona']]['storage_state'],fixture['identity_verifier'])
            if gate['status']!='PERSONA_SCOPE_VERIFIED':
                record={'result':'BLOCKED','technical_gate':'BLOCKED','reason':'ACTOR_SCOPE_FAILED'}
            else:record=stage(case)
            if not _valid_reviewers(record):record={'result':'INVALID','technical_gate':'INVALID','reason':'REVIEW_SCHEMA_OR_SCORE_INVALID'}
            record=dict(record,case_id=case['case_id'])
            if record.get('technical_gate') in ('BLOCKED','INVALID') or record['result']=='INVALID' or record.get('stop_reason'):
                stopped=record.get('stop_reason') or record.get('reason') or record['result']
        except ResourceStop:
            stopped=budget.stop_reason;record={'case_id':case['case_id'],'result':'INCONCLUSIVE','technical_gate':'PASS','stop_reason':stopped}
        except Exception:
            stopped='SUITE_CONTROLLER_ERROR';record={'case_id':case['case_id'],'result':'INVALID','technical_gate':'INVALID','reason':stopped}
        finally:
            if budget.active is not None:budget.finish_task()
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
                result=dispatch(case,browser,fixture,payload['dataset'],payload['projection'],payload['allocation'],
                                policy,executor,reviewer,budget,evidence)
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
        'executor_model':executor_id,'analyst_model':reviewer_id,'provider':'chatgpt_plan',
        'suite_sha256':canonical_hash(suite),'dataset_sha256':canonical_hash(dataset),
        'reference_projection_sha256':canonical_hash(projection),'allocation_reference_sha256':canonical_hash(allocation),
        'environment':ready['dependencies'],'viewport':{'width':1280,'height':800},
        'locale':'de-DE','timezone':'Europe/Berlin',
        'ble_assembly_sha256':fixture['suite_copy']['runtime']['sha256'],
        'active_runtime':ready['active_runtime'],
        'verdict':'NO-GO','technical_status':'NOT_STARTED','functional_status':'NOT_RUN','model_calls':0,'execution_started':False}
    manifest['sqbf_commit']=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
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
            summary=summary,accounting=result['accounting'],browser_version=result['browser_version'])
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
        manifest['completed_at']=now_iso()
        # Credentials/tokens never enter persisted manifests or reports.
        (evidence.path/'run.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        (evidence.path/'completion-report.md').write_text(completion_text(manifest,result.get('records',[])),encoding='utf-8')
        index_run(output,evidence.path)
    return {'status':'SUITE_RUN_RECORDED','run_id':manifest['run_id'],'verdict':manifest['verdict'],
            'technical_status':manifest['technical_status'],'path':str(evidence.path)}


def finalise_oracles(manifest,result,fixture,dataset,projection,allocation,current):
    receipts=collect_receipts(fixture)
    pdfs=[]
    for record in result.get('records',[]):
        if record['case_id']=='NSN014-REPORT':
            pdfs=record.get('downloads',[]) or [d for p in record.get('positions',[]) for d in p.get('downloads',[])]
    final_oracles={'static_fixture_unchanged':static_fixture_unchanged(fixture,current),
        'receipt':verify_receipts(receipts,dataset,fixture,phase='after_modules'),
        'measurements':verify_inputs(collect_inputs(fixture),projection,fixture,kinds=KINDS),
        'allocations':verify_allocations(collect_allocations(fixture),projection,allocation,fixture),
        'reports':verify_reports(collect_reports(fixture),receipts,projection,fixture,pdfs)}
    manifest['final_oracles']=final_oracles
    if not final_oracles['static_fixture_unchanged']:
        manifest.update(verdict='NO-GO',technical_status='INVALID',reason='STATIC_FIXTURE_CHANGED')
    if manifest['verdict']=='GO' and any(final_oracles[k]['status']!='PASS' for k in ('receipt','measurements','allocations','reports')):
        manifest.update(verdict='NO-GO',functional_status='NOT_CONFIRMED',reason='FINAL_ORACLE_FAILED')


def completion_text(manifest,records):
    def text(value):
        value=str(value).replace('\\','\\\\').replace('\n',' ').replace('\r',' ').replace('`',"'")
        for char in ('[',']','!','*','_','#','|'):value=value.replace(char,'\\'+char)
        return value.replace('<','&lt;').replace('>','&gt;')
    accounting=manifest.get('accounting',{})
    lines=['# NSN014 completion report','',f"Run: {manifest['run_id']}",f"Result: {manifest['verdict']}",
        f"Technical: {manifest['technical_status']}",f"Functional: {manifest['functional_status']}",
        f"Measurement: {manifest.get('measurement_status','NOT_STARTED')}",
        f"SQBF commit: {manifest['sqbf_commit']}",f"BLE build: {manifest['software_version']}",
        f"Executor: {manifest['executor_model']}; reviewer: {manifest['analyst_model']}",
        f"Model request attempts: {manifest.get('model_calls',0)}",'', '## Timing and usage','',
        f"AI controller elapsed seconds: {accounting.get('elapsed_seconds','unknown')}",
        f"Model wait seconds: {accounting.get('model_wait_seconds','unknown')}",
        f"Other controller elapsed seconds: {accounting.get('non_model_elapsed_seconds','unknown')}",'']
    for actor,usage in accounting.get('actors',{}).items():
        lines.append(f"- {actor}: {usage['model_calls']} request attempts")
        for key,value in usage['tokens'].items():
            total=value['complete_total'] if value['complete_total'] is not None else 'unknown'
            lines.append(f"  - {key}: total {total}; known sum {value['known_sum']}; unknown calls {value['unknown_calls']}")
    lines+=['','## Case results and independent evidence','']
    if manifest.get('final_oracles'):
        lines.insert(len(lines)-2,'Final independent Oracles: '+text({key:value.get('status') if isinstance(value,dict) else value for key,value in manifest['final_oracles'].items()}))
    for record in records:
        lines+=['### '+text(record['case_id']),'',
            f"Result: {text(record['result'])}; technical: {text(record.get('technical_gate','unverified'))}; oracle: {text(record.get('oracle_gate','unverified'))}"]
        if record.get('reason'):lines.append('Reason: '+text(record['reason']))
        if record.get('missing_prerequisites'):lines.append('Missing prerequisites: '+text(record['missing_prerequisites']))
        for item in [record]+record.get('positions',[]):
            if item.get('executor_statement'):
                lines.append('- Executor statement (unverified): '+text(item['executor_statement'].get('reason','')))
            review=item.get('review') or {}
            if review:
                lines.append('- Reviewer '+text(item.get('position_id','case'))+': '+text(review.get('verdict')))
                lines.append('  - UX scores: '+text(review.get('scores',{})))
                lines.extend('  - Finding: '+text(f) for f in review.get('findings',[]))
            for review in item.get('pdf_reviews',[]):
                lines.append('- PDF pages '+text(review['pages'])+': '+text(review['verdict'])+'; UX scores: '+text(review.get('scores',{})))
                lines.extend('  - Finding: '+text(f) for f in review.get('findings',[]))
        lines.append('')
    lines+=['## Evidence and interpretation','',
        '- Per-case events/screenshots, PDF downloads, cases.json and accounting.json remain local and private.',
        '- accounting.json records every request reservation and known usage before the next operation.',
        '- UX scores are individual reviewer judgements; there is no invented overall score.',
        '- AI controller time is not human work time. Existing standards remain unchanged; norm conformity is excluded.',
        '- Missing prerequisites/resource stops remain explicit; there is no automatic retry or repair.',
        '- Report numeric checks compare displayed raw-data precision, not regulatory compliance or release.',
        '- All PDF pages are rendered/reviewed in batches of at most three; raw PDF text is not sent to models.']
    return '\n'.join(lines)+'\n'

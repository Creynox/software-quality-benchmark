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
from sqbf.bounded import invoke_worker, model_spec, restore_model, suite_model_spec, BudgetExceeded
from sqbf.calibration import SuiteBudget, ResourceStop
from sqbf.models import Scenario
from sqbf.reporting import Evidence, now_iso, index_run
from sqbf.suites import suite_check, canonical_hash, aggregate, validate_suite, comparison_key
from sqbf.no_write_oracle import snapshot
from sqbf.oracle import verify_docker_identity
from sqbf.scope_check import verify_runtime
from . import report_html, report_spec, stage_effects
from .allocation_oracle import collect_allocations, verify_allocations
from .calculation_oracle import collect_report_calculations, persisted_basis, verify_calculations, expected_calculations
from .measurement_guard import make_contract
from .measurement_oracle import collect_inputs, verify_inputs, KINDS, PERSISTED_NAMES
from .report_oracle import collect_reports, verify_reports, expected_numbers
from .receipt_oracle import collect_receipts, verify_receipts, collect_plan_products, verify_plan_products
from .suite_acceptance import check_fixture
from .persona_scope import check_persona
from .measurement_runner import run_measurements, required_saves, INSTRUCTIONS as MEASUREMENT_INSTRUCTIONS
from .task_vocabulary import MODULE_TITLES
from .measurement_guard import CLASSIFY as MEASUREMENT_GUARD_RULES
from .inspection_guard import CLASSIFY as INSPECTION_GUARD_RULES
from .protected_oracle import collect_scoped_hashes
from .side_effect_probe import table_hashes
from .inspection_runner import run_inspection, run_reports, run_plan_creation, ENTRY_PATHS, INSTRUCTIONS as INSPECTION_INSTRUCTIONS
from .receipt_contract_check import check_receipt_form, check_entry_routes
from .stage_support import (REVIEW_SCHEMA, SCORING_VERSION, RUBRIC_VERSION, CATEGORIES, SEVERITIES, DIMENSIONS,
                            executor_schema, valid_review, cause_source)
from .provider_probe import evaluate_probe, provider_probe

CASE_KINDS={'NSN014-PREPARATION':['allocations','wash'],'NSN014-SIEVE':['sieve','partial'],
            'NSN014-SHAPE':['shape'],'NSN014-BOILING':['boiling'],'NSN014-SE':['sand']}
READ_CASES={'NSN014-RECEIPT','NSN014-ASSESS','NSN014-WPK','NSN014-ANALYSIS','NSN014-RIGHTS'}
CASE_IDS=READ_CASES|set(CASE_KINDS)|{'NSN014-PLAN','NSN014-REPORT'}
MUTABLE_TABLES={'samples','lims_sample','ble_reports','sqbf_measurement_inputs_v1','sqbf_allocation_inputs_v1'}
REPOSITORY=Path(__file__).resolve().parents[3]
SOURCE_PATHS=('sqbf','projects')
OBJECTIVE_STATUS={'INVALID':'INVALID_HARNESS'}
# A stage blocked only because its Oracle could not evaluate what the stage did (after the stage-effect gate passed) leaves the fixture as it is:
# the following stages still run (live run 824fa661 lost the read-only RIGHTS stage to the report Oracle). The stage itself stays BLOCKED.
EVALUATION_ONLY_BLOCKS={'REPORT_ORACLE_UNAVAILABLE'}


def objective_status(result):
    return OBJECTIVE_STATUS.get(result,result)


def static_state(fixture,current,*,resolved=(),scoped_baseline=None,collect=None):
    """Protected-data gate against the prepared baseline. Nothing may differ, except an audit-only stamp that a stage
    contract allows for exactly one table and its named target rows (live run 45eb301f: plan-wide sample creation stamps
    sampling_plans.updated_at/updated_by on the plan row). Raw hashes decide first; only if a table differs is the scoped
    comparison against the baseline taken at readiness made. Any other difference, the table set or the pinned baseline fails.
    """
    baseline=fixture['suite_copy']['prepared_tables']
    if canonical_hash(baseline)!=fixture['suite_copy']['prepared_state_sha256'] or set(baseline)!=set(current['tables']):
        return {'unchanged':False,'changed_tables':['BASELINE_OR_TABLE_SET'],'audit_only_tables':[],'audit_only':[]}
    differing=sorted(t for t,v in baseline.items() if t not in MUTABLE_TABLES and current['tables'][t]!=v)
    if not differing:return {'unchanged':True,'changed_tables':[],'audit_only_tables':[],'audit_only':[]}
    if not resolved or scoped_baseline is None or collect is None:
        return {'unchanged':False,'changed_tables':differing,'audit_only_tables':[],'audit_only':[]}
    delta=stage_effects.protected_delta(baseline,current['tables'],resolved,scoped_baseline,collect(fixture,resolved),mutable=MUTABLE_TABLES)
    return {'unchanged':delta['unchanged'],'changed_tables':delta['changed_tables'],
            'audit_only_tables':[a['table'] for a in delta['audit_only']],'audit_only':delta['audit_only']}


def static_fixture_unchanged(fixture,current,**kwargs):
    return static_state(fixture,current,**kwargs)['unchanged']


def static_gate(fixture,resolved,scoped_baseline,*,snapshot_fn=None,collect=None):
    snapshot_fn=snapshot_fn or snapshot
    return static_state(fixture,snapshot_fn(fixture,enforce_counts=False),resolved=resolved,scoped_baseline=scoped_baseline,
                        collect=collect or collect_scoped_hashes)


def all_tables(fixture,*,run=subprocess.run):
    """Count and hash of every public table (controller role, READ ONLY): the basis of the per-stage side-effect findings."""
    verify_docker_identity(fixture,run=run)
    db=fixture['database']
    return table_hashes(run,db['container'],db['bootstrap_user'],db['name'])


def capture_state(fixture,resolved,*,snapshot_fn=None,all_fn=None,collect=None):
    """Everything one stage gate compares: protected hashes, every public table, and the scoped rows of the allowances."""
    return {'tables':(snapshot_fn or snapshot)(fixture,enforce_counts=False)['tables'],'all':(all_fn or all_tables)(fixture),
            'scoped':(collect or collect_scoped_hashes)(fixture,resolved)}


def guarded_stage(fixture,contract,case_id,tracker,run_case,*,capture=None):
    """One stage between two captured states. The start state must equal the end of the previous stage (the prepared baseline for
    the first one), otherwise something outside the suite wrote to the protected data. After the stage only the contract's
    allowances may differ in the protected tables (INVALID otherwise); every other table is a finding, never an abort."""
    capture=capture or capture_state
    resolved=stage_effects.allowances(contract,fixture,case_id)
    before=capture(fixture,resolved)
    if before['tables']!=tracker['tables']:
        changed=sorted(t for t in tracker['tables'] if before['tables'].get(t)!=tracker['tables'][t])
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'STATIC_FIXTURE_CHANGED','changed_tables':changed}
    started=time.monotonic()
    result=dict(run_case())
    result['stage_wall_seconds']=round(time.monotonic()-started,3)
    after=capture(fixture,resolved)
    hard,facts=stage_effect_gate(fixture,contract,case_id,before,after,previous=tracker['previous'])
    tracker.update(tables=after['tables'],previous=after)
    if hard:
        return dict(result,result='INVALID',technical_gate='INVALID',reason='STATIC_FIXTURE_CHANGED',changed_tables=hard,**facts)
    return dict(result,**facts)


def stage_effect_gate(fixture,contract,case_id,before,after,*,previous=None):
    """Judge one stage from its start and end state. Returns (hard, facts): hard is the list of protected tables that changed
    outside an allowance (the suite stops), facts are findings and audit-only stamps for the record."""
    resolved=stage_effects.allowances(contract,fixture,case_id)
    delta=stage_effects.protected_delta(before['tables'],after['tables'],resolved,before['scoped'],after['scoped'],mutable=MUTABLE_TABLES)
    protected=set(fixture['suite_copy']['prepared_tables'])-MUTABLE_TABLES
    facts={'audit_only_changes':[a['table'] for a in delta['audit_only']],'audit_only_scope':delta['audit_only'],
           'side_effect_findings':stage_effects.findings(contract,case_id,before['all'],after['all'],protected=protected),
           'external_changes_before_stage':stage_effects.external_changes(previous['all'] if previous else None,before['all'])}
    return delta['changed_tables'],facts


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


def budget_approval(suite,fixture):
    """Extended resource profiles need a PO approval recorded in the private manifest.

    The record must name the profile, this exact suite hash and the exact ceilings, so a
    later suite edit or a larger limit invalidates it. Base-limit suites need no approval.
    """
    policy=suite['resource_policy'];profile=policy.get('profile')
    if profile is None:return {'status':'BASE_LIMITS','profile':None}
    bound={'profile':profile,'suite_sha256':canonical_hash(suite),
           'hard_seconds':policy['hard_seconds'],'hard_model_calls':policy['hard_model_calls']}
    approval=fixture['suite_copy'].get('budget_approval')
    if (not isinstance(approval,dict) or approval.get('approved_by')!='PO' or not approval.get('approved_at')
            or not approval.get('statement') or any(approval.get(k)!=v for k,v in bound.items())):
        return {'status':'BUDGET_APPROVAL_MISSING','profile':profile,'required':bound}
    return {'status':'BUDGET_APPROVED','profile':profile,'approved_at':approval['approved_at'],
            'approval_sha256':canonical_hash(approval)}


def check_ready(suite,dataset,fixture,projection,allocation,*,provider_probe=None,executor_id='gpt-6-luna',reviewer_id='gpt-6.1-sol'):
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
        try:contract=stage_effects.load_contract(CASE_IDS)
        except (stage_effects.ContractError,OSError,ValueError):return dict(blocked,reason='SIDE_EFFECT_CONTRACT_INVALID')
        scoped_baseline=collect_scoped_hashes(fixture,stage_effects.allowances(contract,fixture))
        public_tables=all_tables(fixture)
        side_effects={'contract_id':contract['contract_id'],'contract_sha256':stage_effects.contract_hash(contract),
                      'read_only_stages':sorted(k for k,v in contract['stages'].items() if v['mode']=='read_only'),
                      'write_stages':sorted(k for k,v in contract['stages'].items() if v['mode']=='write'),
                      'audit_only_allowances':[{k:a[k] for k in ('case_id','table','columns','max_rows')} for a in contract['audit_only_allowances']],
                      'public_tables_hashed':len(public_tables)}
        runtime=verify_runtime(fixture['target_url'],fixture['suite_copy']['application_root'],fixture['identity_scope_check'])
        if any(runtime[k]!=fixture['suite_copy']['runtime'][k] for k in ('assembly','sha256')):
            return dict(blocked,reason='ACTIVE_RUNTIME_MISMATCH')
        start=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='before')
        if (start['status']!='RECEIPT_START_VERIFIED' or collect_inputs(fixture)
                or collect_allocations(fixture) or collect_reports(fixture)):
            return dict(blocked,reason='UNUSED_START_STATE_NOT_VERIFIED')
        plan_products=verify_plan_products(collect_plan_products(fixture),fixture)
        if plan_products['status']!='PLAN_PRODUCTS_CREATABLE':
            return dict(blocked,reason='PLAN_PRODUCT_PRECONDITION_FAILED',plan_products=plan_products)
        policy=Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json',fixture['target_url']).read_only_policy
        form=check_receipt_form(fixture,dataset,policy)
        if form['status']!='RECEIPT_UI_CONTRACT_VERIFIED':return dict(blocked,reason='RECEIPT_UI_CONTRACT_FAILED',form=form)
        routes=check_entry_routes(fixture,policy,route_probes(suite,fixture))
        if routes['status']!='ENTRY_ROUTES_VERIFIED':return dict(blocked,reason='ENTRY_ROUTE_CONTRACT_FAILED',entry_routes=routes)
        probe=evaluate_probe(provider_probe,executor_id,reviewer_id)
        if probe['status'] in ('PROBE_FAILED','PROBE_NOT_CURRENT'):
            # A supplied probe that failed or is stale must not be read as "UX layer assured".
            return dict(blocked,reason='PROVIDER_PROBE_NOT_USABLE',provider_probe=probe)
        budget=budget_approval(suite,fixture)
        if budget['status']=='BUDGET_APPROVAL_MISSING':
            # Every other gate above passed; only the PO's budget decision is outstanding.
            return dict(blocked,reason='BUDGET_APPROVAL_MISSING',other_gates='PASSED',budget_approval=budget,
                        request_estimate=estimate,provider_probe=probe,plan_products=plan_products)
        return {'status':'READY_FOR_SINGLE_SUITE_RUN','model_calls':0,'database_writes':0,
                'budget_approval':budget,'provider_probe':probe,'plan_products':plan_products,'source':source,
                'protected_scoped_baseline':scoped_baseline,'side_effects':side_effects,'side_effect_contract':contract,
                'scoring_version':SCORING_VERSION,'rubric_version':RUBRIC_VERSION,'stage_contracts':contracts,
                'fixture_gates':gates,'dependencies':dependencies,'native_receipt_form':form,'entry_routes':routes,
                'active_runtime':runtime,'request_estimate':estimate,'persona_context':persona_context(suite,fixture),
                'fresh_subscription_authorization_required_at_execution':True,'current_provider_catalog_checked':False,
                'limitations':['Readiness is not a successful benchmark or proof of defect-free BLE behaviour.',
                               *([] if probe['ux_layer_assured'] else ['Provider schemas not probed: the UX layer may be unavailable (NOT_EVALUATED) during the run.']),
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
            evaluation_only=record.get('technical_gate')=='BLOCKED' and record.get('reason') in EVALUATION_ONLY_BLOCKS
            if (record.get('technical_gate') in ('BLOCKED','INVALID') and not evaluation_only or record['result']=='INVALID'
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
            contract=payload['side_effect_contract']
            if stage_effects.contract_hash(contract)!=payload['side_effect_contract_sha256']:raise ValueError('SIDE_EFFECT_CONTRACT_CHANGED')
            # The state the next stage must start from: the prepared baseline, then the end state of the previous stage.
            tracker={'tables':fixture['suite_copy']['prepared_tables'],'previous':None}
            def stage(case):
                def run_case():
                    return dispatch(case,browser,fixture,payload['dataset'],payload['projection'],payload['allocation'],
                                    policy,executor,reviewer,budget,Evidence(root/case['case_id']))
                return guarded_stage(fixture,contract,case['case_id'],tracker,run_case)
            records=execute_cases(suite,fixture,budget,stage,write=write)
            summary=aggregate(suite,records)
            return {'records':records,'summary':summary,'accounting':budget.report(),'browser_version':browser.version}
        finally:browser.close()


def run_suite(suite,dataset,fixture,projection,allocation,output,executor_id,reviewer_id,*,headed=False,provider_probe=None):
    """Explicit live entry point; preflight precedes browser OAuth or inference."""
    ready=check_ready(suite,dataset,fixture,projection,allocation,provider_probe=provider_probe,
                      executor_id=executor_id,reviewer_id=reviewer_id)
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
        ready=check_ready(suite,dataset,fixture,projection,allocation,provider_probe=provider_probe,
                          executor_id=executor_id,reviewer_id=reviewer_id)
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
        'executor_instructions_sha256':instructions_hash(),'guard_rules_sha256':guard_rules_hash(),
        'sqbf_commit':ready['source']['commit'],'sqbf_source_clean':ready['source']['clean'],
        'suite_sha256':canonical_hash(suite),'dataset_sha256':canonical_hash(dataset),
        'reference_projection_sha256':canonical_hash(projection),'allocation_reference_sha256':canonical_hash(allocation),
        'protected_scoped_baseline':ready['protected_scoped_baseline'],'side_effects':ready['side_effects'],
        'side_effect_contract_sha256':ready['side_effects']['contract_sha256'],
        'fixture_manifest_sha256':canonical_hash(fixture),
        'prepared_state_sha256':fixture['suite_copy']['prepared_state_sha256'],
        'environment':ready['dependencies'],'viewport':{'width':1280,'height':800},
        'locale':'de-DE','timezone':'Europe/Berlin',
        'ble_assembly_sha256':fixture['suite_copy']['runtime']['sha256'],
        'active_runtime':ready['active_runtime'],'request_estimate':ready['request_estimate'],
        'resource_policy':suite['resource_policy'],'budget_approval':ready['budget_approval'],'provider_probe':ready['provider_probe'],
        'verdict':'NO-GO','technical_status':'NOT_STARTED','functional_status':'NOT_RUN','model_calls':0,'execution_started':False}
    (evidence.path/'run.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    result={}
    try:
        from sqbf.plan_login import _load_host, authorize_or_reuse, catalog
        from sqbf.providers import ChatGPTPlanModel
        directory=Path(os.environ['LOCALAPPDATA'])/'SQBF'/'plan-login'
        credential=authorize_or_reuse(_load_host(directory));available=catalog(credential)
        if executor_id not in available or reviewer_id not in available:raise ValueError('MODEL_UNAVAILABLE')
        executor=ChatGPTPlanModel(executor_id,credential,executor_schema())
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
            'side_effect_contract':ready['side_effect_contract'],'side_effect_contract_sha256':ready['side_effects']['contract_sha256'],
            'executor':suite_model_spec(executor),'reviewer':suite_model_spec(reviewer)},suite['resource_policy']['hard_seconds'])
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
        write_run_documents(evidence.path,manifest,records)
        index_run(output,evidence.path)
    return {'status':'SUITE_RUN_RECORDED','run_id':manifest['run_id'],'verdict':manifest['verdict'],
            'technical_status':manifest['technical_status'],'path':str(evidence.path)}


def write_run_documents(path,manifest,records,*,history_roots=None,gates=None):
    """run.json first, then the reports: the points report is derived data and must never keep the manifest of a finished run from being written.
    bericht.html (for humans) compares with the newest earlier run of the same kind below `history_roots` (default: the folder's parent); a
    benchmark run also refreshes uebersicht.html in its parent folder."""
    card=None
    try:
        card=scorecard_of(manifest,records)
        manifest['report_spec']={'spec_version':card['spec_version'],'spec_sha256':card['spec_sha256'],'run_result':card['result']['run_result'],
                                 'points':card['points']['points'],'max_points':card['points']['max_points']}
    except Exception as error:
        manifest['report_spec']={'error':type(error).__name__}
    # Credentials/tokens never enter persisted manifests or reports.
    (path/'run.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (path/'completion-report.md').write_text(completion_text(manifest,records),encoding='utf-8')
    if card:
        (path/'scorecard.json').write_text(json.dumps(card,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (path/'punktebericht.md').write_text('\n'.join(report_spec.render(card))+'\n',encoding='utf-8')
        try:
            report_html.write_report(path,card,history_roots=tuple(history_roots) if history_roots else (path.parent,),gates=gates)
            if card['run'].get('kind','BENCHMARK')=='BENCHMARK':report_html.write_overview(path.parent)
        except Exception as error:
            manifest['report_html']={'error':type(error).__name__}
            (path/'run.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')


def finalise_oracles(manifest,result,fixture,dataset,projection,allocation,current):
    receipts=collect_receipts(fixture)
    pdfs=[]
    for record in result.get('records',[]):
        if record['case_id']=='NSN014-REPORT':
            pdfs=record.get('downloads',[]) or [d for p in record.get('positions',[]) for d in p.get('downloads',[])]
    basis=persisted_basis(collect_inputs(fixture))
    contract=stage_effects.load_contract(CASE_IDS)
    if stage_effects.contract_hash(contract)!=manifest.get('side_effect_contract_sha256'):
        static={'unchanged':False,'changed_tables':['SIDE_EFFECT_CONTRACT_CHANGED'],'audit_only_tables':[],'audit_only':[]}
    else:
        # Every stage was judged on its own while it ran; this is the run-wide check against the prepared baseline, with the
        # allowances of all stages and the scoped baseline taken at readiness.
        static=static_state(fixture,current,resolved=stage_effects.allowances(contract,fixture),
                            scoped_baseline=manifest.get('protected_scoped_baseline'),collect=collect_scoped_hashes)
    stage_findings=[{'case_id':r['case_id'],'findings':r['side_effect_findings']} for r in result.get('records',[]) if r.get('side_effect_findings')]
    final_oracles={'static_fixture_unchanged':static['unchanged'],'static_fixture_audit_only_tables':static['audit_only_tables'],
        'static_fixture_audit_only_scope':static['audit_only'],'side_effect_findings':stage_findings,
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
            'oracle_gate':record.get('oracle_gate'),'reason':record.get('reason') or record.get('stop_reason') or record.get('error_code'),
            'review_errors':sorted({i['review_error'] for i in [record]+record.get('positions',[]) if i.get('review_error')}),
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


def guard_rules_hash():
    """Hash of the click rules of both guards: what the executor may do changes with them (PO decision 2026-10-19: passive text, boiling selector,
    save in the allocation task), so runs with different rules are not directly comparable either."""
    return canonical_hash({'measurement':MEASUREMENT_GUARD_RULES,'inspection':INSPECTION_GUARD_RULES})


def instructions_hash():
    """Hash of everything the executor is told besides the screenshot (instructions of both runners, module titles): runs with different wording
    are not directly comparable (the neutral hint of 2026-10-19 changed run 7 against run 6)."""
    return canonical_hash({'measurement':MEASUREMENT_INSTRUCTIONS,'inspection':INSPECTION_INSTRUCTIONS,'module_titles':MODULE_TITLES})


def effort_rows(records):
    """One row per measured task: operating effort (actions, scrolls, scrolls after the last typed value, rejected clicks), what became of the save
    and where an incomplete position comes from. Measurements for the separation of model, suite and BLE causes; not a verdict."""
    rows=[]
    for record in records:
        results={p['position_id']:p for p in record.get('position_results',[])}
        for item in record.get('positions',[]):
            effort=item.get('effort')
            if not effort:continue
            result=results.get(item.get('position_id'))
            reached=item.get('module_reached')
            save_rejected=any(isinstance(r.get('target'),dict) and r['target'].get('label')=='Speichern' for r in item.get('rejected_actions',[]))
            rows.append({'case':str(record['case_id']).replace('NSN014-',''),'position':item.get('position_id','—'),'kind':item.get('kind','—'),
                         'reached':'—' if reached is None else 'ja' if reached else 'nein','status':item.get('status','—'),
                         'origin':cause_source(result.get('result'),result.get('class'),effort['rejected'],reached=reached,save_rejected=save_rejected) if result else '—',
                         'effort':effort,'save':item.get('save_status','—')})
    return rows


def scorecard_of(manifest,records):
    """The evaluation as numbers by the fixed specification (report_spec): checks, points, origins, operating measurements, cost, comparability.
    The reviewer answers are counted for their own section; they never change a point."""
    return report_spec.build_scorecard(manifest,records,effort_rows(records),[review for record in records for review in _reviews(record)])


def punktebericht(manifest,records):
    """The report for the PO and the review agent: fixed sections, fixed tables, fixed wording (specification nsn014-report-spec, versioned)."""
    return report_spec.render(scorecard_of(manifest,records))


def completion_text(manifest,records):
    def text(value):
        value=str(value).replace('\\','\\\\').replace('\n',' ').replace('\r',' ').replace('`',"'")
        for char in ('[',']','!','*','_','#','|'):value=value.replace(char,'\\'+char)
        return value.replace('<','&lt;').replace('>','&gt;')
    accounting=manifest.get('accounting',{})
    try:top=punktebericht(manifest,records)
    except Exception as error:top=['# NSN014 Punktebericht','',f'Der Punktebericht konnte nicht erzeugt werden ({type(error).__name__}); cases.json und run.json sind unverändert.']
    lines=top+['','---','','# Anhang: Detailbericht (Belege, nicht Teil der Punkte)','','## A0. Lauf','',
        f"- Lauf: {text(manifest['run_id'])}",f"- Gesamtergebnis: {text(manifest['verdict'])}",
        f"- Technischer Status: {text(manifest['technical_status'])}",f"- Funktionaler Status: {text(manifest['functional_status'])}",
        f"- Messstatus: {text(manifest.get('measurement_status','NOT_STARTED'))}",
        f"- Suite: {text(manifest['scenario_id'])} v{text(manifest['scenario_version'])}; Bewertung {text(manifest.get('scoring_version'))}; "
        f"UX-Rubrik {text(manifest.get('rubric_version'))} (vorläufig)",
        f"- SQBF-Commit: {text(manifest['sqbf_commit'])}; BLE-Build: {text(manifest['software_version'])}",
        f"- Executor: {text(manifest['executor_model'])}; Reviewer: {text(manifest['analyst_model'])}",
        f"- Modellanfragen: {text(manifest.get('model_calls',0))} von höchstens {text(manifest['resource_policy']['hard_model_calls'])}; "
        f"Zeitgrenze {text(manifest['resource_policy']['hard_seconds'])} s; Budgetfreigabe: {text(manifest['budget_approval']['status'])}",
        f"- Provider-Vorabprüfung: {text(manifest.get('provider_probe',{}).get('status','NOT_PROBED'))}",
        f"- Executor-Anweisung und Aufgabenwortlaut (SHA256): {text(manifest.get('executor_instructions_sha256','nicht erfasst'))}; Läufe mit anderem Wortlaut sind nicht direkt vergleichbar",
        f"- Klickregeln der Guards (SHA256): {text(manifest.get('guard_rules_sha256','nicht erfasst'))}; Läufe mit anderen Regeln sind ebenfalls nicht direkt vergleichbar",'']
    if manifest.get('final_oracles'):
        lines+=['Abschließende unabhängige Oracles: '+text({key:value.get('status') if isinstance(value,dict) else value
                                                       for key,value in manifest['final_oracles'].items()}),'']
    matrix=manifest.get('case_matrix') or case_matrix(records)
    lines+=['## A0a. Stufenmatrix','','| Stufe | Persona | Objektiver Status | Grund | UX-Urteil |','|---|---|---|---|---|']
    for row in matrix:
        lines.append('| '+' | '.join(text(v) for v in (row['case_id'],row['persona'],row['objective_status'],
                                                       row['reason'] or '—',row['ux_verdict']))+' |')
    passed=[r for r in matrix if r['objective_status']=='PASS']
    failed=[r for r in matrix if r['objective_status']=='FAIL']
    lines+=['','## A1. Was in BLE funktioniert','']
    lines+=['- '+text(r['case_id'])+': objektiv bestanden' for r in passed] or ['- Keine Stufe objektiv bestanden.']
    for row in matrix:
        good=[p['position_id'] for p in row['position_results'] if p['result']=='PASS']
        if good and row['objective_status']!='PASS':lines.append('- '+text(row['case_id'])+': bestandene Positionen '+text(good))
    lines+=['','## A2. Was in BLE nicht funktioniert','']
    lines+=['- '+text(r['case_id'])+': '+text(r['fail_classes'] or r['reason'])+'; Positionen '+
            text([p['position_id'] for p in r['position_results'] if p['result']=='FAIL']) for r in failed] or [
            '- Keine objektiv belegte BLE-Abweichung.']
    lines+=['','## A3. BLE- oder SQBF-Problem','']
    for row in matrix:
        if row['objective_status']!='PASS':
            lines.append('- '+text(row['case_id'])+' ('+text(row['objective_status'])+'): '+
                         text(ATTRIBUTION.get({'INVALID_HARNESS':'INVALID'}.get(row['objective_status'],row['objective_status']),'')))
    lines+=['','## A3a. Ursachen unvollständiger Positionen und Bedienaufwand','',
            'Ursprung: MODELL = der Agent hat aufgegeben, nicht gespeichert oder ein Feld nicht übernommen; SUITE = Test-Suite (Guard-Ablehnung, Wortlaut, Harness); '
            'PROVIDER = Anfrage ausgefallen; VORSTUFE = Voraussetzung fehlt (Modul nicht geöffnet, Feld nicht angeboten, Vorstufe unvollständig); '
            'BLE-ABWEICHUNG = objektiv belegt. Bedienprobleme von BLE (etwa die Auffindbarkeit der Speicherschaltfläche) stehen nur als unbestätigte '
            'Reviewer-Beobachtungen in Abschnitt A4 und in Abschnitt 8 des Punkteberichts (nur gezählt). Aktionen, Scrolls, abgelehnte Klicks und Speicherstatus sind Messwerte, kein Urteil.','']
    rows=effort_rows(records)
    if rows:
        lines+=['| Stufe | Position | Modul | Modul erreicht | Status | Ursprung | Aktionen | Scrolls | davon nach letzter Eingabe | abgelehnte Klicks | Speichern |','|---|---|---|---|---|---|---|---|---|---|---|']
        for row in rows:
            effort=row['effort']
            lines.append('| '+' | '.join(text(v) for v in (row['case'],row['position'],row['kind'],row['reached'],row['status'],row['origin'],effort['actions'],effort['scrolls'],
                                                         '—' if effort['scrolls_after_last_entry'] is None else effort['scrolls_after_last_entry'],
                                                         effort['rejected'],row['save']))+' |')
        saves={}
        for row in rows:saves[row['save']]=saves.get(row['save'],0)+1
        lines+=['',f"Summe: {text(sum(r['effort']['actions'] for r in rows))} Aktionen, {text(sum(r['effort']['scrolls'] for r in rows))} Scrolls, "
                f"{text(sum(r['effort']['rejected'] for r in rows))} abgelehnte Klicks; Speichern: "+text(', '.join(f'{k} {v}' for k,v in sorted(saves.items()))),'']
    else:
        lines+=['- Keine Bedienaufwand-Messung vorhanden.','']
    summary=manifest.get('ux_summary') or ux_summary(records)
    lines+=['','## A4. UX-Befunde nach Kategorie und Schweregrad','',
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
    lines+=['','## A5. Priorität','',
            'P1 objektive BLE-Abweichungen (fachlich bestätigen, dann BLE-Issue):']
    lines+=['- '+text(r['case_id'])+': '+text(r['fail_classes']) for r in failed] or ['- keine']
    lines+=['P2 Harness-/Voraussetzungsstopps vor einem Retest beheben:']
    lines+=['- '+text(r['case_id'])+': '+text(r['reason'] or 'Grund nicht erfasst') for r in matrix if r['objective_status'] in ('INVALID_HARNESS','BLOCKED')] or ['- keine']
    lines+=['- UX-Review ausgefallen in '+text(r['case_id'])+': '+text(', '.join(r['review_errors'])) for r in matrix if r['review_errors']]
    lines+=['P3 kritische/major UX-Befunde:']+(['- '+e for e in priority] or ['- keine'])
    lines+=['P4 weitere UX-Befunde (minor/info):']+(['- '+e for e in minor] or ['- keine'])
    lines+=['','## A6. Retest-Benchmark','',
        f"- Vergleichsschlüssel (Suite, Datensatz, Modelle, Viewport, Browser): {text(manifest.get('comparison_key','nicht verfügbar'))}",
        f"- Suite-SHA256: {text(manifest['suite_sha256'])}; Datensatz-SHA256: {text(manifest['dataset_sha256'])}",
        f"- Fixture-Startzustand-SHA256: {text(manifest.get('prepared_state_sha256'))}",
        '- Retest: neue Fixture aus derselben Golden-Basis, gleiche Suite-/Bewertungs-/Rubrik-Version, ein Lauf ohne Retry.',
        '- Verglichen werden Prüfpunkte, Punkte und Quoten des Punkteberichts (Abschnitt 7 dort nennt die Bedingungen); UX-Werte nur als Beobachtung.',
        '','## A7. Zeit und Nutzung','',
        f"Controller-Laufzeit (s): {text(accounting.get('elapsed_seconds','unbekannt'))}",
        f"Modell-Wartezeit (s): {text(accounting.get('model_wait_seconds','unbekannt'))}",
        f"Übrige Controller-Zeit (s): {text(accounting.get('non_model_elapsed_seconds','unbekannt'))}",'']
    for actor,usage in accounting.get('actors',{}).items():
        lines.append(f"- {text(actor)}: {text(usage['model_calls'])} Anfragen")
        for key,value in usage['tokens'].items():
            total=value['complete_total'] if value['complete_total'] is not None else 'unbekannt'
            lines.append(f"  - {text(key)}: gesamt {text(total)}; bekannte Summe {text(value['known_sum'])}; ohne Angabe {text(value['unknown_calls'])}")
    lines+=['','## A8. Stufendetails','']
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
    lines+=['## A9. Evidenz und Interpretation','',
        '- Ereignisse, Screenshots, PDF-Downloads, cases.json, accounting.json und run.json bleiben lokal und privat.',
        '- Objektive Status stammen aus Controller- und unabhängigen Read-only-Oracles; der Reviewer bestimmt sie nicht.',
        '- Harte Sicherheits- oder Datenfehler werden nicht durch UX-Werte kompensiert; die Punkte stehen im Punktebericht oben.',
        '- Berechnungen werden aus persistierten Rohdaten unabhängig nachgerechnet; Teilsiebung/gekoppelte Siebung ist NOT_COVERED.',
        '- KI-Controllerzeit ist keine menschliche Arbeitszeit. Normkonformität und Freigabe sind ausgeschlossen.',
        '- Fehlende Voraussetzungen und Ressourcenstopps bleiben explizit; es gibt keinen automatischen Retry.']
    return '\n'.join(lines)+'\n'

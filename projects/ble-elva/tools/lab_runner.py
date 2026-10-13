"""One bounded LAB-01 attempt; read-only persistence verification in parent."""
from dataclasses import asdict
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import time
import subprocess
from urllib.parse import urlsplit
from uuid import uuid4

from sqbf.bounded import LabBudget, BudgetExceeded, ask_bounded, invoke_worker, model_spec, restore_model
from .lab_guard import KEYS, allowed_path, check_action, event_guard, transport_allowed, validate_target, validate_source
from sqbf.models import Scenario, validate_action, safe_action_log, ActionValidationError
from sqbf.no_write_oracle import snapshot
from sqbf.oracle import collect_snapshot, verify_before, verify_after
from sqbf.read_only import ReadOnlyViolation
from sqbf.reporting import Evidence, index_run
from sqbf.session_credentials import load_credentials
from sqbf.smoke_runner import ACTION_SCHEMA, decision_metadata

LAB_ACTION_SCHEMA = copy.deepcopy(ACTION_SCHEMA)
LAB_ACTION_SCHEMA['properties']['key']['enum'] = [None, *KEYS]
INSTRUCTIONS = '''Act as a real user using only screenshots, task and your prior visible actions.
Return one strict JSON action with all fields, null for unused fields. Coordinates are screenshot pixels.
No tools, code, DOM, APIs, files, passwords, browser shortcuts or hidden URLs.
Create only the requested synthetic product through visible core fields. No norms, samples, reports,
limits, optional fields, activation switches, edits or deletions. Click Speichern exactly once only after
all requested fields are correct. If validation fails, stop blocked; do not retry saving.
After saving, return to products, find and reopen the saved product and inspect its fields before done.
The visible Produkt bearbeiten icon may be used only to reopen the saved fields for inspection;
do not change any value or save again there.
Allowed keys: ControlOrMeta+A, Backspace, Delete, Escape. Use clicks to select dropdown options.
'''
REVIEW_INSTRUCTIONS = '''Independently judge this product-creation workflow from screenshots and visible actions only.
No database evidence is provided. PASS requires visibly saved and reopened product with requested fields;
otherwise FAIL or INCONCLUSIVE. Distinguish executor difficulties from product UX issues.
Scores 0-5 for findability, clarity, task_progress, error_recovery. Strict JSON, no tools.
'''


def review_images(images, reopened):
    """Respect the provider's existing three-image bound."""
    if len(reopened)>=3:
        return [reopened[0],reopened[len(reopened)//2],reopened[-1]]
    return [images[0]]+(reopened if reopened else images[-2:])


def browser_pilot(payload):
    from playwright.sync_api import sync_playwright
    from sqbf.runner import apply_action
    scenario = Scenario(**payload['scenario'])
    executor, reviewer = restore_model(payload['executor']), restore_model(payload['reviewer'])
    budget = LabBudget(payload['seconds'], scenario.max_model_calls)
    evidence = Evidence.attach(payload['folder'])
    started = time.monotonic()
    actions, usage, images = [], [], []
    status, review, model_wait = 'INCOMPLETE', None, 0.0
    saved = left = reopened = False
    reopened_images=[]

    def ask(model, prompt, png, stage):
        nonlocal model_wait
        evidence.event('model_call_started', stage=stage)
        t = time.monotonic()
        try:
            return ask_bounded(model, prompt, png, budget)
        finally:
            elapsed = time.monotonic()-t
            model_wait += elapsed
            evidence.event('model_call_finished', stage=stage, duration_seconds=round(elapsed, 6))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not payload['headed'])
        try:
            context = browser.new_context(viewport={'width':1280,'height':800}, storage_state=payload['storage_state'],
                                         accept_downloads=False, service_workers='block')
            context.add_init_script(event_guard())
            origin = scenario.url.rstrip('/')
            def request(route):
                if transport_allowed(route.request.url,route.request.method,origin,scenario.read_only_policy):
                    route.continue_()
                else:
                    evidence.event('blocked_request',method=route.request.method,path=urlsplit(route.request.url).path)
                    route.abort()
            context.route('**/*', request)
            page = context.new_page()
            page.set_default_timeout(3000)
            page.goto(scenario.url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(1000)
            for turn in range(scenario.max_actions+1):
                budget.remaining()
                path=urlsplit(page.url).path
                if not allowed_path(path): raise ReadOnlyViolation('LAB_PAGE_SCOPE_DENIED')
                is_record=path not in ('/','/products','/products/new')
                if saved and path=='/products':left=True
                if saved and left and is_record:reopened=True
                png=page.screenshot(animations='disabled',timeout=min(5000,budget.remaining()*1000))
                evidence.snapshot(png,f'step-{len(actions)}');images.append(png)
                if reopened:reopened_images.append(png)
                if len(actions)>=scenario.max_actions:raise BudgetExceeded('Action budget exhausted')
                if budget.calls>=budget.limit-1:raise BudgetExceeded('Executor call budget exhausted')
                result=ask(executor,INSTRUCTIONS+'\nTASK:\n'+scenario.task+'\nPREVIOUS VISIBLE ACTIONS:\n'+
                           json.dumps(actions,ensure_ascii=False),png,'executor')
                usage.append({'stage':'executor','usage':result.usage})
                action={k:v for k,v in result.data.items() if v is not None}
                metadata=decision_metadata(action)
                evidence.event('action_received',turn=turn+1,**metadata)
                try:
                    validate_action(action,1280,800)
                    state=check_action(page,action)
                except (ActionValidationError,ReadOnlyViolation) as e:
                    evidence.event('action_rejected',turn=turn+1,error_code=e.code if isinstance(e,ActionValidationError) else 'LAB_ACTION_SCOPE_DENIED',**metadata)
                    raise
                evidence.event('agent_decision',**safe_action_log(action))
                if action['action'] in ('done','blocked'):
                    status=action['action'].upper();break
                if state['target']['kind']=='save':saved=True
                apply_action(page,action);actions.append(action)
                page.wait_for_timeout(500)
            if images:
                # Up to three initial/reopened views, within provider bounds.
                # No DOM/Oracle facts or source hints reach the reviewer.
                selection=review_images(images,reopened_images)
                result=ask(reviewer,REVIEW_INSTRUCTIONS+'\n'+json.dumps({'task':scenario.task,'actions':actions},ensure_ascii=False),
                           selection,'reviewer')
                usage.append({'stage':'reviewer','usage':result.usage});review=result.data
                if any(type(v) is not int or not 0<=v<=5 for v in review['scores'].values()):raise ValueError()
        except Exception as e:
            status='BLOCKED_TIMEOUT' if isinstance(e,BudgetExceeded) else 'BLOCKED_WRITE_SCOPE' if isinstance(e,ReadOnlyViolation) else 'ERROR'
            evidence.event('stopped_fail_closed',error_code=e.code if isinstance(e,ActionValidationError) else status)
        finally:
            browser.close()
    return {'executor_status':status,'actions':len(actions),'model_calls':budget.calls,'usage':usage,
            'usage_unavailable_calls':budget.calls-len(usage),'review':review,'events':evidence.events,'images':evidence.images,
            'model_wait_seconds':round(model_wait,6),'timing_complete':True,
            'save_clicked_once':saved,'returned_to_list':left,'reopened':reopened}


def oracle_dsn(fixture):
    from psycopg.conninfo import make_conninfo
    credentials=load_credentials(Path(fixture['oracle_credential_file']),'sqbf_oracle_ro')
    return make_conninfo(host='127.0.0.1',port=fixture['database']['host_port'],dbname=fixture['database']['name'],
                         user='sqbf_oracle_ro',password=credentials['password'],connect_timeout=5)


def unchanged_except_product(before,after):
    return before['docker']==after['docker'] and before['identity']==after['identity'] and all(
        before['tables'][k]==after['tables'].get(k) for k in before['tables'] if k!='workspace_products')


def runner_identity():
    root=Path(__file__).resolve().parents[3]
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True,timeout=5).stdout.strip()
    dirty=subprocess.run(['git','status','--porcelain'],cwd=root,capture_output=True,text=True,check=True,timeout=5).stdout.strip()
    if dirty:raise ReadOnlyViolation('RUNNER_SOURCE_DIRTY')
    return head


def run_lab(scenario,executor,reviewer,output_root,storage_state,headed,fixture_path):
    fixture=json.loads(Path(fixture_path).read_text(encoding='utf-8-sig'))
    validate_target(scenario,fixture)
    runner_commit=runner_identity()
    if not storage_state or reviewer is None:raise ValueError('LAB requires session and separate reviewer')
    source=json.loads(Path(fixture['working_copy']['source_fixture']).read_text(encoding='utf-8-sig'))
    validate_source(source)
    if snapshot(source)!=fixture['working_copy']['source_snapshot']:raise ReadOnlyViolation('SOURCE_CHANGED')
    before=snapshot(fixture)
    dsn=oracle_dsn(fixture)
    baseline=verify_before(collect_snapshot(dsn,fixture),fixture)
    folder=Path(output_root)/str(uuid4());evidence=Evidence(folder)
    started=time.monotonic()
    manifest={'run_id':folder.name,'scenario_id':scenario.scenario_id,'scenario_version':scenario.scenario_version,
              'persona':scenario.persona,'fixture_id':fixture['fixture_id'],'software_version':scenario.software_version,
              'executor_model':'chatgpt_plan:'+executor.model,'analyst_model':'chatgpt_plan:'+reviewer.model,
              'budget_actions':scenario.max_actions,'budget_minutes':scenario.max_minutes,'budget_model_calls':scenario.max_model_calls,
              'started_at':datetime.now(timezone.utc).isoformat(),'auth':'SEPARATE_CHATGPT_PLAN_OAUTH','tokens_persisted':False}
    manifest['runner_commit']=runner_commit
    manifest['fixture_setup_worktree_commit']=fixture['fixture_setup_worktree_commit']
    (folder/'oracle-before.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
    result={};review=None;oracle={'status':'UNVERIFIED'}
    try:
        seconds=scenario.max_minutes*60-60
        result=invoke_worker('lab-pilot',{'scenario':asdict(scenario),'executor':model_spec(executor),'reviewer':model_spec(reviewer),
             'folder':str(folder),'storage_state':str(Path(storage_state).resolve()),'headed':headed,'seconds':seconds},seconds)
        evidence.events=result['events'];evidence.images=result['images'];review=result['review']
    except Exception as e:
        for name,attribute in [('events.json','events'),('evidence.json','images')]:
            path=folder/name
            if path.exists():setattr(evidence,attribute,json.loads(path.read_text(encoding='utf-8')))
        evidence.event('stopped_fail_closed',error_code='BUDGET_EXCEEDED' if isinstance(e,BudgetExceeded) else 'WORKER_FAILURE')
    # Mandatory even after failure. No writes, cleanup, fallback or retries.
    source_unchanged=others_unchanged=None
    try:
        source_unchanged=snapshot(source)==fixture['working_copy']['source_snapshot']
    except Exception:
        source_unchanged=False
    try:
        others_unchanged=unchanged_except_product(before,snapshot(fixture,enforce_counts=False))
    except Exception:
        others_unchanged=False
    try:
        after=collect_snapshot(dsn,fixture)
        (folder/'oracle-after.json').write_text(json.dumps(after,indent=2,default=str),encoding='utf-8')
        persistence=verify_after(after,fixture,baseline)
        oracle={'status':'PASS' if others_unchanged and source_unchanged else 'FAIL','persistence':persistence,
                'protected_tables_unchanged':others_unchanged,'source_unchanged':source_unchanged}
    except Exception:
        oracle={'status':'FAIL','error_code':'PERSISTENCE_OR_ISOLATION_FAILED',
                'protected_tables_unchanged':others_unchanged,'source_unchanged':source_unchanged}
    valid_images=len(evidence.images)>=2 and all(hashlib.sha256((folder/i['name']).read_bytes()).hexdigest()==i['sha256'] for i in evidence.images)
    technical='PASS' if result.get('executor_status')=='DONE' and result.get('reopened') and valid_images and review and time.monotonic()-started<scenario.max_minutes*60 else 'FAIL'
    verdict='GO' if technical=='PASS' and oracle['status']=='PASS' and review['verdict']=='PASS' else 'NO-GO'
    manifest.update({k:v for k,v in result.items() if k not in ('events','images','review')})
    manifest.update(executor_status=result.get('executor_status','ERROR'),actions=result.get('actions',0),
                    model_calls=result.get('model_calls',sum(e['kind']=='model_call_started' for e in evidence.events)),
                    technical_status=technical,functional_status=oracle['status'],oracle=oracle,
                    completion_status=verdict,wall_seconds=round(time.monotonic()-started,2),finished_at=datetime.now(timezone.utc).isoformat())
    manifest['active_seconds_excluding_model_wait']=round(max(0,manifest['wall_seconds']-result['model_wait_seconds']),6) if result.get('timing_complete') else None
    (folder/'oracle.json').write_text(json.dumps(oracle,indent=2,default=str),encoding='utf-8')
    evidence.finish(manifest,review,verdict);index_run(Path(output_root),folder)
    return folder

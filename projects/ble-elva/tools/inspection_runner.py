"""Inspection/report controller; screenshots and visible inputs only reach models."""
import base64
import json
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from sqbf.bounded import invoke_worker
from sqbf.calibration import ResourceStop, ask_calibrated
from sqbf.models import validate_action, safe_action_log, ActionValidationError
from sqbf.no_write_oracle import snapshot
from sqbf.read_only import ReadOnlyViolation
from sqbf.runner import apply_action
from .inspection_guard import contract, event_guard, check_action, transport_allowed
from .persona_scope import check_persona
from .receipt_oracle import collect_receipts,verify_receipts
from .report_oracle import collect_reports, verify_reports, expected_numbers

INSTRUCTIONS='''Use only screenshots, the task and prior visible actions. Return one strict JSON UI action.
No tools, code, files, DOM, DB, APIs, browser shortcuts, hidden URLs or passwords.
Inspect permitted screens; do not create, change, save, delete, release, sign, finalize or send data.
Only if this task explicitly allows a non-official report: generate one Prüfbericht per requested sample
and download its PDF once. Never regenerate, archive, delete or mark a report official.
Only if this task explicitly allows plan sample creation: create the designated existing plan's samples once. No manual extra samples or second creation attempt.
If unavailable, explain blocked. Completion requires visible evidence; never invent missing data.
'''


def run_view(browser,fixture,persona,entry,paths,task,policy,executor,reviewer,budget,evidence,*,report_position=None,plan_samples=False):
    config=contract(fixture,paths,report=report_position is not None,plan_samples=plan_samples)
    context=browser.new_context(viewport={'width':1280,'height':800},storage_state=fixture['personas'][persona]['storage_state'],
        locale='de-DE',timezone_id='Europe/Berlin',
        service_workers='block',accept_downloads=report_position is not None)
    images,actions,downloads=[],[],[];generated=set();downloaded=set()
    outcome={'status':'INCONCLUSIVE','technical_gate':'PASS','review':None,'downloads':downloads}
    try:
        context.add_init_script(event_guard(config))
        context.route('**/*',lambda route:route.continue_() if transport_allowed(route.request.url,route.request.method,config,policy) else route.abort())
        page=context.new_page();page.set_default_timeout(3000)
        page.goto(config['origin']+entry,wait_until='domcontentloaded',timeout=min(15000,budget.remaining()*1000));page.wait_for_timeout(800)
        pdf_images=[]
        while True:
            budget.remaining()
            if urlsplit(page.url).path=='/login':raise ReadOnlyViolation('SESSION_INVALIDATED')
            png=page.screenshot(animations='disabled',timeout=min(5000,budget.remaining()*1000))
            images.append(png);evidence.snapshot(png,'inspection')
            answer=ask_calibrated(executor,INSTRUCTIONS+'\nTask:\n'+task+'\nPrevious visible actions:\n'+
                json.dumps(actions,ensure_ascii=False),png,budget,'executor')
            action={k:v for k,v in answer.data.items() if v is not None};validate_action(action,1280,800)
            state=check_action(page,action,config,generated)
            if state['kind']=='download' and state['scope'] in downloaded:raise ReadOnlyViolation('DUPLICATE_PDF_DOWNLOAD')
            evidence.event('inspection_action',persona=persona,**safe_action_log(action))
            if action['action'] in ('done','blocked'):
                outcome['status']=action['action'].upper();outcome['executor_statement']=safe_action_log(action);break
            if state['kind'] in ('generate','plan_samples'):generated.add(state['scope'])
            budget.action()
            if state['kind']=='download':
                downloaded.add(state['scope'])
                with page.expect_download(timeout=min(15000,budget.remaining()*1000)) as pending:
                    apply_action(page,action)
                download=pending.value
                path=evidence.path/('download-'+uuid4().hex+'.pdf')
                download.save_as(path)
                pdf=invoke_worker('pdf-check',{'path':str(path),'required_text':[
                    report_position['sample_code'],report_position['product'],'Enzberg']},min(15,budget.remaining()))
                pdf_images=[base64.b64decode(p) for p in pdf.pop('images')]
                for image in pdf_images:evidence.snapshot(image,'report-pdf')
                downloads.append(dict(pdf,report_id=state['scope'].split('/')[-1],file_name=path.name))
            else:apply_action(page,action)
            actions.append(action);page.wait_for_timeout(500)
        selected=[images[i] for i in sorted(set((0,len(images)//2,len(images)-1)))]
        review=ask_calibrated(reviewer,'Independently review the requested UI workflow and, if supplied, rendered PDF pages. '
            'Use only these images and visible actions. No DB facts. Separate agent difficulty, UI defects and unsupported assertions. '
            'No normative conformity or release verdict. Return configured strict review schema.\n'+task+'\n'+
            json.dumps({'visible_actions':actions,'unverified_executor_statement':outcome.get('executor_statement')},ensure_ascii=False),selected,budget,'reviewer')
        outcome['review']=review.data
        if pdf_images:
            outcome['pdf_reviews']=[]
            for offset in range(0,len(pdf_images),3):
                expected={k:str(v) for k,v in expected_numbers(report_position).items()}
                batch=ask_calibrated(reviewer,
                    'Review only these rendered PDF pages for identity, readable layout and visible values inconsistent with the supplied source test inputs. '
                    'These inputs are instructions, not DB persistence evidence. Do not require every field on each page batch; other pages are reviewed separately. '
                    'No normative conformity, release or signature claim. Return configured strict review schema.\n'+
                    json.dumps({'task':task,'pages':list(range(offset+1,min(offset+4,len(pdf_images)+1))),
                                'total_pages':len(pdf_images),'source_expected_display_inputs':expected},ensure_ascii=False),
                    pdf_images[offset:offset+3],budget,'reviewer')
                outcome['pdf_reviews'].append(dict(batch.data,pages=list(range(offset+1,min(offset+4,len(pdf_images)+1)))))
    except ResourceStop:
        outcome.update(status='INCONCLUSIVE',stop_reason=budget.stop_reason)
    except (ReadOnlyViolation,ActionValidationError) as error:
        code=error.code if isinstance(error,ActionValidationError) else 'INSPECTION_GUARD_STOP'
        evidence.event('action_rejected',error_code=code);outcome.update(status='BLOCKED',technical_gate='BLOCKED',error_code=code)
    except Exception:
        evidence.event('inspection_harness_failure',error_code='INSPECTION_RUNNER_ERROR')
        outcome.update(status='INVALID',technical_gate='INVALID',error_code='INSPECTION_RUNNER_ERROR')
    finally:context.close()
    return outcome


def run_inspection(browser,fixture,projection,case,policy,executor,reviewer,budget,evidence):
    scope=check_persona(fixture,case['persona'],fixture['personas'][case['persona']]['storage_state'],fixture['identity_verifier'])
    if scope['status']!='PERSONA_SCOPE_VERIFIED':return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'ACTOR_SCOPE_FAILED'}
    if case['case_id']=='NSN014-RIGHTS':
        permissions=fixture['personas']['plant_lead']['allowed_permissions']
        if any(not p.endswith(('.view','.read')) for p in permissions):
            return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'VIEWER_HAS_MUTATING_CAPABILITY'}
    before=snapshot(fixture,enforce_counts=False)
    paths=['/beprobung/'+fixture['suite_copy']['mapping']['plan_id'],'/samples','/quality/wpk','/analytics']
    for row in collect_receipts(fixture)['samples']:paths.append('/samples/'+row['id'])
    entry={'NSN014-RECEIPT':'/samples','NSN014-PLAN':paths[0],'NSN014-ASSESS':'/samples','NSN014-WPK':'/quality/wpk',
           'NSN014-ANALYSIS':'/analytics','NSN014-RIGHTS':paths[0]}[case['case_id']]
    outcome=run_view(browser,fixture,case['persona'],entry,paths,case['task'],policy,executor,reviewer,budget,evidence)
    after=snapshot(fixture,enforce_counts=False)
    unchanged=before==after;review=outcome.get('review') or {}
    if outcome['technical_gate']!='PASS' or outcome.get('stop_reason'):
        return dict(outcome,result='INCONCLUSIVE' if outcome.get('stop_reason') else outcome['status'])
    if not unchanged:return dict(outcome,result='INVALID',technical_gate='INVALID',reason='PROTECTED_DATA_CHANGED_DURING_INSPECTION')
    reviewed=review.get('verdict') in ('PASS','FAIL','INCONCLUSIVE')
    return dict(outcome,result='PASS' if outcome['status']=='DONE' and review.get('verdict')=='PASS' else 'FAIL' if reviewed else 'INVALID',
                oracle_gate='PASS',evidence_verified=reviewed,protected_data_unchanged=unchanged,scope_verified=True)


def run_plan_creation(browser,fixture,dataset,projection,case,policy,executor,reviewer,budget,evidence):
    before=collect_receipts(fixture)
    if verify_receipts(before,dataset,fixture,phase='before')['status']!='RECEIPT_START_VERIFIED':
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'PLAN_START_NOT_EMPTY'}
    path='/beprobung/'+fixture['suite_copy']['mapping']['plan_id']
    result=run_view(browser,fixture,'laboratory_lead',path,[path],case['task'],policy,executor,reviewer,budget,evidence,plan_samples=True)
    if result['technical_gate']!='PASS' or result.get('stop_reason'):
        return dict(result,result='INCONCLUSIVE' if result.get('stop_reason') else result['status'])
    oracle=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='after_plan')
    if oracle.get('reason')=='EXTRA_OR_DUPLICATE_PROBE' or oracle.get('mismatched_positions') or oracle.get('orphan_lims'):
        return dict(result,result='BLOCKED',technical_gate='BLOCKED',reason='PLAN_SAMPLE_INTEGRITY_FAILED',oracle=oracle)
    review=result.get('review') or {};reviewed=review.get('verdict') in ('PASS','FAIL','INCONCLUSIVE')
    return dict(result,result='PASS' if oracle['status']=='PASS' and result['status']=='DONE' and review.get('verdict')=='PASS'
                else 'FAIL' if reviewed and oracle['status'] in ('PASS','FAIL') else 'INVALID',
                oracle_gate=oracle['status'],evidence_verified=reviewed,oracle=oracle)


def run_reports(browser,fixture,projection,case,policy,executor,reviewer,budget,evidence):
    receipts=collect_receipts(fixture);actual={r['sample_code']:r for r in receipts['samples']}
    outcomes=[];downloads=[];missing=[]
    before=snapshot(fixture,enforce_counts=False)
    for position in projection['positions']:
        probe=actual.get(position['sample_code'])
        if probe is None:missing.append(position['position_id']);continue
        if probe['product_id']!=fixture['suite_copy']['mapping']['positions'][position['position_id']]:
            return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'WRONG_REPORT_SAMPLE'}
        path='/samples/'+probe['id']
        task='Generate exactly one non-official Prüfbericht and download PDF for '+position['sample_code']+' / '+position['product']+'. No release, signature or dispatch.'
        result=run_view(browser,fixture,case['persona'],path,[path],task,policy,executor,reviewer,budget,evidence,report_position=position)
        outcomes.append(result);downloads+=result['downloads']
        if result['technical_gate']!='PASS' or result.get('stop_reason'):
            return {'result':'INCONCLUSIVE' if result.get('stop_reason') else result['status'],'technical_gate':result['technical_gate'],
                    'stop_reason':result.get('stop_reason'),'positions':outcomes}
    after=snapshot(fixture,enforce_counts=False)
    if any(after['tables'][k]!=v for k,v in before['tables'].items() if k!='ble_reports'):
        return {'result':'INVALID','technical_gate':'INVALID','reason':'UNRELATED_REPORT_WRITE'}
    oracle=verify_reports(collect_reports(fixture),receipts,projection,fixture,downloads)
    if oracle['status'] not in ('PASS','FAIL'):return {'result':'BLOCKED','technical_gate':'BLOCKED','oracle':oracle}
    reviewed=bool(outcomes) and all((r.get('review') or {}).get('verdict') in ('PASS','FAIL','INCONCLUSIVE') for r in outcomes)
    passed=reviewed and oracle['status']=='PASS' and all(r['status']=='DONE' and r['review']['verdict']=='PASS'
        and r.get('pdf_reviews') and all(p['verdict']=='PASS' for p in r['pdf_reviews']) for r in outcomes)
    return {'result':'INCONCLUSIVE' if missing else 'PASS' if passed else 'FAIL' if reviewed else 'INVALID',
            'technical_gate':'PASS' if reviewed or missing else 'INVALID','oracle_gate':oracle['status'],
            'evidence_verified':reviewed,'positions':outcomes,'oracle':oracle,'missing_prerequisites':missing,'downloads':downloads}

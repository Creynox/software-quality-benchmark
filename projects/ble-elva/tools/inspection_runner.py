"""Inspection/report controller; screenshots and visible inputs only reach models.

Objective case results (scoring nsn014-objective-v1) come from controller and
independent Oracle evidence. The reviewer adds a separate, versioned UX layer
(rubric nsn014-ux-rubric-v1) and never turns a result into PASS or FAIL.
"""
import base64
import json
from uuid import uuid4
from urllib.parse import urlsplit
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from sqbf.bounded import invoke_worker
from sqbf.calibration import ResourceStop, ask_calibrated
from sqbf.models import validate_action, safe_action_log, ActionValidationError, ALLOWED_ACTIONS
from sqbf.no_write_oracle import snapshot
from sqbf.read_only import ReadOnlyViolation
from sqbf.runner import apply_action
from .calculation_oracle import collect_report_calculations, persisted_basis, verify_calculations
from .inspection_guard import contract, event_guard, check_action, transport_allowed
from .measurement_oracle import collect_inputs
from .persona_scope import check_persona
from .receipt_oracle import collect_receipts,verify_receipts
from .report_oracle import collect_reports, verify_reports, expected_numbers
from .stage_support import StallDetector, ask_review, classify_rejection, incomplete_reason, review_prompt, ux_verdicts

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
    images,actions,downloads=[],[],[];generated=set();downloaded=set();stall=StallDetector()
    outcome={'status':'INCONCLUSIVE','technical_gate':'PASS','review':None,'downloads':downloads,
             'download_failures':[],'capability_actions':[]}
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
            images.append(png);evidence.snapshot(png,'inspection');stall.observe(png)
            if stall.stalled():
                evidence.event('stopped_no_visible_progress',persona=persona);outcome['status']='STALLED';break
            answer=ask_calibrated(executor,INSTRUCTIONS+'\nTask:\n'+task+'\nPrevious visible actions:\n'+
                json.dumps(actions,ensure_ascii=False),png,budget,'executor')
            action={k:v for k,v in answer.data.items() if v is not None}
            try:
                validate_action(action,1280,800)
                state=check_action(page,action,config,generated)
                # Only a click activates a control; scroll/wait/done over it never counts.
                clicked=action['action']=='click'
                if clicked and state['kind']=='download' and state['scope'] in downloaded:raise ReadOnlyViolation('DUPLICATE_PDF_DOWNLOAD')
            except (ReadOnlyViolation,ActionValidationError) as error:
                code,critical=classify_rejection(error)
                if critical:raise
                kind=action.get('action')
                evidence.event('action_rejected',persona=persona,error_code=code,
                               action=kind if isinstance(kind,str) and kind in ALLOWED_ACTIONS else 'REDACTED')
                outcome.update(status='REJECTED',rejected_action_code=code);break
            evidence.event('inspection_action',persona=persona,**safe_action_log(action));stall.record(action)
            if action['action'] in ('done','blocked'):
                outcome['status']='DONE' if action['action']=='done' else 'BLOCKED'
                outcome['executor_statement']=safe_action_log(action);break
            if clicked and state['kind'] in ('generate','plan_samples'):
                generated.add(state['scope']);outcome['capability_actions'].append({'kind':state['kind'],'scope':state['scope']})
            budget.action()
            if clicked and state['kind']=='download':
                downloaded.add(state['scope']);report_id=state['scope'].split('/')[-1]
                try:
                    with page.expect_download(timeout=min(15000,budget.remaining()*1000)) as pending:
                        apply_action(page,action)
                    download=pending.value
                except PlaywrightTimeoutError:
                    # No file is observable product behaviour or timing; never a harness verdict.
                    evidence.event('pdf_download_not_received',persona=persona)
                    outcome['download_failures'].append({'report_id':report_id,'reason':'PDF_DOWNLOAD_NOT_RECEIVED'})
                    actions.append(action);page.wait_for_timeout(500);continue
                path=evidence.path/('download-'+uuid4().hex+'.pdf')
                download.save_as(path)
                pdf=invoke_worker('pdf-check',{'path':str(path),'required_text':[
                    report_position['sample_code'],report_position['product'],'Enzberg']},min(15,budget.remaining()))
                new_images=[base64.b64decode(p) for p in pdf.pop('images')]
                for image in new_images:evidence.snapshot(image,'report-pdf')
                pdf_images.extend(new_images)
                downloads.append(dict(pdf,report_id=report_id,file_name=path.name))
                if pdf.get('pdf_integrity')=='INVALID_ARTIFACT':
                    evidence.event('pdf_artifact_invalid',persona=persona,error_code=pdf.get('artifact_error'))
            else:apply_action(page,action)
            actions.append(action);page.wait_for_timeout(500)
        if images:
            selected=[images[i] for i in sorted(set((0,len(images)//2,len(images)-1)))]
            review,review_error=ask_review(ask_calibrated,reviewer,review_prompt('Independently review the requested UI workflow from these images and visible actions only. '
                'No DB facts. Separate agent difficulty, UI defects and unsupported assertions. '
                'No normative conformity or release verdict. Return the configured strict review schema.',
                '\n'+task+'\n'+json.dumps({'visible_actions':actions,'unverified_executor_statement':outcome.get('executor_statement'),
                                            'controller_stop':None if outcome['status'] in ('DONE','BLOCKED') else incomplete_reason(outcome)},
                                           ensure_ascii=False)),selected,budget,evidence,persona=persona)
            outcome['review']=review
            if review_error:outcome['review_error']=review_error
        if pdf_images:
            outcome['pdf_reviews']=[]
            for offset in range(0,len(pdf_images),3):
                expected={k:str(v) for k,v in expected_numbers(report_position).items()}
                batch,batch_error=ask_review(ask_calibrated,reviewer,review_prompt(
                    'Review only these rendered PDF pages for identity, readable layout and visible values inconsistent with the supplied source test inputs. '
                    'These inputs are instructions, not DB persistence evidence. Do not require every field on each page batch; other pages are reviewed separately. '
                    'No normative conformity, release or signature claim. Return the configured strict review schema.',
                    '\n'+json.dumps({'task':task,'pages':list(range(offset+1,min(offset+4,len(pdf_images)+1))),
                                     'total_pages':len(pdf_images),'source_expected_display_inputs':expected},ensure_ascii=False)),
                    pdf_images[offset:offset+3],budget,evidence,persona=persona)
                if batch is not None:outcome['pdf_reviews'].append(dict(batch,pages=list(range(offset+1,min(offset+4,len(pdf_images)+1)))))
                else:outcome['review_error']=batch_error
    except ResourceStop:
        outcome.update(status='INCONCLUSIVE',stop_reason=budget.stop_reason)
    except (ReadOnlyViolation,ActionValidationError) as error:
        code,_=classify_rejection(error)
        evidence.event('action_rejected',error_code=code);outcome.update(status='BLOCKED',technical_gate='BLOCKED',error_code=code)
    except Exception:
        evidence.event('inspection_harness_failure',error_code='INSPECTION_RUNNER_ERROR')
        outcome.update(status='INVALID',technical_gate='INVALID',error_code='INSPECTION_RUNNER_ERROR')
    finally:context.close()
    outcome.update(screenshots=len(images),visible_actions=len(actions))
    return outcome


def _technical_stop(outcome):
    if outcome.get('stop_reason'):return dict(outcome,result='INCONCLUSIVE')
    return dict(outcome,result='BLOCKED' if outcome['technical_gate']=='BLOCKED' else 'INVALID')


# The suite keeps every persona's existing BLE permissions. The WPK account is a
# Laborleiter without fpc.view, so the FPC area (/quality/wpk) is access-denied for it;
# its plan-versus-completed task starts on the designated plan. /quality/wpk stays a
# permitted navigation target, so a visible denial there is a UX observation.
ENTRY_PATHS={
    'NSN014-RECEIPT':lambda fixture:'/samples',
    'NSN014-ASSESS':lambda fixture:'/samples',
    'NSN014-WPK':lambda fixture:'/beprobung/'+fixture['suite_copy']['mapping']['plan_id'],
    'NSN014-ANALYSIS':lambda fixture:'/analytics',
    'NSN014-RIGHTS':lambda fixture:'/beprobung/'+fixture['suite_copy']['mapping']['plan_id'],
}


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
    entry=ENTRY_PATHS[case['case_id']](fixture)
    outcome=run_view(browser,fixture,case['persona'],entry,paths,case['task'],policy,executor,reviewer,budget,evidence)
    after=snapshot(fixture,enforce_counts=False)
    if outcome['technical_gate']!='PASS' or outcome.get('stop_reason'):return _technical_stop(outcome)
    if before!=after:return dict(outcome,result='INVALID',technical_gate='INVALID',reason='PROTECTED_DATA_CHANGED_DURING_INSPECTION')
    common=dict(oracle_gate='PASS',oracle_scope='NO_SIDE_EFFECTS_AND_PERSONA_SCOPE',display_traceability='REVIEWER_ASSESSED',
                evidence_verified=outcome['screenshots']>0,protected_data_unchanged=True,scope_verified=True,
                ux_verdict=ux_verdicts([outcome]))
    if outcome['status']=='DONE':return dict(outcome,result='PASS',**common)
    return dict(outcome,result='INCONCLUSIVE',reason=incomplete_reason(outcome),**common)


def run_plan_creation(browser,fixture,dataset,projection,case,policy,executor,reviewer,budget,evidence):
    before=collect_receipts(fixture)
    if verify_receipts(before,dataset,fixture,phase='before')['status']!='RECEIPT_START_VERIFIED':
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'PLAN_START_NOT_EMPTY'}
    path='/beprobung/'+fixture['suite_copy']['mapping']['plan_id']
    result=run_view(browser,fixture,'laboratory_lead',path,[path],case['task'],policy,executor,reviewer,budget,evidence,plan_samples=True)
    if result['technical_gate']!='PASS' or result.get('stop_reason'):return _technical_stop(result)
    oracle=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='after_plan')
    attempted=any(a['kind']=='plan_samples' for a in result['capability_actions'])
    common=dict(oracle=oracle,ux_verdict=ux_verdicts([result]),evidence_verified=result['screenshots']>0)
    if oracle.get('reason')=='EXTRA_OR_DUPLICATE_PROBE' or oracle.get('mismatched_positions') or oracle.get('orphan_lims'):
        # Corrupted sample identities make every downstream stage meaningless.
        return dict(result,result='FAIL',technical_gate='PASS',oracle_gate='FAIL',critical_stop=True,
                    reason='PLAN_SAMPLE_INTEGRITY_FAILED',fail_class='PLAN_SAMPLE_INTEGRITY',**common)
    if oracle['status'] not in ('PASS','FAIL'):
        return dict(result,result='BLOCKED',technical_gate='BLOCKED',reason='PLAN_ORACLE_UNAVAILABLE',**common)
    if not attempted:
        if oracle.get('sample_count'):
            return dict(result,result='INVALID',technical_gate='INVALID',reason='UNATTRIBUTED_PLAN_SAMPLE_WRITE',**common)
        return dict(result,result='INCONCLUSIVE',oracle_gate=oracle['status'],
                    reason='PLAN_CREATION_NOT_ATTEMPTED:'+incomplete_reason(result),**common)
    if oracle['status']=='FAIL':
        return dict(result,result='FAIL',oracle_gate='FAIL',fail_class='PLAN_SAMPLE_DEVIATION',
                    reason='CREATED_SAMPLES_DEVIATE_FROM_PLAN',**common)
    if result['status']=='DONE':return dict(result,result='PASS',oracle_gate='PASS',**common)
    return dict(result,result='INCONCLUSIVE',oracle_gate='PASS',reason='CREATED_BUT_NOT_CONFIRMED:'+incomplete_reason(result),**common)


def classify_report_position(result,detail,calc_mismatch):
    """Objective per-position report verdict from controller and Oracle evidence."""
    generated=any(a['kind']=='generate' for a in result.get('capability_actions',[]))
    if detail is None:
        return ('INCOMPLETE','REPORT_NOT_PERSISTED_AFTER_GENERATE') if generated else ('INCOMPLETE','REPORT_NOT_GENERATED')
    if not detail['relations_valid']:return 'FAIL','REPORT_RELATION_DEVIATION'
    if detail['numeric_fields']:return 'FAIL','REPORT_VALUE_DEVIATION'
    if detail['position_id'] in calc_mismatch:return 'FAIL','CALCULATION_DEVIATION'
    if detail['pdf_status']=='INVALID_ARTIFACT':return 'FAIL','INVALID_PDF_ARTIFACT'
    if detail['pdf_status']=='IDENTITY_TEXT_MISSING':return 'FAIL','PDF_IDENTITY_MISSING'
    if detail['pdf_status']=='MISSING':
        return 'INCOMPLETE','PDF_DOWNLOAD_NOT_RECEIVED' if result.get('download_failures') else 'PDF_NOT_DOWNLOADED'
    if detail['pdf_status']!='PASS':return 'INCOMPLETE','DUPLICATE_DOWNLOAD_EVIDENCE'
    if result.get('status')!='DONE':return 'INCOMPLETE',incomplete_reason(result)
    return 'PASS',None


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
        result['position_id']=position['position_id']
        outcomes.append(result);downloads+=result['downloads']
        if result['technical_gate']!='PASS' or result.get('stop_reason'):
            return {'result':'INCONCLUSIVE' if result.get('stop_reason') else 'BLOCKED' if result['technical_gate']=='BLOCKED' else 'INVALID',
                    'technical_gate':result['technical_gate'],'stop_reason':result.get('stop_reason'),'positions':outcomes}
    after=snapshot(fixture,enforce_counts=False)
    if any(after['tables'][k]!=v for k,v in before['tables'].items() if k!='ble_reports'):
        return {'result':'INVALID','technical_gate':'INVALID','reason':'UNRELATED_REPORT_WRITE'}
    basis=persisted_basis(collect_inputs(fixture))
    oracle=verify_reports(collect_reports(fixture),receipts,projection,fixture,downloads,basis=basis)
    calculations=verify_calculations(collect_report_calculations(fixture),receipts,basis,fixture)
    if oracle['status'] not in ('PASS','FAIL') or calculations['status'] not in ('PASS','FAIL'):
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'REPORT_ORACLE_UNAVAILABLE','oracle':oracle,
                'calculations':calculations}
    details={d['position_id']:d for d in oracle['positions']}
    mismatched=set(calculations['mismatched_positions'])
    position_results=[]
    for result in outcomes:
        verdict,cls=classify_report_position(result,details.get(result['position_id']),mismatched)
        position_results.append({'position_id':result['position_id'],'result':verdict,'class':cls})
    gate='FAIL' if 'FAIL' in (oracle['status'],calculations['status']) else 'PASS'
    if any(p['result']=='FAIL' for p in position_results):verdict='FAIL'
    elif missing or not outcomes or any(p['result']!='PASS' for p in position_results):verdict='INCONCLUSIVE'
    elif gate!='PASS':verdict='INCONCLUSIVE'  # Residual Oracle findings without a position verdict.
    else:verdict='PASS'
    return {'result':verdict,'technical_gate':'PASS','oracle_gate':gate,'evidence_verified':True,
            'positions':outcomes,'position_results':position_results,'oracle':oracle,'calculations':calculations,
            'fail_classes':sorted({p['class'] for p in position_results if p['result']=='FAIL'}),
            'missing_prerequisites':missing,'downloads':downloads,'ux_verdict':ux_verdicts(outcomes)}

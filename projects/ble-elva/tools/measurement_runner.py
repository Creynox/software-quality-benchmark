"""Screenshot-only numeric module driver; independent DB evidence stays outside.

Objective verdicts (nsn014-objective-v1): a module PASSes when the executor
completed it and the independent read-only Oracle finds exactly the approved
inputs persisted. FAIL requires that the controller observed every approved
field typed with its exact value (and the module saved) while the persisted
state still deviates. Anything else is an incomplete measurement, never a
product verdict. The reviewer's UX judgement is recorded separately.
"""
import json
import copy
from urllib.parse import urlsplit
from sqbf.calibration import ResourceStop, ask_calibrated
from sqbf.models import validate_action, safe_action_log, ActionValidationError, ALLOWED_ACTIONS
from sqbf.read_only import ReadOnlyViolation
from sqbf.runner import apply_action
from .measurement_guard import make_contract, event_guard, check_action, transport_allowed
from .measurement_oracle import collect_inputs, verify_inputs
from .receipt_oracle import collect_receipts
from .allocation_oracle import collect_allocations, verify_allocations
from .stage_support import StallDetector, ask_review, classify_rejection, incomplete_reason, review_prompt, ux_verdicts
from sqbf.suites import canonical_hash
from sqbf.no_write_oracle import snapshot

INSTRUCTIONS='''Work only from the displayed screenshots, source inputs below and your previous visible actions.
Return one strict JSON UI action. No tools, files, DOM, APIs, hidden URLs, passwords or browser shortcuts.
Enter only the supplied original numbers in their corresponding visible fields. Do not invent missing values.
Physical laboratory operations are simulated. Existing norms, method profiles and product settings stay unchanged.
Save each module or individual shape fraction once only, then inspect the resulting state. No save retry.
No release, signature, finalization, delete, dispatch, master data or optional notes.
Allowed keys: ControlOrMeta+A, Backspace, Delete, Tab, Escape. Select controls only through visible UI.
If a field or prerequisite is unavailable or validation fails, explain blocked instead of bypassing it.
'''
RAW_KINDS={'allocations':set(),'wash':{'wash'},'sieve':{'sieves'},'partial':{'partial_series','preparation','sieves'},
           'shape':{'shape'},'boiling':{'boiling','boiling_repetitions'},'sand':{'sand'}}


def required_saves(contract):
    """Save scopes the controller must have seen before a deviation can be a product fault."""
    if contract['kind']=='allocations':return set()
    if contract['kind']=='shape':return {key.split(':')[-1] for key in contract['fields'] if key.startswith('Einwaage gesamt (g):')}
    return {'module'}


def run_position(browser,fixture,position,probe_id,kind,policy,executor,reviewer,budget,evidence):
    contract=make_contract(fixture,probe_id,position,kind)
    context=browser.new_context(viewport={'width':1280,'height':800},
        locale='de-DE',timezone_id='Europe/Berlin',
        storage_state=fixture['personas']['laboratory_staff']['storage_state'],accept_downloads=False,service_workers='block')
    images,actions,saved,filled=[],[],set(),set();stall=StallDetector()
    outcome={'position_id':position['position_id'],'kind':kind,'status':'INCONCLUSIVE','technical_gate':'PASS','review':None}
    try:
        context.add_init_script(event_guard(contract))
        context.route('**/*',lambda route:route.continue_() if transport_allowed(route.request.url,route.request.method,contract,policy) else route.abort())
        page=context.new_page();page.set_default_timeout(3000)
        page.goto(contract['origin']+contract['root'],wait_until='domcontentloaded',timeout=min(15000,budget.remaining()*1000))
        page.wait_for_timeout(800)
        task=json.dumps({'sample_code':position['sample_code'],'product':position['product'],
                          'module':kind,'source_inputs':contract['fields']},ensure_ascii=False)
        while True:
            budget.remaining()
            if urlsplit(page.url).path=='/login':raise ReadOnlyViolation('SESSION_INVALIDATED')
            png=page.screenshot(animations='disabled',timeout=min(5000,budget.remaining()*1000))
            images.append(png);evidence.snapshot(png,position['position_id']+'-'+kind);stall.observe(png)
            if stall.stalled():
                evidence.event('stopped_no_visible_progress',position=position['position_id'],module=kind)
                outcome['status']='STALLED';break
            response=ask_calibrated(executor,INSTRUCTIONS+'\nTask:\n'+task+'\nPrevious visible actions:\n'+
                json.dumps(actions,ensure_ascii=False),png,budget,'executor')
            action={k:v for k,v in response.data.items() if v is not None}
            try:
                validate_action(action,1280,800)
                state=check_action(page,action,contract,saved)
            except (ReadOnlyViolation,ActionValidationError) as error:
                code,critical=classify_rejection(error)
                if critical:raise
                name=action.get('action')
                evidence.event('action_rejected',position=position['position_id'],module=kind,error_code=code,
                               action=name if isinstance(name,str) and name in ALLOWED_ACTIONS else 'REDACTED')
                outcome.update(status='REJECTED',rejected_action_code=code);break
            evidence.event('measurement_action',position=position['position_id'],module=kind,**safe_action_log(action))
            stall.record(action)
            if action['action'] in ('done','blocked'):
                outcome['status']='DONE' if action['action']=='done' else 'BLOCKED'
                outcome['executor_statement']=safe_action_log(action);break
            if action['action']=='click' and state['target']['kind'] in ('save','setup'):saved.add(state['target']['scope'])
            # The guard admitted this text only as the exact approved value of the focused field.
            if action['action']=='type' and state.get('focused') in contract['fields']:filled.add(state['focused'])
            budget.action();apply_action(page,action);actions.append(action);page.wait_for_timeout(500)
        if images:
            review,review_error=ask_review(ask_calibrated,reviewer,review_prompt(
                'Independently review this laboratory data-entry attempt from screenshots and visible actions only. '
                'The source values are test instructions, not proof of persistence. No database/hidden facts. '
                'Separate agent difficulty, missing prerequisite, application UX and unproven persistence. '
                'No normative conformity verdict. Return the configured strict review schema.',
                '\n'+task+'\n'+json.dumps({'visible_actions':actions,'unverified_executor_statement':outcome.get('executor_statement'),
                                            'controller_stop':None if outcome['status'] in ('DONE','BLOCKED') else incomplete_reason(outcome)},
                                           ensure_ascii=False)),[images[i] for i in sorted(set((0,len(images)//2,len(images)-1)))],budget,evidence,
                position=position['position_id'],module=kind)
            outcome['review']=review
            if review_error:outcome['review_error']=review_error
        outcome['save_scopes_attempted']=sorted(saved)
    except ResourceStop:
        outcome.update(status='INCONCLUSIVE',stop_reason=budget.stop_reason)
    except (ReadOnlyViolation,ActionValidationError) as error:
        code,_=classify_rejection(error)
        evidence.event('action_rejected',position=position['position_id'],error_code=code)
        outcome.update(status='BLOCKED',technical_gate='BLOCKED',error_code=code)
    except Exception:
        evidence.event('measurement_harness_failure',position=position['position_id'],error_code='MEASUREMENT_RUNNER_ERROR')
        outcome.update(status='INVALID',technical_gate='INVALID',error_code='MEASUREMENT_RUNNER_ERROR')
    finally:
        context.close()
    outcome.update(screenshots=len(images),fields_required=len(contract['fields']),fields_entered=len(filled),
                   fully_entered=set(contract['fields'])<=filled and required_saves(contract)<=saved)
    return outcome


def classify_position(outcomes,mismatched):
    """One position across this case's modules: PASS, FAIL or INCOMPLETE with reason."""
    if mismatched and all(o.get('fully_entered') for o in outcomes):
        return 'FAIL','PERSISTED_VALUE_DEVIATION'
    unfinished=[o for o in outcomes if o['status']!='DONE']
    if unfinished:return 'INCOMPLETE',incomplete_reason(unfinished[0])
    if mismatched:return 'INCOMPLETE','EXECUTOR_DONE_WITHOUT_ALL_APPROVED_INPUTS'
    return 'PASS',None


def run_measurements(browser,fixture,projection,case_kinds,policy,executor,reviewer,budget,evidence,allocation_reference=None):
    if canonical_hash(projection)!=fixture['suite_copy'].get('measurement_reference_sha256'):
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'MEASUREMENT_REFERENCE_CHANGED'}
    allocated={}
    if 'allocations' in case_kinds:
        if allocation_reference is None or canonical_hash(allocation_reference)!=fixture['suite_copy'].get('allocation_reference_sha256'):
            return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'ALLOCATION_REFERENCE_CHANGED'}
        allocated={p['position_id']:p['allocations'] for p in allocation_reference['positions']}
    receipts=collect_receipts(fixture);actual={r['sample_code']:r for r in receipts['samples']}
    if len(actual)!=len(receipts['samples']):
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'DUPLICATE_SAMPLE_CODES'}
    expected_codes={p['sample_code'] for p in projection['positions']}
    if set(actual)-expected_codes:
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'UNEXPECTED_SAMPLE_CODES'}
    before=snapshot(fixture,enforce_counts=False)
    outcomes=[];prerequisite_missing=[]
    for position in projection['positions']:
        position=copy.deepcopy(position)
        if allocated:position['allocations']=allocated[position['position_id']]
        probe=actual.get(position['sample_code'])
        for kind in case_kinds:
            rawkind={'sieve':'sieves','partial':'partial_series'}.get(kind,kind)
            if kind=='allocations':
                if not any(r['actual_amount_g'] is not None for r in position['allocations']):continue
            elif not position['measurements'][rawkind]:continue
            if probe is None:
                prerequisite_missing.append({'position_id':position['position_id'],'kind':kind});continue
            if probe['product_id']!=fixture['suite_copy']['mapping']['positions'][position['position_id']]:
                return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'WRONG_PROBE_PRODUCT'}
            outcome=run_position(browser,fixture,position,probe['id'],kind,policy,executor,reviewer,budget,evidence)
            outcomes.append(outcome)
            # Only critical faults stop the case; a prevented or unfinished task does not.
            if outcome['technical_gate']!='PASS' or outcome.get('stop_reason'):
                return {'result':'INCONCLUSIVE' if outcome.get('stop_reason') else 'BLOCKED' if outcome['technical_gate']=='BLOCKED' else 'INVALID',
                        'technical_gate':outcome['technical_gate'],'stop_reason':outcome.get('stop_reason'),'positions':outcomes}
    after=snapshot(fixture,enforce_counts=False)
    mutable={'samples','lims_sample','sqbf_measurement_inputs_v1','sqbf_allocation_inputs_v1'}
    if collect_receipts(fixture)!=receipts or any(after['tables'][k]!=v for k,v in before['tables'].items() if k not in mutable):
        return {'result':'INVALID','technical_gate':'INVALID','reason':'UNRELATED_MEASUREMENT_WRITE'}
    kinds=set({'sieve':'sieves','partial':'partial_series'}.get(k,k) for k in case_kinds if k!='allocations')
    if 'boiling' in kinds:kinds.add('boiling_repetitions')
    if 'partial_series' in kinds:kinds.add('preparation')
    oracles=[];input_mismatch=set();allocation_mismatch=set()
    if kinds:
        inputs=verify_inputs(collect_inputs(fixture),projection,fixture,kinds=kinds);oracles.append(inputs)
        input_mismatch={(m['position_id'],m['kind']) for m in inputs.get('mismatches',[])}
    if allocated:
        allocations=verify_allocations(collect_allocations(fixture),projection,allocation_reference,fixture);oracles.append(allocations)
        allocation_mismatch=set(allocations.get('mismatched_positions',[]))
    oracle={'status':'BLOCKED' if not oracles or any(o['status'] not in ('PASS','FAIL') for o in oracles)
            else 'FAIL' if any(o['status']=='FAIL' for o in oracles) else 'PASS','components':oracles}
    if oracle['status'] not in ('PASS','FAIL'):
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'MEASUREMENT_ORACLE_UNAVAILABLE','oracle':oracle}
    position_results=[]
    for key in dict.fromkeys(o['position_id'] for o in outcomes):
        own=[o for o in outcomes if o['position_id']==key]
        mismatched=(key in allocation_mismatch and any(o['kind']=='allocations' for o in own)) or any(
            (key,raw) in input_mismatch for o in own for raw in RAW_KINDS[o['kind']])
        verdict,cls=classify_position(own,mismatched)
        position_results.append({'position_id':key,'result':verdict,'class':cls})
    # Deviations at positions the executor never reached remain incomplete measurement.
    unvisited=sorted(({m[0] for m in input_mismatch}|allocation_mismatch)-{p['position_id'] for p in position_results})
    if any(p['result']=='FAIL' for p in position_results):result='FAIL'
    elif prerequisite_missing or not outcomes or any(p['result']!='PASS' for p in position_results):result='INCONCLUSIVE'
    elif oracle['status']!='PASS':result='INCONCLUSIVE'
    else:result='PASS'
    return {'result':result,'technical_gate':'PASS','oracle_gate':oracle['status'],'evidence_verified':True,
            'positions':outcomes,'position_results':position_results,'missing_prerequisites':prerequisite_missing,
            'unvisited_deviations':unvisited,
            'fail_classes':sorted({p['class'] for p in position_results if p['result']=='FAIL'}),
            'oracle':oracle,'ux_verdict':ux_verdicts(outcomes)}

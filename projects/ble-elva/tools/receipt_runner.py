"""Receipt stage controller; model sees screenshots and source-bound task only."""
import json
from urllib.parse import urlsplit

from sqbf.calibration import ResourceStop, ask_calibrated
from sqbf.models import validate_action, safe_action_log, ActionValidationError
from sqbf.read_only import ReadOnlyViolation
from sqbf.runner import apply_action
from .receipt_guard import make_contract, event_guard, check_action, transport_allowed
from .receipt_oracle import collect_receipts, verify_receipts


INSTRUCTIONS = '''Work only from the screenshot, the task and your prior visible actions.
Return one strict JSON UI action. No tools, files, DOM, APIs, passwords, hidden URLs or browser shortcuts.
Register only the designated sample with the exact customer, project, plant, product, code and date.
Use visible dropdown options; do not change product master data or activate an inactive product.
Click Probe anlegen once only after all requested fields are visibly correct.
Never repeat a Save, create another sample, edit, delete, release, sign or send anything.
After saving inspect the resulting view, then done. If unavailable or validation fails, blocked.
Allowed keys: ControlOrMeta+A, Backspace, Delete, Escape. Use clicks for dropdown choices.
'''


def run_position(browser, fixture, position, sampling_date, policy, executor, reviewer, budget, evidence):
    contract = make_contract(fixture, position, sampling_date)
    context = browser.new_context(viewport={'width':1280,'height':800},
        storage_state=fixture['personas']['laboratory_staff']['storage_state'],
        service_workers='block', accept_downloads=False)
    saved = False
    actions, images = [], []
    result = {'position_id': position['position_id'], 'status': 'INCONCLUSIVE', 'save_attempted': False,
              'review': None, 'technical_gate': 'PASS'}
    try:
        context.add_init_script(event_guard(contract))
        def route(request):
            if transport_allowed(request.request.url, request.request.method, contract['origin'], policy,
                                 controller_saved=saved):
                request.continue_()
            else:
                request.abort()
        context.route('**/*', route)
        page = context.new_page(); page.set_default_timeout(3000)
        page.goto(contract['origin']+'/samples',wait_until='domcontentloaded',timeout=min(15000,budget.remaining()*1000))
        page.wait_for_timeout(800)
        task = 'Register exactly this sample; all fields are required:\n'+json.dumps(contract['fields'],ensure_ascii=False)
        while True:
            budget.remaining()
            if urlsplit(page.url).path == '/login':
                raise ReadOnlyViolation('SESSION_INVALIDATED')
            png = page.screenshot(animations='disabled',timeout=min(5000,budget.remaining()*1000))
            images.append(png); evidence.snapshot(png,position['position_id']+'-receipt')
            answer=ask_calibrated(executor,INSTRUCTIONS+'\n'+task+'\nPrior visible actions:\n'+
                                  json.dumps(actions,ensure_ascii=False),png,budget,'executor')
            action={k:v for k,v in answer.data.items() if v is not None}
            validate_action(action,1280,800)
            state=check_action(page,action,contract,controller_saved=saved)
            evidence.event('receipt_action',position=position['position_id'],**safe_action_log(action))
            if action['action'] in ('done','blocked'):
                result['status']=action['action'].upper();result['executor_statement']=safe_action_log(action);break
            if state['target']['kind']=='save':
                saved=True;result['save_attempted']=True
            budget.action(); apply_action(page,action); actions.append(action)
            page.wait_for_timeout(500)
        # Separate reviewer receives only allowed task, visible actions and images.
        review=ask_calibrated(reviewer,
            'Independently review sample registration using these screenshots and visible actions only. '
            'No DB or hidden facts. Distinguish observable UX failure from agent difficulty. '
            'Return the configured strict review schema; completion alone is not persistence proof.\n'+
            task+'\n'+json.dumps({'visible_actions':actions,'unverified_executor_statement':result.get('executor_statement')},ensure_ascii=False),
            [images[i] for i in sorted(set((0,len(images)//2,len(images)-1)))],budget,'reviewer')
        result['review']=review.data
        return result
    except ResourceStop:
        result.update(status='INCONCLUSIVE',stop_reason=budget.stop_reason)
        return result
    except (ReadOnlyViolation,ActionValidationError) as error:
        code=error.code if isinstance(error,ActionValidationError) else 'RECEIPT_GUARD_STOP'
        evidence.event('action_rejected',position=position['position_id'],error_code=code)
        result.update(status='BLOCKED',technical_gate='BLOCKED',error_code=code)
        return result
    except Exception:
        evidence.event('receipt_harness_failure',position=position['position_id'],error_code='RECEIPT_RUNNER_ERROR')
        result.update(status='INVALID',technical_gate='INVALID',error_code='RECEIPT_RUNNER_ERROR')
        return result
    finally:
        context.close()


def run_receipt(browser, fixture, dataset, policy, executor, reviewer, budget, evidence):
    baseline=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='before')
    if baseline['status']!='RECEIPT_START_VERIFIED':
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'RECEIPT_START_INVALID'}
    positions=[]
    for position in dataset['positions']:
        outcome=run_position(browser,fixture,position,dataset['reference']['sampling_date'],policy,
                             executor,reviewer,budget,evidence)
        positions.append(outcome)
        if outcome['technical_gate']!='PASS' or outcome.get('stop_reason'):
            return {'result':'INCONCLUSIVE' if outcome.get('stop_reason') else outcome['status'],
                    'technical_gate':outcome['technical_gate'],'positions':positions,
                    'stop_reason':outcome.get('stop_reason')}
    oracle=verify_receipts(collect_receipts(fixture),dataset,fixture,phase='after')
    if (oracle.get('reason')=='EXTRA_OR_DUPLICATE_PROBE' or oracle.get('mismatched_positions') or oracle.get('orphan_lims')):
        return {'result':'BLOCKED','technical_gate':'BLOCKED','reason':'RECEIPT_INTEGRITY_FAILED','oracle':oracle,'positions':positions}
    valid=oracle['status'] in ('PASS','FAIL')
    reviewed=all(isinstance(p['review'],dict) and p['review'].get('verdict') in ('PASS','FAIL','INCONCLUSIVE') for p in positions)
    passed=valid and oracle['status']=='PASS' and all(p['status']=='DONE' and p['review'].get('verdict')=='PASS' for p in positions)
    return {'result':'PASS' if passed else 'FAIL' if valid and reviewed else 'INVALID',
            'technical_gate':'PASS' if valid and reviewed else 'INVALID',
            'oracle_gate':oracle['status'],'evidence_verified':valid and reviewed,
            'positions':positions,'oracle':oracle}

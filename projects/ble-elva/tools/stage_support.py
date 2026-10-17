"""Shared NSN014 stage controls: reviewer contract, stall detection, guard outcomes.

Objective case results come from controller evidence and independent Oracles.
The reviewer contributes a separate, versioned and provisional UX judgement; it
never decides PASS/FAIL. A guard rejection is a prevented action, not a safety
breach: only the affected task ends, unless the session itself became invalid.
"""
import copy
import hashlib

from sqbf.bounded import BudgetExceeded
from sqbf.calibration import ResourceStop
from sqbf.plan_credentials import REFUSED_CODES
from sqbf.models import ActionValidationError
from sqbf.smoke_runner import ACTION_SCHEMA

SCORING_VERSION = 'nsn014-objective-v1'
RUBRIC_VERSION = 'nsn014-ux-rubric-v1'
DIMENSIONS = ('findability', 'clarity', 'task_progress', 'error_recovery')
CATEGORIES = ('BLE_DEFECT_CANDIDATE', 'UX_IMPROVEMENT', 'AGENT_DIFFICULTY', 'HARNESS_SUSPECTED', 'UNCLEAR')
SEVERITIES = ('critical', 'major', 'minor', 'info')
CRITICAL_REJECTIONS = {'SESSION_INVALIDATED'}


def executor_schema():
    """Executor response schema used by the suite (restricted key set); shared with the provider probe."""
    schema = copy.deepcopy(ACTION_SCHEMA)
    schema['properties']['key']['enum'] = [None, 'ControlOrMeta+A', 'Backspace', 'Delete', 'Tab', 'Escape']
    return schema


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


REVIEW_SCHEMA = _object({
    'verdict': {'type': 'string', 'enum': ['PASS', 'FAIL', 'INCONCLUSIVE']},
    'reason': {'type': 'string'},
    'scores': _object({name: {'type': ['integer', 'null']} for name in DIMENSIONS}),
    'findings': {'type': 'array', 'items': _object({
        'category': {'type': 'string', 'enum': list(CATEGORIES)},
        'severity': {'type': 'string', 'enum': list(SEVERITIES)},
        'observed': {'type': 'string'},
        'expected': {'type': 'string'},
        'suggestion': {'type': 'string'},
        'evidence': {'type': 'string'},
    })},
})

RUBRIC = '''Rubric nsn014-ux-rubric-v1 (provisional UX judgement; never a database, release or conformity verdict).
Score findability, clarity, task_progress and error_recovery from 0 to 5 using only the supplied images and visible actions:
0 no usable orientation or function; 1 massive obstacles; 2 clear obstacles; 3 basically usable with friction;
4 good with small obstacles; 5 clear and effective. Use null (NOT_EVALUATED) when the images show no evidence for a dimension.
findability = locating the required screen or control; clarity = labels, values, states and messages are understandable;
task_progress = visible progress and feedback towards the goal; error_recovery = validation, error messages and ways back.
Every finding needs category (BLE_DEFECT_CANDIDATE for visible product misbehaviour, UX_IMPROVEMENT, AGENT_DIFFICULTY for
executor confusion, HARNESS_SUSPECTED for test-setup effects, UNCLEAR), severity (critical, major, minor, info), observed,
expected, suggestion and evidence (image number or PDF page). Never invent hidden data or values.
verdict: PASS if the visible evidence supports the requested outcome, FAIL if it visibly contradicts it, otherwise INCONCLUSIVE.
'''


def review_prompt(intro, payload):
    return intro + '\n' + RUBRIC + payload


def valid_review(review):
    """Strict local check in addition to the provider-side JSON schema."""
    if not isinstance(review, dict) or review.get('verdict') not in ('PASS', 'FAIL', 'INCONCLUSIVE'):
        return False
    scores = review.get('scores')
    if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
        return False
    if any(value is not None and (type(value) is not int or not 0 <= value <= 5) for value in scores.values()):
        return False
    findings = review.get('findings')
    if not isinstance(findings, list):
        return False
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {'category', 'severity', 'observed', 'expected',
                                                            'suggestion', 'evidence'}:
            return False
        if finding['category'] not in CATEGORIES or finding['severity'] not in SEVERITIES:
            return False
        if any(not isinstance(finding[key], str) for key in ('observed', 'expected', 'suggestion', 'evidence')):
            return False
    return True


def classify_rejection(error):
    """Return (code, critical). Prevented agent actions are task-level stops."""
    if isinstance(error, ActionValidationError):
        return error.code, False
    code = str(error) or 'GUARD_REJECTED'
    return code, code in CRITICAL_REJECTIONS


# A rejected action has no effect on the page (the guard runs before it is applied). The first live run (413f7abe) ended
# eleven of twelve tasks at the very first rejection, so nothing could be observed. A task now continues after a rejection,
# is told that the action had no effect, and ends only after this many of them.
MAX_REJECTIONS_PER_TASK = 3
REJECTION_NOTE = ('An entry with "rejected_by_controller" in the previous actions had no effect on the page; do not repeat it, '
                  'choose another permitted action or report blocked. The page can also move between your screenshot and your click '
                  '(it recalculates and re-renders): after a rejection read the newest screenshot again before you choose the next action.')
TARGET_JS = r"""({x,y})=>{const nm=s=>(s||'').replace(/\s+/g,' ').trim().slice(0,60);
 const e=Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null;if(!e)return null;
 const c=e.closest('button,a,input,select,textarea,[role=tab],[role=menuitem],[role=option],.mud-menu-item,.mud-list-item,.mud-select,.mud-chip,tr,.mud-expand-panel-header')||e;
 const tag=c.tagName.toLowerCase();let label=c.getAttribute('aria-label')||'';
 if(!label){label=['input','select','textarea'].includes(tag)?nm(c.closest('.mud-input-control')?.querySelector('label')?.innerText):nm(c.innerText);}
 return {tag,role:c.getAttribute('role'),label:nm(label),href:(c.getAttribute('href')||'').replace(/[0-9a-f]{8}-[0-9a-f-]{27}/g,'<id>').slice(0,80)};}"""


def describe_target(page, action):
    """Role and visible label (never a field value) of the element a rejected click or text entry aimed at; None if unknown."""
    try:
        target = page.evaluate(TARGET_JS, {'x': action.get('x'), 'y': action.get('y')})
    except Exception:
        return None
    return target if isinstance(target, dict) else None


def rejection_marker(code, action, target):
    """Entry for the executor's list of previous actions: what was rejected and what it aimed at, without typed text."""
    safe = {k: v for k, v in action.items() if k != 'text'}
    if action.get('action') == 'type':
        safe['typed_chars'] = len(action.get('text') or '')
    return {'rejected_by_controller': code, 'action': safe, 'target': target}


class StallDetector:
    """Harness safety: unchanged screen while the same action repeats.

    This is not a product threshold. It ends one task as INCONCLUSIVE instead of
    consuming the shared suite request budget without visible progress.
    """

    def __init__(self, screens=4, actions=3):
        self.screens, self.actions_needed = screens, actions
        self.hashes, self.actions = [], []

    def observe(self, png):
        self.hashes.append(hashlib.sha256(png).hexdigest())

    def record(self, action):
        kind = action.get('action')
        x, y = action.get('x'), action.get('y')
        position = (round(x / 5), round(y / 5)) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else None
        text = action.get('text')
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest() if isinstance(text, str) else None
        self.actions.append((kind, position, action.get('key'), action.get('amount'), digest))

    def stalled(self):
        if len(self.hashes) < self.screens or len(self.actions) < self.actions_needed:
            return False
        return (len(set(self.hashes[-self.screens:])) == 1
                and len(set(self.actions[-self.actions_needed:])) == 1)


INCOMPLETE_REASONS = {
    'BLOCKED': 'EXECUTOR_REPORTED_BLOCKED',
    'REJECTED': 'AGENT_ACTION_REJECTED',
    'STALLED': 'NO_VISIBLE_PROGRESS',
    'INCONCLUSIVE': 'NO_TERMINAL_SIGNAL',
    'EXECUTOR_FAILED': 'EXECUTOR_REQUEST_FAILED',
}


def incomplete_reason(outcome):
    reason = INCOMPLETE_REASONS.get(outcome.get('status'), 'TASK_NOT_COMPLETED')
    if outcome.get('rejected_action_code'):
        reason += ':' + outcome['rejected_action_code']
    return reason


def ux_verdicts(outcomes):
    """Separate UX layer; reported next to, never folded into, objective results."""
    verdicts = []
    for item in outcomes:
        review = item.get('review')
        if review:
            verdicts.append(review.get('verdict'))
        verdicts.extend(r.get('verdict') for r in item.get('pdf_reviews', []))
    if not verdicts:
        return 'NOT_EVALUATED'
    if 'FAIL' in verdicts:
        return 'FAIL'
    return 'PASS' if all(v == 'PASS' for v in verdicts) else 'INCONCLUSIVE'


EXECUTOR_FAILURE_LIMIT = 3
AUTHORIZATION_FAILURES = ('PROVIDER_HTTP_401', 'PROVIDER_HTTP_403') + REFUSED_CODES


class ExecutorRequestFailed(RuntimeError):
    """One executor request failed or did not return an action object. `code` is a fixed identifier, never provider text."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def ask_executor(ask, executor, prompt, image, budget, evidence, **context):
    """One executor request: returns the action dict, or raises ExecutorRequestFailed (the task ends INCONCLUSIVE, no retry).

    The fourth live run (083896e6, 16.10.2026) lost its PREPARATION stage and the whole suite to a single failed provider
    request, because a generic handler turned it into INVALID_HARNESS. A provider or response fault is a measurement gap,
    not a harness defect: it ends only the task in progress. After EXECUTOR_FAILURE_LIMIT consecutive failures (a systematic
    outage or quota stop) the suite stops as INCONCLUSIVE instead of spending the remaining requests on a dead provider.
    """
    failure = None
    try:
        data = ask(executor, prompt, image, budget, 'executor').data
        if not isinstance(data, dict):
            failure = 'EXECUTOR_RESPONSE_NOT_AN_OBJECT'
    except ResourceStop:
        raise
    except Exception as error:
        failure = getattr(error, 'code', None) or ('EXECUTOR_REQUEST_TIMEOUT' if isinstance(error, BudgetExceeded) else 'EXECUTOR_CALL_FAILED')
        context['exception_type'] = type(error).__name__
    if failure is None:
        budget.executor_failures = 0
        return {k: v for k, v in data.items() if v is not None}
    if failure in AUTHORIZATION_FAILURES:
        # The ChatGPT-plan access token lives about one hour and is never refreshed (live run 6c23f768 ended at 3603 s with HTTP 401): every further
        # request would fail the same way, so the suite stops now instead of after three more positions.
        evidence.event('executor_call_failed', error_code=failure, consecutive_failures=getattr(budget, 'executor_failures', 0) + 1, **context)
        budget.stop('PROVIDER_AUTHORIZATION_EXPIRED')
    budget.executor_failures = getattr(budget, 'executor_failures', 0) + 1
    evidence.event('executor_call_failed', error_code=failure, consecutive_failures=budget.executor_failures, **context)
    if budget.executor_failures >= EXECUTOR_FAILURE_LIMIT:
        budget.stop('EXECUTOR_UNAVAILABLE_AFTER_REPEATED_FAILURES')
    raise ExecutorRequestFailed(failure)


REVIEWER_FAILURE_LIMIT = 3


def ask_review(ask, reviewer, prompt, images, budget, evidence, **context):
    """Best-effort UX review: returns (data, None) or (None, error_code).

    A failed reviewer request is recorded with a fixed code and never repeated (each later
    review belongs to another stage or position). After REVIEWER_FAILURE_LIMIT consecutive
    failures the reviewer is switched off for the rest of the run, so a systematic fault
    costs at most three requests while an input-specific one does not remove the whole UX
    layer. Objective results never depend on it; only the resource ceiling still stops the run.
    """
    if getattr(budget, 'reviewer_failures', 0) >= REVIEWER_FAILURE_LIMIT:
        return None, 'REVIEWER_DISABLED_AFTER_REPEATED_FAILURES'
    try:
        data = ask(reviewer, prompt, images, budget, 'reviewer').data
        budget.reviewer_failures = 0
        return data, None
    except ResourceStop:
        raise
    except Exception as error:
        code = getattr(error, 'code', None) or 'REVIEWER_CALL_FAILED'
        budget.reviewer_failures = getattr(budget, 'reviewer_failures', 0) + 1
        evidence.event('reviewer_call_failed', error_code=code, consecutive_failures=budget.reviewer_failures, exception_type=type(error).__name__, **context)
        return None, code

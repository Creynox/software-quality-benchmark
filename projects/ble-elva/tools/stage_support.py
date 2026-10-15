"""Shared NSN014 stage controls: reviewer contract, stall detection, guard outcomes.

Objective case results come from controller evidence and independent Oracles.
The reviewer contributes a separate, versioned and provisional UX judgement; it
never decides PASS/FAIL. A guard rejection is a prevented action, not a safety
breach: only the affected task ends, unless the session itself became invalid.
"""
import hashlib

from sqbf.models import ActionValidationError

SCORING_VERSION = 'nsn014-objective-v1'
RUBRIC_VERSION = 'nsn014-ux-rubric-v1'
DIMENSIONS = ('findability', 'clarity', 'task_progress', 'error_recovery')
CATEGORIES = ('BLE_DEFECT_CANDIDATE', 'UX_IMPROVEMENT', 'AGENT_DIFFICULTY', 'HARNESS_SUSPECTED', 'UNCLEAR')
SEVERITIES = ('critical', 'major', 'minor', 'info')
CRITICAL_REJECTIONS = {'SESSION_INVALIDATED'}


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

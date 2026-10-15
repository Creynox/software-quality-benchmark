"""Controller-only measurement for regular suites; pilot budgets stay unchanged.

No browser, model, authentication or database operation is performed here.
Call reservations include failed requests; unknown token usage stays unknown.
"""
import time


class ResourceStop(RuntimeError):
    """Incomplete measurement, never evidence of an application failure."""


def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get('mode') != 'calibration':
        raise ValueError('Explicit calibration policy required')
    for key, ceiling in [('hard_seconds', 7200), ('hard_model_calls', 1000)]:
        value = policy.get(key)
        if type(value) is not int or not 1 <= value <= ceiling:
            raise ValueError('Invalid global resource ceiling')
    if (policy.get('limit_result') != 'INCONCLUSIVE'
            or policy.get('automatic_retry') is not False
            or policy.get('task_marks_are_hard_limits') is not False):
        raise ValueError('Resource stops must preserve incomplete measurement semantics')
    return policy


class SuiteBudget:
    def __init__(self, policy, clock=time.monotonic, on_change=lambda report: None):
        self.policy = dict(validate_policy(policy))
        self.clock = clock
        self.started = clock()
        self.calls = 0
        self.tasks = []
        self.active = None
        self.requests = []
        self.stop_reason = None
        self.on_change = on_change

    def _stop(self, reason):
        self.stop_reason = reason
        self.on_change(self.report())
        raise ResourceStop(reason)

    def remaining(self):
        if self.stop_reason:
            raise ResourceStop(self.stop_reason)
        left = self.policy['hard_seconds'] - (self.clock() - self.started)
        if left <= 0:
            self._stop('SUITE_TIME_CEILING')
        return left

    def start_task(self, case):
        self.remaining()
        if self.active is not None or any(t['case_id'] == case['case_id'] for t in self.tasks):
            raise ValueError('No overlapping tasks or automatic task retry')
        marks = case['observation_marks']
        for key in ('seconds', 'actions'):
            if type(marks.get(key)) is not int or marks[key] < 1:
                raise ValueError('Positive task observation marks required')
        self.active = {'case_id': case['case_id'], 'started': self.clock(),
                       'marks': dict(marks), 'actions': 0}
        self.tasks.append(self.active)
        self.active['persona']=case.get('persona')
        self.on_change(self.report())

    def action(self):
        self.remaining()
        if self.active is None:
            raise ValueError('Task required before an action')
        self.active['actions'] += 1
        self.on_change(self.report())

    def finish_task(self):
        if self.active is None:
            raise ValueError('No active task')
        if any(r['finished'] is None for r in self.requests):
            raise ValueError('Complete the pending request before closing its task')
        self.active['finished'] = self.clock()
        self.active = None
        self.on_change(self.report())

    def claim(self, actor='executor'):
        self.remaining()
        if self.active is None or actor not in ('executor', 'reviewer'):
            raise ValueError('Explicit task and actor required')
        if any(r['finished'] is None for r in self.requests):
            raise ValueError('Sequential request accounting required')
        if self.calls >= self.policy['hard_model_calls']:
            self._stop('SUITE_CALL_CEILING')
        self.calls += 1
        self.requests.append({'actor': actor, 'case_id': self.active['case_id'],
                              'started': self.clock(), 'finished': None, 'usage': None})
        self.on_change(self.report())
        return self.calls - 1

    def complete_call(self, ticket, usage=None):
        if type(ticket) is not int or not 0 <= ticket < len(self.requests):
            raise ValueError('Unknown request reservation')
        request = self.requests[ticket]
        if request['finished'] is not None:
            raise ValueError('Request already completed')
        # Whitelist numerical accounting only. Never retain model text or tokens.
        clean = {}
        if isinstance(usage, dict):
            for key in ('input_tokens', 'output_tokens', 'total_tokens'):
                value = usage.get(key)
                if type(value) is int and value >= 0:
                    clean[key] = value
        request.update(finished=self.clock(), usage=clean)
        self.on_change(self.report())
        self.remaining()  # Time spent waiting for a response counts too.

    def report(self):
        now = self.clock()
        if now - self.started >= self.policy['hard_seconds'] and not self.stop_reason:
            self.stop_reason = 'SUITE_TIME_CEILING'
        tasks = []
        for task in self.tasks:
            seconds = max(0, task.get('finished', now) - task['started'])
            tasks.append({'case_id': task['case_id'], 'persona':task.get('persona'), 'elapsed_seconds': seconds,
                          'actions': task['actions'], 'observation_marks': task['marks'],
                          'time_mark_exceeded': seconds > task['marks']['seconds'],
                          'action_mark_exceeded': task['actions'] > task['marks']['actions']})
        actors = {}
        for actor in ('executor', 'reviewer'):
            calls = [r for r in self.requests if r['actor'] == actor]
            tokens = {}
            for key in ('input_tokens', 'output_tokens', 'total_tokens'):
                known = [r['usage'][key] for r in calls if r['usage'] is not None and key in r['usage']]
                tokens[key] = {'known_sum': sum(known), 'unknown_calls': len(calls) - len(known),
                               'complete_total': sum(known) if len(known) == len(calls) else None}
            actors[actor] = {'model_calls': len(calls), 'tokens': tokens,
                             'model_wait_seconds': sum((now if r['finished'] is None else r['finished']) - r['started'] for r in calls)}
        elapsed = max(0, now - self.started)
        wait = sum(v['model_wait_seconds'] for v in actors.values())
        requests=[{'case_id':r['case_id'],'actor':r['actor'],
                   'elapsed_seconds':(now if r['finished'] is None else r['finished'])-r['started'],
                   'completed':r['finished'] is not None,'usage':r['usage']} for r in self.requests]
        return {'elapsed_seconds': elapsed, 'model_calls': self.calls, 'actors': actors,'requests':requests,
                'tasks': tasks, 'model_wait_seconds': wait,
                'non_model_elapsed_seconds': max(0, elapsed - wait),
                'stop_reason': self.stop_reason,
                'resource_result': 'INCONCLUSIVE' if self.stop_reason else None,
                'timing_kind': 'AI controller wall time; not human work time'}


def ask_calibrated(model, prompt, screenshots, budget, actor):
    """Use the existing tool-less worker; account both success and request failure.

    Inputs are supplied by an approved stage adapter. This helper grants no
    browser/filesystem/DB access and does not make an unimplemented stage ready.
    """
    import base64
    from .bounded import invoke_worker, model_spec
    from .providers import ModelResponse

    spec = model_spec(model)  # Reject unsupported/PAYG model before reserving.
    images = screenshots if isinstance(screenshots, list) else [screenshots]
    payload = {'provider': spec, 'prompt': prompt,
               'images': [base64.b64encode(png).decode('ascii') for png in images]}
    ticket = budget.claim(actor)
    usage = None
    try:
        response = invoke_worker('model', payload, min(30, budget.remaining()))
        usage = response['usage']
        return ModelResponse(response['data'], usage)
    finally:
        budget.complete_call(ticket, usage)

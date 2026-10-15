import copy
import importlib
import unittest
from sqbf.models import ActionValidationError
from sqbf.read_only import ReadOnlyViolation

module=importlib.import_module('projects.ble-elva.tools.stage_support')


def review(**changes):
    value={'verdict':'PASS','reason':'visible','scores':dict.fromkeys(module.DIMENSIONS,3),
           'findings':[{'category':'UX_IMPROVEMENT','severity':'minor','observed':'o','expected':'e',
                        'suggestion':'s','evidence':'image 2'}]}
    value.update(changes)
    return value


class StageSupportTests(unittest.TestCase):
    def test_review_schema_is_strict_and_allows_not_evaluated_dimensions(self):
        schema=module.REVIEW_SCHEMA
        self.assertFalse(schema['additionalProperties']);self.assertEqual(set(schema['required']),set(schema['properties']))
        scores=schema['properties']['scores']
        self.assertEqual(set(scores['required']),set(module.DIMENSIONS))
        self.assertTrue(all(v['type']==['integer','null'] for v in scores['properties'].values()))
        finding=schema['properties']['findings']['items']
        self.assertEqual(finding['properties']['category']['enum'],list(module.CATEGORIES))
        self.assertFalse(finding['additionalProperties'])
        self.assertIn('nsn014-ux-rubric-v1',module.review_prompt('intro',''))

    def test_valid_review_accepts_null_but_rejects_out_of_range_bool_and_unknown_findings(self):
        self.assertTrue(module.valid_review(review()))
        nulls=review();nulls['scores']['error_recovery']=None;self.assertTrue(module.valid_review(nulls))
        for value in (6,-1,True,2.5,'3'):
            bad=review();bad['scores']['clarity']=value;self.assertFalse(module.valid_review(bad))
        missing=review();del missing['scores']['clarity'];self.assertFalse(module.valid_review(missing))
        self.assertFalse(module.valid_review(review(verdict='GO')))
        self.assertFalse(module.valid_review({k:v for k,v in review().items() if k!='findings'}))
        for key,value in (('category','BLE_DEFECT'),('severity','blocker'),('observed',None)):
            bad=review();bad['findings'][0][key]=value;self.assertFalse(module.valid_review(bad))
        extra=copy.deepcopy(review());extra['findings'][0]['raw_values']='x';self.assertFalse(module.valid_review(extra))

    def test_only_an_invalidated_session_is_a_critical_rejection(self):
        self.assertEqual(module.classify_rejection(ActionValidationError('ACTION_OUT_OF_BOUNDS')),('ACTION_OUT_OF_BOUNDS',False))
        self.assertEqual(module.classify_rejection(ReadOnlyViolation('DUPLICATE_PDF_DOWNLOAD')),('DUPLICATE_PDF_DOWNLOAD',False))
        self.assertEqual(module.classify_rejection(ReadOnlyViolation('SESSION_INVALIDATED')),('SESSION_INVALIDATED',True))
        self.assertEqual(module.classify_rejection(ReadOnlyViolation()),('GUARD_REJECTED',False))

    def test_stall_requires_unchanged_screen_and_repeated_action(self):
        stall=module.StallDetector();action={'action':'click','x':100,'y':200}
        for _ in range(3):stall.observe(b'same');stall.record(action)
        self.assertFalse(stall.stalled());stall.observe(b'same');self.assertTrue(stall.stalled())
        moving=module.StallDetector()
        for i in range(6):moving.observe(b'screen'+bytes([i]));moving.record(action)
        self.assertFalse(moving.stalled())
        typed=module.StallDetector()
        for value in ('95','122','96','121'):typed.observe(b'same');typed.record({'action':'type','text':value})
        self.assertFalse(typed.stalled())
        for _ in range(3):typed.observe(b'same');typed.record({'action':'type','text':'95'})
        self.assertTrue(typed.stalled())
        varied=module.StallDetector()
        for i in range(6):varied.observe(b'same');varied.record({'action':'click','x':100+i*20,'y':200})
        self.assertFalse(varied.stalled())

    def test_incomplete_reasons_and_separate_ux_verdict(self):
        self.assertEqual(module.incomplete_reason({'status':'BLOCKED'}),'EXECUTOR_REPORTED_BLOCKED')
        self.assertEqual(module.incomplete_reason({'status':'REJECTED','rejected_action_code':'X'}),'AGENT_ACTION_REJECTED:X')
        self.assertEqual(module.incomplete_reason({'status':'STALLED'}),'NO_VISIBLE_PROGRESS')
        self.assertEqual(module.incomplete_reason({'status':'INCONCLUSIVE'}),'NO_TERMINAL_SIGNAL')
        self.assertEqual(module.ux_verdicts([{'review':None}]),'NOT_EVALUATED')
        self.assertEqual(module.ux_verdicts([{'review':review()},{'review':review(verdict='FAIL')}]),'FAIL')
        self.assertEqual(module.ux_verdicts([{'review':review(),'pdf_reviews':[review()]}]),'PASS')
        self.assertEqual(module.ux_verdicts([{'review':review(),'pdf_reviews':[review(verdict='INCONCLUSIVE')]}]),'INCONCLUSIVE')


class ReviewerBestEffortTests(unittest.TestCase):
    class Budget:
        pass

    class Evidence:
        def __init__(self):
            self.events = []

        def event(self, kind, **fields):
            self.events.append((kind, fields))

    def test_repeated_reviewer_failures_switch_the_reviewer_off_but_one_does_not(self):
        from sqbf.providers import ModelResponse
        evidence, budget, calls = self.Evidence(), self.Budget(), []

        class Failure(RuntimeError):
            code = 'PROVIDER_HTTP_400'

        def ask(model, prompt, images, budget_, actor):
            calls.append(actor)
            raise Failure('provider text that must never be stored')
        self.assertEqual(module.ask_review(ask, 'r', 'p', [b'x'], budget, evidence, persona='lead'), (None, 'PROVIDER_HTTP_400'))
        for _ in range(2):module.ask_review(ask, 'r', 'p', [b'x'], budget, evidence)
        self.assertEqual(module.ask_review(ask, 'r', 'p', [b'x'], budget, evidence), (None, 'REVIEWER_DISABLED_AFTER_REPEATED_FAILURES'))
        self.assertEqual(calls, ['reviewer'] * module.REVIEWER_FAILURE_LIMIT)
        self.assertEqual(evidence.events[0], ('reviewer_call_failed', {'error_code': 'PROVIDER_HTTP_400', 'consecutive_failures': 1, 'persona': 'lead'}))
        self.assertEqual(len(evidence.events), 3);self.assertNotIn('provider text', str(evidence.events))

    def test_a_success_resets_the_consecutive_failure_count(self):
        from sqbf.providers import ModelResponse
        budget, evidence, outcomes = self.Budget(), self.Evidence(), ['fail', 'fail', 'ok', 'fail', 'fail', 'ok', 'fail']

        def ask(model, prompt, images, budget_, actor):
            if outcomes.pop(0) == 'fail':raise RuntimeError('x')
            return ModelResponse({'verdict': 'PASS'}, {})
        results = [module.ask_review(ask, 'r', 'p', [], budget, evidence)[1] for _ in range(7)]
        self.assertEqual(results, ['REVIEWER_CALL_FAILED', 'REVIEWER_CALL_FAILED', None, 'REVIEWER_CALL_FAILED', 'REVIEWER_CALL_FAILED', None,
                                   'REVIEWER_CALL_FAILED'])
        self.assertEqual(outcomes, [])
        plain = self.Budget()
        self.assertEqual(module.ask_review(lambda *a: (_ for _ in ()).throw(ValueError('x')), 'r', 'p', [], plain, evidence),
                         (None, 'REVIEWER_CALL_FAILED'))
        good = self.Budget()
        self.assertEqual(module.ask_review(lambda *a: ModelResponse({'verdict': 'PASS'}, {}), 'r', 'p', [], good, evidence),
                         ({'verdict': 'PASS'}, None))

    def test_only_the_resource_ceiling_still_stops_the_run(self):
        from sqbf.calibration import ResourceStop
        budget = self.Budget()
        with self.assertRaises(ResourceStop):
            module.ask_review(lambda *a: (_ for _ in ()).throw(ResourceStop('SUITE_CALL_CEILING')), 'r', 'p', [], budget, self.Evidence())
        self.assertFalse(hasattr(budget, 'reviewer_error'))

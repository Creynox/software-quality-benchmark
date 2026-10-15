import importlib
import unittest
from unittest.mock import MagicMock,patch
from sqbf.calibration import SuiteBudget
from sqbf.providers import ModelResponse
from test_calibration import policy
from test_measurement_guard import position
from test_suite_fixture import owned_fixture

module=importlib.import_module('projects.ble-elva.tools.measurement_runner')


class MeasurementRunnerTests(unittest.TestCase):
    def test_screenshot_model_receives_no_fixture_or_session_or_database_paths(self):
        f=owned_fixture();f['personas']={'laboratory_staff':{'storage_state':'do-not-disclose-private-session'}}
        p=position();p.update(sample_code='SYNTHETIC-01',product='Synthetic stone')
        browser=MagicMock();page=browser.new_context.return_value.new_page.return_value
        page.url=f['target_url']+'samples/11111111-1111-4111-8111-111111111111';page.screenshot.return_value=b'png'
        budget=SuiteBudget(policy());budget.start_task({'case_id':'SE','observation_marks':{'seconds':600,'actions':60}})
        answers=[ModelResponse({'action':'blocked','reason':'Synthetic fixture UI missing'},{}),
                 ModelResponse({'verdict':'INCONCLUSIVE','scores':dict.fromkeys(('findability','clarity','task_progress','error_recovery'),2)},{})]
        with patch.object(module,'ask_calibrated',side_effect=answers) as ask,patch.object(module,'check_action'):
            result=module.run_position(browser,f,p,'11111111-1111-4111-8111-111111111111','sand',{},object(),object(),budget,MagicMock())
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['technical_gate'],'PASS');self.assertEqual(ask.call_count,2)
        for call in ask.call_args_list:
            self.assertNotIn('do-not-disclose-private-session',call.args[1]);self.assertNotIn('container_id',call.args[1])
        self.assertIn('unverified_executor_statement',ask.call_args_list[-1].args[1])
        browser.new_context.return_value.close.assert_called_once()

    def run_boiling(self,offered):
        f=owned_fixture();f['personas']={'laboratory_staff':{'storage_state':'x'}}
        p=position();p.update(sample_code='SYNTHETIC-01',product='Synthetic stone')
        browser=MagicMock();page=browser.new_context.return_value.new_page.return_value
        page.url=f['target_url']+'samples/11111111-1111-4111-8111-111111111111';page.screenshot.return_value=b'png'
        budget=SuiteBudget(policy());budget.start_task({'case_id':'SE','observation_marks':{'seconds':600,'actions':60}})
        answers=[ModelResponse({'action':'blocked','reason':'field missing'},{}),
                 ModelResponse({'verdict':'INCONCLUSIVE','scores':dict.fromkeys(('findability','clarity','task_progress','error_recovery'),2)},{})]
        with patch.object(module,'ask_calibrated',side_effect=answers) as ask,patch.object(module,'check_action'),patch.object(module,'offered_fields',return_value=offered):
            result=module.run_position(browser,f,p,'11111111-1111-4111-8111-111111111111','boiling',{},object(),object(),budget,MagicMock())
        return result,ask

    def test_numbers_reach_the_executor_in_german_notation_only(self):
        result,ask=self.run_boiling(set())
        prompt=ask.call_args_list[0].args[1]
        self.assertIn('99,5',prompt);self.assertIn('0,5',prompt)
        self.assertNotIn('99.5',prompt);self.assertNotIn('0.5',prompt)
        self.assertIn('thousands separator',prompt)

    def test_missing_controls_are_recorded_and_executor_created_rows_are_not_counted(self):
        result,_=self.run_boiling({'Einwaage vor Kochen:1'})
        self.assertEqual(result['fields_offered'],1)
        # The repetition row fields (suffix :1) are created by the executor; only the module field can be absent.
        self.assertEqual(result['fields_not_offered'],['Geschaedigte Koerner / Mergelmasse'])
        self.assertFalse(result['offered_entered'])
        result,_=self.run_boiling(set())
        self.assertEqual(result['fields_offered'],0);self.assertTrue(result['offered_entered'])

    def test_absent_fields_are_evidence_for_the_reviewer_and_never_a_fail(self):
        entered=dict(status='DONE',fully_entered=False,offered_entered=True,fields_not_offered=['KF:5.6'])
        self.assertEqual(module.classify_position([entered],True),('INCOMPLETE','APPROVED_FIELDS_NOT_PRESENT_ON_PAGE'))
        blocked=dict(entered,status='BLOCKED')
        self.assertEqual(module.classify_position([blocked],True),('INCOMPLETE','APPROVED_FIELDS_NOT_PRESENT_ON_PAGE'))
        # Negative cases: an executor that left a present field empty, or that stalled, keeps its own class.
        skipped=dict(entered,offered_entered=False)
        self.assertEqual(module.classify_position([skipped],True),('INCOMPLETE','EXECUTOR_DONE_WITHOUT_ALL_APPROVED_INPUTS'))
        self.assertEqual(module.classify_position([dict(entered,status='STALLED')],True)[1],module.incomplete_reason(dict(entered,status='STALLED')))
        # Everything entered, saved and still deviating is a persisted deviation (FAIL), also when more controls were present than needed.
        self.assertEqual(module.classify_position([dict(status='DONE',fully_entered=True,offered_entered=True,fields_not_offered=[])],True),
                         ('FAIL','PERSISTED_VALUE_DEVIATION'))
        self.assertEqual(module.classify_position([dict(status='DONE',fully_entered=True,offered_entered=True,fields_not_offered=[])],False),('PASS',None))

    def test_one_module_with_absent_fields_does_not_excuse_a_skipped_module(self):
        absent=dict(status='DONE',fully_entered=False,offered_entered=True,fields_not_offered=['KF:5.6'])
        skipped=dict(status='DONE',fully_entered=False,offered_entered=False,fields_not_offered=[])
        self.assertEqual(module.classify_position([absent,skipped],True),('INCOMPLETE','EXECUTOR_DONE_WITHOUT_ALL_APPROVED_INPUTS'))

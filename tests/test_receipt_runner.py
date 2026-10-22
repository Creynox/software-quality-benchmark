import importlib
import unittest
from unittest.mock import MagicMock, patch
from sqbf.calibration import SuiteBudget, ResourceStop
from sqbf.providers import ModelResponse
from test_calibration import policy
from test_suite_fixture import owned_fixture

module=importlib.import_module('projects.ble-elva.tools.receipt_runner')
guard=importlib.import_module('projects.ble-elva.tools.receipt_guard')


class ReceiptRunnerTests(unittest.TestCase):
    def fixture(self):
        f=owned_fixture(); f['suite_copy']['preparation_context']={'customer':'SQBF Enzberg','project':'SQBF NSN 014','sample_owner':'Werk Enzberg'}
        f['personas']={'laboratory_staff':{'storage_state':'local-secret-state'}}
        return f

    def test_position_sends_only_task_images_and_visible_actions_to_models(self):
        browser=MagicMock(); context=browser.new_context.return_value
        page=context.new_page.return_value;page.url='http://127.0.0.1:5082/samples'
        page.screenshot.return_value=b'png'
        budget=SuiteBudget(policy());budget.start_task({'case_id':'receipt','observation_marks':{'seconds':600,'actions':60}})
        f=self.fixture(); p={'position_id':'P01','product':'synthetic','inputs':{'sample_code':'TEST-01'}}
        calls=[ModelResponse({'action':'blocked','reason':'Product unavailable'},{}),
               ModelResponse({'verdict':'INCONCLUSIVE','reason':'No save visible','findings':[]},{})]
        with patch.object(module,'ask_calibrated',side_effect=calls) as ask, patch.object(module,'check_action'):
            result=module.run_position(browser,f,p,'2026-05-08',{},object(),object(),budget,MagicMock())
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['technical_gate'],'PASS')
        self.assertFalse(result['save_attempted']);self.assertEqual(ask.call_count,2)
        for call in ask.call_args_list:
            prompt=call.args[1]
            self.assertNotIn('local-secret-state',prompt);self.assertNotIn('database',prompt.lower())
            self.assertNotIn('tenant_id',prompt);self.assertNotIn('controller',prompt)
        self.assertEqual(ask.call_args_list[-1].args[-1],'reviewer')
        context.close.assert_called_once()

    def test_no_review_or_next_position_after_security_stop(self):
        f=self.fixture();p={'position_id':'P01','product':'synthetic','inputs':{'sample_code':'TEST-01'}}
        b=MagicMock();page=b.new_context.return_value.new_page.return_value;page.url='http://127.0.0.1:5082/login'
        budget=SuiteBudget(policy());budget.start_task({'case_id':'receipt','observation_marks':{'seconds':600,'actions':60}})
        with patch.object(module,'ask_calibrated') as ask:
            result=module.run_position(b,f,p,'2026-05-08',{},object(),object(),budget,MagicMock())
        ask.assert_not_called();self.assertEqual(result['technical_gate'],'BLOCKED')

    def test_final_record_view_is_read_only_and_requires_controller_save(self):
        page=MagicMock();page.url='http://127.0.0.1:5082/samples/11111111-1111-4111-8111-111111111111'
        c=guard.make_contract(self.fixture(),{'position_id':'P01','product':'synthetic','inputs':{'sample_code':'TEST-01'}},'2026-05-08')
        guard.check_action(page,{'action':'done'},c,controller_saved=True)
        for action,saved in [({'action':'click','x':1,'y':2},True),({'action':'done'},False)]:
            with self.assertRaises(module.ReadOnlyViolation):guard.check_action(page,action,c,controller_saved=saved)
        page.evaluate.assert_not_called()

    def test_resource_stop_does_not_start_another_position_or_retry(self):
        f=self.fixture();dataset={'positions':[{'position_id':'P01'},{'position_id':'P02'}],'reference':{'sampling_date':'2026-05-08'}}
        with patch.object(module,'collect_receipts'),patch.object(module,'verify_receipts',return_value={'status':'RECEIPT_START_VERIFIED'}), \
             patch.object(module,'run_position',return_value={'technical_gate':'PASS','status':'INCONCLUSIVE','stop_reason':'SUITE_CALL_CEILING'}) as position:
            result=module.run_receipt(object(),f,dataset,{},object(),object(),object(),object())
        position.assert_called_once();self.assertEqual(result['result'],'INCONCLUSIVE')

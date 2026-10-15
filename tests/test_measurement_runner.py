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

import copy
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock,patch
from sqbf.calibration import SuiteBudget
from sqbf.suites import aggregate,canonical_hash
from sqbf.cli import main
from test_suite_fixture import owned_fixture

module=importlib.import_module('projects.ble-elva.tools.regular_runner')


def suite():
    return json.loads(Path('projects/ble-elva/suites/enzberg-nsn014-v0.4.json').read_text(encoding='utf-8'))


def verdict(result='PASS'):
    return {'result':result,'technical_gate':'PASS','oracle_gate':'PASS','evidence_verified':True,
            'review':{'verdict':'PASS','scores':dict.fromkeys(('findability','clarity','task_progress','error_recovery'),3)}}


def fixture():
    f=owned_fixture();f['personas']={k:{'storage_state':'private-'+k} for k in suite()['personas']}
    f['identity_verifier']='private-verifier'
    return f


class RegularRunnerTests(unittest.TestCase):
    def test_complete_twelve_case_mock_schedule_has_no_retry(self):
        s=suite();stage=MagicMock(side_effect=lambda case:verdict())
        scope=MagicMock(return_value={'status':'PERSONA_SCOPE_VERIFIED'})
        checkpoints=[]
        records=module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,
            write=lambda records,accounting:checkpoints.append(copy.deepcopy(records)),scope_fn=scope)
        self.assertEqual(len(records),12);self.assertEqual(stage.call_count,12);self.assertEqual(scope.call_count,12)
        self.assertEqual(aggregate(s,records)['measurement_status'],'COMPLETE_VALID')
        self.assertEqual(len({r['case_id'] for r in records}),12);self.assertEqual(len(checkpoints),12)

    def test_ordinary_task_failure_continues_but_security_or_harness_failure_stops(self):
        s=suite();scope=MagicMock(return_value={'status':'PERSONA_SCOPE_VERIFIED'})
        stage=MagicMock(side_effect=lambda case:verdict('FAIL') if case['case_id']=='NSN014-PLAN' else verdict())
        records=module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,scope_fn=scope)
        self.assertEqual(stage.call_count,12);self.assertEqual(aggregate(s,records)['result'],'FAIL')
        for record in ({'result':'BLOCKED','technical_gate':'BLOCKED'}, {'result':'INVALID','technical_gate':'INVALID'}):
            stage=MagicMock(return_value=record)
            records=module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,scope_fn=scope)
            stage.assert_called_once();self.assertTrue(all(r['result']=='BLOCKED' for r in records[1:]))

    def test_scope_failure_before_stage_and_invalid_reviewer_score_cannot_pass(self):
        s=suite();stage=MagicMock()
        records=module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,
            scope_fn=MagicMock(return_value={'status':'BLOCKED_SCOPE_VERIFICATION'}))
        stage.assert_not_called();self.assertEqual(records[0]['reason'],'ACTOR_SCOPE_FAILED')
        invalid=verdict();invalid['review']['scores']['clarity']=6
        stage=MagicMock(return_value=invalid)
        records=module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,
            scope_fn=MagicMock(return_value={'status':'PERSONA_SCOPE_VERIFIED'}))
        stage.assert_called_once();self.assertEqual(records[0]['result'],'INVALID')

    def test_global_resource_stop_is_not_application_failure(self):
        s=suite();now=[0];budget=SuiteBudget(s['resource_policy'],clock=lambda:now[0])
        def stage(case):now[0]=7201;budget.remaining()
        records=module.execute_cases(s,fixture(),budget,stage,
            scope_fn=MagicMock(return_value={'status':'PERSONA_SCOPE_VERIFIED'}))
        self.assertEqual(records[0]['result'],'INCONCLUSIVE');self.assertEqual(records[0]['stop_reason'],'SUITE_TIME_CEILING')
        self.assertEqual(aggregate(s,records)['measurement_status'],'INCOMPLETE')

    def test_all_case_ids_dispatch_to_a_real_registered_adapter(self):
        s=suite();empty=object();args=[empty]*10
        with patch.object(module,'run_plan_creation',return_value=verdict()) as receipt, \
             patch.object(module,'run_measurements',return_value=verdict()) as measurements, \
             patch.object(module,'run_inspection',return_value=verdict()) as inspection, \
             patch.object(module,'run_reports',return_value=verdict()) as reports, \
             patch.object(module,'collect_receipts'),patch.object(module,'verify_receipts',return_value={'status':'PASS'}):
            for case in s['cases']:module.dispatch(case,*args)
        self.assertEqual((receipt.call_count,measurements.call_count,inspection.call_count,reports.call_count),(1,5,5,1))

    def test_readiness_missing_adapter_stops_before_browser_db_or_auth(self):
        s=suite();s['cases'][0]['implementation']='pending'
        with patch.object(module,'check_fixture') as gates,patch.object(module,'collect_inputs') as oracle:
            result=module.check_ready(s,{},fixture(),{}, {})
        self.assertEqual(result['reason'],'ADAPTER_COVERAGE_PENDING');gates.assert_not_called();oracle.assert_not_called()

    def test_cli_default_is_model_free_and_requires_explicit_execute_flag(self):
        s=suite()
        with patch.object(module,'load_inputs',return_value=(s,{},fixture(),{},{})), \
             patch.object(module,'check_ready',return_value={'status':'READY_FOR_SINGLE_SUITE_RUN','model_calls':0}) as check, \
             patch.object(module,'run_suite') as execute:
            result=main(['run-suite','--suite','projects/ble-elva/suites/enzberg-nsn014-v0.4.json','--fixture','private',
                         '--dataset','private','--projection','private','--allocations','private'])
        self.assertEqual(result,0);check.assert_called_once();execute.assert_not_called()

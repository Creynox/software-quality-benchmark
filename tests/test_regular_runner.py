import copy
import importlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import MagicMock,patch
from sqbf.calibration import SuiteBudget
from sqbf.suites import aggregate,canonical_hash
from sqbf.cli import main
from test_suite_fixture import owned_fixture
from test_measurement_guard import position

module=importlib.import_module('projects.ble-elva.tools.regular_runner')
DIMENSIONS=('findability','clarity','task_progress','error_recovery')


def suite():
    return json.loads(Path('projects/ble-elva/suites/enzberg-nsn014-v0.4.json').read_text(encoding='utf-8'))


def review(verdict='PASS',score=3,findings=()):
    return {'verdict':verdict,'reason':'visible','scores':dict.fromkeys(DIMENSIONS,score),'findings':list(findings)}


def verdict(result='PASS'):
    return {'result':result,'technical_gate':'PASS','oracle_gate':'PASS','evidence_verified':True,'review':review()}


def fixture():
    f=owned_fixture();f['personas']={k:{'storage_state':'private-'+k,'role':k,'allowed_permissions':['samples.view']}
                                     for k in suite()['personas']}
    f['identity_verifier']='private-verifier'
    return f


def finding(category='BLE_DEFECT_CANDIDATE',severity='major'):
    return {'category':category,'severity':severity,'observed':'Save button hidden','expected':'Visible save',
            'suggestion':'Show save','evidence':'image 2'}


class RegularRunnerTests(unittest.TestCase):
    def run_cases(self,stage,s=None):
        s=s or suite()
        return module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,
                                    scope_fn=MagicMock(return_value={'status':'PERSONA_SCOPE_VERIFIED'}))

    def test_complete_twelve_case_mock_schedule_has_no_retry(self):
        s=suite();stage=MagicMock(side_effect=lambda case:verdict())
        scope=MagicMock(return_value={'status':'PERSONA_SCOPE_VERIFIED'})
        checkpoints=[]
        records=module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,
            write=lambda records,accounting:checkpoints.append(copy.deepcopy(records)),scope_fn=scope)
        self.assertEqual(len(records),12);self.assertEqual(stage.call_count,12);self.assertEqual(scope.call_count,12)
        self.assertEqual(aggregate(s,records)['measurement_status'],'COMPLETE_VALID')
        self.assertEqual(len({r['case_id'] for r in records}),12);self.assertEqual(len(checkpoints),12)
        self.assertEqual([r['persona'] for r in records],[c['persona'] for c in s['cases']])

    def test_ordinary_task_failure_continues_but_security_or_harness_failure_stops(self):
        s=suite()
        stage=MagicMock(side_effect=lambda case:verdict('FAIL') if case['case_id']=='NSN014-PLAN' else verdict())
        records=self.run_cases(stage,s)
        self.assertEqual(stage.call_count,12);self.assertEqual(aggregate(s,records)['result'],'FAIL')
        for record in ({'result':'BLOCKED','technical_gate':'BLOCKED'},{'result':'INVALID','technical_gate':'INVALID'}):
            stage=MagicMock(return_value=record);records=self.run_cases(stage,s)
            stage.assert_called_once();self.assertTrue(all(r['result']=='NOT_RUN' for r in records[1:]))
            self.assertEqual(records[1]['reason'],'UPSTREAM_CRITICAL_STOP')
            self.assertEqual(aggregate(s,records)['measurement_status'],'INVALID' if record['result']=='INVALID' else 'INCOMPLETE')
        self.assertEqual(records[0]['objective_status'],'INVALID_HARNESS')

    def test_integrity_fault_with_critical_stop_ends_suite_after_recording_the_fail(self):
        s=suite();corrupt=dict(verdict('FAIL'),critical_stop=True,reason='PLAN_SAMPLE_INTEGRITY_FAILED')
        stage=MagicMock(return_value=corrupt);records=self.run_cases(stage,s)
        stage.assert_called_once();self.assertEqual(records[0]['objective_status'],'FAIL')
        self.assertEqual(records[1]['upstream_reason'],'PLAN_SAMPLE_INTEGRITY_FAILED')
        summary=aggregate(s,records)
        self.assertEqual((summary['result'],summary['counts']['NOT_RUN']),('FAIL',11))

    def test_scope_failure_before_stage_and_invalid_reviewer_score_cannot_pass(self):
        s=suite();stage=MagicMock()
        records=module.execute_cases(s,fixture(),SuiteBudget(s['resource_policy']),stage,
            scope_fn=MagicMock(return_value={'status':'BLOCKED_SCOPE_VERIFICATION'}))
        stage.assert_not_called();self.assertEqual(records[0]['reason'],'ACTOR_SCOPE_FAILED')
        invalid=verdict();invalid['review']['scores']['clarity']=6
        stage=MagicMock(return_value=invalid);records=self.run_cases(stage,s)
        stage.assert_called_once();self.assertEqual(records[0]['result'],'INVALID')

    def test_not_evaluated_dimensions_and_pdf_page_batches_are_valid_reviews(self):
        record=verdict();record['review']['scores']['error_recovery']=None
        record['positions']=[{'review':review(findings=[finding()]),'pdf_reviews':[dict(review('INCONCLUSIVE',None),pages=[1,2,3])]}]
        self.assertTrue(module._valid_reviewers(record))
        record['positions'][0]['pdf_reviews'][0]['findings']=[dict(finding(),category='OTHER')]
        self.assertFalse(module._valid_reviewers(record))

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

    def test_receipt_oracle_separates_missing_plan_prerequisite_from_inconsistent_state(self):
        case=next(c for c in suite()['cases'] if c['case_id']=='NSN014-RECEIPT');args=[object()]*10
        for oracle,expected in (({'status':'PASS'},('PASS','PASS')),
                                ({'status':'FAIL','missing_positions':['P1'],'mismatched_positions':[],'orphan_lims':False},('INCONCLUSIVE','PASS')),
                                ({'status':'FAIL','missing_positions':[],'mismatched_positions':['P2'],'orphan_lims':False},('BLOCKED','BLOCKED')),
                                ({'status':'BLOCKED_RECEIPT_EVIDENCE'},('BLOCKED','BLOCKED'))):
            with patch.object(module,'run_inspection',return_value=verdict()),patch.object(module,'collect_receipts'), \
                 patch.object(module,'verify_receipts',return_value=oracle):
                result=module.dispatch(case,*args)
            self.assertEqual((result['result'],result['technical_gate']),expected,oracle)
        self.assertEqual(result['reason'],'RECEIPT_ORACLE_UNAVAILABLE')

    def test_readiness_missing_adapter_stops_before_browser_db_or_auth(self):
        s=suite();s['cases'][0]['implementation']='pending'
        with patch.object(module,'check_fixture') as gates,patch.object(module,'collect_inputs') as oracle:
            result=module.check_ready(s,{},fixture(),{}, {})
        self.assertEqual(result['reason'],'ADAPTER_COVERAGE_PENDING');gates.assert_not_called();oracle.assert_not_called()

    def test_uncommitted_sqbf_source_blocks_readiness_before_fixture_access(self):
        f=fixture();f['suite_copy']['application_root']='D:/Temp/sqbf-unit-nonexistent/app'
        dirty={'commit':'c'*40,'clean':False,'checked_paths':['sqbf','projects']}
        with patch.object(module,'source_state',return_value=dirty),patch.object(module,'check_fixture') as gates:
            result=module.check_ready(suite(),{},f,{},{})
        self.assertEqual(result['reason'],'SQBF_SOURCE_NOT_COMMITTED');gates.assert_not_called()

    def test_source_state_reads_commit_and_porcelain_of_executed_paths(self):
        calls=[]
        def run(command,**kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command,0,stdout='a'*40+'\n' if 'rev-parse' in command else ' M sqbf/x.py\n')
        state=module.source_state(run=run)
        self.assertEqual(state,{'commit':'a'*40,'clean':False,'checked_paths':['sqbf','projects']})
        self.assertEqual(calls[1][-3:],['--','sqbf','projects'])
        clean=module.source_state(run=lambda command,**kwargs:subprocess.CompletedProcess(command,0,stdout='a'*40 if 'rev-parse' in command else ''))
        self.assertTrue(clean['clean'])

    def test_request_estimate_is_a_lower_bound_per_case(self):
        s=suite();f=fixture();p=position()
        projection={'positions':[dict(p,position_id=key,sample_code='S-'+key) for key in s['required_position_ids']]}
        allocation={'positions':[{'position_id':key,'allocations':p['allocations']} for key in s['required_position_ids']]}
        estimate=module.estimate_requests(s,projection,allocation,f)
        self.assertEqual(set(estimate['per_case']),{c['case_id'] for c in s['cases']})
        self.assertEqual(estimate['per_case']['NSN014-REPORT'],70);self.assertEqual(estimate['per_case']['NSN014-RIGHTS'],3)
        self.assertEqual(estimate['per_case']['NSN014-SE'],10*(2*4+1+2+1))
        self.assertTrue(estimate['fits_ceiling']);self.assertEqual(estimate['hard_model_calls'],1000)
        s['resource_policy']['hard_model_calls']=10
        self.assertFalse(module.estimate_requests(s,projection,allocation,f)['fits_ceiling'])

    def test_route_probes_cover_every_persona_entry_once(self):
        f=fixture();f['suite_copy']['mapping']={'plan_id':'11111111-1111-4111-8111-111111111111'}
        probes=module.route_probes(suite(),f)
        self.assertEqual({(persona,path) for persona,path,_ in probes},{
            ('laboratory_staff','/samples'),('laboratory_lead','/samples'),('wpk_lead','/quality/wpk'),
            ('plant_lead','/analytics'),('plant_lead','/beprobung/11111111-1111-4111-8111-111111111111')})
        staff=next(stages for persona,_,stages in probes if persona=='laboratory_staff')
        self.assertEqual(len(staff),6)

    def test_persona_context_records_roles_and_permissions_without_identities(self):
        f=fixture();f['personas']['plant_lead'].update(username='secret-user',user_id='secret-id')
        context=module.persona_context(suite(),f)
        self.assertEqual(context['plant_lead']['cases'],['NSN014-ANALYSIS','NSN014-RIGHTS'])
        self.assertEqual(context['plant_lead']['permissions_sha256'],canonical_hash(['samples.view']))
        self.assertNotIn('secret',json.dumps(context))

    def test_final_calculation_mismatch_revokes_go(self):
        manifest={'verdict':'GO'};f=fixture()
        passing={'status':'PASS'}
        with patch.object(module,'collect_receipts'),patch.object(module,'collect_inputs',return_value=[]), \
             patch.object(module,'collect_allocations'),patch.object(module,'collect_reports'), \
             patch.object(module,'collect_report_calculations'),patch.object(module,'static_fixture_unchanged',return_value=True), \
             patch.object(module,'verify_receipts',return_value=passing),patch.object(module,'verify_inputs',return_value=passing), \
             patch.object(module,'verify_allocations',return_value=passing),patch.object(module,'verify_reports',return_value=passing) as reports, \
             patch.object(module,'verify_calculations',return_value={'status':'FAIL'}):
            module.finalise_oracles(manifest,{'records':[]},f,{},{},{},{})
        self.assertEqual((manifest['verdict'],manifest['reason']),('NO-GO','FINAL_ORACLE_FAILED'))
        self.assertEqual(reports.call_args.kwargs['basis'],{})

    def test_case_matrix_and_german_report_keep_objective_status_and_ux_apart(self):
        records=[dict(verdict(),case_id='NSN014-PLAN',persona='laboratory_lead',objective_status='PASS',ux_verdict='PASS'),
                 {'case_id':'NSN014-SE','persona':'laboratory_staff','result':'FAIL','objective_status':'FAIL','technical_gate':'PASS',
                  'oracle_gate':'FAIL','fail_classes':['PERSISTED_VALUE_DEVIATION'],'ux_verdict':'FAIL',
                  'position_results':[{'position_id':'P1','result':'FAIL','class':'PERSISTED_VALUE_DEVIATION'},
                                      {'position_id':'P2','result':'PASS','class':None}],
                  'positions':[{'position_id':'P1','review':review('FAIL',None,[finding(),finding('UX_IMPROVEMENT','minor')])}]},
                 {'case_id':'NSN014-WPK','persona':'wpk_lead','result':'INVALID','objective_status':'INVALID_HARNESS',
                  'technical_gate':'INVALID','reason':'INSPECTION_RUNNER_ERROR'},
                 {'case_id':'NSN014-RIGHTS','persona':'plant_lead','result':'NOT_RUN','objective_status':'NOT_RUN',
                  'reason':'UPSTREAM_CRITICAL_STOP'}]
        matrix=module.case_matrix(records)
        self.assertEqual([r['objective_status'] for r in matrix],['PASS','FAIL','INVALID_HARNESS','NOT_RUN'])
        self.assertEqual(matrix[1]['ux_scores']['clarity'],'NOT_EVALUATED');self.assertEqual(matrix[0]['ux_scores']['clarity'],{'n':1,'min':3,'max':3})
        summary=module.ux_summary(records)
        self.assertEqual(summary['finding_counts']['BLE_DEFECT_CANDIDATE']['major'],1);self.assertIsNone(summary['global_score'])
        manifest={'run_id':'r','verdict':'NO-GO','technical_status':'INVALID','functional_status':'INVALID','scenario_id':'ENZBERG-NSN014',
                  'scenario_version':'0.4','scoring_version':module.SCORING_VERSION,'rubric_version':module.RUBRIC_VERSION,
                  'sqbf_commit':'c','software_version':'b','executor_model':'e','analyst_model':'a','suite_sha256':'s',
                  'dataset_sha256':'d','case_matrix':matrix,'ux_summary':summary}
        text=module.completion_text(manifest,records)
        for heading in ('## 1. Was in BLE funktioniert','## 2. Was in BLE nicht funktioniert','## 3. BLE- oder SQBF-Problem',
                        '## 4. UX-Befunde nach Kategorie und Schweregrad','## 5. Priorität','## 6. Retest-Benchmark'):
            self.assertIn(heading,text)
        self.assertIn('NSN014-SE: \\[\'PERSISTED\\_VALUE\\_DEVIATION\'\\]',text)
        self.assertIn('SQBF/Harness',text);self.assertIn('BLE-Kandidat (unbestätigt): major 1',text)
        self.assertIn('bestandene Positionen',text);self.assertNotIn('<script',module.completion_text(
            dict(manifest,run_id='<script>'),records))

    def test_cli_default_is_model_free_and_requires_explicit_execute_flag(self):
        s=suite()
        with patch.object(module,'load_inputs',return_value=(s,{},fixture(),{},{})), \
             patch.object(module,'check_ready',return_value={'status':'READY_FOR_SINGLE_SUITE_RUN','model_calls':0}) as check, \
             patch.object(module,'run_suite') as execute:
            result=main(['run-suite','--suite','projects/ble-elva/suites/enzberg-nsn014-v0.4.json','--fixture','private',
                         '--dataset','private','--projection','private','--allocations','private'])
        self.assertEqual(result,0);check.assert_called_once();execute.assert_not_called()

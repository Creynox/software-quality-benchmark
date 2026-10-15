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

    def test_stage_contracts_round_trip_the_reference_through_every_oracle_vocabulary(self):
        from test_measurement_oracle import inputs
        f,projection,_=inputs();s=suite()
        s['required_position_ids']=[p['position_id'] for p in projection['positions']]
        allocation={'positions':[{'position_id':p['position_id'],'allocations':[]} for p in projection['positions']]}
        result=module.stage_contracts(s,projection,allocation,f)
        self.assertEqual((result['status'],result['vocabulary_roundtrip']),('STAGE_CONTRACTS_VERIFIED','PASS'),result)
        self.assertEqual(result['measurement_tasks'],11)  # ten wash modules and one sand module
        broken=copy.deepcopy(projection);broken['positions'][0]['measurements']['sand'][0]={'sand_height_mm':'95','suspension_height_mm':'122'}
        f['suite_copy']['measurement_reference_sha256']=canonical_hash(broken)
        result=module.stage_contracts(s,broken,allocation,f)
        self.assertEqual((result['status'],result['step'],result['error_type']),('BLOCKED_STAGE_CONTRACTS','measurement_contracts','KeyError'))

    def test_route_probes_cover_every_persona_entry_once(self):
        f=fixture();f['suite_copy']['mapping']={'plan_id':'11111111-1111-4111-8111-111111111111'}
        probes=module.route_probes(suite(),f)
        self.assertEqual({(persona,path) for persona,path,_ in probes},{
            ('laboratory_staff','/samples'),('laboratory_lead','/samples'),('wpk_lead','/beprobung/11111111-1111-4111-8111-111111111111'),
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
                  'resource_policy':suite()['resource_policy'],'budget_approval':{'status':'BASE_LIMITS'},
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


class EntryRouteHandlerTests(unittest.TestCase):
    def test_route_handler_takes_only_the_route_and_binds_its_own_contract(self):
        import inspect
        check=importlib.import_module('projects.ble-elva.tools.receipt_contract_check')
        seen=[];allowed=lambda url,method,config,policy:seen.append((url,method,config,policy)) or url.endswith('/ok')
        handlers=[check.route_handler({'origin':str(i)},'policy',allowed) for i in range(2)]
        self.assertTrue(all(len(inspect.signature(h).parameters)==1 for h in handlers))
        route=MagicMock();route.request.url='http://x/ok';route.request.method='GET'
        handlers[1](route);route.continue_.assert_called_once();route.abort.assert_not_called()
        self.assertEqual(seen[-1][2],{'origin':'1'})
        route=MagicMock();route.request.url='http://x/no';route.request.method='POST'
        handlers[0](route);route.abort.assert_called_once()


def suite_v041():
    return json.loads(Path('projects/ble-elva/suites/enzberg-nsn014-v0.4.1.json').read_text(encoding='utf-8'))


def approval(s,**changes):
    value={'approved_by':'PO','approved_at':'2026-10-15','statement':'PO budget approval reference',
           'profile':s['resource_policy']['profile'],'suite_sha256':canonical_hash(s),
           'hard_seconds':s['resource_policy']['hard_seconds'],'hard_model_calls':s['resource_policy']['hard_model_calls']}
    value.update(changes);return value


class BudgetChangeTests(unittest.TestCase):
    def test_historical_v04_is_immutable_and_v041_changes_only_the_resource_contract(self):
        old,new=suite(),suite_v041()
        self.assertEqual(canonical_hash(old),'fbc65e91611bcb9122d5f26f8ae996f404f6966951adf315ad599af0bbd9084a')
        self.assertEqual((old['version'],new['version'],new['supersedes']),('0.4','0.4.1','0.4'))
        self.assertEqual({k for k in set(old)|set(new) if old.get(k)!=new.get(k)},{'version','supersedes','change_note','resource_policy'})
        self.assertEqual(new['cases'],old['cases'])
        self.assertEqual({k:v for k,v in new['resource_policy'].items() if k not in ('profile','hard_seconds','hard_model_calls')},
                         {k:v for k,v in old['resource_policy'].items() if k not in ('hard_seconds','hard_model_calls')})
        self.assertEqual((new['resource_policy']['hard_seconds'],new['resource_policy']['hard_model_calls'],
                          new['resource_policy']['automatic_retry']),(10800,1500,False))
        self.assertEqual(old['resource_policy']['hard_model_calls'],1000)
        module.validate_suite(old);module.validate_suite(new)

    def test_extended_suite_is_not_ready_without_a_matching_po_approval_record(self):
        s=suite_v041();f=fixture()
        self.assertEqual(module.budget_approval(suite(),f)['status'],'BASE_LIMITS')
        missing=module.budget_approval(s,f)
        self.assertEqual((missing['status'],missing['required']['hard_model_calls']),('BUDGET_APPROVAL_MISSING',1500))
        self.assertEqual(missing['required']['suite_sha256'],canonical_hash(s))
        f['suite_copy']['budget_approval']=approval(s)
        granted=module.budget_approval(s,f)
        self.assertEqual((granted['status'],granted['approved_at']),('BUDGET_APPROVED','2026-10-15'))
        for changes in ({'approved_by':'Claude'},{'approved_by':'po'},{'approved_at':''},{'statement':''},{'hard_model_calls':1000},
                        {'hard_seconds':7200},{'profile':'other'},{'suite_sha256':'0'*64}):
            f['suite_copy']['budget_approval']=approval(s,**changes)
            self.assertEqual(module.budget_approval(s,f)['status'],'BUDGET_APPROVAL_MISSING',changes)
        f['suite_copy']['budget_approval']=approval(s)
        edited=dict(s,resource_policy=dict(s['resource_policy'],hard_model_calls=1400))
        self.assertEqual(module.budget_approval(edited,f)['status'],'BUDGET_APPROVAL_MISSING')
        f['suite_copy']['budget_approval']='approved'
        self.assertEqual(module.budget_approval(s,f)['status'],'BUDGET_APPROVAL_MISSING')

    def test_readiness_reports_only_the_budget_decision_as_open_after_all_other_gates(self):
        s=suite_v041();f=fixture();p=position();ids=s['required_position_ids']
        dataset={'dataset_id':'d'}
        projection={'source_sha256':canonical_hash(dataset),'positions':[dict(p,position_id=k,sample_code='S-'+k) for k in ids]}
        allocation={'source_dataset_id':'d','positions':[{'position_id':k,'allocations':p['allocations']} for k in ids]}
        f['suite_copy'].update(application_root='D:/Temp/sqbf-unit-nonexistent/app',receipt_entrypoint='plan_replenish_once',
            suite_sha256=canonical_hash(s),runtime={'assembly':'a','sha256':'s'},
            measurement_reference_sha256=canonical_hash(projection),allocation_reference_sha256=canonical_hash(allocation),
            mapping={'plan_id':'11111111-1111-4111-8111-111111111111',
                     'positions':{k:'00000000-0000-4000-8000-0000000000%02d'%i for i,k in enumerate(ids)}})
        f['personas']['laboratory_lead']['allowed_permissions']=['sampling.manage','samples.view']
        f['read_only_oracle']={'expected_counts':{'product_test_method_derived_steps':20,'product_test_method_input_specs':11,
            'product_test_method_sampling_steps':9,'product_sample_preparation_steps':5,'product_original_sample_split_requirements':15}}
        clean={'commit':'c'*40,'clean':True,'checked_paths':['sqbf','projects']}
        with patch.object(module,'source_state',return_value=clean),patch.object(module,'check_fixture',return_value={'status':'FIXTURE_GATES_VERIFIED'}), \
             patch.object(module,'snapshot'),patch.object(module,'static_fixture_unchanged',return_value=True), \
             patch.object(module,'verify_runtime',return_value={'assembly':'a','sha256':'s'}), \
             patch.object(module,'verify_receipts',return_value={'status':'RECEIPT_START_VERIFIED'}),patch.object(module,'collect_receipts'), \
             patch.object(module,'collect_inputs',return_value=[]),patch.object(module,'collect_allocations',return_value=[]), \
             patch.object(module,'collect_reports',return_value=[]),patch.object(module.Scenario,'load'), \
             patch.object(module,'check_receipt_form',return_value={'status':'RECEIPT_UI_CONTRACT_VERIFIED'}), \
             patch.object(module,'check_entry_routes',return_value={'status':'ENTRY_ROUTES_VERIFIED'}), \
             patch.object(module,'stage_contracts',return_value={'status':'STAGE_CONTRACTS_VERIFIED'}), \
             patch.object(module,'collect_plan_products'),patch.object(module,'verify_plan_products',
                                                                       return_value={'status':'PLAN_PRODUCTS_CREATABLE'}):
            blocked=module.check_ready(s,dataset,f,projection,allocation)
            self.assertEqual((blocked['status'],blocked['reason'],blocked.get('other_gates')),
                             ('BLOCKED_SUITE_READINESS','BUDGET_APPROVAL_MISSING','PASSED'),blocked)
            self.assertEqual(blocked['request_estimate']['hard_model_calls'],1500);self.assertEqual(blocked['model_calls'],0)
            f['suite_copy']['budget_approval']=approval(s)
            ready=module.check_ready(s,dataset,f,projection,allocation)
            with patch.object(module,'evaluate_probe',return_value={'status':'PROBE_FAILED','ux_layer_assured':False,'codes':{}}):
                probe_failed=module.check_ready(s,dataset,f,projection,allocation,provider_probe='probe.json')
            with patch.object(module,'evaluate_probe',return_value={'status':'PROBE_PASSED','ux_layer_assured':True}):
                probe_passed=module.check_ready(s,dataset,f,projection,allocation,provider_probe='probe.json')
        self.assertEqual((ready['status'],ready['budget_approval']['status']),('READY_FOR_SINGLE_SUITE_RUN','BUDGET_APPROVED'))
        self.assertTrue(ready['request_estimate']['fits_ceiling'])
        self.assertEqual((ready['provider_probe']['status'],ready['provider_probe']['ux_layer_assured']),('NOT_PROBED',False))
        self.assertTrue(any('not probed' in x for x in ready['limitations']))
        self.assertEqual((probe_failed['status'],probe_failed['reason']),('BLOCKED_SUITE_READINESS','PROVIDER_PROBE_NOT_USABLE'))
        self.assertEqual((probe_passed['status'],probe_passed['provider_probe']['status']),('READY_FOR_SINGLE_SUITE_RUN','PROBE_PASSED'))
        self.assertFalse(any('not probed' in x for x in probe_passed['limitations']))


class PlanPreconditionGateTests(unittest.TestCase):
    def test_inactive_plan_product_blocks_readiness_before_the_ui_or_budget_checks(self):
        s=suite();f=fixture();p=position();ids=s['required_position_ids'];dataset={'dataset_id':'d'}
        projection={'source_sha256':canonical_hash(dataset),'positions':[dict(p,position_id=k,sample_code='S-'+k) for k in ids]}
        allocation={'source_dataset_id':'d','positions':[{'position_id':k,'allocations':p['allocations']} for k in ids]}
        f['suite_copy'].update(application_root='D:/Temp/sqbf-unit-nonexistent/app',receipt_entrypoint='plan_replenish_once',
            suite_sha256=canonical_hash(s),runtime={'assembly':'a','sha256':'s'},
            measurement_reference_sha256=canonical_hash(projection),allocation_reference_sha256=canonical_hash(allocation),
            mapping={'plan_id':'11111111-1111-4111-8111-111111111111',
                     'positions':{k:'00000000-0000-4000-8000-0000000000%02d'%i for i,k in enumerate(ids)}})
        f['personas']['laboratory_lead']['allowed_permissions']=['sampling.manage','samples.view']
        f['read_only_oracle']={'expected_counts':{'product_test_method_derived_steps':20,'product_test_method_input_specs':11,
            'product_test_method_sampling_steps':9,'product_sample_preparation_steps':5,'product_original_sample_split_requirements':15}}
        blocked_plan={'status':'PLAN_PRODUCTS_BLOCKED','blocked_positions':[{'position_id':'P06','reasons':['PRODUCT_INACTIVE']}]}
        with patch.object(module,'source_state',return_value={'commit':'c'*40,'clean':True,'checked_paths':[]}), \
             patch.object(module,'check_fixture',return_value={'status':'FIXTURE_GATES_VERIFIED'}), \
             patch.object(module,'snapshot'),patch.object(module,'static_fixture_unchanged',return_value=True), \
             patch.object(module,'verify_runtime',return_value={'assembly':'a','sha256':'s'}), \
             patch.object(module,'verify_receipts',return_value={'status':'RECEIPT_START_VERIFIED'}),patch.object(module,'collect_receipts'), \
             patch.object(module,'collect_inputs',return_value=[]),patch.object(module,'collect_allocations',return_value=[]), \
             patch.object(module,'collect_reports',return_value=[]),patch.object(module,'collect_plan_products'), \
             patch.object(module,'verify_plan_products',return_value=blocked_plan), \
             patch.object(module,'check_receipt_form') as form,patch.object(module,'check_entry_routes') as routes, \
             patch.object(module,'stage_contracts',return_value={'status':'STAGE_CONTRACTS_VERIFIED'}):
            result=module.check_ready(s,dataset,f,projection,allocation)
        self.assertEqual((result['status'],result['reason']),('BLOCKED_SUITE_READINESS','PLAN_PRODUCT_PRECONDITION_FAILED'))
        self.assertEqual(result['plan_products']['blocked_positions'][0]['position_id'],'P06')
        form.assert_not_called();routes.assert_not_called();self.assertEqual(result['model_calls'],0)


class ReviewerIsolationReportTests(unittest.TestCase):
    def test_failed_reviewer_leaves_objective_status_and_is_reported_with_its_code(self):
        records=[{'case_id':'NSN014-PLAN','persona':'laboratory_lead','result':'INVALID','objective_status':'INVALID_HARNESS',
                  'technical_gate':'INVALID','error_code':'INSPECTION_RUNNER_ERROR','review_error':'PROVIDER_HTTP_400'},
                 {'case_id':'NSN014-SE','persona':'laboratory_staff','result':'PASS','objective_status':'PASS','technical_gate':'PASS',
                  'oracle_gate':'PASS','positions':[{'review_error':'REVIEWER_DISABLED_AFTER_FAILURE'}]}]
        matrix=module.case_matrix(records)
        self.assertEqual((matrix[0]['reason'],matrix[0]['review_errors']),('INSPECTION_RUNNER_ERROR',['PROVIDER_HTTP_400']))
        self.assertEqual((matrix[1]['objective_status'],matrix[1]['ux_verdict'],matrix[1]['review_errors']),
                         ('PASS','NOT_EVALUATED',['REVIEWER_DISABLED_AFTER_FAILURE']))
        manifest={'run_id':'r','verdict':'NO-GO','technical_status':'INVALID','functional_status':'INVALID','scenario_id':'S',
                  'scenario_version':'0.4.1','sqbf_commit':'c','software_version':'b','executor_model':'e','analyst_model':'a',
                  'suite_sha256':'s','dataset_sha256':'d','case_matrix':matrix,'ux_summary':module.ux_summary(records),
                  'resource_policy':suite()['resource_policy'],'budget_approval':{'status':'BASE_LIMITS'}}
        text=module.completion_text(manifest,records)
        self.assertIn('NSN014-PLAN: INSPECTION\\_RUNNER\\_ERROR',text);self.assertNotIn('NSN014-PLAN: None',text)
        self.assertIn('UX-Review ausgefallen in NSN014-PLAN: PROVIDER\\_HTTP\\_400',text)

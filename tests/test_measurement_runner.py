import importlib
import unittest
from unittest.mock import MagicMock,patch
from uuid import UUID
from sqbf.calibration import SuiteBudget
from sqbf.suites import canonical_hash
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

    def run_with_states(self,answers,states,*,test_order_done=False,shown=None):
        f=owned_fixture();f['personas']={'laboratory_staff':{'storage_state':'x'}}
        p=position();p.update(sample_code='SYNTHETIC-01',product='Synthetic stone')
        browser=MagicMock();page=browser.new_context.return_value.new_page.return_value
        page.url=f['target_url']+'samples/11111111-1111-4111-8111-111111111111';page.screenshot.return_value=b'png';page.evaluate.return_value=shown
        budget=SuiteBudget(policy());budget.start_task({'case_id':'SE','observation_marks':{'seconds':600,'actions':60}})
        review=ModelResponse({'verdict':'INCONCLUSIVE','scores':dict.fromkeys(('findability','clarity','task_progress','error_recovery'),2)},{})
        with patch.object(module,'ask_calibrated',side_effect=answers+[review]) as ask,patch.object(module,'check_action',side_effect=states) as check, \
             patch.object(module,'offered_fields',return_value=set()),patch.object(module,'apply_action'):
            result=module.run_position(browser,f,p,'11111111-1111-4111-8111-111111111111','sand',{},object(),object(),budget,MagicMock(),test_order_done=test_order_done)
        return result,ask,check

    def test_a_rejected_click_is_reported_to_the_executor_and_the_task_continues(self):
        # Live run 413f7abe: the first rejection ended eleven of twelve tasks; now the executor can follow another path.
        from sqbf.read_only import ReadOnlyViolation
        click=ModelResponse({'action':'click','x':10,'y':10,'reason':'test order'},{})
        order=ModelResponse({'action':'click','x':20,'y':20,'reason':'order'},{})
        done=ModelResponse({'action':'blocked','reason':'no field'},{})
        result,ask,_=self.run_with_states([click,order,done],[ReadOnlyViolation('MEASUREMENT_ACTION_SCOPE_DENIED'),{'target':{'kind':'setup','scope':'test_order'},'focused':None},{}])
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual([r['error_code'] for r in result['rejected_actions']],['MEASUREMENT_ACTION_SCOPE_DENIED'])
        self.assertTrue(result['test_order_created']);self.assertIn('test_order',result['save_scopes_attempted'])
        prompt=ask.call_args_list[1].args[1]
        self.assertIn('rejected_by_controller',prompt);self.assertIn('MEASUREMENT_ACTION_SCOPE_DENIED',prompt);self.assertIn('Testauftrag erzeugen',module.INSTRUCTIONS)
        # The same screenshot with different coordinates is not a stall, and the rejected click never counts as a visible action.
        self.assertNotIn('"reason": "test order"',prompt.split('Previous visible actions:')[1].split('rejected_by_controller')[0])

    def test_a_pre_filled_field_that_does_not_show_exactly_the_approved_number_is_not_entered_and_can_never_make_a_fail(self):
        # Guarded dry run 16.10.2026: typing 250 into a field that already held 250 persisted 250250; the controller had counted the field as
        # entered because the guard had admitted the text, and would have reported a persisted-value FAIL of BLE.
        click=ModelResponse({'action':'click','x':10,'y':10,'reason':'focus'},{})
        typed=ModelResponse({'action':'type','text':'95','reason':'enter'},{})
        done=ModelResponse({'action':'done','reason':'finished'},{})
        state={'target':{'kind':'field'},'focused':'Sandhöhe:A'}
        result,_,_=self.run_with_states([click,typed,done],[state,state,{}],shown='9595')
        self.assertEqual(result['fields_entered'],0);self.assertEqual(result['fields_not_matching_after_typing'],['Sandhöhe:A']);self.assertFalse(result['fully_entered'])
        result,_,_=self.run_with_states([click,typed,done],[state,state,{}],shown=' 95 ')
        self.assertEqual((result['fields_entered'],result['fields_not_matching_after_typing']),(1,[]))
        result,_,_=self.run_with_states([click,typed,done],[state,state,{}],shown=None)   # unreadable: not counted as entered
        self.assertEqual(result['fields_entered'],0)
        self.assertEqual(module.classify_position([dict(result,fully_entered=False,status='DONE')],True)[0],'INCOMPLETE')
        self.assertIn('select its content first',module.INSTRUCTIONS)

    def test_more_than_the_allowed_rejections_end_only_that_task(self):
        from sqbf.read_only import ReadOnlyViolation
        answers=[ModelResponse({'action':'click','x':10*(i+1),'y':10,'reason':'r'},{}) for i in range(4)]
        result,ask,_=self.run_with_states(answers,[ReadOnlyViolation('MEASUREMENT_ACTION_SCOPE_DENIED')]*4)
        self.assertEqual((result['status'],result['rejected_action_code'],len(result['rejected_actions'])),('REJECTED','MEASUREMENT_ACTION_SCOPE_DENIED',4))
        self.assertEqual(result['technical_gate'],'PASS');self.assertEqual(ask.call_count,5)  # four actions and the review

    def test_a_critical_rejection_still_stops_at_once(self):
        from sqbf.read_only import ReadOnlyViolation
        click=ModelResponse({'action':'click','x':10,'y':10,'reason':'r'},{})
        result,ask,_=self.run_with_states([click],[ReadOnlyViolation('SESSION_INVALIDATED')])
        self.assertEqual((result['status'],result['technical_gate'],result['error_code']),('BLOCKED','BLOCKED','SESSION_INVALIDATED'));self.assertEqual(ask.call_count,1)

    def test_the_test_order_is_created_once_per_sample_across_modules(self):
        calls=[]
        def run_position(browser,fixture,position,probe,kind,*args,**kwargs):
            calls.append((position['position_id'],kind,kwargs.get('test_order_done')))
            return {'position_id':position['position_id'],'kind':kind,'status':'DONE','technical_gate':'PASS','fully_entered':True,'test_order_created':not kwargs.get('test_order_done')}
        f=owned_fixture();f['suite_copy']['mapping']={'positions':{}};projection={'positions':[]};receipts={'samples':[],'lims':[],'plan_items':[]}
        key='P1';product=str(UUID(int=101));f['suite_copy']['mapping']['positions'][key]=product
        m={k:[] for k in ('wash','shape','boiling','boiling_repetitions','sand','sieves','preparation','partial_series')}
        m['wash']=position()['measurements']['wash'];m['sieves']=position()['measurements']['sieves']
        projection['positions'].append({'position_id':key,'sample_code':'S1','product':'Stone','measurements':m})
        receipts['samples'].append({'id':str(UUID(int=501)),'sample_code':'S1','product_id':product})
        f['suite_copy']['measurement_reference_sha256']=canonical_hash(projection)
        oracle={'status':'PASS','checks':1,'mismatches':[]}
        with patch.object(module,'collect_receipts',return_value=receipts),patch.object(module,'snapshot',return_value={'tables':{}}), \
             patch.object(module,'run_position',side_effect=run_position),patch.object(module,'collect_inputs'),patch.object(module,'verify_inputs',return_value=oracle):
            module.run_measurements(object(),f,projection,['wash','sieve'],{},None,None,None,None)
        self.assertEqual(calls,[('P1','wash',False),('P1','sieve',True)])

    def run_gate(self,after_receipts,after_tables=None):
        def run_position(browser,fixture,position,probe,kind,*args,**kwargs):
            return {'position_id':position['position_id'],'kind':kind,'status':'DONE','technical_gate':'PASS','fully_entered':True}
        f=owned_fixture();f['suite_copy']['mapping']={'positions':{}};key='P1';product=str(UUID(int=101));f['suite_copy']['mapping']['positions'][key]=product
        m={k:[] for k in ('wash','shape','boiling','boiling_repetitions','sand','sieves','preparation','partial_series')};m['wash']=position()['measurements']['wash']
        projection={'positions':[{'position_id':key,'sample_code':'S1','product':'Stone','measurements':m}]}
        f['suite_copy']['measurement_reference_sha256']=canonical_hash(projection)
        start={'samples':[{'id':str(UUID(int=501)),'sample_code':'S1','product_id':product}],'lims':[],'plan_items':[{'id':'i1'}]}
        before={'tables':{'workspace_products':{'count':1,'hash':'a'},'samples':{'count':1,'hash':'s'}}}
        after={'tables':dict(before['tables'],**(after_tables or {}))}
        with patch.object(module,'collect_receipts',side_effect=[start,after_receipts]),patch.object(module,'snapshot',side_effect=[before,after]),              patch.object(module,'run_position',side_effect=run_position),patch.object(module,'collect_inputs'),patch.object(module,'verify_inputs',return_value={'status':'PASS','checks':1,'mismatches':[]}):
            return module.run_measurements(object(),f,projection,['wash'],{},None,None,None,None)

    def test_a_lazy_lims_sample_is_not_an_unrelated_write_but_changed_sample_identities_or_protected_tables_are(self):
        # First guarded dry run (16.10.2026): starting the partial sieve creates the LIMS sample, which made SIEVE INVALID_HARNESS.
        start={'samples':[{'id':str(UUID(int=501)),'sample_code':'S1','product_id':str(UUID(int=101))}],'lims':[],'plan_items':[{'id':'i1'}]}
        with_lims=dict(start,lims=[{'id':'l1','probe_id':str(UUID(int=501))}])
        self.assertEqual(self.run_gate(with_lims)['result'],'PASS')
        for changed in (dict(start,samples=[]),dict(start,plan_items=[])):
            self.assertEqual(self.run_gate(changed)['result'],'INVALID')
        self.assertEqual(self.run_gate(with_lims,{'workspace_products':{'count':2,'hash':'b'}})['reason'],'UNRELATED_MEASUREMENT_WRITE')
        # Mutable benchmark tables may change.
        self.assertEqual(self.run_gate(start,{'samples':{'count':1,'hash':'changed'}})['result'],'PASS')

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

    # ---- provider / response faults (live run 083896e6, 16.10.2026) -----------------------------------------------------------------------
    # One failed executor request (usage {} in the accounting) ended in the generic handler and made the whole PREPARATION stage and the
    # suite INVALID_HARNESS. A provider or response fault is a measurement gap of one position; only a systematic one stops the suite.
    def run_failing(self,answers,*,failures=0):
        f=owned_fixture();f['personas']={'laboratory_staff':{'storage_state':'x'}}
        p=position();p.update(sample_code='SYNTHETIC-01',product='Synthetic stone')
        browser=MagicMock();page=browser.new_context.return_value.new_page.return_value
        page.url=f['target_url']+'samples/11111111-1111-4111-8111-111111111111';page.screenshot.return_value=b'png';page.evaluate.return_value=None
        budget=SuiteBudget(policy());budget.start_task({'case_id':'SE','observation_marks':{'seconds':600,'actions':60}});budget.executor_failures=failures
        evidence=MagicMock()
        with patch.object(module,'ask_calibrated',side_effect=answers) as ask,patch.object(module,'check_action',return_value={'target':{'kind':'field'},'focused':None}), \
             patch.object(module,'offered_fields',return_value=set()),patch.object(module,'apply_action'):
            result=module.run_position(browser,f,p,'11111111-1111-4111-8111-111111111111','sand',{},object(),object(),budget,evidence)
        return result,ask,budget,evidence

    def test_a_failed_executor_request_ends_only_that_position_and_is_never_a_harness_defect(self):
        from sqbf.bounded import WorkerFailed
        result,ask,budget,evidence=self.run_failing([WorkerFailed('PROVIDER_ERROR')])
        self.assertEqual((result['status'],result['technical_gate'],result['executor_error_code']),('EXECUTOR_FAILED','PASS','PROVIDER_ERROR'))
        self.assertNotIn('stop_reason',result);self.assertEqual(budget.executor_failures,1);self.assertEqual(ask.call_count,1)  # no retry, no review
        event=[c for c in evidence.event.call_args_list if c.args[0]=='executor_call_failed'][0]
        self.assertEqual(event.kwargs['error_code'],'PROVIDER_ERROR');self.assertEqual(event.kwargs['exception_type'],'WorkerFailed')
        self.assertEqual(module.classify_position([result],False),('INCOMPLETE','EXECUTOR_REQUEST_FAILED'))
        # Without a code from the worker the failure still gets a fixed identifier; a worker timeout has its own.
        self.assertEqual(self.run_failing([WorkerFailed(None)])[0]['executor_error_code'],'EXECUTOR_CALL_FAILED')
        from sqbf.bounded import BudgetExceeded
        self.assertEqual(self.run_failing([BudgetExceeded('deadline')])[0]['executor_error_code'],'EXECUTOR_REQUEST_TIMEOUT')

    def test_a_response_that_is_not_an_action_object_is_a_failed_request_not_a_crash(self):
        for data in (None,['click'],'click',3):
            result,_,budget,evidence=self.run_failing([ModelResponse(data,{})])
            self.assertEqual((result['status'],result['technical_gate'],result['executor_error_code']),('EXECUTOR_FAILED','PASS','EXECUTOR_RESPONSE_NOT_AN_OBJECT'),data)
        # An empty or unusable usage block alone is fine: the action is still taken.
        result,_,budget,_=self.run_failing([ModelResponse({'action':'blocked','reason':'no field'},{}),
                                            ModelResponse({'verdict':'INCONCLUSIVE','scores':dict.fromkeys(('findability','clarity','task_progress','error_recovery'),2)},{})])
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(budget.executor_failures,0)

    def test_repeated_executor_failures_stop_the_suite_as_incomplete_measurement_and_a_success_resets_the_count(self):
        from sqbf.bounded import WorkerFailed
        result,_,budget,_=self.run_failing([WorkerFailed('PROVIDER_ERROR')],failures=2)
        self.assertEqual((result['status'],result['technical_gate'],result['stop_reason']),('INCONCLUSIVE','PASS','EXECUTOR_UNAVAILABLE_AFTER_REPEATED_FAILURES'))
        self.assertEqual(budget.stop_reason,'EXECUTOR_UNAVAILABLE_AFTER_REPEATED_FAILURES')
        result,_,budget,_=self.run_failing([ModelResponse({'action':'blocked','reason':'x'},{}),
                                            ModelResponse({'verdict':'INCONCLUSIVE','scores':dict.fromkeys(('findability','clarity','task_progress','error_recovery'),2)},{})],failures=2)
        self.assertEqual(budget.executor_failures,0);self.assertIsNone(budget.stop_reason)

    def test_the_harness_failure_names_the_exception_class_and_nothing_else(self):
        class Strange(RuntimeError):pass
        f=owned_fixture();f['personas']={'laboratory_staff':{'storage_state':'x'}};p=position();p.update(sample_code='SYNTHETIC-01',product='Synthetic stone')
        browser=MagicMock();page=browser.new_context.return_value.new_page.return_value
        page.url=f['target_url']+'samples/11111111-1111-4111-8111-111111111111';page.screenshot.side_effect=Strange('secret page text 12,5')
        budget=SuiteBudget(policy());budget.start_task({'case_id':'SE','observation_marks':{'seconds':600,'actions':60}});evidence=MagicMock()
        result=module.run_position(browser,f,p,'11111111-1111-4111-8111-111111111111','sand',{},object(),object(),budget,evidence)
        self.assertEqual((result['status'],result['technical_gate'],result['error_code'],result['exception_type']),('INVALID','INVALID','MEASUREMENT_RUNNER_ERROR','Strange'))
        event=[c for c in evidence.event.call_args_list if c.args[0]=='measurement_harness_failure'][0]
        self.assertEqual(event.kwargs['exception_type'],'Strange');self.assertNotIn('secret',repr(event))

    def test_a_position_with_a_failed_executor_request_does_not_stop_the_other_positions(self):
        order=[]
        def run_position(browser,fixture,position,probe,kind,*args,**kwargs):
            order.append(position['position_id'])
            if position['position_id']=='P1':
                return {'position_id':'P1','kind':kind,'status':'EXECUTOR_FAILED','technical_gate':'PASS','fully_entered':False,'executor_error_code':'PROVIDER_ERROR'}
            return {'position_id':position['position_id'],'kind':kind,'status':'DONE','technical_gate':'PASS','fully_entered':True}
        f=owned_fixture();f['suite_copy']['mapping']={'positions':{}};products={'P1':str(UUID(int=101)),'P2':str(UUID(int=102))}
        f['suite_copy']['mapping']['positions'].update(products)
        m={k:[] for k in ('wash','shape','boiling','boiling_repetitions','sand','sieves','preparation','partial_series')};m['wash']=position()['measurements']['wash']
        projection={'positions':[{'position_id':k,'sample_code':'S'+k,'product':'Stone','measurements':m} for k in products]}
        f['suite_copy']['measurement_reference_sha256']=canonical_hash(projection)
        receipts={'samples':[{'id':str(UUID(int=500+i)),'sample_code':'S'+k,'product_id':v} for i,(k,v) in enumerate(products.items())],'lims':[],'plan_items':[{'id':'i1'}]}
        tables={'tables':{'samples':{'count':2,'hash':'s'}}}
        with patch.object(module,'collect_receipts',return_value=receipts),patch.object(module,'snapshot',return_value=tables), \
             patch.object(module,'run_position',side_effect=run_position),patch.object(module,'collect_inputs'),patch.object(module,'verify_inputs',return_value={'status':'PASS','checks':1,'mismatches':[]}):
            result=module.run_measurements(object(),f,projection,['wash'],{},None,None,None,None)
        self.assertEqual(order,['P1','P2']);self.assertEqual(result['technical_gate'],'PASS');self.assertEqual(result['result'],'INCONCLUSIVE')
        self.assertEqual([(p['position_id'],p['result'],p['class']) for p in result['position_results']],[('P1','INCOMPLETE','EXECUTOR_REQUEST_FAILED'),('P2','PASS',None)])

    # ---- derived values (guarded dry run with replayed provider faults, 16.10.2026) -------------------------------------------------------
    # The partial sieve stores a preparation mass that BLE derives from the allocation of the pan material. Without that allocation it stores 0,
    # and SIEVE reported "persisted value deviation" (FAIL) for a position whose PREPARATION had failed on the provider, not on BLE.
    def run_partial(self,*,mismatches,gaps,own_kinds=('partial',),fully_entered=True):
        def run_position(browser,fixture,position,probe,kind,*args,**kwargs):
            return {'position_id':position['position_id'],'kind':kind,'status':'DONE','technical_gate':'PASS','fully_entered':fully_entered,'offered_entered':True,'fields_not_offered':[]}
        f=owned_fixture();f['suite_copy']['mapping']={'positions':{}};key='P1';product=str(UUID(int=101));f['suite_copy']['mapping']['positions'][key]=product
        m={k:[] for k in ('wash','shape','boiling','boiling_repetitions','sand','sieves','preparation','partial_series')};m['partial_series']=[{'x':1}]
        projection={'positions':[{'position_id':key,'sample_code':'S1','product':'Stone','measurements':m}]}
        f['suite_copy']['measurement_reference_sha256']=canonical_hash(projection)
        receipts={'samples':[{'id':str(UUID(int=501)),'sample_code':'S1','product_id':product}],'lims':[],'plan_items':[{'id':'i1'}]}
        tables={'tables':{'samples':{'count':1,'hash':'s'}}}
        with patch.object(module,'collect_receipts',return_value=receipts),patch.object(module,'snapshot',return_value=tables), \
             patch.object(module,'run_position',side_effect=run_position),patch.object(module,'collect_inputs'), \
             patch.object(module,'verify_inputs',return_value={'status':'FAIL' if mismatches else 'PASS','checks':1,'mismatches':[{'position_id':'P1','kind':k} for k in mismatches]}), \
             patch.object(module,'derived_value_gaps',return_value=set(gaps)) as derived:
            result=module.run_measurements(object(),f,projection,list(own_kinds),{},None,None,None,None)
        return result,derived

    def test_a_derived_value_deviation_is_incomplete_when_its_inputs_were_not_persisted_as_approved(self):
        result,derived=self.run_partial(mismatches=['preparation'],gaps=['P1'])
        self.assertEqual(result['position_results'],[{'position_id':'P1','result':'INCOMPLETE','class':'DERIVED_VALUE_UPSTREAM_INCOMPLETE'}])
        self.assertEqual((result['result'],result['derived_value_gaps']),('INCONCLUSIVE',['P1']));derived.assert_called_once()
        self.assertEqual(self.run_partial(mismatches=['partial_series'],gaps=['P1'])[0]['position_results'][0]['class'],'DERIVED_VALUE_UPSTREAM_INCOMPLETE')

    def test_a_derived_value_deviation_with_all_inputs_persisted_is_still_a_persisted_value_fail(self):
        result,_=self.run_partial(mismatches=['preparation'],gaps=[])
        self.assertEqual(result['position_results'],[{'position_id':'P1','result':'FAIL','class':'PERSISTED_VALUE_DEVIATION'}])
        self.assertEqual(result['result'],'FAIL')

    def test_a_deviation_of_an_own_input_is_not_excused_by_an_upstream_gap_and_no_gap_is_computed_without_a_derived_deviation(self):
        result,derived=self.run_partial(mismatches=['preparation','sieves'],gaps=['P1'])
        self.assertEqual(result['position_results'][0]['result'],'FAIL')
        result,derived=self.run_partial(mismatches=[],gaps=['P1']);derived.assert_not_called()
        self.assertEqual((result['result'],result['derived_value_gaps']),('PASS',[]))

    def test_classification_of_a_derived_gap(self):
        done=dict(status='DONE',fully_entered=True,offered_entered=True,fields_not_offered=[])
        self.assertEqual(module.classify_position([done],False,True),('INCOMPLETE','DERIVED_VALUE_UPSTREAM_INCOMPLETE'))
        self.assertEqual(module.classify_position([done],False,False),('PASS',None))
        self.assertEqual(module.classify_position([done],True,True),('FAIL','PERSISTED_VALUE_DEVIATION'))
        # An unfinished position keeps its own reason.
        self.assertEqual(module.classify_position([dict(done,status='EXECUTOR_FAILED')],False,True),('INCOMPLETE','EXECUTOR_REQUEST_FAILED'))

    def test_derived_value_gaps_combine_wash_mismatches_and_missing_pan_allocations_and_assume_a_gap_without_evidence(self):
        f=owned_fixture();projection={'positions':[{'position_id':'P1'},{'position_id':'P2'},{'position_id':'P3'}]}
        reference={'positions':[]};f['suite_copy']['allocation_reference_sha256']=canonical_hash(reference)
        wash={'status':'FAIL','mismatches':[{'position_id':'P2','kind':'wash'}]}
        with patch.object(module,'verify_inputs',return_value=wash),patch.object(module,'collect_allocations',return_value=[]), \
             patch.object(module,'prerequisite_gaps',return_value={'P3'}) as gaps:
            self.assertEqual(module.derived_value_gaps(f,projection,reference,[]),{'P2','P3'})
            self.assertEqual(gaps.call_args.args[3],'Siebanalyse')
            # Unusable evidence is never read as "inputs present".
            everything={'P1','P2','P3'}
            self.assertEqual(module.derived_value_gaps(f,projection,None,[]),everything)
            self.assertEqual(module.derived_value_gaps(f,projection,{'positions':['changed']},[]),everything)
        with patch.object(module,'verify_inputs',return_value={'status':'BLOCKED_MEASUREMENT_EVIDENCE'}):
            self.assertEqual(module.derived_value_gaps(f,projection,reference,[]),everything)

    # ---- uncommitted last field (live run 6c23f768) ---------------------------------------------------------------------------------------
    def test_a_value_typed_into_a_field_that_is_still_focused_at_the_end_is_not_a_persisted_deviation(self):
        click=ModelResponse({'action':'click','x':10,'y':10,'reason':'focus'},{})
        typed=ModelResponse({'action':'type','text':'95','reason':'enter'},{})
        done=ModelResponse({'action':'done','reason':'finished'},{})
        state={'target':{'kind':'field'},'focused':'Sandhöhe:A'}
        with patch.object(module,'focused_field',return_value='Sandhöhe:A'):
            result,_,_=self.run_with_states([click,typed,done],[state,state,{}],shown='95')
        self.assertEqual((result['field_focused_at_end'],result['fields_entered'],result['fully_entered']),('Sandhöhe:A',1,False))
        self.assertEqual(module.classify_position([result],True),('INCOMPLETE','LAST_FIELD_NOT_COMMITTED'))
        with patch.object(module,'focused_field',return_value=None):
            result,_,_=self.run_with_states([click,typed,done],[state,state,{}],shown='95')
        self.assertIsNone(result['field_focused_at_end']);self.assertEqual(result['fields_entered'],1)
        # With every field entered and left, the same persisted mismatch is attributable to BLE.
        self.assertEqual(module.classify_position([dict(result,status='DONE',fully_entered=True)],True),('FAIL','PERSISTED_VALUE_DEVIATION'))
        # A failed executor request right after typing is the same case.
        from sqbf.bounded import WorkerFailed
        with patch.object(module,'focused_field',return_value='Sandhöhe:A'):
            result,_,_,_=(lambda r:(r[0],r[1],r[2],r[3]))(self.run_failing([WorkerFailed('RESPONSE_NOT_JSON')]))
        self.assertEqual(result['status'],'EXECUTOR_FAILED');self.assertFalse(result['fully_entered'])

    def test_the_instructions_give_the_neutral_hint_and_never_the_position_of_a_control_or_a_click_path(self):
        # PO decision 2026-10-19: findability stays a measurement. The hint says controls may lie outside the visible part and that the usual
        # navigation helps; it never names the save control, its position, the module cards or the button that opens a module.
        text=module.INSTRUCTIONS
        self.assertIn('Controls may not be within the currently visible part of the page',text)
        self.assertIn('usual navigation options of the interface',text);self.assertIn('leave the field',text)
        for forbidden in ('Speichern','Erfassen','further down','card','top of','header','scroll to','upper right','Zu den Modulen'):
            self.assertNotIn(forbidden,text,forbidden)
        self.assertIn('Testauftrag erzeugen',text)  # the one permitted setup action must still be named

    def test_the_task_names_the_module_and_the_fields_in_bles_words(self):
        # Live run fdea63ef: "no wash module", "no allocations module" - the task used internal names, a suite defect.
        result,ask=self.run_boiling(set())
        prompt=ask.call_args_list[0].args[1]
        self.assertIn('"module": "Kochversuch"',prompt);self.assertIn('Einwaage vor Kochen, Wiederholung 1',prompt)
        for internal in ('"module": "boiling"','Einwaage vor Kochen:1','source_inputs": {"Einwaage vor Kochen:'):
            self.assertNotIn(internal,prompt)

    def test_effort_and_save_status_are_recorded_for_every_position(self):
        click=ModelResponse({'action':'click','x':10,'y':10,'reason':'focus'},{})
        typed=ModelResponse({'action':'type','text':'95','reason':'enter'},{})
        scroll=ModelResponse({'action':'scroll','x':1200,'y':400,'amount':300,'reason':'search'},{})
        done=ModelResponse({'action':'blocked','reason':'no save control'},{})
        state={'target':{'kind':'field'},'focused':'Sandhöhe:A'}
        with patch.object(module,'focused_field',return_value=None):
            result,_,_=self.run_with_states([click,typed,scroll,scroll,done],[state,state,{},{},{}],shown='95')
        self.assertEqual(result['effort'],{'actions':4,'scrolls':2,'clicks':1,'typed':1,'keys':0,'waits':0,'rejected':0,'scrolls_after_last_entry':2})
        self.assertEqual(result['save_status'],'NOT_SAVED_PARTIAL_ENTRY')  # one of the several sand fields only
        self.assertFalse(result['module_reached'])  # the stand-in page stays on the sample page, never on the module route

    def test_save_status_tells_saved_from_not_found_from_prevented(self):
        c={'kind':'wash','fields':{'a':'1','b':'2'}}
        entered=lambda n,total=2:{'fields_entered':n,'fields_required':total}
        self.assertEqual(module.save_status({'kind':'allocations','fields':{}},entered(1),set(),[]),'NOT_REQUIRED')
        self.assertEqual(module.save_status(c,entered(2),{'module'},[]),'SAVED')
        self.assertEqual(module.save_status(c,entered(2),set(),[]),'NOT_SAVED_AFTER_ENTRY')
        self.assertEqual(module.save_status(c,entered(1),set(),[]),'NOT_SAVED_PARTIAL_ENTRY')
        self.assertEqual(module.save_status(c,entered(0),set(),[]),'NOT_REACHED')
        self.assertEqual(module.save_status(c,entered(2),set(),[{'error_code':'X','action':'click','target':{'label':'Speichern'}}]),'SAVE_CLICK_REJECTED')
        shape={'kind':'shape','fields':{'Einwaage gesamt (g):5.6':'1'}}
        self.assertEqual(module.save_status(shape,entered(1,1),{'5.6'},[]),'SAVED')

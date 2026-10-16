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

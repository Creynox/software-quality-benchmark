import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,patch
from uuid import UUID
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from sqbf.calibration import SuiteBudget
from sqbf.providers import ModelResponse
from sqbf.read_only import ReadOnlyViolation
from sqbf.suites import canonical_hash
from test_calibration import policy
from test_measurement_guard import position
from test_suite_fixture import owned_fixture

inspection=importlib.import_module('projects.ble-elva.tools.inspection_runner')
measurement=importlib.import_module('projects.ble-elva.tools.measurement_runner')
DIMENSIONS=('findability','clarity','task_progress','error_recovery')
PLAN='11111111-1111-4111-8111-111111111111'
REPORT='22222222-2222-4222-8222-222222222222'


def review(verdict='PASS'):
    return ModelResponse({'verdict':verdict,'reason':'r','scores':dict.fromkeys(DIMENSIONS,3),'findings':[]},{})


def act(action,**extra):
    return ModelResponse(dict({'action':action},**extra),{})


def fixture():
    f=owned_fixture()
    f['personas']={k:{'storage_state':'private-'+k,'allowed_permissions':['samples.view','reports.view']}
                   for k in ('laboratory_lead','laboratory_staff','wpk_lead','plant_lead')}
    f['identity_verifier']='verifier';f['suite_copy']['mapping']={'plan_id':PLAN,'positions':{}}
    return f


def budget():
    value=SuiteBudget(policy());value.start_task({'case_id':'T','observation_marks':{'seconds':600,'actions':60}})
    return value


def browser(path):
    value=MagicMock();page=value.new_context.return_value.new_page.return_value
    page.url='http://127.0.0.1:5082'+path;page.screenshot.return_value=b'png'
    return value,page


class ViewControllerTests(unittest.TestCase):
    def view(self,answers,states,*,path='/samples',report_position=None,folder=None):
        b,page=browser(path);evidence=MagicMock();evidence.path=Path(folder or '.')
        with patch.object(inspection,'ask_calibrated',side_effect=answers) as ask, \
             patch.object(inspection,'check_action',side_effect=states),patch.object(inspection,'apply_action'):
            outcome=inspection.run_view(b,fixture(),'laboratory_lead',path,[path],'task',{},object(),object(),budget(),evidence,
                                        report_position=report_position)
        return outcome,ask,page,evidence

    def test_prevented_agent_action_ends_only_the_task_and_is_still_reviewed(self):
        outcome,ask,_,evidence=self.view([act('click',x=10,y=10),review()],[ReadOnlyViolation('BLOCKED_INSPECTION_TARGET')])
        self.assertEqual((outcome['status'],outcome['technical_gate']),('REJECTED','PASS'))
        self.assertEqual(outcome['rejected_action_code'],'BLOCKED_INSPECTION_TARGET');self.assertEqual(ask.call_count,2)
        self.assertIn('AGENT_ACTION_REJECTED',ask.call_args_list[-1].args[1])
        self.assertEqual(evidence.event.call_args_list[0].kwargs['action'],'click')

    def test_invalidated_session_is_a_critical_technical_stop(self):
        b,page=browser('/samples');page.url='http://127.0.0.1:5082/login'
        with patch.object(inspection,'ask_calibrated') as ask:
            outcome=inspection.run_view(b,fixture(),'laboratory_lead','/samples',['/samples'],'task',{},object(),object(),budget(),MagicMock())
        ask.assert_not_called()
        self.assertEqual((outcome['status'],outcome['technical_gate'],outcome['error_code']),('BLOCKED','BLOCKED','SESSION_INVALIDATED'))

    def test_unchanged_screen_with_repeated_action_stops_without_more_requests(self):
        answers=[act('click',x=10,y=10)]*3+[review()]
        outcome,ask,_,_=self.view(answers,[{'kind':'read_control'}]*3)
        self.assertEqual(outcome['status'],'STALLED');self.assertEqual(ask.call_count,4)
        self.assertEqual((outcome['screenshots'],outcome['visible_actions']),(4,3))

    def test_missing_download_is_product_evidence_and_the_task_continues(self):
        answers=[act('click',x=10,y=10),act('done',reason='downloaded'),review()]
        b,page=browser('/reports/'+REPORT);manager=MagicMock();manager.__exit__.side_effect=PlaywrightTimeoutError('timeout')
        page.expect_download.return_value=manager;evidence=MagicMock();evidence.path=Path('.')
        with patch.object(inspection,'ask_calibrated',side_effect=answers), \
             patch.object(inspection,'check_action',side_effect=[{'kind':'download','scope':'/reports/'+REPORT},{'kind':'blocked'}]), \
             patch.object(inspection,'apply_action'),patch.object(inspection,'invoke_worker') as worker:
            outcome=inspection.run_view(b,fixture(),'laboratory_lead','/reports/'+REPORT,['/reports/'+REPORT],'task',{},
                                        object(),object(),budget(),evidence,report_position={'sample_code':'S','product':'P'})
        worker.assert_not_called();self.assertEqual(outcome['status'],'DONE');self.assertEqual(outcome['technical_gate'],'PASS')
        self.assertEqual(outcome['download_failures'],[{'report_id':REPORT,'reason':'PDF_DOWNLOAD_NOT_RECEIVED'}])

    def test_unreadable_pdf_is_recorded_as_invalid_artifact_not_harness_failure(self):
        answers=[act('click',x=10,y=10),act('done',reason='downloaded'),review()]
        with tempfile.TemporaryDirectory() as folder:
            b,page=browser('/reports/'+REPORT);evidence=MagicMock();evidence.path=Path(folder)
            invalid={'pdf_integrity':'INVALID_ARTIFACT','artifact_error':'NOT_A_PDF','pages':0,'images':[],'sha256':'a'*64}
            with patch.object(inspection,'ask_calibrated',side_effect=answers) as ask, \
                 patch.object(inspection,'check_action',side_effect=[{'kind':'download','scope':'/reports/'+REPORT},{'kind':'blocked'}]), \
                 patch.object(inspection,'apply_action'),patch.object(inspection,'invoke_worker',return_value=invalid):
                outcome=inspection.run_view(b,fixture(),'laboratory_lead','/reports/'+REPORT,['/reports/'+REPORT],'task',{},
                                            object(),object(),budget(),evidence,report_position={'sample_code':'S','product':'P'})
        self.assertEqual((outcome['status'],outcome['technical_gate']),('DONE','PASS'))
        self.assertEqual(outcome['downloads'][0]['pdf_integrity'],'INVALID_ARTIFACT');self.assertEqual(ask.call_count,3)
        self.assertNotIn('pdf_reviews',outcome)
        self.assertIn('pdf_artifact_invalid',[c.args[0] for c in evidence.event.call_args_list])

    def test_only_a_click_activates_a_capability_or_download(self):
        generate={'kind':'generate','scope':'/samples'}
        answers=[act('scroll',x=10,y=10,amount=200),act('wait',x=10,y=10),act('done',x=10,y=10,reason='seen'),review()]
        outcome,_,page,_=self.view(answers,[generate,generate,{'kind':'download','scope':'/reports/'+REPORT}],
                                   report_position={'sample_code':'S','product':'P'})
        self.assertEqual((outcome['status'],outcome['capability_actions']),('DONE',[]))
        page.expect_download.assert_not_called()
        answers=[act('click',x=10,y=10),act('done',reason='generated'),review()]
        outcome,_,_,_=self.view(answers,[generate,{'kind':'blocked'}],report_position={'sample_code':'S','product':'P'})
        self.assertEqual(outcome['capability_actions'],[generate])

    def test_second_download_of_the_same_report_is_prevented(self):
        answers=[act('click',x=10,y=10),act('click',x=10,y=10),review()]
        with tempfile.TemporaryDirectory() as folder:
            b,page=browser('/reports/'+REPORT);evidence=MagicMock();evidence.path=Path(folder)
            valid={'pdf_integrity':'PASS','artifact_error':None,'pages':1,'images':[],'sha256':'a'*64}
            with patch.object(inspection,'ask_calibrated',side_effect=answers), \
                 patch.object(inspection,'check_action',return_value={'kind':'download','scope':'/reports/'+REPORT}), \
                 patch.object(inspection,'apply_action'),patch.object(inspection,'invoke_worker',return_value=valid):
                outcome=inspection.run_view(b,fixture(),'laboratory_lead','/reports/'+REPORT,['/reports/'+REPORT],'task',{},
                                            object(),object(),budget(),evidence,report_position={'sample_code':'S','product':'P'})
        self.assertEqual((outcome['status'],outcome['rejected_action_code']),('REJECTED','DUPLICATE_PDF_DOWNLOAD'))
        self.assertEqual(len(outcome['downloads']),1)


def outcome(status='DONE',**extra):
    value={'status':status,'technical_gate':'PASS','review':review().data,'downloads':[],'download_failures':[],
           'capability_actions':[],'screenshots':3,'visible_actions':2}
    value.update(extra);return value


class InspectionResultTests(unittest.TestCase):
    def inspect(self,result,case='NSN014-WPK',snapshots=({'tables':{}},{'tables':{}}),f=None):
        f=f or fixture()
        with patch.object(inspection,'check_persona',return_value={'status':'PERSONA_SCOPE_VERIFIED'}), \
             patch.object(inspection,'snapshot',side_effect=list(snapshots)), \
             patch.object(inspection,'collect_receipts',return_value={'samples':[]}), \
             patch.object(inspection,'run_view',return_value=result) as view:
            value=inspection.run_inspection(object(),f,{},{'case_id':case,'persona':'wpk_lead','task':'t'},{},object(),object(),None,None)
        return value,view

    def test_reviewer_never_overrides_the_objective_inspection_result(self):
        failed=outcome(review=review('FAIL').data)
        value,view=self.inspect(failed)
        self.assertEqual((value['result'],value['oracle_gate'],value['ux_verdict']),('PASS','PASS','FAIL'))
        self.assertEqual(view.call_args.args[3],'/beprobung/'+PLAN);self.assertIn('/quality/wpk',view.call_args.args[4])
        value,_=self.inspect(outcome('REJECTED',rejected_action_code='X'))
        self.assertEqual((value['result'],value['reason']),('INCONCLUSIVE','AGENT_ACTION_REJECTED:X'))

    def test_side_effect_during_inspection_is_invalid_and_technical_stop_is_kept(self):
        value,_=self.inspect(outcome(),snapshots=({'tables':{'a':1}},{'tables':{'a':2}}))
        self.assertEqual((value['result'],value['technical_gate']),('INVALID','INVALID'))
        value,_=self.inspect(outcome('BLOCKED',technical_gate='BLOCKED',error_code='SESSION_INVALIDATED'))
        self.assertEqual(value['result'],'BLOCKED')

    def test_rights_case_requires_a_view_only_persona(self):
        f=fixture();f['personas']['plant_lead']['allowed_permissions']=['samples.view','samples.edit']
        with patch.object(inspection,'check_persona',return_value={'status':'PERSONA_SCOPE_VERIFIED'}),patch.object(inspection,'run_view') as view:
            value=inspection.run_inspection(object(),f,{},{'case_id':'NSN014-RIGHTS','persona':'plant_lead','task':'t'},{},None,None,None,None)
        view.assert_not_called();self.assertEqual(value['reason'],'VIEWER_HAS_MUTATING_CAPABILITY')


class PlanCreationTests(unittest.TestCase):
    def plan(self,result,after):
        with patch.object(inspection,'collect_receipts'),patch.object(inspection,'run_view',return_value=result), \
             patch.object(inspection,'verify_receipts',side_effect=[{'status':'RECEIPT_START_VERIFIED'},after]):
            return inspection.run_plan_creation(object(),fixture(),{},{},{'task':'t'},{},None,None,None,None)

    def test_plan_outcomes_are_objective(self):
        created=[{'kind':'plan_samples','scope':'/beprobung/'+PLAN}]
        self.assertEqual(self.plan(outcome(capability_actions=created),{'status':'PASS'})['result'],'PASS')
        partial=self.plan(outcome(capability_actions=created),{'status':'FAIL','missing_positions':['P1'],'mismatched_positions':[]})
        self.assertEqual((partial['result'],partial['fail_class']),('FAIL','PLAN_SAMPLE_DEVIATION'));self.assertNotIn('critical_stop',partial)
        corrupt=self.plan(outcome(capability_actions=created),{'status':'FAIL','reason':'EXTRA_OR_DUPLICATE_PROBE'})
        self.assertEqual((corrupt['result'],corrupt['critical_stop']),('FAIL',True))
        unconfirmed=self.plan(outcome('REJECTED',capability_actions=created,rejected_action_code='X'),{'status':'PASS'})
        self.assertEqual(unconfirmed['result'],'INCONCLUSIVE');self.assertTrue(unconfirmed['reason'].startswith('CREATED_BUT_NOT_CONFIRMED'))
        idle=self.plan(outcome('BLOCKED'),{'status':'FAIL','missing_positions':['P1'],'mismatched_positions':[],'sample_count':0})
        self.assertEqual(idle['result'],'INCONCLUSIVE')
        unattributed=self.plan(outcome('BLOCKED'),{'status':'PASS','sample_count':10})
        self.assertEqual(unattributed['result'],'INVALID')
        self.assertEqual(self.plan(outcome(capability_actions=created),{'status':'BLOCKED_RECEIPT_EVIDENCE'})['result'],'BLOCKED')

    def test_non_empty_start_blocks_before_any_browser_work(self):
        with patch.object(inspection,'collect_receipts'),patch.object(inspection,'run_view') as view, \
             patch.object(inspection,'verify_receipts',return_value={'status':'BLOCKED_RECEIPT_EVIDENCE'}):
            value=inspection.run_plan_creation(object(),fixture(),{},{},{'task':'t'},{},None,None,None,None)
        view.assert_not_called();self.assertEqual(value['reason'],'PLAN_START_NOT_EMPTY')


class ReportClassificationTests(unittest.TestCase):
    def test_position_classes(self):
        detail={'position_id':'P1','relations_valid':True,'pdf_status':'PASS','numeric_fields':[]}
        generated=outcome(capability_actions=[{'kind':'generate','scope':'/samples/x'}])
        cases=[(outcome(),None,set(),('INCOMPLETE','REPORT_NOT_GENERATED')),
               (generated,None,set(),('INCOMPLETE','REPORT_NOT_PERSISTED_AFTER_GENERATE')),
               (generated,dict(detail,relations_valid=False),set(),('FAIL','REPORT_RELATION_DEVIATION')),
               (generated,dict(detail,numeric_fields=['dry_g']),set(),('FAIL','REPORT_VALUE_DEVIATION')),
               (generated,detail,{'P1'},('FAIL','CALCULATION_DEVIATION')),
               (generated,dict(detail,pdf_status='INVALID_ARTIFACT'),set(),('FAIL','INVALID_PDF_ARTIFACT')),
               (generated,dict(detail,pdf_status='IDENTITY_TEXT_MISSING'),set(),('FAIL','PDF_IDENTITY_MISSING')),
               (generated,dict(detail,pdf_status='MISSING'),set(),('INCOMPLETE','PDF_NOT_DOWNLOADED')),
               (dict(generated,download_failures=[{'report_id':'r'}]),dict(detail,pdf_status='MISSING'),set(),
                ('INCOMPLETE','PDF_DOWNLOAD_NOT_RECEIVED')),
               (generated,dict(detail,pdf_status='DUPLICATE_DOWNLOAD'),set(),('INCOMPLETE','DUPLICATE_DOWNLOAD_EVIDENCE')),
               (dict(generated,status='STALLED'),detail,set(),('INCOMPLETE','NO_VISIBLE_PROGRESS')),
               (generated,detail,set(),('PASS',None))]
        for result,item,mismatch,expected in cases:
            self.assertEqual(inspection.classify_report_position(result,item,mismatch),expected)

    def test_report_case_aggregates_positions_and_calculations(self):
        f=fixture();projection={'positions':[]};receipts={'samples':[]}
        for i in (1,2):
            key='P'+str(i);product=str(UUID(int=100+i));f['suite_copy']['mapping']['positions'][key]=product
            projection['positions'].append({'position_id':key,'sample_code':'S'+str(i),'product':'Stone','measurements':{}})
            receipts['samples'].append({'id':str(UUID(int=500+i)),'sample_code':'S'+str(i),'product_id':product})
        generated=outcome(capability_actions=[{'kind':'generate','scope':'/samples/x'}])
        details={'status':'PASS','positions':[{'position_id':k,'report_id':'r'+k,'relations_valid':True,'pdf_status':'PASS',
                                               'numeric_fields':[]} for k in ('P1','P2')]}
        with patch.object(inspection,'collect_receipts',return_value=receipts),patch.object(inspection,'snapshot',return_value={'tables':{}}), \
             patch.object(inspection,'run_view',side_effect=lambda *a,**k:dict(generated)),patch.object(inspection,'collect_inputs',return_value=[]), \
             patch.object(inspection,'collect_reports'),patch.object(inspection,'collect_report_calculations'), \
             patch.object(inspection,'verify_reports',return_value=details) as reports, \
             patch.object(inspection,'verify_calculations',return_value={'status':'FAIL','mismatched_positions':['P2']}):
            value=inspection.run_reports(object(),f,projection,{'persona':'laboratory_lead'},{},None,None,None,None)
        self.assertEqual((value['result'],value['oracle_gate'],value['fail_classes']),('FAIL','FAIL',['CALCULATION_DEVIATION']))
        self.assertEqual([p['result'] for p in value['position_results']],['PASS','FAIL'])
        self.assertEqual(reports.call_args.kwargs['basis'],{})


class MeasurementClassificationTests(unittest.TestCase):
    def test_fail_requires_every_approved_value_entered_and_saved(self):
        done={'status':'DONE','fully_entered':True}
        self.assertEqual(measurement.classify_position([done],True),('FAIL','PERSISTED_VALUE_DEVIATION'))
        self.assertEqual(measurement.classify_position([dict(done,fully_entered=False)],True),
                         ('INCOMPLETE','EXECUTOR_DONE_WITHOUT_ALL_APPROVED_INPUTS'))
        self.assertEqual(measurement.classify_position([{'status':'STALLED','fully_entered':False}],True),('INCOMPLETE','NO_VISIBLE_PROGRESS'))
        self.assertEqual(measurement.classify_position([done],False),('PASS',None))
        self.assertEqual(measurement.required_saves({'kind':'allocations','fields':{}}),set())
        self.assertEqual(measurement.required_saves({'kind':'shape','fields':{'Einwaage gesamt (g):4':'1','Schlecht geformt (g):4':'1'}}),{'4'})

    def test_typed_exact_values_and_saves_are_tracked_by_the_controller(self):
        f=fixture();p=position();p.update(sample_code='S1',product='Stone')
        b,page=browser('/samples/'+PLAN)
        fields=measurement.make_contract(f,PLAN,p,'sand')['fields']
        answers=[];states=[]
        for label,value in fields.items():
            answers.append(act('type',text=value));states.append({'target':{'kind':'field'},'focused':label})
        answers+=[act('click',x=5,y=5),act('done',reason='saved'),review()]
        states+=[{'target':{'kind':'save','scope':'module'},'focused':None},{'target':{'kind':'none'},'focused':None}]
        with patch.object(measurement,'ask_calibrated',side_effect=answers),patch.object(measurement,'check_action',side_effect=states), \
             patch.object(measurement,'apply_action'):
            value=measurement.run_position(b,f,p,PLAN,'sand',{},object(),object(),budget(),MagicMock())
        self.assertEqual((value['status'],value['fields_required'],value['fields_entered'],value['fully_entered']),('DONE',4,4,True))

    def test_case_result_attributes_deviations_per_position(self):
        f=fixture();projection={'positions':[]};receipts={'samples':[]}
        for i in (1,2,3):
            key='P'+str(i);product=str(UUID(int=100+i));f['suite_copy']['mapping']['positions'][key]=product
            measurements={k:[] for k in ('wash','shape','boiling','boiling_repetitions','sand','sieves','preparation','partial_series')}
            measurements['sand']=position()['measurements']['sand']
            projection['positions'].append({'position_id':key,'sample_code':'S'+str(i),'product':'Stone','measurements':measurements})
            if i<3:receipts['samples'].append({'id':str(UUID(int=500+i)),'sample_code':'S'+str(i),'product_id':product})
        f['suite_copy']['measurement_reference_sha256']=canonical_hash(projection)
        runs={'P1':{'status':'DONE','fully_entered':True},'P2':{'status':'REJECTED','rejected_action_code':'X','fully_entered':False}}
        def run_position(browser,fixture,position,probe,kind,*args):
            return dict(runs[position['position_id']],position_id=position['position_id'],kind=kind,technical_gate='PASS')
        oracle={'status':'FAIL','mismatches':[{'position_id':k,'kind':'sand'} for k in ('P1','P2','P3')]}
        with patch.object(measurement,'collect_receipts',return_value=receipts),patch.object(measurement,'snapshot',return_value={'tables':{}}), \
             patch.object(measurement,'run_position',side_effect=run_position),patch.object(measurement,'collect_inputs'), \
             patch.object(measurement,'verify_inputs',return_value=oracle):
            value=measurement.run_measurements(object(),f,projection,['sand'],{},None,None,None,None)
        self.assertEqual((value['result'],value['oracle_gate'],value['fail_classes']),('FAIL','FAIL',['PERSISTED_VALUE_DEVIATION']))
        self.assertEqual([(p['position_id'],p['result']) for p in value['position_results']],[('P1','FAIL'),('P2','INCOMPLETE')])
        self.assertEqual(value['missing_prerequisites'],[{'position_id':'P3','kind':'sand'}]);self.assertEqual(value['unvisited_deviations'],['P3'])


class ReviewerFailureDoesNotInvalidateTheStageTests(unittest.TestCase):
    def test_failed_review_keeps_the_executor_result_and_the_stage_continues(self):
        class Failure(RuntimeError):
            code = 'PROVIDER_HTTP_400'
        b, page = browser('/samples');evidence = MagicMock();evidence.path = Path('.')
        calls = []
        def ask(model, prompt, images, budget_, actor):
            calls.append(actor)
            if actor == 'reviewer':raise Failure('x')
            return act('done', reason='seen')
        with patch.object(inspection, 'ask_calibrated', side_effect=ask), \
             patch.object(inspection, 'check_action', return_value={'kind': 'blocked'}), patch.object(inspection, 'apply_action'):
            value = inspection.run_view(b, fixture(), 'plant_lead', '/samples', ['/samples'], 'task', {}, object(), object(), budget(), evidence)
        self.assertEqual((value['status'], value['technical_gate'], value['review_error']), ('DONE', 'PASS', 'PROVIDER_HTTP_400'))
        self.assertIsNone(value['review']);self.assertEqual(calls, ['executor', 'reviewer'])
        self.assertEqual(inspection.ux_verdicts([value]), 'NOT_EVALUATED')

    def test_measurement_position_survives_a_failed_review_and_does_not_retry_it(self):
        class Failure(RuntimeError):
            code = 'RESPONSE_SCHEMA_MISMATCH'
        f = fixture();p = position();p.update(sample_code='S1', product='Stone')
        b, page = browser('/samples/' + PLAN)
        calls = []
        def ask(model, prompt, images, budget_, actor):
            calls.append(actor)
            if actor == 'reviewer':raise Failure('x')
            return act('blocked', reason='unavailable')
        shared = budget()
        with patch.object(measurement, 'ask_calibrated', side_effect=ask), patch.object(measurement, 'check_action'):
            first = measurement.run_position(b, f, p, PLAN, 'sand', {}, object(), object(), shared, MagicMock())
            second = measurement.run_position(b, f, p, PLAN, 'sand', {}, object(), object(), shared, MagicMock())
            reviews_after_two = calls.count('reviewer')
            third = measurement.run_position(b, f, p, PLAN, 'sand', {}, object(), object(), shared, MagicMock())
            fourth = measurement.run_position(b, f, p, PLAN, 'sand', {}, object(), object(), shared, MagicMock())
        self.assertEqual((first['status'], first['technical_gate'], first['review_error']), ('BLOCKED', 'PASS', 'RESPONSE_SCHEMA_MISMATCH'))
        self.assertEqual(second['review_error'], 'RESPONSE_SCHEMA_MISMATCH')  # next position, new request, not a retry
        self.assertEqual(reviews_after_two, 2)
        self.assertEqual((third['review_error'], fourth['review_error']), ('RESPONSE_SCHEMA_MISMATCH', 'REVIEWER_DISABLED_AFTER_REPEATED_FAILURES'))
        self.assertEqual(calls.count('reviewer'), 3)
        self.assertTrue(all(o['technical_gate'] == 'PASS' for o in (first, second, third, fourth)))

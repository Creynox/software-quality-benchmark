import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from test_suite_fixture import owned_fixture

scripted=importlib.import_module('projects.ble-elva.tools.scripted_executor')
dry=importlib.import_module('projects.ble-elva.tools.dry_run')
ROOT='/samples/11111111-1111-4111-8111-111111111111'


def info(path=ROOT,fields=None,controls=None,focused=None,rows=0,panels=None,scrollable=False):
    return {'path':path,'fields':fields or {},'controls':controls or [],'rows':rows,'panels':panels or [],'focused':focused,'height':800,'scrollable':scrollable}


def control(text,x=100,y=300,href=None,aria=None,panel='',disabled=False):
    return {'tag':'a' if href else 'button','text':text,'aria':aria,'href':href,'role':None,'disabled':disabled,'x':x,'y':y,'panel':panel}


def field(y=300,reachable=True):
    return {'x':500,'y':y,'visible':True,'reachable':reachable,'value':''}


class Page:
    """Page stand-in: evaluate() answers the location query and the page-info query in turn."""
    def __init__(self,path,infos):
        self.path,self.infos=path,list(infos)

    def evaluate(self,script,arg=None):
        if script=='()=>location.pathname':return self.path
        return self.infos.pop(0) if len(self.infos)>1 else self.infos[0]


def executor(page,case='NSN014-PREPARATION'):
    return scripted.ScriptedExecutor(lambda:page,lambda:case)


def prompt(task,history=()):
    return 'Work.\nTask:\n'+json.dumps(task)+'\nPrevious visible actions:\n'+json.dumps(list(history))


def task(kind='wash',inputs=None):
    return {'sample_code':'S','product':'P','module':kind,'source_inputs':inputs or {'Probenmasse feucht':'200,5','Schale + Probe feucht':'300'}}


class ScriptedExecutorTests(unittest.TestCase):
    def test_it_answers_with_the_strict_action_schema_and_a_neutral_review(self):
        page=Page(ROOT,[info(controls=[control('Testauftrag erzeugen')])])
        ex=executor(page);response=ex(None,prompt(task()),b'png',None,'executor')
        self.assertEqual(set(response.data),{'action','x','y','text','key','amount','seconds','reason'})
        review=ex(None,'review prompt',[b'png'],None,'reviewer').data
        self.assertEqual((review['verdict'],set(review['scores'].values())),('INCONCLUSIVE',{None}))

    def test_injected_provider_faults_hit_only_the_named_executor_requests(self):
        # Replays what live run 083896e6 met (a failed request) and a response that is not an action object; reviewer requests never count.
        from sqbf.bounded import WorkerFailed
        page=Page(ROOT,[info(controls=[control('Testauftrag erzeugen')])])
        ex=scripted.ScriptedExecutor(lambda:page,lambda:'NSN014-PREPARATION',{2:'raise',3:'not_object'})
        self.assertEqual(ex(None,prompt(task()),b'png',None,'executor').data['action'],'click')
        ex(None,'review prompt',[b'png'],None,'reviewer')
        with self.assertRaises(WorkerFailed) as caught:ex(None,prompt(task()),b'png',None,'executor')
        self.assertEqual(caught.exception.code,'SIMULATED_PROVIDER_FAULT')
        self.assertIsNone(ex(None,prompt(task()),b'png',None,'executor').data)
        self.assertEqual(ex(None,prompt(task()),b'png',None,'executor').data['action'],'click')

    def test_on_the_sample_page_it_follows_bles_guidance_then_opens_the_module_by_its_route_whatever_the_card_says(self):
        controls=[control('Testauftrag erzeugen',x=1000,y=215),control('Ergebnis prüfen',x=770,y=400,href=ROOT+'/uf-fine'),control('Erfassen',x=300,y=500,href=ROOT+'/sieve-analysis')]
        ex=executor(Page(ROOT,[info(controls=controls)]))
        first=ex(None,prompt(task()),b'',None,'executor').data
        self.assertEqual((first['action'],first['x'],first['y']),('click',1000,215))
        second=ex(None,prompt(task(),[{'action':'click'}]),b'',None,'executor').data
        self.assertEqual((second['action'],second['x'],second['y']),('click',770,400))  # uf-fine, not the sieve card

    def test_it_scrolls_to_find_the_module_card_a_bounded_number_of_times_then_reports_blocked(self):
        ex=executor(Page(ROOT,[info(controls=[],scrollable=True)]))
        actions=[ex(None,prompt(task(),[{'action':'scroll'}]*i),b'',None,'executor').data for i in range(8)]
        self.assertEqual([a['action'] for a in actions[:6]],['scroll']*6);self.assertEqual(actions[6]['action'],'blocked')
        self.assertTrue(all(a['x']>=1190 for a in actions[:6]))  # scrolls over the page margin, never over the input column
        self.assertEqual(len({a['x'] for a in actions[:6]}),6)   # varied, so a page that cannot scroll is not mistaken for a stall

    def test_the_task_in_bles_words_is_translated_back_to_the_internal_module_and_field_names(self):
        vocabulary=scripted.internal_inputs
        path=ROOT+'/sieve-analysis'
        t=task('Siebanalyse',{'Einwaage (g)':'285','Rückstand (g), Sieb 31,5 mm':'12'})
        fields={'main_input':field(300),'sieve:31.5':field(380)}
        ex=executor(Page(path,[info(path,fields)]))
        first=ex(None,prompt(t),b'',None,'executor').data
        self.assertEqual((first['action'],first['y']),('click',300));self.assertIn('main_input',first['reason'])
        self.assertEqual(vocabulary('sieve',{'Rückstand (g), Sieb 31,5 mm':'12'}),{'sieve:31.5':'12'})

    def test_a_value_is_typed_only_into_the_focused_field_then_tab_then_it_waits_for_blazor(self):
        path=ROOT+'/uf-fine';t=task()
        fields={'Probenmasse feucht':field(300),'Schale + Probe feucht':field(380)}
        pages=[info(path,fields),                                       # decide: click the first field
               info(path,fields,focused=None),                          # focus lost: click again
               info(path,fields,focused='Probenmasse feucht'),          # type
               info(path,fields,focused='Probenmasse feucht'),          # Tab
               info(path,fields,focused='Schale + Probe feucht'),       # wait for the recalculation
               info(path,fields,focused='Schale + Probe feucht')]       # next field is focused already but state wants a click
        ex=executor(Page(path,pages))
        a1=ex(None,prompt(t),b'',None,'executor').data
        self.assertEqual((a1['action'],a1['y']),('click',300))
        a2=ex(None,prompt(t,[a1]),b'',None,'executor').data
        self.assertEqual((a2['action'],a2['y']),('click',300))
        a3=ex(None,prompt(t,[a1,a2]),b'',None,'executor').data
        self.assertEqual((a3['action'],a3['key']),('key','ControlOrMeta+A'))   # the field may be pre-filled: replace, never append
        a4=ex(None,prompt(t,[a1,a2,a3]),b'',None,'executor').data
        self.assertEqual((a4['action'],a4['text']),('type','200,5'))          # German notation exactly as in the task
        a5=ex(None,prompt(t,[a1,a2,a3,a4]),b'',None,'executor').data
        self.assertEqual((a5['action'],a5['key']),('key','Tab'))
        a6=ex(None,prompt(t,[a1,a2,a3,a4,a5]),b'',None,'executor').data
        self.assertEqual((a6['action'],a6['seconds']),('wait',1))
        a7=ex(None,prompt(t,[a1,a2,a3,a4,a5,a6]),b'',None,'executor').data
        self.assertEqual((a7['action'],a7['y']),('click',380))

    def test_after_the_fields_it_saves_once_scrolls_to_find_the_button_and_never_ends_unsaved_as_done(self):
        path=ROOT+'/uf-fine';t=task(inputs={'Probenmasse feucht':'200'});fields={'Probenmasse feucht':field(300)}
        ex=executor(Page(path,[info(path,fields,controls=[control('Speichern',x=1150,y=160)])]))
        ex.state={'typed':['Probenmasse feucht'],'setup':[]}
        save=ex(None,prompt(t,[{'action':'type'}]),b'',None,'executor').data
        self.assertEqual((save['action'],save['x'],save['y']),('click',1150,160))
        end=ex(None,prompt(t,[{'action':'click'}]),b'',None,'executor').data
        self.assertEqual(end['action'],'done')
        hidden=executor(Page(path,[info(path,fields,scrollable=True)]));hidden.state={'typed':['Probenmasse feucht'],'setup':[]}
        first=hidden(None,prompt(t,[{'action':'type'}]),b'',None,'executor').data
        self.assertEqual((first['action'],first['amount']),('scroll',-1400))
        hidden.state['scrolls']={'save_up':1,'save_down':5}
        self.assertEqual(hidden(None,prompt(t,[{'action':'type'}]),b'',None,'executor').data['action'],'blocked')

    def test_a_new_task_resets_the_state_but_a_rejection_marker_does_not(self):
        ex=executor(Page(ROOT,[info(controls=[control('Testauftrag erzeugen')])]))
        ex(None,prompt(task()),b'',None,'executor');self.assertTrue(ex.state.get('ordered'))
        ex(None,prompt(task(),[{'rejected_by_controller':'X'}]),b'',None,'executor');self.assertTrue(ex.state.get('ordered'))
        ex(None,prompt(task()),b'',None,'executor');self.assertEqual(ex.state.get('ordered'),True)  # empty history: fresh state, order clicked again
        self.assertEqual(scripted.german_fraction('11,2 mm (11.2 mm)'),'11.2');self.assertEqual(scripted.german_fraction('8 mm'),'8');self.assertIsNone(scripted.german_fraction('x'))

    def test_inspection_tasks_follow_the_listed_read_only_controls_and_report_flow(self):
        page=Page('/samples',[info('/samples',controls=[control('Offen'),control('ENZBERG-20260508-NSN-014-01',y=500)])])
        ex=executor(page,'NSN014-RECEIPT')
        first=ex(None,'Task:\nPrüfe den Probeneingang\nPrevious visible actions:\n[]',b'',None,'executor').data
        self.assertEqual((first['action'],first['y']),('click',300))
        ex.state={'step':3}
        self.assertEqual(ex(None,'Task:\nx\nPrevious visible actions:\n[{"a":1}]',b'',None,'executor').data['y'],500)
        self.assertEqual(ex(None,'Task:\nx\nPrevious visible actions:\n[{"a":1}]',b'',None,'executor').data['action'],'done')
        report=executor(Page(ROOT,[info(controls=[control('Weitere Aktionen',x=1243,y=213,aria='Weitere Aktionen')])]),'NSN014-REPORT')
        self.assertEqual(report(None,'Task:\nreport\nPrevious visible actions:\n[]',b'',None,'executor').data['x'],1243)
        menu=executor(Page(ROOT,[info(controls=[control('Prüfbericht',x=1150,y=260)])]),'NSN014-REPORT')
        self.assertEqual(menu(None,'Task:\nreport\nPrevious visible actions:\n[]',b'',None,'executor').data['y'],260)
        download=executor(Page('/reports/22222222-2222-4222-8222-222222222222',[info('/reports/22222222-2222-4222-8222-222222222222',controls=[control('PDF herunterladen',y=150)])]),'NSN014-REPORT')
        self.assertEqual(download(None,'Task:\nreport\nPrevious visible actions:\n[]',b'',None,'executor').data['y'],150)
        self.assertEqual(download(None,'Task:\nreport\nPrevious visible actions:\n[{"a":1}]',b'',None,'executor').data['action'],'done')

    def test_the_report_page_gets_time_to_offer_the_pdf_before_the_script_gives_up(self):
        # Clean dry run 16.10.2026: the first report page was met before BLE had rendered its menu, REPORT P01 stayed incomplete.
        path='/reports/22222222-2222-4222-8222-222222222222'
        prompt_='Task:\nreport\nPrevious visible actions:\n[{"a":1}]'  # a non-empty history keeps the script's state between calls
        ex=executor(Page(path,[info(path,controls=[]),info(path,controls=[]),info(path,controls=[control('PDF herunterladen',y=150)])]),'NSN014-REPORT')
        self.assertEqual([ex(None,prompt_,b'',None,'executor').data['action'] for _ in range(3)],['wait','wait','click'])
        gone=executor(Page(path,[info(path,controls=[])]),'NSN014-REPORT')
        actions=[gone(None,prompt_,b'',None,'executor').data['action'] for _ in range(7)]
        self.assertEqual(actions,['wait']*5+['blocked']*2)


class DryRunToolTests(unittest.TestCase):
    def test_only_an_unclaimed_scratch_clone_is_accepted(self):
        f=owned_fixture()
        with tempfile.TemporaryDirectory() as directory:
            f['suite_copy']['application_root']=str(Path(directory)/'app')
            for clone in ({},{'purpose':'fixture'},None):
                f['suite_copy']['clone']=clone
                with self.assertRaises(dry.DryRunRefused):dry.require_scratch(f)
            f['suite_copy']['clone']={'purpose':'scratch'};dry.require_scratch(f)
            (Path(directory)/'benchmark-consumed.json').write_text('{}',encoding='utf-8')
            with self.assertRaises(dry.DryRunRefused):dry.require_scratch(f)

    def test_the_summary_reports_rejections_as_guard_gaps_and_harness_stops_separately(self):
        records=[{'case_id':'NSN014-SE','result':'PASS','positions':[{'position_id':'P1','rejected_actions':[]}]},
                 {'case_id':'NSN014-RECEIPT','result':'PASS','rejected_actions':[{'error_code':'X','action':'click','target':{'label':'Meine'}}]},
                 {'case_id':'NSN014-SIEVE','result':'INVALID','reason':'UNRELATED_MEASUREMENT_WRITE'}]
        report=dry.summarize(records,{'final_oracles':{'receipt':{'status':'PASS'},'static_fixture_unchanged':True}},[{'action':'click'}])
        self.assertEqual(report['status'],'DRY_RUN_FOUND_GUARD_OR_HARNESS_GAPS');self.assertEqual(report['harness_stops'],['NSN014-SIEVE'])
        self.assertEqual(report['guard_coverage_gaps'],[{'error_code':'X','action':'click','target':{'label':'Meine'},'case_id':'NSN014-RECEIPT'}])
        self.assertEqual((report['model_calls'],report['scripted_actions']),(0,1))
        clean=dry.summarize([records[0]],{'final_oracles':{}},[])
        self.assertEqual(clean['status'],'DRY_RUN_COMPLETED')


if __name__=='__main__':
    unittest.main()

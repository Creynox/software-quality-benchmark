import importlib
import unittest
from html import escape
from unittest.mock import MagicMock
from test_suite_fixture import owned_fixture
from sqbf.read_only import ReadOnlyViolation

module=importlib.import_module('projects.ble-elva.tools.measurement_guard')


def position():
    return {'position_id':'P01','allocations':[{'target_process':'Kornform','target_sieve_mm':'4','actual_amount_g':'100'}],'measurements':{
        'wash':[{'container_g':'100','container_wet_g':'300','container_dry_g':'290','container_washed_g':'280'}],
        'sand':[{'sand_height_mm':'95','suspension_height_mm':'122'},{'sand_height_mm':'96','suspension_height_mm':'121'}],
        'boiling':[{'marl_g':'0.5'}],'boiling_repetitions':[{'order':1,'minutes':'10','initial_g':'100','final_g':'99.5'}],
        'shape':[{'fraction':'4 mm','total_g':'100','poor_g':'3'}],
        'sieves':[{'input_g':'2000','points':[{'sieve_mm':'8','partial':False,'retained_g':'200'}]}],
        'preparation':[{'dry_g':'400'}],
        'partial_series':[{'initial_g':'200','points':[{'pan':False,'sieve_mm':'2','retained_g':'20'}]},
                          {'initial_g':'200','points':[{'pan':False,'sieve_mm':'2','retained_g':'21'}]}]}}


class MeasurementGuardTests(unittest.TestCase):
    def contract(self,kind):
        return module.make_contract(owned_fixture(),'11111111-1111-4111-8111-111111111111',position(),kind)

    def test_all_six_profiles_are_source_bound_to_a_single_probe(self):
        for kind in module.ROUTES:
            c=self.contract(kind)
            self.assertTrue(c['fields']);self.assertNotIn('tenant_id',str(c));self.assertNotIn('credential',str(c))
            self.assertEqual(c['origin'],'http://127.0.0.1:5082')
        self.assertEqual(self.contract('wash')['fields']['Probenmasse feucht'],'200')
        self.assertEqual(self.contract('sand')['fields']['Sandhöhe:A'],'95')
        self.assertEqual(self.contract('partial')['fields']['partial:2:B'],'21')
        for bad in ('NaN','-1','Infinity'):
            with self.assertRaises(ValueError):module.number(bad)

    def test_native_guard_blocks_delete_and_second_save_and_latches_across_reload(self):
        from playwright.sync_api import sync_playwright
        c=self.contract('wash')
        fields=''.join('<div class="mud-input-control"><label>'+escape(label)+'</label><input value="'+value+'"></div>' for label,value in c['fields'].items())
        html=fields+'<button id="save" onclick="window.writes++">Speichern</button><button id="delete" onclick="window.deletes++">Löschen</button><script>window.writes=0;window.deletes=0;</script>'
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context();context.add_init_script(module.event_guard(c))
            context.route(c['origin']+'/**',lambda route:route.fulfill(status=200,body=html,content_type='text/html'))
            page=context.new_page();page.goto(c['origin']+c['path'])
            page.locator('#delete').click();self.assertEqual(page.evaluate('window.deletes'),0)
            page.locator('#save').click();page.locator('#save').click();self.assertEqual(page.evaluate('window.writes'),1)
            page.reload();page.locator('#save').click();self.assertEqual(page.evaluate('window.writes'),0)
            context.close();browser.close()

    def test_controller_rejects_unknown_fields_wrong_values_and_repeat_save(self):
        c=self.contract('wash');page=MagicMock();page.url=c['origin']+c['path']
        page.evaluate.return_value={'focused':'Probenmasse feucht','target':{'kind':'field'}}
        module.check_action(page,{'action':'type','text':'200'},c,set())
        with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'type','text':'999'},c,set())
        for key in ('Enter','ControlOrMeta+L','ControlOrMeta+Shift+I'):
            with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'key','key':key},c,set())
        page.evaluate.return_value={'focused':None,'target':{'kind':'save','scope':'module'}}
        module.check_action(page,{'action':'click'},c,set())
        with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'click'},c,{'module'})

    def test_all_native_control_contexts_identify_the_correct_source_field(self):
        from playwright.sync_api import sync_playwright
        def control(label):return '<div class="mud-input-control"><label>'+escape(label)+'</label><input></div>'
        htmls={
            'wash':control('Probenmasse feucht'),
            'sand':'<div class="se-best-card"><span class="se-best-letter">A</span>'+control('Sandhöhe')+'</div>',
            'shape':'<div class="kf-panel"><span class="kf-panel-label">4 mm</span>'+control('Einwaage gesamt (g)')+'</div>',
            'boiling':'<div class="kv-rep-row"><span class="kv-rep-num">1</span>'+control('Einwaage vor Kochen')+'</div>',
            'sieve':'<div class="sa-kpi-einwaage">'+control('')+'</div>',
            'partial':'<table><tr><td data-label="Sieb">2 mm</td><td data-label="Siebturm B">'+control('')+'</td></tr></table>',
            'allocations':'<div class="sa-ec"><span class="sa-ec-label">KF</span><span class="sa-ec-sieb">4 mm</span>'+control('')+'</div>',
        }
        keys={'wash':'Probenmasse feucht','sand':'Sandhöhe:A','shape':'Einwaage gesamt (g):4',
              'boiling':'Einwaage vor Kochen:1','sieve':'main_input','partial':'partial:2:B','allocations':'KF:4'}
        with sync_playwright() as p:
            browser=p.chromium.launch()
            for kind,html in htmls.items():
                config=self.contract(kind);context=browser.new_context();context.add_init_script(module.event_guard(config))
                context.route(config['origin']+'/**',lambda route:route.fulfill(body=html,content_type='text/html; charset=utf-8'))
                page=context.new_page();page.goto(config['origin']+config['path']);page.locator('input').click()
                action={'action':'type','text':config['fields'][keys[kind]]}
                state=module.check_action(page,action,config,set())
                self.assertEqual(state['focused'],keys[kind]);context.close()
            browser.close()

    def test_other_sample_other_origin_and_release_page_are_denied(self):
        c=self.contract('sand');page=MagicMock()
        for url in ('http://127.0.0.1:5059'+c['path'],c['origin']+'/samples/22222222-2222-4222-8222-222222222222/sand-equivalent',c['origin']+c['root']+'/release'):
            page.url=url
            with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'done'},c,set())
        page.evaluate.assert_not_called()

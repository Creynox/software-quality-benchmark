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
        'sand':[{'sand_height':'95','suspension_height':'122'},{'sand_height':'96','suspension_height':'121'}],
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

    def test_derived_partial_values_are_not_approved_input_fields(self):
        # BLE shows the K basis read-only and derives the pan loss of each tower; neither can be typed.
        p=position()
        for series in p['measurements']['partial_series']:series['points'].append({'pan':True,'sieve_mm':'0','retained_g':'0.5'})
        c=module.make_contract(owned_fixture(),'11111111-1111-4111-8111-111111111111',p,'partial')
        self.assertEqual(sorted(c['fields']),['Einwaage Siebturm A','Einwaage Siebturm B','partial:2:A','partial:2:B'])
        self.assertFalse([name for name in c['fields'] if 'pan' in name or 'K-Basis' in name])

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

    def test_typed_numbers_must_use_the_decimal_comma_because_a_point_is_a_thousands_separator(self):
        # BLE parses de-DE: "1.250" is read as 1250, so a point would corrupt the value silently (dry run 15.10.2026).
        c=self.contract('boiling');page=MagicMock();page.url=c['origin']+c['path']
        page.evaluate.return_value={'focused':'Rückwaage nach Kochen:1','target':{'kind':'field'}}
        self.assertEqual(c['fields']['Rückwaage nach Kochen:1'],'99.5')
        module.check_action(page,{'action':'type','text':'99,5'},c,set())
        for text in ('99.5','995','99,50',' 99,5','99,5 '):
            with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'type','text':text},c,set())
        page.evaluate.return_value={'focused':'Einwaage vor Kochen:1','target':{'kind':'field'}}
        module.check_action(page,{'action':'type','text':'100'},c,set())
        with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'type','text':'100,0'},c,set())
        self.assertEqual(module.german('1250.5'),'1250,5');self.assertEqual(module.german('7'),'7')

    def test_pan_row_of_the_main_sieve_maps_to_sieve_zero_under_every_label(self):
        from playwright.sync_api import sync_playwright
        p=position();p['measurements']['sieves'][0]['points'].append({'sieve_mm':'0','partial':False,'retained_g':'12.5'})
        c=module.make_contract(owned_fixture(),'11111111-1111-4111-8111-111111111111',p,'sieve')
        self.assertEqual(c['fields']['sieve:0'],'12.5');self.assertEqual(c['fields']['sieve:8'],'200')
        def row(label):
            return ('<table><tr><td data-label="Sieb">'+escape(label)+'</td><td class="sieve-residue-input"><div class="mud-input-control">'
                    '<label></label><input></div></td></tr></table>')
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            for label,expected in (('Boden','sieve:0'),('Pfanne','sieve:0'),('Anteile gesamt < 0,063 mm','sieve:0'),('8 mm','sieve:8')):
                context=browser.new_context();context.add_init_script(module.event_guard(c))
                html=row(label)  # bound per iteration; a default argument would receive Playwright's request object
                context.route(c['origin']+'/**',(lambda body:lambda route:route.fulfill(body=body,content_type='text/html; charset=utf-8'))(html))
                page=context.new_page();page.goto(c['origin']+c['path']);page.locator('input').click()
                state=module.check_action(page,{'action':'type','text':module.german(c['fields'][expected])},c,set())
                self.assertEqual(state['focused'],expected,label)
                # The neighbouring sieve value is not accepted in this row.
                other='sieve:8' if expected=='sieve:0' else 'sieve:0'
                with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'type','text':module.german(c['fields'][other])},c,set())
                context.close()
            browser.close()

    def test_offered_fields_ignore_the_save_latch_and_disabled_or_unapproved_inputs(self):
        from playwright.sync_api import sync_playwright
        c=self.contract('wash')
        def control(label,extra=''):return '<div class="mud-input-control"><label>'+escape(label)+'</label><input '+extra+'></div>'
        html=control('Probenmasse feucht')+control('Schale + Probe feucht','disabled')+control('Unbekanntes Feld')
        with sync_playwright() as pw:
            browser=pw.chromium.launch();context=browser.new_context();context.add_init_script(module.event_guard(c))
            context.route(c['origin']+'/**',lambda route:route.fulfill(body=html,content_type='text/html; charset=utf-8'))
            page=context.new_page();page.goto(c['origin']+c['path'])
            self.assertEqual(module.offered_fields(page,c),{'Probenmasse feucht'})
            page.evaluate("sessionStorage.setItem('sqbf-module-save:'+%r+':module','attempted')"%c['path'])
            # After the one allowed save the field is latched for typing, yet the page still offers it.
            page.locator('input').first.click()
            self.assertIsNone(page.evaluate("({config})=>{__C__ return field(document.activeElement);}".replace('__C__',module.CLASSIFY),{'config':c}))
            self.assertEqual(module.offered_fields(page,c),{'Probenmasse feucht'})
            context.close();browser.close()

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

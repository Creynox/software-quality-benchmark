import importlib
import unittest
from html import escape
from sqbf.read_only import ReadOnlyViolation
from test_suite_fixture import owned_fixture

module=importlib.import_module('projects.ble-elva.tools.receipt_guard')


def contract():
    fixture=owned_fixture()
    fixture['suite_copy']['preparation_context']={'customer':'SQBF Enzberg','project':'SQBF NSN 014','sample_owner':'Werk Enzberg'}
    return module.make_contract(fixture,{'position_id':'P01','product':'Synthetic stone',
                                       'inputs':{'sample_code':'SYNTHETIC-01'}},'2026-05-08')


class ReceiptGuardTests(unittest.TestCase):
    def test_native_save_guard_blocks_incomplete_and_survives_full_reload(self):
        from playwright.sync_api import sync_playwright
        cfg=contract()
        fields=''.join('<div class="mud-input-control"><label>'+escape(k)+'</label><input value="'+escape(v,quote=True)+'"></div>'
                       for k,v in cfg['fields'].items())
        html=fields+'<button id="save" onclick="window.syntheticWrites++">Probe anlegen</button><script>window.syntheticWrites=0;</script>'
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context()
            context.add_init_script(module.event_guard(cfg))
            context.route('http://127.0.0.1:54321/**',lambda route:route.fulfill(status=200,body=html,content_type='text/html'))
            page=context.new_page();page.goto('http://127.0.0.1:54321/samples/create')
            page.locator('#save').click()
            self.assertEqual(page.evaluate('window.syntheticWrites'),1)
            page.locator('#save').click()
            self.assertEqual(page.evaluate('window.syntheticWrites'),1)
            page.reload();page.locator('#save').click()
            self.assertEqual(page.evaluate('window.syntheticWrites'),0)
            self.assertEqual(page.evaluate('window.__sqbfReceiptSaved'),True)
            context.close();browser.close()

    def test_exact_values_and_complete_single_save_required(self):
        c=contract();state={'target':{'kind':'save'},'focused':{'kind':'field','field':'Probencode'},'complete':True,'saved':False}
        module.allow_operation({'action':'click'},state,c,controller_saved=False)
        for changed in ({'complete':False},{'saved':True}):
            s=dict(state,**changed)
            with self.assertRaises(ReadOnlyViolation):module.allow_operation({'action':'click'},s,c,controller_saved=False)
        with self.assertRaises(ReadOnlyViolation):module.allow_operation({'action':'click'},state,c,controller_saved=True)
        module.allow_operation({'action':'type','text':'SYNTHETIC-01'},state,c,controller_saved=False)
        with self.assertRaises(ReadOnlyViolation):module.allow_operation({'action':'type','text':'UNRELATED'},state,c,controller_saved=False)

    def test_unrelated_buttons_fields_and_browser_shortcuts_block(self):
        c=contract();s={'target':{'kind':'blocked'},'focused':{'kind':'field','field':'Passwort'},'complete':True,'saved':False}
        for action in ({'action':'click'},{'action':'type','text':'private'},{'action':'key','key':'Enter'},
                       {'action':'key','key':'ControlOrMeta+L'},{'action':'key','key':'Tab'}):
            with self.assertRaises(ReadOnlyViolation):module.allow_operation(action,s,c,controller_saved=False)

    def test_controller_latch_cannot_be_omitted_and_native_latch_survives_reload(self):
        with self.assertRaises(TypeError):module.allow_operation({'action':'done'},{},contract())
        script=module.event_guard(contract())
        self.assertIn("sessionStorage.getItem(saveKey)",script)
        self.assertIn("sessionStorage.setItem(saveKey,'attempted')",script)
        self.assertIn("document.addEventListener('submit',stop,true)",script)

    def test_normal_source_data_and_date_are_explicit(self):
        c=contract()
        self.assertEqual(c['fields']['Entnahmedatum'],'08.05.2026')
        self.assertEqual(c['editable'],['Probencode','Entnahmedatum'])
        self.assertNotIn('password',str(c).lower())
        self.assertNotIn('tenant_id',c)

import importlib
import unittest
from unittest.mock import MagicMock
from test_suite_fixture import owned_fixture
from sqbf.read_only import ReadOnlyViolation

module=importlib.import_module('projects.ble-elva.tools.inspection_guard')


class InspectionGuardTests(unittest.TestCase):
    def test_plan_capability_is_separate_and_single_use(self):
        from playwright.sync_api import sync_playwright
        f=owned_fixture();f['suite_copy']['mapping']={'plan_id':'11111111-1111-4111-8111-111111111111'}
        path='/beprobung/'+f['suite_copy']['mapping']['plan_id'];config=module.contract(f,[path],plan_samples=True)
        html='<script>window.writes=0</script><button onclick="window.writes++">Proben anlegen / nachanlegen</button><button onclick="window.writes+=100">Plan archivieren</button>'
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context();context.add_init_script(module.event_guard(config))
            context.route(config['origin']+'/**',lambda route:route.fulfill(body=html,content_type='text/html; charset=utf-8'))
            page=context.new_page();page.goto(config['origin']+path)
            page.get_by_text('Plan archivieren',exact=True).click()
            button=page.get_by_text('Proben anlegen / nachanlegen',exact=True);button.click();button.click()
            self.assertEqual(page.evaluate('window.writes'),1)
            page.reload();button.click();self.assertEqual(page.evaluate('window.writes'),0)
            context.close();browser.close()
        with self.assertRaises(ValueError):module.contract(f,[path],report=True,plan_samples=True)
    def test_only_authorized_pdf_button_can_trigger_one_same_origin_blob_download(self):
        from playwright.sync_api import sync_playwright
        path='/reports/11111111-1111-4111-8111-111111111111'
        config=module.contract(owned_fixture(),['/samples'],report=True)
        html='''<button id="pdf" onclick="downloadTwice()">PDF herunterladen</button><script>
        function downloadTwice(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['synthetic transport test']));a.download='synthetic.bin';document.body.appendChild(a);a.click();a.click();a.remove();}
        </script>'''
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(accept_downloads=False)
            context.add_init_script(module.event_guard(config));context.route(config['origin']+'/**',lambda route:route.fulfill(body=html,content_type='text/html; charset=utf-8'))
            page=context.new_page();page.goto(config['origin']+path);events=[];page.on('download',lambda download:events.append(download))
            with page.expect_download():page.locator('#pdf').click()
            page.wait_for_timeout(200);self.assertEqual(len(events),1)
            context.close();browser.close()
    def test_readonly_mode_cannot_enable_report_or_other_mutation(self):
        config=module.contract(owned_fixture(),['/analytics'])
        page=MagicMock();page.url=config['origin']+'/analytics'
        for state in ({'kind':'blocked'},{'kind':'generate','scope':'/analytics'}):
            page.evaluate.return_value=state
            with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'click'},config,set())
        for action in ({'action':'type','text':'hello'},{'action':'key','key':'Enter'}):
            with self.assertRaises(ReadOnlyViolation):module.check_action(page,action,config,set())

    def test_report_single_generation_and_other_report_action_denied(self):
        path='/samples/11111111-1111-4111-8111-111111111111'
        config=module.contract(owned_fixture(),[path],report=True)
        page=MagicMock();page.url=config['origin']+path;page.evaluate.return_value={'kind':'generate','scope':path}
        module.check_action(page,{'action':'click'},config,set())
        with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'click'},config,{path})
        page.evaluate.return_value={'kind':'blocked'}
        with self.assertRaises(ReadOnlyViolation):module.check_action(page,{'action':'click'},config,set())

    def test_native_guard_blocks_release_sign_delete_and_latches_report_generation(self):
        from playwright.sync_api import sync_playwright
        path='/samples/11111111-1111-4111-8111-111111111111'
        config=module.contract(owned_fixture(),[path],report=True)
        html='<script>window.calls=[]</script>'+''.join('<button onclick="window.calls.push(this.textContent)">'+label+'</button>' for label in ('Prüfbericht','Freigeben','Abzeichnen','Probe löschen','Versenden'))
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context();context.add_init_script(module.event_guard(config))
            context.route(config['origin']+'/**',lambda route:route.fulfill(body=html,content_type='text/html; charset=utf-8'))
            page=context.new_page();page.goto(config['origin']+path)
            for label in ('Freigeben','Abzeichnen','Probe löschen','Versenden','Prüfbericht','Prüfbericht'):page.get_by_text(label,exact=True).click()
            self.assertEqual(page.evaluate('window.calls'),['Prüfbericht'])
            page.reload();page.get_by_text('Prüfbericht',exact=True).click();self.assertEqual(page.evaluate('window.calls'),[])
            context.close();browser.close()

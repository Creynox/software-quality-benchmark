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

    def classify(self,html,selector,*,config=None,path='/samples'):
        """Classification of the element a click at the centre of `selector` would hit, in real Chromium with the real guard script."""
        from playwright.sync_api import sync_playwright
        config=config or module.contract(owned_fixture(),[path,'/beprobung'],report=True)
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(viewport={'width':1280,'height':800});context.add_init_script(module.event_guard(config))
            context.route(config['origin']+'/**',lambda route:route.fulfill(body=html,content_type='text/html; charset=utf-8'))
            page=context.new_page();page.goto(config['origin']+path)
            state=page.evaluate("""({config,selector})=>{__C__
              const e=document.querySelector(selector);const r=e.getBoundingClientRect();
              return classify(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}""".replace('__C__',module.CLASSIFY),{'config':config,'selector':selector})
            context.close();browser.close()
        return state['kind']

    def test_menu_entry_is_a_div_in_ble_and_must_be_recognised_while_deleting_stays_blocked(self):
        # Live run 413f7abe: "Prüfbericht" is a div.mud-menu-item, the guard only knew button and .mud-list-item, so no report could be generated.
        menu='<div class="mud-popover mud-popover-open"><div class="mud-menu-item mud-ripple mud-list-item-clickable" id="%s"><p class="mud-typography mud-menu-item-text">%s</p></div></div>'
        path='/samples/11111111-1111-4111-8111-111111111111'
        config=module.contract(owned_fixture(),[path],report=True)
        self.assertEqual(self.classify(menu%('x','Prüfbericht'),'#x',config=config,path=path),'generate')
        self.assertEqual(self.classify(menu%('x','Probe löschen'),'#x',config=config,path=path),'blocked')
        self.assertEqual(self.classify('<div role="menuitem" id="x">Prüfbericht</div>','#x',config=config,path=path),'generate')
        # Without the report capability the same entry is not a generate action.
        read_only=module.contract(owned_fixture(),[path])
        self.assertEqual(self.classify(menu%('x','Prüfbericht'),'#x',config=read_only,path=path),'blocked')

    def test_presentational_controls_are_read_controls_and_every_writing_control_stays_blocked(self):
        read=('<button id="x">Meine</button>','<button id="x">Nach Probencode sortieren</button>','<button id="x">Neu: 7</button>','<button id="x">Weitere Filter</button>',
              '<button id="x">Woche</button>','<button id="x" aria-label="Navigation umschalten">&#9776;</button>','<button id="x">ENZBERG-20260508-NSN-014-04</button>',
              '<button role="tab" id="x">Übersicht</button>','<div class="mud-select"><div id="x">Werk</div></div>','<div class="mud-expand-panel-header" id="x">Panel</div>')
        for html in read:self.assertEqual(self.classify(html,'#x'),'read_control',html)
        write=('<button id="x">Neue Probe</button>','<button id="x">Plan bearbeiten</button>','<button id="x">Abschliessen</button>','<button id="x">Archivieren</button>',
               '<button id="x">Loeschen</button>','<button id="x">Prüfbericht erstellen</button>','<button id="x">Produkt hinzufügen</button>','<button id="x">Aus Plan entfernen</button>',
               '<button id="x">Proben anlegen / nachanlegen</button>','<button id="x">Freigeben</button>','<button id="x">Speichern</button>','<button id="x">Anforderungen anlegen</button>',
               '<button role="tab" id="x">Proben schließen</button>','<button id="x" aria-label="Probe ENZBERG-20260508-NSN-014-05 schließen">x</button>',
               '<form><button id="x">Meine</button></form>','<button id="x">Benutzermenü öffnen</button>','<button id="x">Dunkles Design aktivieren</button>')
        for html in write:self.assertEqual(self.classify(html,'#x'),'blocked',html)

    def test_same_page_anchor_scrolls_but_other_anchors_and_links_stay_scoped(self):
        path='/samples/11111111-1111-4111-8111-111111111111'
        config=module.contract(owned_fixture(),[path,'/beprobung'])
        for href,expected in ((path+'#module-bereich','navigation'),('/beprobung','navigation'),('/samples/22222222-2222-4222-8222-222222222222','blocked'),
                              ('/admin/users','blocked'),('/beprobung#x','blocked'),(path+'?edit=1','blocked'),('http://evil.example/'+path,'blocked')):
            self.assertEqual(self.classify('<a id="x" href="%s">link</a>'%href,'#x',config=config,path=path),expected,href)

    def test_a_row_of_the_sample_list_opens_its_detail_whether_or_not_aria_selected_is_present(self):
        # Live run 083896e6: the model clicked the row "Probe <code> auswählen" and the rule demanded aria-selected, so the click was rejected
        # and RECEIPT ended after one attempt.
        row='<table><tbody><tr id="x" %s><td>ENZBERG-20260508-NSN-014-02</td><td>KSM</td></tr></tbody></table>'
        for attributes in ('aria-label="Probe ENZBERG-20260508-NSN-014-02 auswählen"','aria-selected="false" aria-label="Probe ENZBERG-20260508-NSN-014-02 auswählen"'):
            self.assertEqual(self.classify(row%attributes,'#x'),'read_control',attributes)
        # Everything else that is a row, or says "Probe ...", stays blocked.
        for attributes in ('','aria-label="Probe ENZBERG-20260508-NSN-014-02 löschen"','aria-label="Plan NSN 014 auswählen"','aria-label="Zeile auswählen"'):
            self.assertEqual(self.classify(row%attributes,'#x'),'blocked',attributes)
        self.assertEqual(self.classify(row%'aria-label="Probe ENZBERG-20260508-NSN-014-02 auswählen"','#x',path='/beprobung',
                                       config=module.contract(owned_fixture(),['/samples','/beprobung'])),'blocked')

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

    def test_sidebar_group_toggles_only_expand_the_menu(self):
        # Live run 6c23f768: RECEIPT wanted to open the plan through the sidebar group "Beprobung" and the click was rejected.
        group='<div class="mud-nav-group"><button id="x" aria-label="%s">Beprobung</button></div>'
        self.assertEqual(self.classify(group%'Toggle Beprobung','#x'),'read_control')
        self.assertEqual(self.classify(group%'Toggle Qualität','#x'),'read_control')
        # Only inside the sidebar group, and only a plain "Toggle <name>".
        self.assertEqual(self.classify('<button id="x" aria-label="Toggle Beprobung">Beprobung</button>','#x'),'blocked')
        self.assertEqual(self.classify(group%'Beprobung löschen','#x'),'blocked')
        self.assertEqual(self.classify(group%'Toggle Beprobung/Plan archivieren','#x'),'blocked')
        self.assertEqual(self.classify('<form><div class="mud-nav-group"><button id="x" aria-label="Toggle Beprobung">B</button></div></form>','#x'),'blocked')

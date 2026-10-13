"""Offline LAB write boundaries and browser event regressions; no BLE writes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqbf.bounded import Budget, LabBudget, BudgetExceeded
from sqbf.write_profile import load_write_profile
guard=load_write_profile("LAB-01-SINGLE-PRODUCT-v1","lab_guard")
FIELDS, KEYS=guard.FIELDS, guard.KEYS
allow_operation, allowed_path, check_action=guard.allow_operation, guard.allowed_path, guard.check_action
event_guard, transport_allowed, validate_target=guard.event_guard, guard.transport_allowed, guard.validate_target
lab=load_write_profile("LAB-01-SINGLE-PRODUCT-v1","lab_runner")
LAB_ACTION_SCHEMA, unchanged_except_product=lab.LAB_ACTION_SCHEMA, lab.unchanged_except_product
from sqbf.models import Scenario
from sqbf.read_only import ReadOnlyViolation

PROFILE='projects/ble-elva/scenarios/sts-0-45-product-core-v0.3.json'


def fixture():
    f=json.loads(Path('projects/ble-elva/fixtures/enzberg-product-core-v0.2.json').read_text(encoding='utf-8'))
    f.update(target_url='http://127.0.0.1:5081/',working_copy={'disposable':True,'never_reset':True,
        'source_fixture':'original.json','source_snapshot':{'tables':{}},'golden_sha256':'a'*64})
    f['database'].update(host_port=55433,name='sqbf_lab01_test',container='sqbf-lab01-test')
    f['oracle_expectations'].update(material_base='Kalkstein',material_origin='gebrochen')
    return f


class LabTests(unittest.TestCase):
    def test_only_verified_disposable_working_target(self):
        s=Scenario.load(PROFILE);f=fixture();validate_target(s,f)
        for update in ({'target_url':'http://127.0.0.1:5080/'},
                       {'working_copy':{'disposable':False}}, {'oracle_expectations':{}}):
            bad=copy.deepcopy(f);bad.update(update)
            with self.assertRaises(ReadOnlyViolation):validate_target(s,bad)
        for port in (5433,55432):
            bad=copy.deepcopy(f);bad['database']['host_port']=port
            with self.assertRaises(ReadOnlyViolation):validate_target(s,bad)

    def test_core_budget_unchanged_lab_budget_hard_bounded(self):
        for seconds,calls in ((301,12),(300,13)):
            with self.assertRaises(ValueError):Budget(seconds,calls)
        lab=LabBudget(1500,152);lab.calls=152
        with self.assertRaises(BudgetExceeded):lab.claim()
        for seconds,calls in ((1501,152),(1500,153)):
            with self.assertRaises(ValueError):LabBudget(seconds,calls)

    def test_no_unapproved_pages_origins_methods(self):
        origin='http://127.0.0.1:5081';policy=Scenario.load(PROFILE).read_only_policy
        for path in ('/','/products','/products/new','/products/11111111-1111-1111-1111-111111111111'):
            self.assertTrue(allowed_path(path))
            self.assertTrue(transport_allowed(origin+path,'GET',origin,policy))
        for path in ('/norms','/samples','/products/delete','/login'):
            self.assertFalse(allowed_path(path))
            self.assertFalse(transport_allowed(origin+path,'GET',origin,policy))
        for url,method in [('http://127.0.0.1:5080/products','GET'),(origin+'/api/products','POST'),(origin+'/products','DELETE')]:
            self.assertFalse(transport_allowed(url,method,origin,policy))

    def test_exact_field_values_single_save_and_keys(self):
        state={'target':{'kind':'save'},'focused':{'kind':'field','field':'Produktname'},'complete':True,'saved':False}
        allow_operation({'action':'click'},state)
        for field in ('complete','saved'):
            bad=copy.deepcopy(state);bad[field]=not bad[field]
            with self.assertRaises(ReadOnlyViolation):allow_operation({'action':'click'},bad)
        allow_operation({'action':'type','text':'STS 0–45'},state)
        for action in ({'action':'type','text':'different product'}, {'action':'key','key':'Enter'},
                       {'action':'key','key':'Tab'}, {'action':'key','key':'ControlOrMeta+R'}):
            with self.assertRaises(ReadOnlyViolation):allow_operation(action,state)
        self.assertEqual(LAB_ACTION_SCHEMA['properties']['key']['enum'],[None,*KEYS])

    def test_protected_hashes_detect_norm_changes_and_identity_switch(self):
        before={'docker':{'id':'one'},'identity':{'read_only':True},'tables':{'workspace_products':{'count':0,'hash':'a'},'norm_versions':{'count':15,'hash':'b'}}}
        after=copy.deepcopy(before);after['tables']['workspace_products']={'count':1,'hash':'c'}
        self.assertTrue(unchanged_except_product(before,after))
        after['tables']['norm_versions']['hash']='d'
        self.assertFalse(unchanged_except_product(before,after))
        after=copy.deepcopy(before);after['docker']['id']='two'
        self.assertFalse(unchanged_except_product(before,after))

    def test_browser_semantic_and_native_event_guard(self):
        from playwright.sync_api import sync_playwright
        # Entirely synthetic HTML. No network or application database.
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':800})
            page.route('**/*',lambda r:r.fulfill(content_type='text/html',body='''<button id="save">Speichern</button><button id="norm">Norm zuordnen</button>
            <div id="fields"></div><script>window.clicks=0;document.addEventListener('click',()=>window.clicks++);</script>'''))
            page.add_init_script(event_guard());page.goto('http://127.0.0.1:5081/products/new')
            page.evaluate('(fields)=>document.querySelector("#fields").innerHTML=Object.entries(fields).map(([label,value])=>`<div class="mud-input-control"><label>${label} *</label><input value="${value}"></div>`).join("")',FIELDS)
            def at(selector):
                box=page.locator(selector).bounding_box();return {'action':'click','x':box['x']+box['width']/2,'y':box['y']+box['height']/2}
            with self.assertRaises(ReadOnlyViolation):check_action(page,at('#norm'))
            page.locator('#norm').click();self.assertEqual(page.evaluate('window.clicks'),0)
            check_action(page,at('#save'));page.locator('#save').click();self.assertEqual(page.evaluate('window.clicks'),1)
            with self.assertRaises(ReadOnlyViolation):check_action(page,at('#save'))
            page.locator('#save').click();self.assertEqual(page.evaluate('window.clicks'),1)
            page.evaluate("history.pushState({},'', '/products/11111111-1111-1111-1111-111111111111')")
            with self.assertRaises(ReadOnlyViolation):check_action(page,at('#save'))
            browser.close()

    def test_provisioner_never_resets_or_reuses_and_waits_for_final_tcp(self):
        source=Path('projects/ble-elva/tools/working_fixture.py').read_text(encoding='utf-8')
        self.assertIn("'pg_isready','-h','127.0.0.1'",source)
        self.assertNotIn('DROP DATABASE',source)
        self.assertNotIn('docker\',\'rm',source)
        self.assertIn('create_private_file(directory/filename)',source)
        self.assertIn('ConnectionStrings__DevelopmentCloneConnection=connection',source)

    def test_explicit_synthetic_material_values_checked_by_oracle(self):
        from test_oracle import FIXTURE, snapshot
        from sqbf.oracle import verify_before,verify_after,OracleError
        f=copy.deepcopy(FIXTURE);f['oracle_expectations'].update(material_base='Kalkstein',material_origin='gebrochen')
        product={'id':'p','tenant_id':'tenant-1','plant_id':'plant-1','laboratory_id':None,
          'name':'STS 0–45','category':'Gemisch','material_class_id':'class-1','product_type_id':'type-1',
          'material_class_code':'unbound_mix','product_type_code':'sts','use_area':'Unbound','product_level':'mixture',
          'material_base':'Kalkstein','material_origin':'gebrochen','grain_lower_mm':0,'grain_upper_mm':45,
          'sieve_range_text':'0/45','product_group':'STS','technical_label':'STS 0/45','norm_limit_set_id':None,
          'product_norm_assignment_count':0,'is_active':True}
        baseline=verify_before(snapshot(),f);after=snapshot(product);after['counts']['products']=1
        verify_after(after,f,baseline)
        product['material_base']='Kies'
        with self.assertRaises(OracleError):verify_after(after,f,baseline)

    def test_rejected_model_action_stops_once_without_ui_or_model_retry(self):
        from dataclasses import asdict
        from unittest.mock import MagicMock
        from sqbf.bounded import model_spec
        from sqbf.providers import ChatGPTPlanCredential,ChatGPTPlanModel,CHATGPT_PLAN_SCOPE,ModelResponse
        from sqbf.reporting import Evidence
        browser_pilot=lab.browser_pilot
        model=ChatGPTPlanModel('gpt-6-luna',ChatGPTPlanCredential('canary',frozenset({CHATGPT_PLAN_SCOPE})),LAB_ACTION_SCHEMA)
        page=MagicMock();page.url='http://127.0.0.1:5081/products/new';page.screenshot.return_value=b'png'
        page.evaluate.return_value={'target':{'kind':'blocked'},'focused':{'kind':'blocked'},'complete':False,'saved':False}
        browser=MagicMock();browser.new_context.return_value.new_page.return_value=page
        playwright=MagicMock();playwright.__enter__.return_value.chromium.launch.return_value=browser
        def ask(model,prompt,png,budget):
            budget.claim();return ModelResponse({'action':'click','x':20,'y':20,'reason':'mock'}, {})
        with tempfile.TemporaryDirectory() as directory,patch('playwright.sync_api.sync_playwright',return_value=playwright), \
                patch.object(lab,'ask_bounded',side_effect=ask) as inference:
            folder=Path(directory)/'pilot';Evidence(folder)
            result=browser_pilot({'scenario':asdict(Scenario.load(PROFILE)),'executor':model_spec(model),'reviewer':model_spec(model),
                                  'seconds':10,'folder':str(folder),'storage_state':'private-session','headed':False})
            self.assertEqual(result['executor_status'],'BLOCKED_WRITE_SCOPE')
            self.assertEqual(inference.call_count,1);page.mouse.click.assert_not_called()
            self.assertEqual(result['model_calls'],1)
            self.assertTrue(any(e.get('error_code')=='LAB_ACTION_SCOPE_DENIED' for e in result['events']))

    def test_failed_worker_still_checks_protected_source_and_indexes_failure(self):
        run_lab=lab.run_lab
        from test_oracle import FIXTURE,snapshot as product_snapshot
        from sqbf.providers import ChatGPTPlanCredential,ChatGPTPlanModel,CHATGPT_PLAN_SCOPE
        f=fixture();f['fixture_data']=copy.deepcopy(FIXTURE['fixture_data']);f['oracle_expectations']=copy.deepcopy(FIXTURE['oracle_expectations'])
        f['oracle_expectations'].update(material_base='Kalkstein',material_origin='gebrochen')
        protected={'docker':{'id':'original'},'identity':{},'tables':{'workspace_products':{'count':0,'hash':'a'}}}
        f['working_copy']['source_snapshot']=protected
        target=copy.deepcopy(protected);target['docker']['id']='working'
        product=product_snapshot();product['database']=f['database']['name']
        model=ChatGPTPlanModel('gpt-6-luna',ChatGPTPlanCredential('canary',frozenset({CHATGPT_PLAN_SCOPE})),LAB_ACTION_SCHEMA)
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'source.json';source.write_text(Path('projects/ble-elva/fixtures/enzberg-product-core-v0.2.json').read_text(encoding='utf-8'),encoding='utf-8');f['working_copy']['source_fixture']=str(source)
            manifest=base/'fixture.json';manifest.write_text(json.dumps(f));runs=base/'runs'
            with patch.object(lab,'snapshot',side_effect=[protected,target,protected,target]) as reads, \
                    patch.object(lab,'runner_identity',return_value='verified-commit'), \
                    patch.object(lab,'oracle_dsn',return_value='secret-canary'), \
                    patch.object(lab,'collect_snapshot',return_value=product), \
                    patch.object(lab,'invoke_worker',side_effect=BudgetExceeded()) as worker:
                folder=run_lab(Scenario.load(PROFILE),model,model,runs,'private-session',False,manifest)
                result=json.loads((folder/'run.json').read_text())
                self.assertEqual(worker.call_count,1);self.assertEqual(reads.call_count,4)
                self.assertEqual(result['verdict'],'NO-GO');self.assertTrue(result['oracle']['source_unchanged'])
                self.assertEqual(result['oracle']['status'],'FAIL')
                self.assertTrue((runs/'index.jsonl').exists())
                self.assertNotIn('secret-canary',(folder/'run.json').read_text())
                payload=worker.call_args.args[1]
                self.assertNotIn('fixture',payload);self.assertNotIn('oracle_credential_file',json.dumps(payload))

    def test_arbitrary_profile_and_unprotected_source_are_denied(self):
        with self.assertRaises(ValueError):load_write_profile('malicious.module','lab_runner')
        with self.assertRaises(ValueError):load_write_profile('LAB-01-SINGLE-PRODUCT-v1','os')
        source=json.loads(Path('projects/ble-elva/fixtures/enzberg-product-core-v0.2.json').read_text(encoding='utf-8'))
        guard.validate_source(source)
        source['database']['host_port']=5433
        with self.assertRaises(ReadOnlyViolation):guard.validate_source(source)

    def test_restart_changed_build_blocks_before_password_or_process(self):
        module=load_write_profile('LAB-01-SINGLE-PRODUCT-v1','working_fixture')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);f=fixture();f['working_copy']['runtime']={'sha256':'a'*64}
            f['identity_scope_check']={'executable':'app.exe','assembly':'app.dll'}
            (root/'app.dll').write_bytes(b'changed-build');manifest=root/'fixture.json';manifest.write_text(json.dumps(f))
            with patch.object(module,'verify_docker_identity'), \
                    patch.object(module,'load_credentials') as credentials, \
                    patch.object(module.subprocess,'Popen') as start:
                with self.assertRaises(ValueError):module.start_working_web(manifest,root)
                credentials.assert_not_called();start.assert_not_called()

    def test_review_evidence_stays_within_existing_image_limit(self):
        images=[bytes([i]) for i in range(20)]
        for count in range(20):
            selection=lab.review_images(images,images[:count])
            self.assertLessEqual(len(selection),3)
            self.assertTrue(all(png in images for png in selection))

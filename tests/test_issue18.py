from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from sqbf.artifact_privacy import ArtifactPrivacyError, check_private_directory
from sqbf.bounded import model_spec
from sqbf.models import Scenario, SEARCH_KEYS, SAFE_KEYS, validate_action, ActionValidationError
from sqbf.providers import ChatGPTPlanCredential, ChatGPTPlanModel, ModelResponse, CHATGPT_PLAN_SCOPE
from sqbf.read_only import allow_operation, ReadOnlyViolation
from sqbf.reporting import Evidence
from sqbf.smoke_runner import ACTION_SCHEMA, INSTRUCTIONS, browser_pilot, decision_metadata, run_smoke


class Issue18Tests(unittest.TestCase):
    def model(self):
        return ChatGPTPlanModel('synthetic',ChatGPTPlanCredential('secret-canary',frozenset({CHATGPT_PLAN_SCOPE})),ACTION_SCHEMA)

    def replay(self, invalid=True, timeout=False):
        scenario=Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json')
        page=MagicMock();page.url=scenario.url;page.screenshot.return_value=b'synthetic-image'
        page.evaluate.return_value={'target':'search','focused':True}
        browser=MagicMock();browser.new_context.return_value.new_page.return_value=page
        manager=MagicMock();manager.__enter__.return_value.chromium.launch.return_value=browser
        clock=[100.0];turn=[0]
        page.wait_for_timeout.side_effect=lambda ms: clock.__setitem__(0,clock[0]+ms/1000)
        def ask(model,prompt,images,budget):
            budget.claim();turn[0]+=1;clock[0]+=2
            if timeout:
                from sqbf.bounded import BudgetExceeded
                raise BudgetExceeded('secret-canary')
            if turn[0]<=4: data={'action':'click','x':20,'y':20}
            elif invalid: data={'action':'key','key':'Control+A','text':'secret-canary','reason':'secret-canary'}
            elif turn[0]==5: data={'action':'key','key':'ControlOrMeta+A'}
            elif turn[0]==6: data={'action':'key','key':'Backspace'}
            elif turn[0]==7: data={'action':'done','reason':'synthetic complete'}
            else: data={'verdict':'PASS','reason':'synthetic review','findings':[],
                        'scores':dict(findability=4,clarity=4,task_progress=4,error_recovery=4)}
            return ModelResponse(data,{'total_tokens':1})
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)/'run';Evidence(folder)
            with patch('playwright.sync_api.sync_playwright',return_value=manager), \
                 patch('sqbf.smoke_runner.ask_bounded',side_effect=ask) as calls, \
                 patch('sqbf.smoke_runner.observation',return_value={'query_visible':True,'empty_visible':True}), \
                 patch('sqbf.smoke_runner.time.monotonic',side_effect=lambda:clock[0]):
                result=browser_pilot({'scenario':asdict(scenario),'executor':model_spec(self.model()),
                    'reviewer':model_spec(self.model()),'seconds':100,'folder':str(folder),
                    'storage_state':'synthetic-only','headed':False})
            all_files=''.join(path.read_text(errors='replace') for path in folder.glob('*.json'))
            self.assertNotIn('secret-canary',all_files)
            return result,page,calls.call_count

    def test_fifth_action_rejection_retained_without_dispatch_retry_or_review(self):
        result,page,calls=self.replay()
        self.assertEqual(result['actions'],4);self.assertEqual(calls,5)
        self.assertEqual(page.mouse.click.call_count,4)
        page.keyboard.press.assert_not_called()
        self.assertIsNone(result['review'])
        rejected=next(e for e in result['events'] if e['kind']=='action_rejected')
        self.assertEqual(rejected['turn'],5)
        self.assertEqual(rejected['error_code'],'KEY_NOT_ALLOWED')
        self.assertEqual(rejected['key'],'REDACTED')
        self.assertNotIn('reason',rejected);self.assertNotIn('text',rejected)
        self.assertEqual(result['model_wait_seconds'],10)
        self.assertAlmostEqual(result['wall_seconds'],12.6)

    def test_canonical_keys_work_with_same_guards_and_reviewer_timing(self):
        result,page,calls=self.replay(invalid=False)
        self.assertEqual(result['executor_status'],'DONE');self.assertEqual(calls,8)
        self.assertEqual([x.args[0] for x in page.keyboard.press.call_args_list],['ControlOrMeta+A','Backspace'])
        self.assertEqual(result['model_wait_seconds'],16)
        self.assertEqual(sum(e['duration_seconds'] for e in result['events'] if e['kind']=='model_call_finished'),16)

    def test_timeout_wait_measured_and_exception_text_redacted(self):
        result,page,calls=self.replay(timeout=True)
        self.assertEqual(calls,1);self.assertEqual(result['model_wait_seconds'],2)
        self.assertEqual(result['executor_status'],'BLOCKED_TIMEOUT')
        page.mouse.click.assert_not_called()

    def test_schema_prompt_validator_guard_agree_no_alias_expansion(self):
        self.assertEqual(ACTION_SCHEMA['properties']['key']['enum'],[None,*SEARCH_KEYS])
        self.assertTrue(set(SEARCH_KEYS)<=SAFE_KEYS)
        policy=Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json').read_only_policy
        for key in SEARCH_KEYS:
            self.assertIn(key,INSTRUCTIONS)
            action={'action':'key','key':key};validate_action(action,1280,800)
            allow_operation(action,'search',True,policy)
            with self.assertRaises(ReadOnlyViolation):allow_operation(action,'search',False,policy)
        for key in ['Control+A','Ctrl+A','ControlOrMeta+A Backspace','secret-canary']:
            with self.assertRaises(ActionValidationError):validate_action({'action':'key','key':key},1280,800)

    def test_metadata_never_contains_arbitrary_action_or_key(self):
        self.assertEqual(decision_metadata({'action':'secret-canary','key':'secret-canary','reason':'secret-canary'}),
                         {'action':'REDACTED','key':'REDACTED'})

    def test_privacy_failure_before_any_artifact_or_model_or_oracle(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)/'blocked'
            with patch('sqbf.reporting.check_private_directory',side_effect=ArtifactPrivacyError()), \
                 patch('sqbf.smoke_runner.snapshot') as oracle,patch('sqbf.smoke_runner.invoke_worker') as worker:
                scenario=Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json')
                with self.assertRaises(ArtifactPrivacyError):
                    run_smoke(scenario,self.model(),self.model(),folder,'local',False,
                              'projects/ble-elva/fixtures/enzberg-product-core-v0.2.json')
                oracle.assert_not_called();worker.assert_not_called()
                self.assertFalse(any(p.is_file() for p in folder.glob('**/*'))) # empty reserved directories only

    def test_real_artifact_directory_acl_checked_before_first_write(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence=Evidence(Path(directory)/'run')
            check_private_directory(evidence.path)
            self.assertEqual(list(evidence.path.iterdir()),[])
            evidence.snapshot(b'synthetic','first')
            if os.name=='nt':
                from sqbf.artifact_privacy import _windows_directory
                # Read-only directory ACL verification plus inheritance applies
                # to files; separately inspect child permissions below.
                script=r"$ErrorActionPreference='Stop'; $p=[Console]::In.ReadToEnd(); $sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; foreach($r in (Get-Acl -LiteralPath $p).Access){if($r.AccessControlType -eq 'Allow' -and $r.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -ne $sid){exit 2}}"
                import subprocess
                subprocess.run(['powershell.exe','-NoProfile','-Command',script],input=str(evidence.path/'000-first.png'),
                  text=True,capture_output=True,check=True,env={k:v for k,v in os.environ.items() if k.lower()!='psmodulepath'})

    def test_report_unknown_durations_are_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            e=Evidence(Path(directory)/'run')
            manifest={'run_id':'r','scenario_id':'s','persona':'p','executor_model':'mock','fixture_id':'f',
                      'software_version':'v','executor_status':'ERROR','actions':0,'budget_actions':10,'wall_seconds':9}
            e.finish(manifest,None,'NO-GO')
            report=(e.path/'report.md').read_text()
            self.assertIn('Modellwartezeit: nicht gemessen',report)
            self.assertIn('Aktive Runnerzeit (ohne Modellwartezeit): nicht gemessen',report)

    def test_parent_report_aggregates_measured_model_wait_and_active_time(self):
        import hashlib
        from sqbf.providers import ModelResponse
        with tempfile.TemporaryDirectory() as directory:
            clock=[100.0]
            def snapshot_mock(fixture):
                clock[0]+=1
                return {'immutable':True}
            def worker(mode,payload,timeout):
                clock[0]+=12
                images=[]
                for i in range(2):
                    name=f'{i}.png';png=b'synthetic';(Path(payload['folder'])/name).write_bytes(png)
                    images.append({'name':name,'sha256':hashlib.sha256(png).hexdigest()})
                return {'events':[],'images':images,'executor_status':'DONE','actions':4,'model_calls':5,
                        'model_wait_seconds':10,'timing_complete':True,
                        'review':{'verdict':'PASS','scores':{},'findings':[]},
                        'observations':[{'query_visible':True,'empty_visible':True},
                          {'target_page':True,'filter_cleared':True,'empty_visible':True}]}
            with patch('sqbf.smoke_runner.snapshot',side_effect=snapshot_mock), \
                 patch('sqbf.smoke_runner.invoke_worker',side_effect=worker), \
                 patch('sqbf.smoke_runner.time.monotonic',side_effect=lambda:clock[0]):
                folder=run_smoke(Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json'),self.model(),self.model(),
                    Path(directory),'synthetic-state',False,'projects/ble-elva/fixtures/enzberg-product-core-v0.2.json')
            manifest=json.loads((folder/'run.json').read_text())
            self.assertEqual(manifest['model_wait_seconds'],10)
            self.assertEqual(manifest['wall_seconds'],14)
            self.assertEqual(manifest['active_seconds_excluding_model_wait'],4)
            self.assertIn('Modellwartezeit: 10.0 Sekunden',(folder/'report.md').read_text())

    def test_hard_worker_abort_reports_partial_timings_as_unknown(self):
        from sqbf.bounded import BudgetExceeded
        with tempfile.TemporaryDirectory() as directory:
            def abort(mode,payload,timeout):
                evidence=Evidence.attach(payload['folder'])
                evidence.event('model_call_finished',stage='executor',duration_seconds=2)
                evidence.event('model_call_started',stage='executor')
                raise BudgetExceeded('synthetic stop')
            with patch('sqbf.smoke_runner.snapshot',return_value={'immutable':True}), \
                 patch('sqbf.smoke_runner.invoke_worker',side_effect=abort) as worker:
                folder=run_smoke(Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json'),self.model(),self.model(),
                    Path(directory),'synthetic-state',False,'projects/ble-elva/fixtures/enzberg-product-core-v0.2.json')
            manifest=json.loads((folder/'run.json').read_text())
            self.assertIsNone(manifest['model_wait_seconds'])
            self.assertIsNone(manifest['active_seconds_excluding_model_wait'])
            self.assertEqual(manifest['measured_model_wait_seconds'],2)
            self.assertFalse(manifest['timing_complete']);self.assertEqual(worker.call_count,1)

    def test_worker_rejects_unprotected_directory_before_model_or_browser(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('sqbf.reporting.check_private_directory',side_effect=ArtifactPrivacyError()), \
             patch('playwright.sync_api.sync_playwright') as browser, \
             patch('sqbf.smoke_runner.ask_bounded') as model:
            scenario=Scenario.load('projects/ble-elva/scenarios/core-smoke-01.json')
            with self.assertRaises(ArtifactPrivacyError):
                browser_pilot({'scenario':asdict(scenario),'executor':model_spec(self.model()),'reviewer':model_spec(self.model()),
                    'seconds':100,'folder':directory,'storage_state':'synthetic-only','headed':False})
            browser.assert_not_called();model.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_registry_reserves_private_file_before_content_and_replacement(self):
        from sqbf.reporting import index_run
        from sqbf.artifact_privacy import create_private_file, _windows_directory
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'run';folder.mkdir()
            (folder/'run.json').write_text(json.dumps({'run_id':'r','scenario_id':'s','software_version':'v',
              'started_at':'today','persona':'synthetic','executor_model':'mock','verdict':'NO-GO'}))
            reserved=[]
            def reserve(path):
                create_private_file(path)
                self.assertEqual(path.read_bytes(),b'')
                if os.name=='nt':_windows_directory(path,False,inherit=False)
                reserved.append(path)
            with patch('sqbf.reporting.create_private_file',side_effect=reserve):
                index_run(root,folder)
            self.assertEqual(len(reserved),1)
            self.assertFalse(reserved[0].exists())
            self.assertTrue((root/'index.jsonl').exists())
            if os.name=='nt':_windows_directory(root/'index.jsonl',False,inherit=False)

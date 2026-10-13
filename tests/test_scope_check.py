import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from sqbf.scope_check import check_scope, evaluate


FIXTURE=Path('projects/ble-elva/fixtures/enzberg-product-core-v0.2.json')


class ScopeCheckTests(unittest.TestCase):
    def setUp(self):
        self.fixture=json.loads(FIXTURE.read_text(encoding='utf-8-sig'))
        f=self.fixture['fixture_data']
        self.ticket={'valid':True,'username':f['laboratory_lead_account'],'user_id':f['laboratory_lead_user_id']}
        self.scope={'database':self.fixture['database']['name'],'role':self.fixture['database']['bootstrap_user'],
                    'read_only':'on','users':1,'user_id':f['laboratory_lead_user_id'],
                    'username':f['laboratory_lead_account'],'active':True,'admin':False,'tenant_id':f['tenant_id'],
                    'tenant_active':True,'laboratory_role':True,'product_permission':True,'plant_valid':True,
                    'expected_plant_scopes':1,'plant_scopes':1,'global_scopes':0,'tenant_scopes':1,'all_scopes':2}

    def test_valid_laboratory_lead_passes(self):
        self.assertEqual(evaluate(self.ticket,self.scope,self.fixture)['status'],'SCOPE_VERIFIED')

    def test_wrong_user_and_tenant_block(self):
        for key,value in [('username','other'),('user_id','other'),('users',2),('tenant_id','other'),('tenant_active',False),('active',False)]:
            with self.subTest(key=key):
                s=dict(self.scope,**{key:value})
                self.assertEqual(evaluate(self.ticket,s,self.fixture)['status'],'BLOCKED_SCOPE_VERIFICATION')

    def test_missing_role_and_permission_block(self):
        for key in ('laboratory_role','product_permission'):
            self.assertEqual(evaluate(self.ticket,dict(self.scope,**{key:False}),self.fixture)['status'],'BLOCKED_SCOPE_VERIFICATION')

    def test_wrong_extra_or_other_scope_blocks(self):
        for key,value in [('plant_valid',False),('expected_plant_scopes',0),('plant_scopes',2),('tenant_scopes',0),('all_scopes',3)]:
            self.assertEqual(evaluate(self.ticket,dict(self.scope,**{key:value}),self.fixture)['status'],'BLOCKED_SCOPE_VERIFICATION')

    def test_global_or_admin_blocks(self):
        for key,value in [('global_scopes',1),('admin',True)]:
            self.assertEqual(evaluate(self.ticket,dict(self.scope,**{key:value}),self.fixture)['status'],'BLOCKED_SCOPE_VERIFICATION')

    def test_invalid_or_mismatched_signed_ticket_blocks(self):
        for key,value in [('valid',False),('username','other'),('user_id','other')]:
            self.assertEqual(evaluate(dict(self.ticket,**{key:value}),self.scope,self.fixture)['status'],'BLOCKED_SCOPE_VERIFICATION')

    def test_wrong_db_role_or_writable_transaction_blocks(self):
        for key,value in [('database','production'),('role','unexpected'),('read_only','off')]:
            self.assertEqual(evaluate(self.ticket,dict(self.scope,**{key:value}),self.fixture)['status'],'BLOCKED_SCOPE_VERIFICATION')

    def invoke(self, run=None, session_status='SESSION_RESTORED', fixture=None):
        run=run or Mock(side_effect=[subprocess.CompletedProcess([],0,json.dumps(self.ticket)),
                                   subprocess.CompletedProcess([],0,json.dumps(self.scope))])
        session=Mock(return_value={'status':session_status})
        runtime=Mock(return_value={'pid':1,'assembly':'mock','sha256':'hash'})
        with tempfile.TemporaryDirectory() as d:
            verifier=Path(d)/'verifier.dll'; verifier.touch()
            with patch('sqbf.scope_check.verify_docker_identity',return_value={'container_id':'verified-id'}):
                result=check_scope(self.fixture['target_url'],'private-session.json',{},fixture or self.fixture,
                                   'application-root',verifier,run=run,session_fn=session,runtime_fn=runtime)
        return result,run

    def test_one_explicit_controller_read_no_retry_no_secret_output(self):
        self.scope['password_hash']='SECRET_CANARY'
        self.ticket['cookie']='SECRET_CANARY'
        result,run=self.invoke()
        self.assertEqual(result['status'],'SCOPE_VERIFIED')
        self.assertEqual(run.call_count,2)
        command=run.call_args.args[0]
        self.assertIn('verified-id',command)
        self.assertIn('ble_benchmark',command)
        self.assertNotIn('sqbf_oracle_ro',command)
        self.assertNotIn('SECRET_CANARY',json.dumps(result))
        sql=run.call_args.kwargs['input']
        self.assertTrue(sql.startswith('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;'))
        self.assertTrue(sql.rstrip().endswith('ROLLBACK;'))
        self.assertFalse(any(word in sql.lower() for word in ('password','security_stamp','token','insert ','update ','delete ','grant ','alter ','create ')))

    def test_missing_read_privilege_is_sanitized_no_retry(self):
        run=Mock(side_effect=[subprocess.CompletedProcess([],0,json.dumps(self.ticket)),
                             subprocess.CalledProcessError(3,[],stderr='SECRET_CANARY')])
        result,run=self.invoke(run)
        self.assertEqual(result['status'],'BLOCKED_SCOPE_VERIFICATION')
        self.assertEqual(result['reason'],'EVIDENCE_UNAVAILABLE')
        self.assertEqual(run.call_count,2)
        self.assertNotIn('SECRET_CANARY',json.dumps(result))

    def test_invalid_restored_session_never_reads_ticket_or_db(self):
        result,run=self.invoke(session_status='BLOCKED_SESSION')
        self.assertEqual(result['reason'],'SESSION_INVALID')
        run.assert_not_called()

    def test_failed_signature_never_queries_db(self):
        result,run=self.invoke(Mock(side_effect=subprocess.CalledProcessError(2,[])))
        self.assertEqual(result['status'],'BLOCKED_SCOPE_VERIFICATION')
        self.assertEqual(run.call_count,1)

    def test_projection_changes_fail_before_sql(self):
        f=copy.deepcopy(self.fixture);f['identity_scope_check']['projection_sha256']='wrong'
        result,run=self.invoke(fixture=f)
        self.assertEqual(result['reason'],'PROJECTION_MISMATCH')
        self.assertEqual(run.call_count,1)

    def test_no_implicit_or_unverified_privileged_fallback(self):
        f=copy.deepcopy(self.fixture);f['identity_scope_check']['role']='postgres'
        result,run=self.invoke(fixture=f)
        self.assertEqual(result['status'],'BLOCKED_SCOPE_VERIFICATION')
        run.assert_not_called()

    def test_missing_config_blocks_without_side_effects(self):
        run=Mock()
        result=check_scope(self.fixture['target_url'],'private-session',{},self.fixture,None,None,run=run)
        self.assertEqual(result['reason'],'CONFIGURATION_MISSING')
        run.assert_not_called()

    def test_cli_gate_failure_prevents_oauth_models_and_runner(self):
        from sqbf.cli import main
        with tempfile.TemporaryDirectory() as d, patch('builtins.print'), \
             patch('sqbf.session_check.check_session',return_value={'status':'SESSION_RESTORED'}), \
             patch('sqbf.scope_check.check_scope',return_value={'status':'BLOCKED_SCOPE_VERIFICATION'}), \
             patch('sqbf.plan_login.authorize') as auth, patch('sqbf.bounded.invoke_worker') as worker, \
             patch('sqbf.cli.run') as runner:
            session=Path(d)/'state.json';session.write_text('{}')
            status=main(['run','--scenario','projects/ble-elva/scenarios/core-smoke-01.json',
                         '--url',self.fixture['target_url'],'--software-version','mock','--fixture-ready',
                         '--executor-provider','chatgpt_plan','--executor-model','gpt-6-luna',
                         '--analyst-provider','chatgpt_plan','--analyst-model','gpt-6.1-sol',
                         '--storage-state',str(session)])
            self.assertEqual(status,2)
            auth.assert_not_called();worker.assert_not_called();runner.assert_not_called()

    def test_model_serialization_contains_no_scope_controller_fields(self):
        from sqbf.bounded import model_spec
        from sqbf.providers import ChatGPTPlanCredential,ChatGPTPlanModel,CHATGPT_PLAN_SCOPE
        from sqbf.smoke_runner import ACTION_SCHEMA
        spec=model_spec(ChatGPTPlanModel('mock',ChatGPTPlanCredential('mock',frozenset([CHATGPT_PLAN_SCOPE])),ACTION_SCHEMA))
        for forbidden in ('fixture_data','identity_scope_check','application_root','verifier','user_id','database','storage_state'):
            self.assertNotIn(forbidden,spec)

    def test_isolation_failure_prevents_all_followup(self):
        run=Mock();runtime=Mock();session=Mock()
        with patch('sqbf.scope_check.verify_docker_identity',side_effect=RuntimeError('SECRET_CANARY')):
            result=check_scope(self.fixture['target_url'],'state',{},self.fixture,'root','verifier',
                               run=run,session_fn=session,runtime_fn=runtime)
        self.assertEqual(result['status'],'BLOCKED_SCOPE_VERIFICATION')
        run.assert_not_called();runtime.assert_not_called();session.assert_not_called()
        self.assertNotIn('SECRET_CANARY',json.dumps(result))

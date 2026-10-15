import copy
import importlib
import unittest
from uuid import UUID
from test_suite_fixture import owned_fixture

module = importlib.import_module('projects.ble-elva.tools.receipt_oracle')


def data():
    f = owned_fixture(); f['fixture_data'].update(customer_id=str(UUID(int=900)),project_id=str(UUID(int=901)))
    f['suite_copy']['mapping'] = {'plan_id':str(UUID(int=902)),'positions':{}}
    d = {'reference':{'sampling_date':'2026-05-08'},'positions':[]}
    records = {'samples':[],'lims':[],'plan_items':[]}
    for i in range(1,11):
        key='P'+str(i);product=str(UUID(int=100+i));item=str(UUID(int=200+i));probe=str(UUID(int=300+i))
        f['suite_copy']['mapping']['positions'][key]=product
        d['positions'].append({'position_id':key,'inputs':{'sample_code':'SYNTHETIC-'+str(i)}})
        records['plan_items'].append({'id':item,'product_id':product,'plan_id':f['suite_copy']['mapping']['plan_id']})
        records['samples'].append({'id':probe,'sample_code':'SYNTHETIC-'+str(i),
            'tenant_id':f['fixture_data']['tenant_id'],'plant_id':f['fixture_data']['plant_id'],
            'laboratory_id':None,'product_id':product,'customer_id':f['fixture_data']['customer_id'],
            'project_id':f['fixture_data']['project_id'],'taken_date':'2026-05-08','sampling_plan_item_id':item})
        records['lims'].append({'id':str(UUID(int=400+i)),'probe_id':probe,'product_id':product,
                               'project_id':f['fixture_data']['project_id']})
    return records,d,f


class ReceiptOracleTests(unittest.TestCase):
    def test_plan_receipt_does_not_invent_immediate_lims_or_require_it_for_plain_samples(self):
        records,d,f=data();records['lims']=[]
        self.assertEqual(module.verify_receipts(records,d,f,phase='after_plan')['status'],'PASS')
        self.assertEqual(module.verify_receipts(records,d,f,phase='after_modules')['status'],'PASS')
        self.assertEqual(module.verify_receipts(records,d,f,phase='after')['status'],'FAIL')
        d['positions'][0]['inputs']['derived_and_repetitions']=[{'series':[{'initial_g':200}]}]
        result=module.verify_receipts(records,d,f,phase='after_modules')
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['mismatched_positions'],['P1'])
    def test_empty_start_and_ten_independently_linked_samples(self):
        records,d,f=data()
        self.assertEqual(module.verify_receipts(records,d,f,phase='after')['status'],'PASS')
        records['samples']=[];records['lims']=[]
        self.assertEqual(module.verify_receipts(records,d,f,phase='before')['status'],'RECEIPT_START_VERIFIED')
        self.assertEqual(module.verify_receipts(records,d,f,phase='after')['status'],'FAIL')

    def test_wrong_tenant_plant_product_customer_project_date_or_plan_link_fail(self):
        for key in ('tenant_id','plant_id','product_id','customer_id','project_id','taken_date','sampling_plan_item_id'):
            records,d,f=data();records['samples'][0][key]='wrong'
            r=module.verify_receipts(records,d,f,phase='after')
            self.assertEqual(r['status'],'FAIL');self.assertEqual(r['mismatched_positions'],['P1'])

    def test_correct_probe_vs_lims_fk_is_required(self):
        records,d,f=data();records['lims'][0]['probe_id']=records['lims'][0]['id']
        result=module.verify_receipts(records,d,f,phase='after')
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['orphan_lims'])

    def test_missing_extra_duplicate_and_no_normative_claim(self):
        for change in ('missing','extra','duplicate'):
            records,d,f=data()
            if change=='missing':records['samples'].pop()
            else:
                row=copy.deepcopy(records['samples'][0]);records['samples'].append(row)
                if change=='extra':row['sample_code']='UNEXPECTED'
            self.assertEqual(module.verify_receipts(records,d,f,phase='after')['status'],'FAIL')
        records,d,f=data()
        result=module.verify_receipts(records,d,f,phase='after')
        self.assertEqual(result['database_writes'],0);self.assertEqual(result['model_calls'],0)
        self.assertIn('No normative certification',result['limitations'][0])

    def test_invalid_read_projection_controlled_block(self):
        records,d,f=data();del records['samples'][0]['tenant_id']
        self.assertEqual(module.verify_receipts(records,d,f,phase='after')['status'],'BLOCKED_RECEIPT_EVIDENCE')


def plan_rows(f):
    return [{'product_id':product,'is_active':True,'use_area_set':True,'product_level_set':True,'owner_ok':True,
             'standard_assignments':2} for product in f['suite_copy']['mapping']['positions'].values()]


class PlanProductPreconditionTests(unittest.TestCase):
    def test_every_plan_product_must_be_one_ble_can_carry_a_sample_for(self):
        _,_,f=data();rows=plan_rows(f)
        ok=module.verify_plan_products(rows,f)
        self.assertEqual((ok['status'],ok['positions_checked'],ok['blocked_positions']),('PLAN_PRODUCTS_CREATABLE',10,[]))
        for column,value,reason in (('is_active',False,'PRODUCT_INACTIVE'),('use_area_set',False,'USE_AREA_MISSING'),
                                    ('product_level_set',False,'PRODUCT_LEVEL_MISSING'),('owner_ok',False,'OWNER_SCOPE_MISMATCH'),
                                    ('standard_assignments',0,'NO_STANDARD_ASSIGNMENT')):
            rows=plan_rows(f);rows[5][column]=value
            blocked=module.verify_plan_products(rows,f)
            self.assertEqual(blocked['status'],'PLAN_PRODUCTS_BLOCKED')
            self.assertEqual(blocked['blocked_positions'],[{'position_id':'P6','reasons':[reason]}])
        rows=plan_rows(f);rows[1]['is_active']=False;rows[1]['use_area_set']=False
        self.assertEqual(module.verify_plan_products(rows,f)['blocked_positions'],
                         [{'position_id':'P2','reasons':['PRODUCT_INACTIVE','USE_AREA_MISSING']}])

    def test_missing_duplicate_or_malformed_rows_block_instead_of_passing(self):
        _,_,f=data()
        for rows in (plan_rows(f)[:-1],plan_rows(f)*2,[{'product_id':'x'}]):
            self.assertEqual(module.verify_plan_products(rows,f)['status'],'BLOCKED_PLAN_PRODUCT_EVIDENCE')
        rows=plan_rows(f)+[dict(plan_rows(f)[0],product_id=str(UUID(int=777)))]
        self.assertEqual(module.verify_plan_products(rows,f)['reason'],'UNEXPECTED_PLAN_PRODUCT_COUNT')
        self.assertEqual(module.verify_plan_products(plan_rows(f)[:-1],f)['reason'],'PLAN_PRODUCT_MISSING')

    def test_collector_uses_the_select_only_role_and_returns_flags_without_names(self):
        import json
        from unittest.mock import patch
        _,_,f=data();f['fixture_data'].update(tenant_id=str(UUID(int=1)),plant_id=str(UUID(int=2)))
        calls=[]
        def run(command,**kwargs):
            calls.append((command,kwargs['input']))
            identity=json.dumps({'database':f['database']['name'],'role':f['database']['oracle_role'],'read_only':'on'})
            from subprocess import CompletedProcess
            return CompletedProcess(command,0,stdout=identity+'\n'+json.dumps(plan_rows(f))+'\n')
        with patch.object(module,'verify_docker_identity',return_value={'container_id':'c'*64}):
            rows=module.collect_plan_products(f,run=run)
        command,sql=calls[0]
        self.assertIn(f['database']['oracle_role'],command);self.assertIn('READ ONLY',sql);self.assertNotIn('p.name',sql)
        self.assertNotRegex(sql,r'(?i)\b(insert|update|delete)\b');self.assertIn(str(UUID(int=2)),sql);self.assertEqual(len(rows),10)
        def wrong_role(command,**kwargs):
            from subprocess import CompletedProcess
            return CompletedProcess(command,0,stdout=json.dumps({'database':'x','role':'y','read_only':'off'})+'\n[]\n')
        with patch.object(module,'verify_docker_identity',return_value={'container_id':'c'*64}):
            with self.assertRaises(ValueError):module.collect_plan_products(f,run=wrong_role)

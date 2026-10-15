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

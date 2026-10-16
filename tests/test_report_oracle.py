import copy
import importlib
import unittest
from uuid import UUID
from sqbf.suites import canonical_hash
from test_measurement_oracle import inputs

module=importlib.import_module('projects.ble-elva.tools.report_oracle')


def reports():
    fixture,projection,_=inputs();records=[];receipts={'samples':[]};downloads=[]
    for i,position in enumerate(projection['positions']):
        position['product']='Synthetic stone '+str(i)
        probe=str(UUID(int=500+i));report=str(UUID(int=600+i))
        receipts['samples'].append({'id':probe,'sample_code':position['sample_code'],
            'product_id':fixture['suite_copy']['mapping']['positions'][position['position_id']],
            'tenant_id':fixture['fixture_data']['tenant_id'],'plant_id':fixture['fixture_data']['plant_id']})
        snapshot={'probe_id':probe,'sample_code':position['sample_code'],'product':position['product'],'plant':'Enzberg','is_official':False}
        snapshot.update({k:float(v) for k,v in module.expected_numbers(position).items()})
        records.append({'id':report,'probe_id':probe,'tenant_id':fixture['fixture_data']['tenant_id'],
            'plant_id':fixture['fixture_data']['plant_id'],'laboratory_id':None,'is_official':False,'status':'DRAFT','snapshot':snapshot})  # BLE persists 'DRAFT'
        downloads.append({'report_id':report,'pdf_integrity':'PASS'})
    fixture['suite_copy']['measurement_reference_sha256']=canonical_hash(projection)
    return fixture,projection,records,receipts,downloads


class ReportOracleTests(unittest.TestCase):
    def test_independent_non_official_snapshot_and_actual_pdf_evidence_required(self):
        f,p,r,probes,pdfs=reports()
        result=module.verify_reports(r,probes,p,f,pdfs)
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['normative_release'])
        self.assertEqual(module.verify_reports(r,probes,p,f,[])['status'],'FAIL')
        self.assertEqual(module.verify_reports(r[:-1],probes,p,f,pdfs)['status'],'FAIL')

    def test_wrong_owner_identity_numeric_fields_or_official_report_never_pass(self):
        for column,value in [('tenant_id','wrong'),('plant_id','wrong'),('is_official',True)]:
            f,p,r,probes,pdfs=reports();r[0][column]=value
            self.assertEqual(module.verify_reports(r,probes,p,f,pdfs)['status'],'FAIL')
        for column,value in [('sample_code','OTHER'),('dry_g',0),('sand_a_mm',9.5)]:
            f,p,r,probes,pdfs=reports();r[0]['snapshot'][column]=value
            self.assertEqual(module.verify_reports(r,probes,p,f,pdfs)['status'],'FAIL')

    def test_draft_status_is_recognized_as_persisted_by_ble_and_no_other_status_is_a_draft(self):
        # Dry run 15.10.2026: BLE stores 'DRAFT'; an exact 'Draft' comparison rejected every report of the suite.
        for status in ('DRAFT','Draft','draft',' DRAFT '):
            f,p,r,probes,pdfs=reports();r[0]['status']=status
            self.assertEqual(module.verify_reports(r,probes,p,f,pdfs)['status'],'PASS',status)
        for status in ('FINAL','Released','APPROVED','ISSUED','',None,'DRAFTED'):
            f,p,r,probes,pdfs=reports();r[0]['status']=status
            result=module.verify_reports(r,probes,p,f,pdfs)
            self.assertEqual(result['status'],'FAIL',status);self.assertFalse(result['positions'][0]['relations_valid'])
        self.assertTrue(module.is_draft('DRAFT'));self.assertFalse(module.is_draft(1))

    def test_half_entered_measurements_give_no_expectation_instead_of_blocking_the_whole_report_stage(self):
        # Guarded dry run 16.10.2026: one shape fraction with a missing value raised TypeError and made REPORT BLOCKED, which stops the suite.
        position={'measurements':{'sieves':[{'input_g':None}],'wash':[{'container_g':'100','container_dry_g':None,'container_washed_g':'230'}],
                                  'shape':[{'total_g':'100','poor_g':None},{'total_g':'50','poor_g':'2'}],'boiling':[{'initial_g':None,'final_g':'99.5'}],
                                  'sand':[{'sand_height':'95','suspension_height':None},{'sand_height':None,'suspension_height':'121'}]}}
        self.assertEqual(module.expected_numbers(position),{'washed_g':130,'shape_total_g':150,'boiling_final_g':'99.5','sand_a_mm':'95','suspension_b_mm':'121'})
        complete={'measurements':{'sieves':[{'input_g':'2000'}],'wash':[{'container_g':'100','container_dry_g':'290','container_washed_g':'280'}],
                                  'shape':[{'total_g':'100','poor_g':'3'}],'boiling':[{'initial_g':'100','final_g':'99.5'}],'sand':[]}}
        self.assertEqual(module.expected_numbers(complete),{'sieve_input_g':'2000','dry_g':190,'washed_g':180,'shape_total_g':100,'shape_poor_g':3,
                                                            'boiling_initial_g':'100','boiling_final_g':'99.5'})
        # The report oracle on persisted data with gaps compares what exists and does not block.
        f,p,r,probes,pdfs=reports()
        basis={pos['sample_code']:{'wash':[{'container_g':None,'container_dry_g':None,'container_washed_g':None}],'shape':[{'total_g':None,'poor_g':None}],
                                   'sieves':[],'boiling':[],'sand':[]} for pos in p['positions']}
        result=module.verify_reports(r,probes,p,f,pdfs,basis=basis)
        self.assertEqual(result['status'],'PASS')

    def test_duplicate_record_and_malformed_or_unknown_probe_blocks(self):
        f,p,r,probes,pdfs=reports();r.append(copy.deepcopy(r[0]))
        self.assertEqual(module.verify_reports(r,probes,p,f,pdfs)['status'],'BLOCKED_REPORT_EVIDENCE')
        f,p,r,probes,pdfs=reports();r[0]['probe_id']='unknown'
        self.assertEqual(module.verify_reports(r,probes,p,f,pdfs)['status'],'BLOCKED_REPORT_EVIDENCE')

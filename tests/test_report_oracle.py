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
            'plant_id':fixture['fixture_data']['plant_id'],'laboratory_id':None,'is_official':False,'status':'Draft','snapshot':snapshot})
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

    def test_duplicate_record_and_malformed_or_unknown_probe_blocks(self):
        f,p,r,probes,pdfs=reports();r.append(copy.deepcopy(r[0]))
        self.assertEqual(module.verify_reports(r,probes,p,f,pdfs)['status'],'BLOCKED_REPORT_EVIDENCE')
        f,p,r,probes,pdfs=reports();r[0]['probe_id']='unknown'
        self.assertEqual(module.verify_reports(r,probes,p,f,pdfs)['status'],'BLOCKED_REPORT_EVIDENCE')

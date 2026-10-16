import copy
import importlib
import unittest
from sqbf.suites import canonical_hash
from test_measurement_oracle import inputs

module=importlib.import_module('projects.ble-elva.tools.allocation_oracle')


def contracts():
    fixture,projection,_=inputs();reference={'positions':[]};records=[]
    for position in projection['positions']:
        row={'target_process':'Kornform','target_sieve_mm':'4','actual_amount_g':'100','material_source_kind':'OriginalSample'}
        reference['positions'].append({'position_id':position['position_id'],'allocations':[dict(row),dict(row,actual_amount_g=None)]})
        records.append(dict(row,sample_code=position['sample_code'],product_id=fixture['suite_copy']['mapping']['positions'][position['position_id']]))
    fixture['suite_copy']['allocation_reference_sha256']=canonical_hash(reference)
    return fixture,projection,reference,records


class AllocationOracleTests(unittest.TestCase):
    def test_exact_recorded_masses_only_and_unrecorded_masses_stay_absent(self):
        f,p,reference,rows=contracts()
        result=module.verify_allocations(rows,p,reference,f)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['expected_recorded_allocations'],10)
        rows.append(copy.deepcopy(rows[0]))
        self.assertEqual(module.verify_allocations(rows,p,reference,f)['status'],'FAIL')

    def test_wrong_mass_kind_sample_relation_and_modified_reference_are_not_pass(self):
        for field,value in [('actual_amount_g','101'),('target_process','SandAequivalent'),('target_sieve_mm','8')]:
            f,p,ref,rows=contracts();rows[0][field]=value
            self.assertEqual(module.verify_allocations(rows,p,ref,f)['status'],'FAIL')
        f,p,ref,rows=contracts();rows[0]['sample_code']='OTHER'
        self.assertEqual(module.verify_allocations(rows,p,ref,f)['status'],'BLOCKED_ALLOCATION_EVIDENCE')
        f,p,ref,rows=contracts();ref['positions'][0]['allocations'][0]['actual_amount_g']='101'
        self.assertEqual(module.verify_allocations(rows,p,ref,f)['reason'],'ALLOCATION_REFERENCE_CHANGED')

    def test_view_has_no_auth_or_personnel_or_free_text(self):
        f,_,_,_=contracts();sql=module.view_sql(f)
        for forbidden in ('identity_users','password','notes','performed_by','created_by','DROP ','DELETE '):
            self.assertNotIn(forbidden,sql)
        self.assertIn('GRANT SELECT ON public.sqbf_allocation_inputs_v1',sql)

    def test_prerequisite_gaps_name_positions_whose_allocation_of_one_process_is_not_persisted_as_approved(self):
        # BLE derives the preparation mass of the partial sieve from the allocation of the pan material and stores 0 without it.
        f,p,reference,rows=contracts()
        for position in reference['positions']:position['allocations'].append(dict(position['allocations'][0],target_process='Siebanalyse',actual_amount_g='560'))
        for row,position in zip(list(rows),p['positions']):
            rows.append(dict(row,target_process='Siebanalyse',actual_amount_g='560'))
        self.assertEqual(module.prerequisite_gaps(rows,p,reference,'Siebanalyse'),set())
        missing=[r for r in rows if not (r['sample_code']==p['positions'][0]['sample_code'] and r['target_process']=='Siebanalyse')]
        self.assertEqual(module.prerequisite_gaps(missing,p,reference,'Siebanalyse'),{p['positions'][0]['position_id']})
        wrong=[dict(r,actual_amount_g='559') if (r['sample_code']==p['positions'][1]['sample_code'] and r['target_process']=='Siebanalyse') else r for r in rows]
        self.assertEqual(module.prerequisite_gaps(wrong,p,reference,'Siebanalyse'),{p['positions'][1]['position_id']})
        # Other processes are not this prerequisite, and a position without a reference allocation of the process has no gap.
        self.assertEqual(module.prerequisite_gaps([r for r in rows if r['target_process']!='Kornform'],p,reference,'Siebanalyse'),set())
        self.assertEqual(module.prerequisite_gaps([],p,reference,'Boiling'),set())

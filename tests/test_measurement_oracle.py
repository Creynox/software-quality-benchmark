import copy
import importlib
import unittest
from uuid import UUID
from test_suite_fixture import owned_fixture
from sqbf.suites import canonical_hash

module=importlib.import_module('projects.ble-elva.tools.measurement_oracle')


def inputs():
    f=owned_fixture();f['suite_copy']['mapping']={'positions':{}}
    projection={'positions':[]};records=[]
    for i in range(1,11):
        key='P'+str(i);product=str(UUID(int=100+i));code='SYNTHETIC-'+str(i)
        f['suite_copy']['mapping']['positions'][key]=product
        groups={k:[] for k in module.KINDS}
        groups['wash']=[{'container_g':'100','container_wet_g':'250','container_dry_g':'240','container_washed_g':'230'}]
        if i==1:groups['sand']=[{'sand_height_mm':'95','suspension_height_mm':'122'},{'sand_height_mm':'96','suspension_height_mm':'121'}]
        projection['positions'].append({'position_id':key,'sample_code':code,'measurements':groups})
        for kind,rows in sorted(groups.items()):
            for j,row in enumerate(rows):
                row=dict(row)
                if kind in ('sand','partial_series'):row['order']=j+1
                records.append({'sample_code':code,'product_id':product,'kind':kind,'inputs':row})
    f['suite_copy']['measurement_reference_sha256']=canonical_hash(projection)
    return f,projection,records


class MeasurementOracleTests(unittest.TestCase):
    def test_exact_inputs_are_required_and_decimal_representation_is_not_a_difference(self):
        f,p,r=inputs();next(row for row in r if row['kind']=='wash')['inputs']['container_g']=100.0
        result=module.verify_inputs(r,p,f,kinds={'wash','sand'})
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['checks'],20)
        self.assertFalse(result['normative_conformity_scoring'])

    def test_missing_wrong_extra_or_duplicate_measurements_fail(self):
        for change in ('missing','wrong','extra'):
            f,p,r=inputs()
            row=next(row for row in r if row['kind']=='wash')
            if change=='missing':r.remove(row)
            if change=='wrong':row['inputs']['container_g']='101'
            if change=='extra':r.append(copy.deepcopy(row))
            result=module.verify_inputs(r,p,f,kinds={'wash'})
            self.assertEqual(result['status'],'FAIL');self.assertIn({'position_id':'P1','kind':'wash'},result['mismatches'])
            self.assertNotIn('container_g',str(result))

    def test_sand_repetition_order_and_units_are_preserved(self):
        f,p,r=inputs();sand=[row for row in r if row['kind']=='sand']
        sand[0]['inputs']['order'],sand[1]['inputs']['order']=2,1
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'sand'})['status'],'FAIL')
        f,p,r=inputs();next(row for row in r if row['kind']=='sand')['inputs']['sand_height_mm']='9.5'
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'sand'})['status'],'FAIL')

    def test_wrong_sample_product_nonfinite_or_unknown_scope_blocks(self):
        for column,value in [('product_id',str(UUID(int=999))),('sample_code','OTHER')]:
            f,p,r=inputs();r[0][column]=value
            self.assertEqual(module.verify_inputs(r,p,f,kinds={'wash'})['status'],'BLOCKED_MEASUREMENT_EVIDENCE')
        f,p,r=inputs();next(row for row in r if row['kind']=='wash')['inputs']['container_g']='NaN'
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'wash'})['status'],'BLOCKED_MEASUREMENT_EVIDENCE')
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'identity'})['status'],'BLOCKED_MEASUREMENT_EVIDENCE')

    def test_projection_view_contains_no_credentials_notes_or_personnel(self):
        f,p,r=inputs();sql=module.view_sql(f)
        self.assertIn('GRANT SELECT ON public.sqbf_measurement_inputs_v1',sql)
        for field in ('identity_users','password','created_by','performed_by','notes','SELECT *'):
            self.assertNotIn(field,sql)
        self.assertNotIn('DROP ',sql);self.assertNotIn('DELETE ',sql)
        f['database']['host_port']=5433
        with self.assertRaises(ValueError):module.view_sql(f)

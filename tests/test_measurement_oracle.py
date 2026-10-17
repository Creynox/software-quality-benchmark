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
        if i==1:groups['sand']=[{'sand_height':'95','suspension_height':'122'},{'sand_height':'96','suspension_height':'121'}]
        projection['positions'].append({'position_id':key,'sample_code':code,'measurements':groups})
        for kind,rows in sorted(groups.items()):
            for j,row in enumerate(rows):
                row=dict(row)
                if kind in ('sand','partial_series'):row['order']=j+1
                if kind=='sand':row={{'sand_height':'sand_height_mm','suspension_height':'suspension_height_mm'}.get(k,k):v for k,v in row.items()}
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
        f,p,r=inputs();next(row for row in r if row['kind']=='sand')['inputs']['sand_height']='95'
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'sand'})['status'],'BLOCKED_MEASUREMENT_EVIDENCE')
        # Persisted unit-suffixed names and reference names describe the same millimetre values.
        f,p,r=inputs()
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'sand'})['status'],'PASS')
        self.assertIn('sand_height_mm',str([row['inputs'] for row in r if row['kind']=='sand']))

    def partial_case(self,persisted_pan,persisted_sieve='114.2',pan_flag=True):
        f,p,r=inputs()
        reference=[{'initial_g':'268.5','dry_g':'268.5','points':[{'sieve_mm':'2','pan':False,'retained_g':'114.2'},
                                                               {'sieve_mm':'0','pan':True,'retained_g':'0.4'}]},
                   {'initial_g':'268.5','dry_g':'268.5','points':[{'sieve_mm':'2','pan':False,'retained_g':'106'},
                                                               {'sieve_mm':'0','pan':True,'retained_g':'0.5'}]}]
        p['positions'][0]['measurements']['partial_series']=reference
        f['suite_copy']['measurement_reference_sha256']=canonical_hash(p)
        sieve=[persisted_sieve,'106']
        for order,series in enumerate(reference,1):
            points=[{'sieve_mm':2.0,'pan':False,'retained_g':float(sieve[order-1])},
                    {'sieve_mm':0.0,'pan':pan_flag,'retained_g':persisted_pan}]
            r.append({'sample_code':'SYNTHETIC-1','product_id':str(UUID(int=101)),'kind':'partial_series',
                      'inputs':{'order':order,'initial_g':268.5,'dry_g':268.5,'points':points}})
        return f,p,r

    def test_the_pan_loss_of_a_partial_tower_is_derived_by_ble_and_never_compared(self):
        # BLE persists the pan loss as NULL (it only shows it as "Siebverlust"); the reference holds the sheet value.
        f,p,r=self.partial_case(None)
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'partial_series'})['status'],'PASS')
        # Even a stored pan value does not matter (derived), but every stored sieve value still has to match exactly.
        f,p,r=self.partial_case(9.9)
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'partial_series'})['status'],'PASS')
        f,p,r=self.partial_case(None,persisted_sieve='114.3')
        result=module.verify_inputs(r,p,f,kinds={'partial_series'})
        self.assertEqual(result['status'],'FAIL');self.assertIn({'position_id':'P1','kind':'partial_series'},result['mismatches'])
        # A point that is not the pan row is never excused by the derived-value rule.
        f,p,r=self.partial_case(None,pan_flag=False)
        self.assertEqual(module.verify_inputs(r,p,f,kinds={'partial_series'})['status'],'FAIL')

    def test_comparable_changes_nothing_outside_partial_series_pan_points(self):
        row={'points':[{'pan':True,'retained_g':'1'}]}
        self.assertIs(module.comparable('sieves',row),row);self.assertIs(module.comparable('wash',row),row)
        self.assertEqual(module.comparable('partial_series',row),{'points':[{'pan':True}]})
        self.assertEqual(row['points'][0]['retained_g'],'1')

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

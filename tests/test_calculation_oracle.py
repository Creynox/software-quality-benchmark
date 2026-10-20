import importlib
import unittest
from decimal import Decimal
from uuid import UUID
from test_suite_fixture import owned_fixture

module=importlib.import_module('projects.ble-elva.tools.calculation_oracle')


def persisted(kind,inputs,code='SYNTHETIC-1'):
    return {'sample_code':code,'product_id':str(UUID(int=101)),'kind':kind,'inputs':inputs}


def scenario():
    f=owned_fixture();f['suite_copy']['mapping']={'positions':{'P1':str(UUID(int=101))}}
    # Persisted view vocabulary (unit-suffixed sand heights), as collect_inputs returns it.
    rows=[persisted('sand',{'order':2,'sand_height_mm':'96','suspension_height_mm':'121'}),
          persisted('sand',{'order':1,'sand_height_mm':'95','suspension_height_mm':'122'}),
          persisted('shape',{'fraction':'4 mm','total_g':'100','poor_g':'3'}),
          persisted('boiling_repetitions',{'order':1,'minutes':'10','initial_g':'100','final_g':'99.5'}),
          persisted('wash',{'container_g':'100','container_wet_g':'250','container_dry_g':'240','container_washed_g':'230'}),
          persisted('sieves',{'input_g':'3000','points':[{'sieve_mm':'16','partial':False,'retained_g':'100'},
                                                         {'sieve_mm':'8','partial':False,'retained_g':'200'},
                                                         {'sieve_mm':'0','partial':False,'retained_g':'2700'}]})]
    basis=module.persisted_basis(rows)
    receipts={'samples':[{'id':str(UUID(int=500)),'sample_code':'SYNTHETIC-1','product_id':str(UUID(int=101))}]}
    # Values as BLE freezes them: 3-decimal method results, 2-decimal residues cumulated for passing.
    report={'id':str(UUID(int=600)),'probe_id':str(UUID(int=500)),'se_a':77.869,'se_b':79.339,'se_endwert':78.604,
            'boiling_reps':[{'order':1,'percent':0.5}],'fine_uf':7.142857142857143,
            'sieve_coupled':False,'sieve_split':None,
            'sieve_fractions':[{'mm':16,'passing':96.67},{'mm':8.0,'passing':90.0},{'mm':0,'passing':0}]}
    return f,basis,receipts,[report]


class CalculationOracleTests(unittest.TestCase):
    def test_persisted_basis_groups_by_sample_and_keeps_repetition_order(self):
        _,basis,_,_=scenario()
        self.assertEqual([r['order'] for r in basis['SYNTHETIC-1']['sand']],[1,2])
        self.assertEqual(basis['SYNTHETIC-1']['sand'][0],{'order':1,'sand_height':'95','suspension_height':'122'})
        with self.assertRaises(ValueError):module.persisted_basis([persisted('unknown',{})])

    def test_method_formulas_are_recomputed_from_raw_inputs(self):
        _,basis,_,_=scenario();out=module.expected_calculations(basis['SYNTHETIC-1'])
        self.assertEqual(out['se_a'],Decimal(95)/Decimal(122)*100)
        self.assertEqual(out['se_mean'],(Decimal(95)/Decimal(122)*100+Decimal(96)/Decimal(121)*100)/2)
        self.assertEqual(out['boiling_loss'],{1:Decimal('0.5')})
        self.assertEqual(out['fine063'],Decimal(10)/Decimal(140)*100)
        self.assertIsNone(out['shape_index'])
        passing={k:v[0] for k,v in out['sieve_passing'].items()}
        self.assertEqual(passing,{'16':Decimal(100)-Decimal(100)/Decimal(3000)*100,'8':Decimal(90),'0':Decimal(0)})
        self.assertEqual(out['sieve_passing']['0'][1],Decimal('0.0155'))
        self.assertEqual(module._sieve_key('10.0'),'10')
        partial=dict(basis['SYNTHETIC-1'],partial_series=[{'order':1,'initial_g':'200','points':[]}])
        self.assertIsNone(module.expected_calculations(partial)['sieve_passing'])
        self.assertEqual(module.expected_calculations({}),{})

    def test_tolerance_reflects_storage_precision_not_display_rounding(self):
        exact=Decimal(95)/Decimal(122)*100
        self.assertEqual(module.compare(77.869,exact),'MATCH')
        self.assertEqual(module.compare(77.87,exact),'MISMATCH')
        self.assertEqual(module.compare(78,exact),'MISMATCH')
        self.assertEqual(module.compare(None,exact),'NOT_AVAILABLE')
        self.assertEqual(module.compare('n/a',exact),'MISMATCH')

    def test_correct_report_passes_and_wrong_result_is_a_positioned_mismatch_without_values(self):
        f,basis,receipts,records=scenario()
        result=module.verify_calculations(records,receipts,basis,f)
        self.assertEqual(result['status'],'PASS',result);self.assertEqual(result['coverage']['MISMATCH'],0)
        self.assertEqual({c['check'] for c in result['checks'] if c['status']=='MATCH'},{'se_index_a','se_index_b','se_mean',
            'boiling_loss_1','fine063','sieve_passing_0','sieve_passing_8','sieve_passing_16'})
        self.assertEqual([c['reason'] for c in result['checks'] if c['status']=='NOT_COVERED'],['SIEVE_LINE_WEIGHTED'])
        for key,value in (('se_endwert',78.61),('fine_uf',7.2),('boiling_reps',[{'order':1,'percent':0.6}])):
            f,basis,receipts,records=scenario();records[0][key]=value
            result=module.verify_calculations(records,receipts,basis,f)
            self.assertEqual(result['status'],'FAIL',key);self.assertEqual(result['mismatched_positions'],['P1'])
            self.assertNotIn(str(value),str(result));self.assertFalse(result['normative_conformity_scoring'])
        f,basis,receipts,records=scenario();records[0]['sieve_fractions'][1]['passing']=89.9
        self.assertEqual(module.verify_calculations(records,receipts,basis,f)['status'],'FAIL')

    def test_missing_result_is_not_available_and_project_specific_sieving_is_not_covered(self):
        f,basis,receipts,records=scenario();records[0]['fine_uf']=None;records[0]['sieve_coupled']=True
        result=module.verify_calculations(records,receipts,basis,f)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual((result['coverage']['NOT_AVAILABLE'],result['coverage']['NOT_COVERED']),(1,2))
        self.assertIn('WASH_COUPLED_REFERENCE_MASS',[c.get('reason') for c in result['checks']])

    def test_a_missing_persisted_input_leaves_out_that_check_and_never_blocks_the_report_stage(self):
        # Live run 824fa661: a wash row with the washed weight not entered raised 'Missing value' and blocked all ten reports of the stage.
        f,basis,receipts,records=scenario();basis['SYNTHETIC-1']['wash'][0]['container_washed_g']=None
        self.assertNotIn('fine063',module.expected_calculations(basis['SYNTHETIC-1']))
        result=module.verify_calculations(records,receipts,basis,f)
        self.assertEqual(result['status'],'PASS',result)
        self.assertNotIn('fine063',{c['check'] for c in result['checks']});self.assertIn('se_mean',{c['check'] for c in result['checks']})
        for kind,key in (('sand','sand_height'),('boiling_repetitions','final_g'),('sieves','input_g')):
            f,basis,receipts,records=scenario();row=basis['SYNTHETIC-1'][kind][0];row[key]=None
            self.assertEqual(module.verify_calculations(records,receipts,basis,f)['status'],'PASS',kind)
        f,basis,receipts,records=scenario();basis['SYNTHETIC-1']['boiling_repetitions'].append({'order':2,'initial_g':'100','final_g':None})
        self.assertEqual(module.expected_calculations(basis['SYNTHETIC-1'])['boiling_loss'],{1:Decimal('0.5')},'complete repetitions are still checked')
        # Contradictory values still block: only a missing value is an incomplete entry.
        f,basis,receipts,records=scenario();basis['SYNTHETIC-1']['wash'][0]['container_washed_g']=True
        self.assertEqual(module.verify_calculations(records,receipts,basis,f)['status'],'BLOCKED_CALCULATION_EVIDENCE')

    def test_duplicate_unknown_or_contradictory_evidence_blocks(self):
        f,basis,receipts,records=scenario()
        self.assertEqual(module.verify_calculations(records*2,receipts,basis,f)['status'],'BLOCKED_CALCULATION_EVIDENCE')
        f,basis,receipts,records=scenario();records[0]['probe_id']='unknown'
        self.assertEqual(module.verify_calculations(records,receipts,basis,f)['status'],'BLOCKED_CALCULATION_EVIDENCE')
        f,basis,receipts,records=scenario();receipts['samples'][0]['product_id']=str(UUID(int=999))
        self.assertEqual(module.verify_calculations(records,receipts,basis,f)['reason'],'UNKNOWN_REPORT_PRODUCT')
        f,basis,receipts,records=scenario();basis['SYNTHETIC-1']['wash'][0]['container_g']='NaN'
        self.assertEqual(module.verify_calculations(records,receipts,basis,f)['status'],'BLOCKED_CALCULATION_EVIDENCE')

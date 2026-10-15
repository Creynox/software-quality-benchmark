import copy
import importlib
import unittest
from uuid import UUID
from sqbf.suites import canonical_hash
from test_suite_fixture import prepared_contracts

module=importlib.import_module('projects.ble-elva.tools.method_fixture')


def contracts():
    _,dataset,fixture,_=prepared_contracts()
    fixture['suite_copy']['dataset_sha256']=dataset['approval']['content_sha256']
    fixture['suite_copy']['mapping']={'positions':{r['position_id']:str(UUID(int=100+i)) for i,r in enumerate(dataset['positions'])}}
    source=[]
    for i,table in enumerate(sorted(module.COLUMNS)):
        source.append({'table':table,'rows':[{'id':str(UUID(int=200+i)),
            'product_id':dataset['positions'][0]['inputs']['product_id'],'is_active':True}]})
    lookups={k:[] for refs in module.REFERENCES.values() for k in refs.values()}
    return fixture,dataset,source,lookups


class MethodFixtureTests(unittest.TestCase):
    def test_original_split_and_preparation_templates_have_separate_empty_target_guard(self):
        f,d,s,l=contracts();groups=[];method=str(UUID(int=888))
        for i,table in enumerate(sorted(module.PREPARATION_COLUMNS)):
            row={k:None for k in module.PREPARATION_COLUMNS[table]}
            row.update(id=str(UUID(int=300+i)),product_id=d['positions'][0]['inputs']['product_id'],is_active=True)
            if table=='product_sample_preparation_steps':row['destination_test_method_id']=method
            groups.append({'table':table,'rows':[row]})
        sql,report=module.compile_preparation(f,d,groups,[method])
        self.assertEqual(sum(report['counts'].values()),2)
        self.assertIn('EMPTY_PREPARATION_TARGET_REQUIRED',sql)
        self.assertNotIn('INSERT INTO samples',sql)
        with self.assertRaises(ValueError):module.compile_preparation(f,d,groups,[])
        next(g['rows'][0] for g in groups if g['table']=='product_sample_preparation_steps')['destination_test_method_id']=None
        module.compile_preparation(f,d,groups,[])
        groups[0]['rows'][0]['password']='never copy'
        with self.assertRaises(ValueError):module.compile_preparation(f,d,groups,[method])

    def test_only_owned_empty_fixture_and_remapped_selected_products(self):
        fixture,dataset,source,lookups=contracts();original=copy.deepcopy(source)
        sql,report=module.compile_methods(fixture,dataset,source,lookups)
        self.assertEqual(source,original);self.assertEqual(sum(report['counts'].values()),3)
        self.assertEqual(len(report['mapping']),3)
        self.assertIn('METHOD_COPY_REQUIRES_UNUSED_EMPTY_TARGET',sql)
        self.assertIn('(SELECT count(*) FROM samples)<>0',sql)
        for forbidden in ('DELETE ','DROP ','TRUNCATE ','identity_users','UPDATE public.','norm_versions'):
            self.assertNotIn(forbidden,sql)
        self.assertFalse(report['norm_changes']);self.assertFalse(report['measured_samples_inserted'])
        fixture['database']['host_port']=5433
        with self.assertRaises(ValueError):module.compile_methods(fixture,dataset,source,lookups)

    def test_unknown_field_unselected_product_duplicate_or_changed_dataset_blocks(self):
        for key,value in [('password','secret'),('product_id',str(UUID(int=999)))]:
            f,d,s,l=contracts();s[0]['rows'][0][key]=value
            with self.assertRaises(ValueError):module.compile_methods(f,d,s,l)
        f,d,s,l=contracts();s[0]['rows'].append(copy.deepcopy(s[0]['rows'][0]))
        with self.assertRaises(ValueError):module.compile_methods(f,d,s,l)
        f,d,s,l=contracts();d['positions'][0]['inputs']['product_id']=str(UUID(int=999))
        with self.assertRaises(ValueError):module.compile_methods(f,d,s,l)

    def test_missing_reference_has_no_substitute(self):
        f,d,s,l=contracts();s[0]['rows'][0]['child_test_method_id']=str(UUID(int=777))
        with self.assertRaises(ValueError):module.compile_methods(f,d,s,l)
        l['workspace_test_methods']=[str(UUID(int=777))]
        module.compile_methods(f,d,s,l)

    def test_values_are_data_not_sql(self):
        f,d,s,l=contracts();s[0]['rows'][0]['display_label']="test'); SELECT 'literal"
        sql,_=module.compile_methods(f,d,s,l)
        self.assertIn("test''); SELECT ''literal",sql)

    def test_catalog_code_collision_requires_identical_sieve_semantics(self):
        f,d,s,l=contracts();old=str(UUID(int=700));current=str(UUID(int=701))
        s[0]['rows'][0]['reference_sieve_size_id']=old
        source={'id':old,'code':'SIEVE_5_6','display_name':'5.6 mm','size_mm':5.6,'sort_order':10,
                'is_active':True,'created_at':'2026-01-01','updated_at':None}
        target=dict(source,id=current,display_name='5,6 mm')
        l['specification_sieve_sizes']=[current]
        catalog=[{'table':'specification_sieve_sizes','rows':[source]}]
        existing=[{'table':'specification_sieve_sizes','rows':[target]}]
        sql,report=module.compile_methods(f,d,s,l,catalog,existing)
        self.assertEqual(report['catalog_aliases'],{old:current})
        self.assertEqual(report['catalog_counts'],{'specification_sieve_sizes':0})
        self.assertNotIn('INSERT INTO public.specification_sieve_sizes',sql)
        target['size_mm']=6.3
        with self.assertRaises(ValueError):module.compile_methods(f,d,s,l,catalog,existing)

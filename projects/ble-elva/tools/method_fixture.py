"""Copy source-selected method settings into an empty owned suite fixture only.

Pure compiler: no source connections, no database execution, no model access.
Never substitutes a method, norm edition, fraction or sieve reference.
"""
import copy
import json
from uuid import UUID, uuid4
from sqbf.suites import canonical_hash, check_dataset
from .suite_fixture import validate_target

COMMON={'id','product_id','created_at','updated_at','is_active','quantity_min','quantity_max','quantity_unit_code'}
COLUMNS={
 'product_test_method_derived_steps': COMMON | {'parent_test_method_id','child_test_method_id','step_order',
    'display_label','source_kind','source_fraction_id','reference_sieve_size_id','secondary_sieve_size_id',
    'fraction_min_sieve_id','fraction_max_sieve_id','is_pan_fraction','quantity_target','drying_required',
    'scaling_mode','is_auto_calculated','default_result_series_count','preparation','origin'},
 'product_test_method_sampling_steps': COMMON | {'test_method_id','step_order','display_label','source_kind',
    'reference_sieve_size_id','secondary_sieve_size_id','reference_sieve_size_code','reference_fraction_id','reference_fraction_code'},
 'product_test_method_input_specs': COMMON | {'test_method_id','quantity_target','pretreatment_code','origin'},
}
REFERENCES={
 'product_test_method_derived_steps': {'parent_test_method_id':'workspace_test_methods','child_test_method_id':'workspace_test_methods',
    'source_fraction_id':'specification_fractions','reference_sieve_size_id':'specification_sieve_sizes',
    'secondary_sieve_size_id':'specification_sieve_sizes','fraction_min_sieve_id':'specification_sieve_sizes',
    'fraction_max_sieve_id':'specification_sieve_sizes'},
 'product_test_method_sampling_steps': {'test_method_id':'workspace_test_methods','reference_fraction_id':'specification_sampling_sources',
    'reference_sieve_size_id':'specification_sieve_sizes','secondary_sieve_size_id':'specification_sieve_sizes'},
 'product_test_method_input_specs': {'test_method_id':'workspace_test_methods'},
}
CATALOG_COLUMNS={
 'specification_sieve_sizes': {'id','code','display_name','size_mm','sort_order','is_active','created_at','updated_at'},
 'workspace_test_methods': {'id','code','name','description','standard_id','is_active','is_composite','has_time_dependency',
    'status','suitable_product_categories','suitable_product_types','test_domain','test_group','title','created_at','updated_at'},
}
PREPARATION_COLUMNS={
 'product_sample_preparation_steps': COMMON | {'destination_test_method_id','display_label','origin','preparation_type',
    'quantity_target','source_kind','step_order'},
 'product_original_sample_split_requirements': {'id','product_id','created_at','updated_at','is_active','label',
    'material_source_kind','process_type','requirement_source','sort_order','target_mass_gram','target_sieve_mm'},
}


def compile_preparation(fixture,dataset,source,method_ids):
    validate_target(fixture)
    review=check_dataset(dataset)
    if review['status']!='DATASET_APPROVED' or review['content_sha256']!=fixture['suite_copy']['dataset_sha256']:
        raise ValueError('Approved source required')
    groups={r['table']:r['rows'] for r in source}
    if len(groups)!=len(source) or set(groups)!=set(PREPARATION_COLUMNS):raise ValueError('Exact preparation table set required')
    products={str(UUID(p['inputs']['product_id'])):str(UUID(fixture['suite_copy']['mapping']['positions'][p['position_id']]))
              for p in dataset['positions']}
    if len(products)!=10:raise ValueError('Exact source products required')
    sql=["BEGIN; SET LOCAL statement_timeout='5s';",
         "DO $$ BEGIN IF (SELECT count(*) FROM samples)<>0 OR (SELECT count(*) FROM lims_sample)<>0 OR (SELECT count(*) FROM ble_reports)<>0"
         +''.join(' OR (SELECT count(*) FROM '+t+')<>0' for t in sorted(groups))
         +" THEN RAISE EXCEPTION 'EMPTY_PREPARATION_TARGET_REQUIRED'; END IF; END $$;"]
    mapping={};counts={}
    for table in sorted(groups):
        clean=[]
        for original in groups[table]:
            if set(original)!=PREPARATION_COLUMNS[table] or original['product_id'] not in products:
                raise ValueError('Unselected or unreviewed preparation record')
            old=str(UUID(original['id']))
            if old in mapping:raise ValueError('Duplicate preparation record')
            if (table=='product_sample_preparation_steps' and original['destination_test_method_id'] is not None
                    and original['destination_test_method_id'] not in method_ids):
                raise ValueError('Missing existing preparation method')
            row=copy.deepcopy(original);row['product_id']=products[row['product_id']];row['id']=str(uuid4())
            mapping[old]=row['id'];clean.append(row)
        counts[table]=len(clean)
        if not clean:continue
        columns=sorted(PREPARATION_COLUMNS[table]);encoded=json.dumps(clean,ensure_ascii=False,allow_nan=False).replace("'","''")
        sql.append('INSERT INTO public.'+table+'('+','.join(columns)+') SELECT '+','.join('j.'+c for c in columns)
            +" FROM jsonb_populate_recordset(NULL::public."+table+",'"+encoded+"'::jsonb) AS j;")
    sql+=['GRANT SELECT ON '+','.join(sorted(groups))+' TO sqbf_oracle_ro;','COMMIT;']
    return '\n'.join(sql),{'counts':counts,'mapping':mapping,'source_sha256':canonical_hash(source),
        'norm_changes':False,'measured_samples_inserted':False}


def compile_methods(fixture, dataset, source, lookups, catalog=None, existing_catalog=None):
    validate_target(fixture)
    review=check_dataset(dataset)
    if review['status']!='DATASET_APPROVED' or review['content_sha256']!=fixture['suite_copy']['dataset_sha256']:
        raise ValueError('Approved exact source dataset required')
    rows={r['table']:r['rows'] for r in source}
    if len(rows)!=len(source) or set(rows)!=set(COLUMNS):raise ValueError('Exact method table set required')
    products={str(UUID(r['inputs']['product_id'])):fixture['suite_copy']['mapping']['positions'][r['position_id']]
              for r in dataset['positions']}
    if len(products)!=10:raise ValueError('Exact ten source products required')
    statements=["BEGIN; SET LOCAL statement_timeout='5s';",
        "DO $$ BEGIN IF (SELECT count(*) FROM samples)<>0 OR (SELECT count(*) FROM lims_sample)<>0 OR (SELECT count(*) FROM ble_reports)<>0"
        + ''.join(' OR (SELECT count(*) FROM '+table+')<>0' for table in sorted(COLUMNS))
        + " THEN RAISE EXCEPTION 'METHOD_COPY_REQUIRES_UNUSED_EMPTY_TARGET'; END IF; END $$;"]
    lookups=copy.deepcopy(lookups)
    missing={}
    for table,records in rows.items():
        for row in records:
            for column,reference in REFERENCES[table].items():
                key=row.get(column)
                if key is not None and str(UUID(key)) not in lookups[reference]:
                    missing.setdefault(reference,set()).add(str(UUID(key)))
    supplied={row['table']:row['rows'] for row in (catalog or [])}
    existing={row['table']:row['rows'] for row in (existing_catalog or [])}
    if len(existing)!=len(existing_catalog or []) or set(existing)-set(CATALOG_COLUMNS):
        raise ValueError('Unexpected existing catalog projection')
    if len(supplied)!=len(catalog or []) or set(supplied)-set(CATALOG_COLUMNS):
        raise ValueError('Only explicitly reviewed missing method/sieve catalog rows allowed')
    aliases,inserted_catalog={},{}
    for table, records in supplied.items():
        ids=[str(UUID(row['id'])) for row in records]
        if len(set(ids))!=len(ids) or set(ids)!=missing.get(table,set()):
            raise ValueError('Catalog must contain exactly the missing referenced IDs')
        if any(set(row)!=CATALOG_COLUMNS[table] for row in records):
            raise ValueError('Unreviewed catalog fields')
        if table=='workspace_test_methods' and any(row['standard_id']!='00000000-0000-0000-0000-000000000000' for row in records):
            raise ValueError('Nonempty legacy standard reference requires independent reference review')
        new=[]
        for row in records:
            matched=[r for r in existing.get(table,[]) if r['code']==row['code']]
            if matched:
                target=matched[0]
                ignored={'id','created_at','updated_at','display_name'}
                if (table!='specification_sieve_sizes' or len(matched)!=1 or target['id'] not in lookups[table]
                        or set(target)!=CATALOG_COLUMNS[table]
                        or any(row[k]!=target[k] for k in set(row)-ignored)):
                    raise ValueError('Same catalog code has different semantics; no replacement')
                aliases[row['id']]=target['id']
            else:new.append(row)
        inserted_catalog[table]=len(new)
        if not new:continue
        encoded=json.dumps(new,ensure_ascii=False,allow_nan=False).replace("'","''")
        columns=sorted(CATALOG_COLUMNS[table])
        statements.append('INSERT INTO public.'+table+'('+','.join(columns)+') SELECT '+','.join('j.'+c for c in columns)
            +" FROM jsonb_populate_recordset(NULL::public."+table+",'"+encoded+"'::jsonb) AS j;")
        lookups[table].extend(r['id'] for r in new)
    mapping,counts={},{}
    for table in sorted(COLUMNS):
        clean=[]
        if not isinstance(rows[table],list):raise ValueError('Invalid method rows')
        for original in rows[table]:
            if not {'id','product_id','is_active'}<=set(original) or set(original)-COLUMNS[table]:
                raise ValueError('Unexpected or incomplete source fields')
            row=copy.deepcopy(original)
            if row['product_id'] not in products:raise ValueError('Unselected source product')
            source_id=str(UUID(row['id']))
            if source_id in mapping:raise ValueError('Duplicate source record')
            for column,reference in REFERENCES[table].items():
                key=row.get(column)
                if key in aliases:
                    key=aliases[key];row[column]=key
                if key is not None and str(UUID(key)) not in lookups[reference]:
                    raise ValueError('Missing existing method/fraction/sieve reference; no substitution')
            row['id']=str(uuid4());row['product_id']=str(UUID(products[row['product_id']]))
            mapping[source_id]=row['id'];clean.append(row)
        counts[table]=len(clean)
        if not clean:continue
        columns=sorted(set().union(*(set(row) for row in clean)))
        values=json.dumps(clean,ensure_ascii=False,allow_nan=False).replace("'","''")
        statements.append('INSERT INTO public.'+table+'('+','.join(columns)+') SELECT '+','.join('j.'+c for c in columns)
            +" FROM jsonb_populate_recordset(NULL::public."+table+",'"+values+"'::jsonb) AS j;")
    statements += ['GRANT SELECT ON '+','.join(sorted(COLUMNS))+' TO sqbf_oracle_ro;','COMMIT;']
    return '\n'.join(statements),{'counts':counts,'mapping':mapping,'source_sha256':canonical_hash(source),
        'catalog_counts':inserted_catalog,'catalog_aliases':aliases,'catalog_sha256':canonical_hash(catalog or []),
        'existing_catalog_sha256':canonical_hash(existing_catalog or []),
        'norm_changes':False,'measured_samples_inserted':False}

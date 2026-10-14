"""Versioned suite contracts and evidence aggregation, independent of any product.

Contract checks perform no browser, model, authentication or database operation.
Unsupported cases remain in the coverage denominator; a score never hides a gate.
"""
import hashlib
import json
from pathlib import Path

RESULTS = {'PASS','FAIL','BLOCKED','NOT_IMPLEMENTED','INVALID','INCONCLUSIVE'}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
                                     ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def validate_suite(suite):
    if (suite.get('schema_version')!=1 or not suite.get('suite_id')
            or not suite.get('version') or not suite.get('dataset_id')):
        raise ValueError('Missing versioned suite identity')
    if suite.get('benchmark_purpose') == 'ux_ui_process_stress':
        if suite.get('normative_conformity_scoring') is not False or not suite.get('standard_policy'):
            raise ValueError('UX stress suite must explicitly exclude normative scoring and preserve standard context')
    required=suite.get('required_position_ids')
    if (not isinstance(required,list) or not required
            or any(not isinstance(key,str) or not key for key in required)
            or len(set(required))!=len(required)):
        raise ValueError('Suite requires an exact dataset position set')
    cases=suite.get('cases')
    if not isinstance(cases,list) or not cases:raise ValueError('Suite requires explicit cases')
    seen=set()
    for case in cases:
        key=case.get('case_id')
        if not isinstance(key,str) or not key or key in seen:raise ValueError('Duplicate/missing case identity')
        if not all(case.get(k) for k in ('persona','task','oracle_contract','fixture_contract','expected')):
            raise ValueError('Case must specify persona, task, fixture, independent oracle and expectations')
        if case.get('implementation') not in ('implemented','pending'):
            raise ValueError('Unknown implementation state')
        if not isinstance(case.get('depends_on'),list) or not set(case['depends_on'])<=seen:
            raise ValueError('Dependencies must reference earlier cases; no cycle or implicit prerequisite')
        if type(case.get('max_minutes')) is not int or not 1<=case['max_minutes']<=25:
            raise ValueError('Individual case time budget missing/outside fixed bound')
        if type(case.get('max_actions')) is not int or not 1<=case['max_actions']<=150:
            raise ValueError('Individual case action budget missing/outside fixed bound')
        if type(case.get('max_model_calls')) is not int or not 2<=case['max_model_calls']<=152:
            raise ValueError('Individual case model budget missing/outside fixed bound')
        seen.add(key)
    if suite.get('automatic_retry') is not False or suite.get('provider')!='chatgpt_plan':
        raise ValueError('Suite requires no retry and subscription-only provider')
    if suite.get('physical_operations')!='simulated':raise ValueError('Physical operations must be explicit simulations')
    if suite.get('real_delivery') is not False:raise ValueError('Real customer delivery is forbidden')
    return suite


def check_dataset(dataset):
    """Approval is bound to content, never an editable unbound READY flag."""
    if dataset.get('schema_version')!=1 or not dataset.get('dataset_id'):
        raise ValueError('Missing dataset identity')
    projection={k:v for k,v in dataset.items() if k!='approval'}
    digest=canonical_hash(projection)
    approval=dataset.get('approval',{})
    positions=dataset.get('positions',[])
    keys=[p.get('position_id') for p in positions if isinstance(p,dict)]
    complete=(bool(positions) and len(keys)==len(positions) and all(keys)
              and len(keys)==len(set(keys)) and not dataset.get('unresolved_questions')
              and all(p.get('input_status')=='verified' and p.get('inputs')
                      and p.get('expected_status')=='verified' and p.get('expected')
                      for p in positions))
    approved=(approval.get('status')=='approved' and approval.get('content_sha256')==digest
              and approval.get('approved_by')=='PO' and bool(approval.get('approved_at')) and complete)
    if dataset.get('benchmark_purpose') == 'ux_ui_process_stress':
        approved = (approved and dataset.get('normative_conformity_scoring') is False
                    and approval.get('scope') == 'UX_UI_PROCESS_SOURCE_REPLAY')
    return {'status':'DATASET_APPROVED' if approved else 'BLOCKED_DATA_REVIEW',
            'content_sha256':digest,'dataset_id':dataset['dataset_id'],'complete':complete}


def suite_check(path,dataset=None):
    suite=validate_suite(json.loads(Path(path).read_text(encoding='utf-8-sig')))
    review=check_dataset(dataset) if dataset is not None else {'status':'BLOCKED_DATA_REVIEW'}
    if dataset is not None and suite.get('dataset_id')!=dataset['dataset_id']:
        review=dict(review,status='BLOCKED_DATASET_MISMATCH')
    if dataset is not None and set(suite['required_position_ids'])!={
            p.get('position_id') for p in dataset.get('positions',[]) if isinstance(p,dict)}:
        review=dict(review,status='BLOCKED_POSITION_MISMATCH')
    pending=[c['case_id'] for c in suite['cases'] if c['implementation']!='implemented']
    return {'suite_id':suite['suite_id'],'version':suite['version'],'contract_sha256':canonical_hash(suite),
            'status':'CONTRACT_READY' if not pending and review['status']=='DATASET_APPROVED' else 'BLOCKED_SETUP',
            'total_cases':len(suite['cases']),'pending_cases':pending,'dataset':review,
            'model_calls':0,'database_writes':0,
            'limitations':['CONTRACT_READY is not a runtime/fixture/session/provider acceptance.']}


def aggregate(suite,records):
    """Keep INVALID separate from product failure and maintain exact coverage."""
    validate_suite(suite)
    cases={c['case_id']:c for c in suite['cases']}
    expected=set(cases);by_id={}
    records=list(records)
    for record in records:
        key=record.get('case_id')
        if key not in expected or key in by_id:raise ValueError('Unknown/duplicate case evidence')
        if record.get('result') not in RESULTS:raise ValueError('Unknown structured result')
        # PASS requires independent technical and functional evidence, not DONE.
        if record['result']=='PASS' and (record.get('technical_gate')!='PASS'
                or record.get('oracle_gate')!='PASS' or record.get('evidence_verified') is not True
                or cases[key]['implementation']!='implemented'):
            raise ValueError('PASS without independent gates/evidence')
        by_id[key]=record
    counts={result:sum(r['result']==result for r in records) for result in sorted(RESULTS)}
    missing=sorted(expected-set(by_id))
    valid=sum(r['result'] in ('PASS','FAIL') for r in records)
    overall=('INVALID' if counts['INVALID'] else 'FAIL' if counts['FAIL'] else
             'INCOMPLETE' if missing or counts['BLOCKED'] or counts['NOT_IMPLEMENTED'] or counts['INCONCLUSIVE'] else 'PASS')
    return {'suite_id':suite['suite_id'],'version':suite['version'],'result':overall,
            'required_cases':len(expected),'recorded_cases':len(by_id),'valid_cases':valid,
            'missing_cases':missing,'counts':counts,'passed_cases':counts['PASS'],
            'coverage':{'valid':valid,'required':len(expected)},
            'score':None,'score_reason':'No authoritative normalization/calibration contract supplied'}


def comparison_key(suite,dataset_sha256,executor,reviewer,viewport,browser_version):
    """Target build deliberately excluded: compare builds at fixed test inputs."""
    return canonical_hash({'suite':canonical_hash(validate_suite(suite)), 'dataset':dataset_sha256,
          'executor':executor,'reviewer':reviewer,'viewport':viewport,'browser':browser_version})

"""Stage-scoped side-effect contract of the NSN014 suite (SQBF issue #21, dry run 2026-10-15).

Live run 45eb301f aborted a stage because BLE stamps updated_at/updated_by on one sampling_plans row; the first fix tolerated
audit-only differences in every protected table, in every stage. This module replaces that with a written contract
(suites/enzberg-nsn014-side-effects-v1.json): an audit stamp is allowed only for one stage, one table, the designated target
rows and the named columns. Everything else in the protected baseline stays byte-identical, stage by stage.

Two layers:
- hard: the protected tables of the prepared baseline (the SELECT-only oracle's view). Any change outside an allowance stops the suite.
- findings: every other table (controller READ ONLY hashes). A write that the stage does not list is recorded for review
  (UNEXPECTED_TABLE_WRITE / WRITE_IN_READ_ONLY_STAGE); it never aborts the run, because BLE may legitimately write more than a
  dry run saw, and an abort would again be a harness false alarm.
"""
import json
import re
from pathlib import Path
from uuid import UUID

from sqbf.suites import canonical_hash

CONTRACT_PATH = Path(__file__).resolve().parents[1] / 'suites' / 'enzberg-nsn014-side-effects-v1.json'
TABLE = re.compile(r'[a-z][a-z0-9_]*')
MODES = ('read_only', 'write')
TARGETS = ('plan_id',)
AUDIT = ('updated_at', 'updated_by')


class ContractError(ValueError):
    pass


def load_contract(case_ids, path=CONTRACT_PATH):
    """Load and validate the contract; returns it with its canonical hash so a run can pin exactly this version."""
    contract = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_contract(contract, case_ids)
    return contract


def contract_hash(contract):
    return canonical_hash(contract)


def validate_contract(contract, case_ids):
    if contract.get('schema_version') != 'sqbf-stage-side-effects-1' or tuple(contract.get('audit_columns', ())) != AUDIT:
        raise ContractError('SCHEMA')
    stages = contract.get('stages')
    if not isinstance(stages, dict) or set(stages) != set(case_ids):
        raise ContractError('STAGES_DIFFER_FROM_SUITE')
    for case_id, stage in stages.items():
        if stage.get('mode') not in MODES:
            raise ContractError('MODE ' + case_id)
        tables = stage.get('tables')
        if not isinstance(tables, list) or any(not isinstance(t, str) or not TABLE.fullmatch(t) for t in tables) or len(set(tables)) != len(tables):
            raise ContractError('TABLES ' + case_id)
        if stage['mode'] == 'read_only' and tables:
            raise ContractError('READ_ONLY_STAGE_LISTS_TABLES ' + case_id)
    seen = set()
    for allowance in contract.get('audit_only_allowances', []):
        key = (allowance.get('case_id'), allowance.get('table'))
        if key in seen or key[0] not in stages or stages[key[0]]['mode'] != 'write' or key[1] not in stages[key[0]]['tables']:
            raise ContractError('ALLOWANCE_NOT_IN_A_WRITE_STAGE_TABLE')
        columns = allowance.get('columns')
        if not columns or not set(columns) <= set(AUDIT) or allowance.get('target') not in TARGETS:
            raise ContractError('ALLOWANCE_SCOPE')
        if type(allowance.get('max_rows')) is not int or not 1 <= allowance['max_rows'] <= 10:
            raise ContractError('ALLOWANCE_ROWS')
        seen.add(key)
    return contract


def allowances(contract, fixture, case_id=None):
    """Resolved audit-only allowances (target rows named) for one stage, or for all stages when case_id is None."""
    resolved = []
    for allowance in contract['audit_only_allowances']:
        if case_id is not None and allowance['case_id'] != case_id:
            continue
        if allowance['target'] == 'plan_id':
            ids = [str(UUID(fixture['suite_copy']['mapping']['plan_id']))]
        else:
            raise ContractError('TARGET')
        resolved.append(dict(allowance, ids=ids))
    return resolved


def scoped_equal(before, after, allowance):
    """The table changed only in the audit columns of the target rows: all other rows byte-identical, target rows
    unchanged apart from the named columns, no target row added or removed, never more rows than the allowance names."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    keys = ('rest_count', 'rest_hash', 'target_count', 'target_hash')
    if any(k not in before or k not in after for k in keys):
        return False
    return (before['rest_count'] == after['rest_count'] and before['rest_hash'] == after['rest_hash']
            and before['target_count'] == after['target_count'] and before['target_hash'] == after['target_hash']
            and 0 < after['target_count'] <= allowance['max_rows'])


def protected_delta(baseline, current, resolved, scoped_baseline, scoped_current, *, mutable):
    """Protected tables only (SELECT-only oracle hashes). Audit-only differences pass only inside an allowance."""
    if set(baseline) != set(current):
        return {'unchanged': False, 'changed_tables': ['BASELINE_OR_TABLE_SET'], 'audit_only': []}
    by_table = {a['table']: a for a in resolved}
    changed, audit_only = [], []
    for table in sorted(t for t, v in baseline.items() if t not in mutable and current[t] != v):
        allowance = by_table.get(table)
        if allowance is not None and scoped_equal((scoped_baseline or {}).get(table), (scoped_current or {}).get(table), allowance):
            audit_only.append({'table': table, 'rows': scoped_current[table]['target_count'], 'columns': list(allowance['columns'])})
        else:
            changed.append(table)
    return {'unchanged': not changed, 'changed_tables': changed, 'audit_only': audit_only}


def findings(contract, case_id, before_all, after_all, *, protected):
    """Every table that changed in a stage but is not listed for it (controller hashes, all public tables).
    Protected tables are judged by protected_delta; this layer only reports the rest."""
    if set(before_all) != set(after_all):
        return [{'code': 'TABLE_SET_CHANGED', 'table': None}]
    stage = contract['stages'][case_id]
    out = []
    for table in sorted(t for t, v in before_all.items() if after_all[t] != v):
        if table in protected or table in stage['tables']:
            continue
        out.append({'code': 'WRITE_IN_READ_ONLY_STAGE' if stage['mode'] == 'read_only' else 'UNEXPECTED_TABLE_WRITE', 'table': table})
    return out


def external_changes(previous_all, current_all):
    """Tables that differ between the end of one stage and the start of the next (nothing of ours ran in between)."""
    if previous_all is None:
        return []
    if set(previous_all) != set(current_all):
        return ['TABLE_SET_CHANGED']
    return sorted(t for t, v in previous_all.items() if current_all[t] != v)

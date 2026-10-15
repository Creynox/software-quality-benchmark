"""Independent recomputation of report results from persisted raw inputs.

The controller recomputes method formulas (sand equivalent, boiling loss, fines
by washing, simple cumulative sieve passing) from the persisted raw measurements
and compares them with the values BLE froze in each report snapshot. Snapshot
values carry BLE's storage precision (3 decimals; sieve passing 2 decimals per
cumulated fraction), so each check has an explicit tolerance derived from that
precision, never a report-display rounding. The shape index is weighted by the
sieve line and allocation sources, and partial or wash-coupled sieving uses
project-specific scaling: these are NOT_COVERED, never a pass or a fault. No
normative conformity, limit or release is evaluated.
"""
import json
import subprocess
from decimal import Decimal, InvalidOperation

from sqbf.no_write_oracle import snapshot
from sqbf.oracle import verify_docker_identity
from .measurement_oracle import KINDS, normalize_inputs
from .suite_fixture import validate_target

STORED_TOLERANCE = Decimal('0.0005')   # one rounding to 3 decimals
SIEVE_STEP_TOLERANCE = Decimal('0.005')  # one rounding to 2 decimals per cumulated fraction


def collect_report_calculations(fixture, *, run=subprocess.run):
    validate_target(fixture); target = verify_docker_identity(fixture, run=run); db = fixture['database']
    snapshot(fixture, run=run, enforce_counts=False)
    # Explicit numeric result keys only; no notes, actors or full snapshot.
    sql = """BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL statement_timeout='5s';
SELECT json_build_object('database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'));
SELECT coalesce(json_agg(json_build_object('id',r.id,'probe_id',r.primary_probe_id,
'se_a',r.snapshot_json::jsonb#>'{sandAequivalent,bestimmungAIndex}',
'se_b',r.snapshot_json::jsonb#>'{sandAequivalent,bestimmungBIndex}',
'se_endwert',r.snapshot_json::jsonb#>'{sandAequivalent,endwert}',
'boiling_reps',(SELECT coalesce(json_agg(json_build_object('order',m->'sortOrder','percent',m->'wasseraufnahmeProzent')),'[]'::json)
  FROM jsonb_array_elements(coalesce(r.snapshot_json::jsonb#>'{kochversuch,messreihen}','[]'::jsonb)) m),
'fine_uf',r.snapshot_json::jsonb#>'{ufFine,fine063Percent}',
'sieve_coupled',r.snapshot_json::jsonb#>'{siebanalyse,isCoupledWithWashFines}',
'sieve_split',r.snapshot_json::jsonb#>'{siebanalyse,teilsiebungSplitMm}',
'sieve_fractions',(SELECT coalesce(json_agg(json_build_object('mm',f->'siebweiteMm','passing',f->'passingPercent')),'[]'::json)
  FROM jsonb_array_elements(coalesce(r.snapshot_json::jsonb#>'{siebanalyse,fractions}','[]'::jsonb)) f))),'[]'::json)
FROM public.ble_reports r; ROLLBACK;"""
    result = run(['docker', 'exec', '-i', target['container_id'], 'psql', '-X', '-q', '-At', '-U', db['oracle_role'],
                  '-d', db['name'], '-v', 'ON_ERROR_STOP=1'], input=sql, capture_output=True, text=True, check=True,
                 timeout=10)
    rows = list(map(json.loads, result.stdout.splitlines()))
    if len(rows) != 2 or rows[0] != {'database': db['name'], 'role': db['oracle_role'], 'read_only': 'on'}:
        raise ValueError('Independent read-only calculation identity failed')
    return rows[1]


def persisted_basis(input_records):
    """Group persisted raw inputs (measurement view rows) per sample code."""
    basis = {}
    for row in input_records:
        if row['kind'] not in KINDS:
            raise ValueError('Unknown persisted measurement kind')
        basis.setdefault(row['sample_code'], {kind: [] for kind in KINDS})[row['kind']].append(
            normalize_inputs(row['kind'], row['inputs']))
    for measurements in basis.values():
        for kind in ('sand', 'boiling_repetitions', 'partial_series'):
            if any('order' in r for r in measurements[kind]):
                measurements[kind] = sorted(measurements[kind], key=lambda r: r.get('order', 0))
    return basis


def _d(value):
    if value is None or isinstance(value, bool):
        raise ValueError('Missing value')
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError('Nonfinite value')
    return number


def _sieve_key(mm):
    # Plain notation: 10 stays '10', not '1E+1'.
    return format(_d(mm).normalize(), 'f')


def _percent(part, total):
    part, total = _d(part), _d(total)
    if total <= 0:
        raise ValueError('Nonpositive reference mass')
    return part / total * Decimal(100)


def expected_calculations(measurements):
    """Method values from raw inputs; keys absent where no inputs exist."""
    out = {}
    sand = measurements.get('sand') or []
    if len(sand) == 2:
        a = _percent(sand[0]['sand_height'], sand[0]['suspension_height'])
        b = _percent(sand[1]['sand_height'], sand[1]['suspension_height'])
        out.update(se_a=a, se_b=b, se_mean=(a + b) / 2)
    if measurements.get('shape'):
        out['shape_index'] = None  # sieve-line weighted: NOT_COVERED
    repetitions = measurements.get('boiling_repetitions') or []
    if repetitions:
        out['boiling_loss'] = {int(r['order']): _percent(_d(r['initial_g']) - _d(r['final_g']), r['initial_g'])
                               for r in repetitions}
    wash = measurements.get('wash') or []
    if len(wash) == 1:
        row = wash[0]
        dry = _d(row['container_dry_g']) - _d(row['container_g'])
        washed = _d(row['container_washed_g']) - _d(row['container_g'])
        if dry > 0:
            out['fine063'] = (dry - washed) / dry * Decimal(100)
    sieves = measurements.get('sieves') or []
    if len(sieves) == 1:
        row = sieves[0]
        simple = (not measurements.get('partial_series') and row.get('split_mm') is None
                  and not any(p.get('partial') for p in row.get('points', [])))
        if simple:
            total = _d(row['input_g']); cumulative = Decimal(0); passing = {}; steps = 0
            if total <= 0:
                raise ValueError('Nonpositive sieve input mass')
            for point in sorted(row['points'], key=lambda p: _d(p['sieve_mm']), reverse=True):
                if point.get('retained_g') is None:
                    continue
                cumulative += _d(point['retained_g']); steps += 1
                value = max(Decimal(0), Decimal(100) - cumulative / total * Decimal(100))
                passing[_sieve_key(point['sieve_mm'])] = (value, SIEVE_STEP_TOLERANCE * steps + STORED_TOLERANCE)
            out['sieve_passing'] = passing
        else:
            out['sieve_passing'] = None  # partial/split method: NOT_COVERED
    return out


def compare(actual, exact, tolerance=STORED_TOLERANCE):
    """MATCH within the tolerance of BLE's storage precision; otherwise MISMATCH."""
    if actual is None:
        return 'NOT_AVAILABLE'
    try:
        value = _d(actual)
    except (ValueError, InvalidOperation):
        return 'MISMATCH'
    return 'MATCH' if abs(value - exact) <= tolerance else 'MISMATCH'


def verify_calculations(records, receipts, basis, fixture):
    """Per report: recomputed checks. Returns identifiers, never raw values."""
    blocked = {'status': 'BLOCKED_CALCULATION_EVIDENCE', 'model_calls': 0, 'database_writes': 0}
    try:
        validate_target(fixture)
        probes = {p['id']: p for p in receipts['samples']}
        if len(probes) != len(receipts['samples']):
            raise ValueError('Duplicate probe identity')
        codes = {}
        for key, product in fixture['suite_copy']['mapping']['positions'].items():
            codes[product] = key
        checks = []
        seen = set()
        for report in records:
            probe = probes[report['probe_id']]
            if probe['id'] in seen:
                return dict(blocked, reason='DUPLICATE_REPORT')
            seen.add(probe['id'])
            position = codes.get(probe['product_id'])
            if position is None:
                return dict(blocked, reason='UNKNOWN_REPORT_PRODUCT')
            expected = expected_calculations(basis.get(probe['sample_code'], {}))

            def add(check, actual, exact, tolerance=STORED_TOLERANCE):
                checks.append({'position_id': position, 'report_id': report['id'], 'check': check,
                               'status': compare(actual, exact, tolerance), 'tolerance': str(tolerance)})

            def not_covered(check, reason):
                checks.append({'position_id': position, 'report_id': report['id'], 'check': check,
                               'status': 'NOT_COVERED', 'tolerance': None, 'reason': reason})
            if 'se_a' in expected:
                add('se_index_a', report.get('se_a'), expected['se_a'])
                add('se_index_b', report.get('se_b'), expected['se_b'])
                # Mean of two 3-decimal indices, itself stored with 3 decimals.
                add('se_mean', report.get('se_endwert'), expected['se_mean'], STORED_TOLERANCE * 2)
            if 'shape_index' in expected:
                not_covered('shape_index', 'SIEVE_LINE_WEIGHTED')
            for order, exact in sorted(expected.get('boiling_loss', {}).items()):
                actual = next((r.get('percent') for r in report.get('boiling_reps', [])
                               if r.get('order') is not None and int(r['order']) == order), None)
                add('boiling_loss_' + str(order), actual, exact)
            if 'fine063' in expected:
                # Only the UF module value; a coupled sieve wash share uses another reference mass.
                add('fine063', report.get('fine_uf'), expected['fine063'])
            if 'sieve_passing' in expected:
                if expected['sieve_passing'] is None or report.get('sieve_split') is not None:
                    not_covered('sieve_passing', 'PARTIAL_SIEVING_SCALED')
                elif report.get('sieve_coupled'):
                    not_covered('sieve_passing', 'WASH_COUPLED_REFERENCE_MASS')
                else:
                    reported = {}
                    for fraction in report.get('sieve_fractions', []):
                        if fraction.get('mm') is not None:
                            reported[_sieve_key(fraction['mm'])] = fraction.get('passing')
                    for sieve, (exact, tolerance) in sorted(expected['sieve_passing'].items(), key=lambda item: _d(item[0])):
                        add('sieve_passing_' + sieve, reported.get(sieve), exact, tolerance)
        mismatches = [c for c in checks if c['status'] == 'MISMATCH']
        coverage = {status: sum(c['status'] == status for c in checks)
                    for status in ('MATCH', 'MISMATCH', 'NOT_AVAILABLE', 'NOT_COVERED')}
        return {'status': 'FAIL' if mismatches else 'PASS', 'report_count': len(records), 'checks': checks, 'coverage': coverage,
                'mismatched_positions': sorted({c['position_id'] for c in mismatches}),
                'model_calls': 0, 'database_writes': 0, 'normative_conformity_scoring': False}
    except (ValueError, TypeError, KeyError, AttributeError, InvalidOperation):
        return dict(blocked, reason='INCOMPLETE_OR_CONTRADICTORY_CALCULATION_EVIDENCE')

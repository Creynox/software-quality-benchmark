"""Controller-only, pure projection of recorded Enzberg measurements.

No database/browser/model access. This is a preparation contract, not a runnable
fixture or a normative release. Only explicitly selected measurement fields
survive; source row IDs, credentials and stored computed results do not.
"""
from decimal import Decimal, ROUND_HALF_UP
import importlib
import re

from sqbf.suites import canonical_hash, validate_suite

math = importlib.import_module('projects.ble-elva.tools.reference_math')


def _n(value):
    value = math.number(value)
    if value == 0:
        return '0'
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _rows(value):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError('Invalid measurement collection')
    return value


def _real(row):
    if type(row.get('origin')) is not int or row['origin'] != 0:
        raise ValueError('Original measurement provenance required')


def _optional_rows(value):
    # SQL JSON aggregates are null for absent rows. Absence is never a synthetic
    # measurement or evidence that a required test is not applicable.
    return [] if value is None else _rows(value)


def _mass_rows(rows, keys):
    return [{key: _n(row[key]) for key in keys} for row in _optional_rows(rows)]


def project_reference(dataset, suite, unit_decision):
    """Export exact position set and actual inputs; never approve or seed them.

    Unit evidence is an explicit controller contract tied to the actual repeated
    readings. A field suffix, averaged legacy heights, or a READY flag cannot
    replace it. Expectations here are arithmetic proposals only.
    """
    validate_suite(suite)
    if dataset.get('dataset_id') != suite['dataset_id']:
        raise ValueError('Dataset mismatch')
    positions = _rows(dataset.get('positions'))
    keys = [row.get('position_id') for row in positions]
    if (len(set(keys)) != len(keys) or set(keys) != set(suite['required_position_ids'])
            or any(not isinstance(key, str) for key in keys)):
        raise ValueError('Exact position set required')
    if (unit_decision.get('status') != 'CONFIRMED_SOURCE_UNIT'
            or unit_decision.get('conversion_authorized') is not True
            or unit_decision.get('original_unit') not in ('cm', 'mm')
            or unit_decision.get('target_unit') != 'mm'
            or not unit_decision.get('decision_by') or not unit_decision.get('decision_date')):
        raise ValueError('Explicit confirmed unit decision required')
    products, samples, projected = set(), set(), []
    seen_sand = 0
    for position in positions:
        data = position['inputs']
        product, sample = position['product'], data['sample_code']
        if (not isinstance(product, str) or not product or product != data['product']
                or product in products or not isinstance(sample, str) or not sample
                or sample in samples or data['plan_date'][:10] != suite['reference']['sampling_date']):
            raise ValueError('Product/sample/date identity mismatch')
        products.add(product); samples.add(sample)
        raw, calculations = {}, {}
        raw['wash'] = _mass_rows(data['wash'], ('container_g', 'container_wet_g',
                                  'container_dry_g', 'container_washed_g'))
        raw['shape'] = []
        for row in _optional_rows(data['shape']):
            _real(row)
            if not re.fullmatch(r'\d+(?:[.,]\d+)? mm', row['fraction']):
                raise ValueError('Invalid recorded fraction')
            index = math.percent(row['poor_g'], row['total_g'])
            raw['shape'].append({'fraction': row['fraction'], 'total_g': _n(row['total_g']),
                                 'poor_g': _n(row['poor_g'])})
            calculations.setdefault('shape_percent_unrounded', []).append(str(index))
        raw['boiling'] = []
        for row in _optional_rows(data['boiling']):
            _real(row)
            raw['boiling'].append({key: _n(row[key]) for key in ('initial_g', 'final_g', 'marl_g')})
            calculations.setdefault('marl_percent_unrounded', []).append(
                str(math.percent(row['marl_g'], row['initial_g'])))
        raw['sieves'] = []
        for row in _optional_rows(data['sieves']):
            _real(row)
            points = []
            for point in _rows(row['points']):
                if type(point.get('partial')) is not bool:
                    raise ValueError('Explicit sieve source required')
                points.append({'sieve_mm': _n(point['sieve_mm']), 'partial': point['partial'],
                               'retained_g': None if point['retained_g'] is None else _n(point['retained_g'])})
            raw['sieves'].append({'input_g': _n(row['input_g']),
                'split_mm': None if row['split_mm'] is None else _n(row['split_mm']),
                'partial_input_g': None if row['partial_input_g'] is None else _n(row['partial_input_g']),
                'points': points})
        raw['partial_series'] = []
        raw['preparation'] = []
        raw['boiling_repetitions'] = []
        sand_records = []
        for row in _optional_rows(data['derived_and_repetitions']):
            if row.get('sample') != sample:
                raise ValueError('Wrong source sample relation')
            if 'series' in row:
                raw['preparation'].append({'taken_g': _n(row['taken_mass']),
                                           'dry_g': _n(row['dried_mass'])})
                for series in _rows(row['series']):
                    points = []
                    for point in _rows(series['points']):
                        if type(point['pan']) is not bool:
                            raise ValueError('Explicit pan marker required')
                        points.append({'sieve_mm': _n(point['mm']), 'pan': point['pan'], 'retained_g': _n(point['mass'])})
                    raw['partial_series'].append({'initial_g': _n(series['initial_mass']),
                        'dry_g': _n(series['dried_mass']), 'points': points})
            elif row.get('module') == 'AGGREGATE_SAND_EQUIVALENT':
                sand_records.append(row)
            elif row.get('module') == 'AGGREGATE_MARL_CONTENT':
                for rep in _rows(row['repetitions']):
                    if type(rep.get('sortOrder')) is not int or rep['sortOrder'] < 1:
                        raise ValueError('Explicit boiling repetition order required')
                    raw['boiling_repetitions'].append({'order': rep['sortOrder'],
                        'minutes': _n(rep['kochzeitMin']), 'initial_g': _n(rep['einwaageVorKochen']),
                        'final_g': _n(rep['rueckwaageNachKochen'])})
        raw['sand'] = []
        if data['sand']:
            if len(sand_records) != 1:
                raise ValueError('Actual two sand repetitions required; no averaged fallback')
            reps = _rows(sand_records[0]['repetitions'])
            if len(reps) != 2 or [r.get('sortOrder') for r in reps] != [1, 2]:
                raise ValueError('Ordered actual sand repetitions required')
            heights = [{'sand_height': r['sandHeightMm'], 'suspension_height': r['suspensionHeightMm']} for r in reps]
            approved_heights = _rows(unit_decision.get('source_repetitions'))
            canonical_heights = lambda rows: [{key: _n(row[key]) for key in ('sand_height', 'suspension_height')}
                                              for row in rows]
            if canonical_hash(canonical_heights(heights)) != canonical_hash(canonical_heights(approved_heights)):
                raise ValueError('Unit decision not bound to actual recorded heights')
            mm = math.sand_heights_mm(heights, unit_decision['original_unit'])
            raw['sand'] = [{key: _n(value) for key, value in row.items()} for row in mm]
            ratios = [math.percent(row['sand_height'], row['suspension_height']) for row in mm]
            individual = [r.quantize(Decimal('.1'), rounding=ROUND_HALF_UP) for r in ratios]
            reported = (sum(individual) / 2).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            calculations['sand_percent_unrounded'] = str(math.sand_equivalent(mm))
            calculations['sand_individual_percent_1dp'] = [str(value) for value in individual]
            calculations['sand_reported_integer'] = str(reported)
            seen_sand += 1
        elif sand_records:
            raise ValueError('Unexpected sand measurements')
        projected.append({'position_id': position['position_id'], 'product': product,
                          'sample_code': sample, 'measurements': raw, 'arithmetic_proposals': calculations,
                          'unrecorded_modules': [key for key in ('wash', 'shape', 'sand', 'boiling', 'sieves')
                                                 if not data[key]]})
    if seen_sand != 1:
        raise ValueError('Reference requires exactly one sand-equivalent sample')
    return {'schema_version': 1, 'dataset_id': dataset['dataset_id'],
            'source_sha256': canonical_hash(dataset), 'unit_decision_sha256': canonical_hash(unit_decision),
            'status': 'PREPARATION_ONLY', 'dataset_approved': False, 'normative_release': False,
            'model_calls': 0, 'database_writes': 0, 'positions': projected,
            'limitations': ['No DB fixture or runtime acceptance.',
                'Arithmetic proposals do not prove normative conformity.',
                'Absent measurements stay absent; no synthetic replacement or averaged fallback.']}


def compare_measurements(expected, actual):
    """Pure independent controller gate over canonical raw measurements.

    The future read-only DB adapter must produce this contract. No screenshot or
    model verdict can substitute for it. Return mismatch identifiers only.
    """
    blocked = {'status': 'BLOCKED_REFERENCE_COMPARISON', 'model_calls': 0, 'database_writes': 0}
    try:
        if expected['dataset_id'] != actual['dataset_id']:
            return dict(blocked, reason='DATASET_MISMATCH')
        def indexed(rows):
            rows = _rows(rows)
            result = {row['position_id']: row for row in rows}
            if len(result) != len(rows) or not result:
                raise ValueError('Duplicate/empty positions')
            return result
        left, right = indexed(expected['positions']), indexed(actual['positions'])
        if set(left) != set(right):
            return dict(blocked, reason='POSITION_SET_MISMATCH')
        mismatches = [key for key in sorted(left) if any(
            canonical_hash(left[key][field]) != canonical_hash(right[key][field])
            for field in ('product', 'sample_code', 'measurements'))]
        return dict(blocked, reason='MEASUREMENT_MISMATCH', positions=mismatches) if mismatches else {
            'status': 'REFERENCE_MEASUREMENTS_MATCH', 'positions_checked': len(left),
            'model_calls': 0, 'database_writes': 0,
            'limitations': ['Projection comparison only; not a DB persistence or release verdict.']}
    except (ValueError, TypeError, KeyError, AttributeError):
        return dict(blocked, reason='INCOMPLETE_EVIDENCE')

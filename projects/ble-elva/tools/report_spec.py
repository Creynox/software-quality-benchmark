"""NSN014 evaluation report: one fixed, versioned definition (PO decision 2026-10-19).

A run is scored by a points system of numbers and facts: every check of a fixed catalogue is PASSED, FAILED, NOT_DECIDED, INVALID or NOT_RUN and
a passed check is one point. The scorecard is computed only from recorded results; the report is rendered from the scorecard only, with fixed
sections, fixed tables and fixed wording. No free text and no assumption enters a number. The reviewer's observations are counted in their own
section and never change a point or the result. Layout, catalogue and rules live in suites/nsn014-report-spec-v1.json and change only by a new
version (MAJOR: rules or catalogue, MINOR: additions at the end, PATCH: wording).
"""
import json
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path

from sqbf.suites import canonical_hash
from .stage_support import CATEGORIES, DIMENSIONS, SEVERITIES, cause_source

SPEC_PATH = Path(__file__).resolve().parents[1] / 'suites' / 'nsn014-report-spec-v1.json'
STAGE_STATUS = {'PASS': 'PASSED', 'FAIL': 'FAILED', 'INCONCLUSIVE': 'NOT_DECIDED', 'BLOCKED': 'NOT_DECIDED', 'INVALID': 'INVALID',
                'INVALID_HARNESS': 'INVALID', 'NOT_RUN': 'NOT_RUN', 'NOT_IMPLEMENTED': 'NOT_RUN'}
POSITION_STATUS = {'PASS': 'PASSED', 'FAIL': 'FAILED', 'INCOMPLETE': 'NOT_DECIDED'}
REVIEW_VERDICTS = ('PASS', 'FAIL', 'INCONCLUSIVE')
TECHNICAL_ABORTS = ('RESOURCE_STOP', 'BLOCKED', 'BLOCKED_OR_INVALID')
OPERATING_KEYS = ('actions', 'scrolls', 'scrolls_after_last_entry', 'clicks', 'typed', 'keys', 'waits', 'rejected')


@lru_cache(maxsize=None)
def _load(path):
    raw = Path(path).read_text(encoding='utf-8-sig')
    return json.loads(raw), canonical_hash(json.loads(raw))


def load_spec(path=SPEC_PATH):
    return _load(str(path))[0]


def spec_sha256(path=SPEC_PATH):
    return _load(str(path))[1]


def catalogue(spec):
    """The fixed list of check ids in stage order: a single-task stage is one check, a measurement or report stage has one check per position."""
    ids = []
    for stage in spec['stage_order']:
        if stage in spec['check_catalogue']['single']:
            ids.append((stage, None))
        ids += [(stage, position) for position in spec['check_catalogue']['positions'].get(stage, [])]
    return ids


def check_id(stage, position):
    return stage if position is None else stage + '/' + position


def validate_spec(spec):
    """Structural self-check of the definition; empty list means it is consistent."""
    problems = []
    stages, single, positions = spec['stage_order'], spec['check_catalogue']['single'], spec['check_catalogue']['positions']
    if set(stages) != set(spec['stage_labels']):
        problems.append('STAGE_LABELS_DO_NOT_MATCH_STAGE_ORDER')
    if set(single) | set(positions) != set(stages) or set(single) & set(positions):
        problems.append('CATALOGUE_DOES_NOT_COVER_EACH_STAGE_ONCE')
    if set(spec['status_order']) != set(spec['status_labels']) or set(spec['status_order']) != set(spec['status_rules']):
        problems.append('STATUS_VOCABULARY_INCONSISTENT')
    if set(spec['origin_order']) != set(spec['origin_labels']):
        problems.append('ORIGIN_VOCABULARY_INCONSISTENT')
    if [section['id'] for section in spec['sections']] != [str(i) for i in range(1, len(spec['sections']) + 1)]:
        problems.append('SECTION_IDS_NOT_CONSECUTIVE')
    if len({check_id(*c) for c in catalogue(spec)}) != len(catalogue(spec)):
        problems.append('DUPLICATE_CHECK_ID')
    return problems


def _pct(part, whole):
    if not whole:
        return None
    return float((Decimal(part) * 100 / Decimal(whole)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def _mean(values):
    return float((Decimal(sum(values)) / Decimal(len(values))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) if values else None


def _origin_code(origin):
    code = str(origin).split(' (')[0]
    return code if code and code != '—' else 'UNKLAR'


def _reason(record):
    return record.get('stop_reason') or record.get('reason') or record.get('upstream_reason')


def _undecided_origin(spec, reason, rejected=0):
    """Origin of a check without result: first the recorded class through the cause rules, then the recorded stage reason."""
    if not reason:
        return 'UNKLAR'
    name = str(reason).split(':')[0]
    if name in spec['stage_reason_origin']:
        return spec['stage_reason_origin'][name]
    return _origin_code(cause_source('INCOMPLETE', reason, rejected))


def _checks(spec, records, rows):
    """One entry per catalogue check plus the consistency findings found while mapping the records onto the catalogue."""
    known = {}
    findings = []
    for record in records:
        stage = record.get('case_id')
        if stage in known:
            findings.append({'rule': 'DUPLICATE_RECORD', 'item': str(stage)})
        elif stage in spec['stage_order']:
            known[stage] = record
        else:
            findings.append({'rule': 'CATALOGUE_MISMATCH', 'item': str(stage)})
    by_position = {(row['case'], row['position']): row for row in rows}
    stage_results = {}
    checks = []
    for stage, position in catalogue(spec):
        record = known.get(stage)
        if position is None or stage not in stage_results:
            if record is None:
                stage_results[stage] = 'NOT_RUN'
            else:
                stage_results[stage] = 'INVALID_HARNESS' if record.get('result') == 'INVALID' else str(record.get('result'))
        status, origin, detail = None, None, None
        if record is None:
            status, origin, detail = 'NOT_RUN', 'NICHT_AUSGEFUEHRT', 'NO_RECORD'
        elif STAGE_STATUS.get(record.get('result')) in ('INVALID', 'NOT_RUN'):
            status = STAGE_STATUS[record['result']]
            origin = 'UNGUELTIG' if status == 'INVALID' else 'NICHT_AUSGEFUEHRT'
            detail = _reason(record)
        elif position is None:
            status = STAGE_STATUS.get(record.get('result'))
            if status is None:
                status, origin, detail = 'NOT_DECIDED', 'UNKLAR', 'UNKNOWN_RESULT:' + str(record.get('result'))
                findings.append({'rule': 'UNKNOWN_RESULT', 'item': stage})
            elif status == 'FAILED':
                origin, detail = 'BLE-ABWEICHUNG', ';'.join(record.get('fail_classes') or []) or _reason(record)
            elif status == 'NOT_DECIDED':
                detail = _reason(record)
                origin = _undecided_origin(spec, detail, (record.get('effort') or {}).get('rejected', 0))
        else:
            found = {p.get('position_id'): p for p in record.get('position_results', []) if isinstance(p, dict)}
            item = found.get(position)
            if item is None:
                status, detail = 'NOT_DECIDED', _reason(record)
                origin = _undecided_origin(spec, detail)
            else:
                status = POSITION_STATUS.get(item.get('result'))
                if status is None:
                    status, origin, detail = 'NOT_DECIDED', 'UNKLAR', 'UNKNOWN_RESULT:' + str(item.get('result'))
                    findings.append({'rule': 'UNKNOWN_RESULT', 'item': check_id(stage, position)})
                elif status == 'FAILED':
                    origin, detail = 'BLE-ABWEICHUNG', item.get('class')
                elif status == 'NOT_DECIDED':
                    detail = item.get('class')
                    row = by_position.get((stage.replace('NSN014-', ''), position))
                    origin = _origin_code(row['origin']) if row else _origin_code(cause_source('INCOMPLETE', detail))
        checks.append({'id': check_id(stage, position), 'stage': stage, 'position': position, 'status': status, 'origin': origin, 'detail': detail})
    for stage, record in known.items():
        found = [p.get('position_id') for p in record.get('position_results', []) if isinstance(p, dict)]
        listed = spec['check_catalogue']['positions'].get(stage, [])
        findings += [{'rule': 'CATALOGUE_MISMATCH', 'item': check_id(stage, pid)} for pid in found if pid not in listed]
    return checks, stage_results, findings


def _critical_stop(spec, records):
    """The first stage (in stage order) that ended BLOCKED or INVALID, with its recorded reason; None if there is none."""
    by_stage = {r.get('case_id'): r for r in records if r.get('case_id') in spec['stage_order']}
    for stage in spec['stage_order']:
        record = by_stage.get(stage)
        if record and record.get('result') in ('BLOCKED', 'INVALID', 'INVALID_HARNESS'):
            return '%s: %s' % (stage, record.get('reason') or record.get('stop_reason') or record.get('error_code') or 'KEIN_GRUND_AUFGEZEICHNET')
    return None


def _reviewer(records, reviews):
    errors = sum(1 for record in records for item in [record] + list(record.get('positions', [])) if item.get('review_error'))
    verdicts = {v: 0 for v in REVIEW_VERDICTS}
    scores = {name: [] for name in DIMENSIONS}
    findings = {category: {severity: 0 for severity in SEVERITIES} for category in CATEGORIES}
    for review in reviews:
        if review.get('verdict') in verdicts:
            verdicts[review['verdict']] += 1
        for name in DIMENSIONS:
            value = (review.get('scores') or {}).get(name)
            if type(value) is int:
                scores[name].append(value)
        for finding in review.get('findings', []):
            if isinstance(finding, dict) and finding.get('category') in findings and finding.get('severity') in findings[finding['category']]:
                findings[finding['category']][finding['severity']] += 1
    return {'reviews': len(reviews), 'review_errors': errors, 'verdicts': verdicts,
            'scores': {name: {'n': len(v), 'min': min(v) if v else None, 'mean': _mean(v), 'max': max(v) if v else None} for name, v in scores.items()},
            'findings': findings, 'note': 'unconfirmed observations; never part of the points'}


def _operating(spec, rows):
    if not rows:  # nothing was measured: no value, never a zero that looks like a measurement
        return {'tasks_measured': 0, 'modules_reached': {key: None for key in spec['reached_labels']}, 'totals': {key: None for key in OPERATING_KEYS},
                'saves': {status: None for status in spec['save_status_order']}, 'save_rate_percent': None}
    totals ={key: sum((row['effort'].get(key) or 0) for row in rows) for key in OPERATING_KEYS}
    saves = {status: 0 for status in spec['save_status_order']}
    for row in rows:
        status = 'NOT_APPLICABLE' if row['save'] in (None, '—') else row['save']
        saves[status] = saves.get(status, 0) + 1
    reached = {'ja': 0, 'nein': 0, 'unbekannt': 0}
    for row in rows:
        reached[row['reached'] if row['reached'] in ('ja', 'nein') else 'unbekannt'] += 1
    return {'tasks_measured': len(rows), 'modules_reached': reached, 'totals': totals, 'saves': saves,
            'save_rate_percent': _pct(saves['SAVED'], saves['SAVED'] + saves['NOT_SAVED_AFTER_ENTRY'])}


def _cost(manifest):
    accounting = manifest.get('accounting') or {}
    actors = accounting.get('actors') or {}
    totals = [(a.get('tokens') or {}).get('total_tokens') or {} for a in actors.values()]
    seconds = lambda key: None if accounting.get(key) is None else int(Decimal(str(accounting[key])).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return {'model_calls': manifest.get('model_calls'), 'executor_calls': (actors.get('executor') or {}).get('model_calls'),
            'reviewer_calls': (actors.get('reviewer') or {}).get('model_calls'), 'elapsed_seconds': seconds('elapsed_seconds'),
            'model_wait_seconds': seconds('model_wait_seconds'), 'tokens_known_sum': sum(t.get('known_sum', 0) for t in totals) if totals else None,
            'tokens_unknown_calls': sum(t.get('unknown_calls', 0) for t in totals) if totals else None}


def _comparability(spec, manifest):
    viewport = manifest.get('viewport')
    values = {'spec_version': spec['spec_version'], 'reviewer_model': manifest.get('analyst_model'),
              'viewport': '%sx%s' % (viewport.get('width'), viewport.get('height')) if isinstance(viewport, dict) else None}
    return {key: values[key] if key in values else manifest.get(key) for key in spec['comparability_keys']}


def run_result(spec, manifest, counts, stage_results, findings):
    """The fixed decision order of the specification; the reasons are the rules that matched, as numbers and codes."""
    reasons = []
    technical, verdict = manifest.get('technical_status'), manifest.get('verdict')
    failed_stages = sum(1 for result in stage_results.values() if result == 'FAIL')
    if counts['INVALID'] or technical == 'INVALID':
        reasons = ['CHECKS_INVALID=%d' % counts['INVALID']] + (['TECHNICAL_STATUS=INVALID'] if technical == 'INVALID' else [])
        result = 'UNGUELTIG'
    elif counts['FAILED'] or failed_stages:
        reasons = ['CHECKS_FAILED=%d' % counts['FAILED'], 'STAGES_FAILED=%d' % failed_stages]
        result = 'NICHT_BESTANDEN'
    elif manifest.get('stop_reason') or technical in TECHNICAL_ABORTS or counts['NOT_RUN']:
        reasons = (['STOP_REASON=%s' % manifest['stop_reason']] if manifest.get('stop_reason') else []) + \
                  (['TECHNICAL_STATUS=%s' % technical] if technical in TECHNICAL_ABORTS else []) + ['CHECKS_NOT_RUN=%d' % counts['NOT_RUN']]
        result = 'ABGEBROCHEN'
    elif counts['PASSED'] == counts['catalogue_checks'] and verdict == 'GO' and not findings:
        result, reasons = 'BESTANDEN', ['CHECKS_PASSED=%d' % counts['PASSED']]
    else:
        reasons = ['CHECKS_NOT_PASSED=%d' % (counts['catalogue_checks'] - counts['PASSED']), 'VERDICT=%s' % verdict]
        result = 'UNVOLLSTAENDIG'
    return {'run_result': result, 'bestanden': result == 'BESTANDEN', 'reasons': reasons}


def build_scorecard(manifest, records, rows, reviews, *, spec=None):
    """The whole evaluation as numbers. `rows` are the effort rows of the run (operating measurements), `reviews` the reviewer answers."""
    spec = spec or load_spec()
    checks, stage_results, findings = _checks(spec, records, rows)
    counts = {status: sum(1 for c in checks if c['status'] == status) for status in spec['status_order']}
    counts['catalogue_checks'] = len(checks)
    by_stage = {}
    for check in checks:
        stage = by_stage.setdefault(check['stage'], {status: 0 for status in spec['status_order']})
        stage[check['status']] += 1
    for stage, result in stage_results.items():
        if result == 'PASS' and by_stage[stage]['PASSED'] != sum(by_stage[stage].values()):
            findings.append({'rule': 'STAGE_PASS_WITH_OPEN_CHECK', 'item': stage})
        if result == 'FAIL' and not by_stage[stage]['FAILED']:
            findings.append({'rule': 'STAGE_FAIL_WITHOUT_FAILED_CHECK', 'item': stage})
    if counts['PASSED'] != counts['catalogue_checks'] and manifest.get('verdict') == 'GO':
        findings.append({'rule': 'VERDICT_GO_WITH_OPEN_CHECK', 'item': 'run'})
    if counts['PASSED'] == counts['catalogue_checks'] and manifest.get('verdict') != 'GO':
        findings.append({'rule': 'ALL_PASSED_WITHOUT_GO', 'item': 'run'})
    points = counts['PASSED']
    origins = {origin: sum(1 for c in checks if c['origin'] == origin) for origin in spec['origin_order']}
    operating = _operating(spec, rows)
    return {
        'spec_id': spec['spec_id'], 'spec_version': spec['spec_version'], 'spec_sha256': canonical_hash(spec),
        'run': {'run_id': manifest.get('run_id'), 'suite_id': manifest.get('scenario_id'), 'suite_version': manifest.get('scenario_version'),
                'scoring_version': manifest.get('scoring_version'), 'rubric_version': manifest.get('rubric_version'),
                'technical_status': manifest.get('technical_status'), 'functional_status': manifest.get('functional_status'),
                'measurement_status': manifest.get('measurement_status'), 'verdict': manifest.get('verdict'), 'stop_reason': manifest.get('stop_reason'),
                'executor_model': manifest.get('executor_model'), 'reviewer_model': manifest.get('analyst_model'),
                'sqbf_commit': manifest.get('sqbf_commit'), 'software_version': manifest.get('software_version'),
                'started_at': manifest.get('started_at'), 'completed_at': manifest.get('completed_at'), 'critical_stop': _critical_stop(spec, records), 'kind': manifest.get('run_kind', 'BENCHMARK')},
        'result': run_result(spec, manifest, counts, stage_results, findings),
        'points': {'points': points, 'max_points': counts['catalogue_checks']},
        'counts': counts,
        'rates': {'points_percent': _pct(points, counts['catalogue_checks']),
                  'coverage_percent': _pct(counts['PASSED'] + counts['FAILED'], counts['catalogue_checks']),
                  'pass_rate_of_decided_percent': _pct(counts['PASSED'], counts['PASSED'] + counts['FAILED']),
                  'save_rate_percent': operating['save_rate_percent']},
        'stages': [{'stage': stage, 'label': spec['stage_labels'][stage], 'stage_result': stage_results[stage],
                    'points': by_stage[stage]['PASSED'], 'checks': sum(by_stage[stage].values()), 'counts': by_stage[stage]} for stage in spec['stage_order']],
        'checks': checks,
        'origins': origins,
        'operating': operating,
        'cost': _cost(manifest),
        'comparability': _comparability(spec, manifest),
        'reviewer_observations': _reviewer(records, reviews),
        'consistency': {'counts': {rule: sum(1 for f in findings if f['rule'] == rule) for rule in spec['consistency_rules']}, 'findings': findings},
    }


def scorecard_problems(scorecard, spec=None):
    """Contract check of a scorecard against the specification: exact keys, the full catalogue, points equal to the passed checks."""
    spec = spec or load_spec()
    problems = []
    if list(scorecard) != spec['scorecard_keys']:
        problems.append('SCORECARD_KEYS')
    if scorecard.get('spec_version') != spec['spec_version']:
        problems.append('SPEC_VERSION')
    if [c['id'] for c in scorecard.get('checks', [])] != [check_id(*c) for c in catalogue(spec)]:
        problems.append('CATALOGUE')
    if scorecard.get('points', {}).get('points') != sum(1 for c in scorecard.get('checks', []) if c['status'] == 'PASSED'):
        problems.append('POINTS')
    if any(c['status'] not in spec['status_order'] for c in scorecard.get('checks', [])):
        problems.append('STATUS')
    return problems


# ---- rendering -----------------------------------------------------------------------------------------------------------------------

def _md(value):
    value = '—' if value is None else str(value)
    value = value.replace('\\', '\\\\').replace('\n', ' ').replace('\r', ' ').replace('`', "'")
    for char in ('[', ']', '!', '*', '_', '#', '|'):
        value = value.replace(char, '\\' + char)
    return value.replace('<', '&lt;').replace('>', '&gt;')


def _num(value, suffix=''):
    return '—' if value is None else (format(value, '.1f').replace('.', ',') if isinstance(value, float) else str(value)) + suffix


def _table(columns, rows):
    return ['| ' + ' | '.join(columns) + ' |', '|' + '---|' * len(columns)] + ['| ' + ' | '.join(_md(v) if isinstance(v, str) else _num(v) for v in row) + ' |' for row in rows]


def render(scorecard, spec=None):
    """The report as Markdown lines, only from the scorecard and the specification."""
    spec = spec or load_spec()
    cols, titles = spec['columns'], {s['id']: s['title'] for s in spec['sections']}
    status, run, points, counts, rates = spec['status_labels'], scorecard['run'], scorecard['points'], scorecard['counts'], scorecard['rates']
    result = scorecard['result']
    stages_run = sum(1 for s in scorecard['stages'] if s['stage_result'] != 'NOT_RUN')
    stop = run['stop_reason']
    lines = ['# NSN014 Punktebericht', '',
             f"Spezifikation {_md(scorecard['spec_id'])} {_md(scorecard['spec_version'])} (SHA256 {_md(scorecard['spec_sha256'])}). "
             + _md(spec['notes']['intro'].format(max_points=points['max_points'])), '',
             f"- Lauf: {_md(run['run_id'])}; Suite {_md(run['suite_id'])} v{_md(run['suite_version'])}; Bewertung {_md(run['scoring_version'])}; UX-Rubrik {_md(run['rubric_version'])}",
             f"- Executor: {_md(run['executor_model'])}; Reviewer: {_md(run['reviewer_model'])}; SQBF-Commit {_md(run['sqbf_commit'])}; BLE-Build {_md(run['software_version'])}", '']
    lines += [f"## 1. {titles['1']}", '']
    lines += _table(cols['kennzahlen'], [
        ['Ergebnis des Laufs', spec['run_result']['labels'][result['run_result']]],
        ['Lauf bestanden', 'ja' if result['bestanden'] else 'nein'],
        ['Gründe für das Ergebnis', '; '.join(result['reasons'])],
        ['Punkte', f"{points['points']} von {points['max_points']}"],
        ['Punkte in Prozent', _num(rates['points_percent'], ' %')],
        ['Objektiv entschiedene Prüfpunkte', f"{counts['PASSED'] + counts['FAILED']} von {points['max_points']} ({_num(rates['coverage_percent'], ' %')})"],
        ['Bestanden unter den entschiedenen', _num(rates['pass_rate_of_decided_percent'], ' %')]] +
        [[status[s], counts[s]] for s in spec['status_order']] +
        [['Stufen ausgeführt', f"{stages_run} von {len(scorecard['stages'])}"],
         ['Abbruchgrund', spec['stop_labels'].get(stop, stop) if stop else None],
         ['Speicherquote', _num(rates['save_rate_percent'], ' %')],
         ['Technischer Status', run['technical_status']],
         ['Kritischer Stopp', run['critical_stop']],
         ['Art des Laufs', spec['run_kinds'].get(run.get('kind', 'BENCHMARK'), run.get('kind'))]]) + ['']
    lines += [f"## 2. {titles['2']}", '']
    lines += _table(cols['stages'], [[s['stage'], s['label'], s['stage_result'], f"{s['points']} von {s['checks']}"] + [s['counts'][k] for k in spec['status_order']]
                                     for s in scorecard['stages']] +
                    [['Summe', '', '', f"{points['points']} von {points['max_points']}"] + [counts[k] for k in spec['status_order']]]) + ['']
    lines += [f"## 3. {titles['3']}", '']
    lines += _table(cols['origins'], [[o, spec['origin_labels'][o], scorecard['origins'][o]] for o in spec['origin_order']]) + ['', _md(spec['notes']['origin']), '']
    lines += [f"## 4. {titles['4']}", '']
    lines += _table(cols['checks'], [[c['id'], status[c['status']], c['origin'], c['detail']] for c in scorecard['checks']]) + ['']
    op = scorecard['operating']
    lines += [f"## 5. {titles['5']}", '']
    lines += _table(cols['operating'], [['Aufgaben mit Bedienmessung', op['tasks_measured']]] +
                    [[spec['reached_labels'][k], op['modules_reached'][k]] for k in spec['reached_labels']] +
                    [[spec['operating_labels'][k], op['totals'][k]] for k in OPERATING_KEYS] +
                    [[f"Speichern: {spec['save_labels'].get(k, k)}", v] for k, v in op['saves'].items()] +
                    [['Speicherquote', _num(op['save_rate_percent'], ' %')]]) + ['']
    cost = scorecard['cost']
    lines += [f"## 6. {titles['6']}", '']
    lines += _table(cols['cost'], [['Modellanfragen', cost['model_calls']], ['Anfragen Executor', cost['executor_calls']], ['Anfragen Reviewer', cost['reviewer_calls']],
                                   ['Laufzeit in Sekunden', cost['elapsed_seconds']], ['Modell-Wartezeit in Sekunden', cost['model_wait_seconds']],
                                   ['Tokens (bekannte Summe)', cost['tokens_known_sum']], ['Anfragen ohne Tokenangabe', cost['tokens_unknown_calls']]]) + ['']
    lines += [f"## 7. {titles['7']}", '']
    lines += _table(cols['comparability'], [[key, value] for key, value in scorecard['comparability'].items()]) + [
        '', _md(spec['notes']['comparability']), '']
    rv = scorecard['reviewer_observations']
    lines += [f"## 8. {titles['8']}", '', f"Reviewer-Antworten: {rv['reviews']}; ausgefallene Reviews: {rv['review_errors']}. {_md(spec['notes']['reviewer'])}", '']
    lines += _table(cols['reviewer_verdicts'], [[v, n] for v, n in rv['verdicts'].items()]) + ['']
    lines += _table(cols['reviewer_scores'], [[name, s['n'], s['min'], s['mean'], s['max']] for name, s in rv['scores'].items()]) + ['']
    lines += _table(cols['reviewer_findings'], [[category] + [counts_[s] for s in SEVERITIES] for category, counts_ in rv['findings'].items()]) + ['']
    if run.get('kind', 'BENCHMARK') != 'BENCHMARK':
        lines += [_md(spec['notes']['no_reviewer']), '']
    lines += [f"## 9. {titles['9']}", '']
    lines += _table(cols['consistency'], [[rule, scorecard['consistency']['counts'][rule]] for rule in spec['consistency_rules']])
    lines += ['', 'Befunde: ' + (_md('; '.join(f"{f['rule']} {f['item']}" for f in scorecard['consistency']['findings'])) if scorecard['consistency']['findings'] else 'keine'), '']
    lines += [f"Prüfsumme der Punktekarte (SHA256): {canonical_hash(scorecard)}"]
    return lines


# ---- comparison of two runs ------------------------------------------------------------------------------------------------------------

def compare(a, b):
    """Fixed comparison of two scorecards: comparable only if all comparability values are equal; the numbers are given in any case."""
    # Not recorded is not equal: a run without a value cannot prove the same conditions (runs 5 and 6 had no instruction hash).
    differing = [key for key in a['comparability'] if a['comparability'][key] is None or b['comparability'].get(key) is None
                 or a['comparability'][key] != b['comparability'].get(key)]
    changed = [{'id': x['id'], 'a': x['status'], 'b': y['status']} for x, y in zip(a['checks'], b['checks']) if x['status'] != y['status']]
    return {'comparable': not differing, 'differing_keys': differing, 'run_a': a['run']['run_id'], 'run_b': b['run']['run_id'],
            'points_a': a['points']['points'], 'points_b': b['points']['points'], 'delta_points': b['points']['points'] - a['points']['points'],
            'delta_points_percent': None if None in (a['rates']['points_percent'], b['rates']['points_percent'])
            else float((Decimal(str(b['rates']['points_percent'])) - Decimal(str(a['rates']['points_percent']))).quantize(Decimal('0.1'))),
            'checks_changed': changed}

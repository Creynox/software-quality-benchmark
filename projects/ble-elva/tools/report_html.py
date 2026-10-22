"""Human-readable NSN014 report (bericht.html) and overview of all runs (uebersicht.html), rendered only from scorecards (PO decision 2026-10-21).

Built like the daily development dashboard the PO uses: dark header, status card, the most important points, segmented bars (one segment per
check), changes since the previous run, open checks by cause in plain language, key figures, open decisions, checklist, next steps, and at
the end the criteria of every check per stage and a glossary (PO feedback 2026-10-22). Machine data stays in scorecard.json. Email-safe:
tables and inline styles only, no scripts, no external files or fonts. Every text is fixed by the report specification (section `html`),
every number comes from the scorecard, the open decisions come from projects/ble-elva/decisions.json.
"""
import html
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from sqbf.suites import canonical_hash

from . import report_spec

DECISIONS_PATH = Path(__file__).resolve().parents[1] / 'decisions.json'
MONTHS = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
FONT = "font-family:'Segoe UI',Arial,Helvetica,sans-serif;"
WIDTH, INNER, GAP = 640, 584, 3
STATUS_COLORS = {'PASSED': '#1f7a6d', 'FAILED': '#b42318', 'NOT_DECIDED': '#e0b13f', 'NOT_RUN': '#d0d5dd', 'INVALID': '#475467'}
RESULT_STYLES = {'BESTANDEN': ('#ecfdf3', '#abefc6', '#067647'), 'UNVOLLSTAENDIG': ('#fffaeb', '#fedf89', '#b54708'),
                 'ABGEBROCHEN': ('#fff4ed', '#f9dbaf', '#c4320a'), 'NICHT_BESTANDEN': ('#fef3f2', '#fecdca', '#b42318'),
                 'UNGUELTIG': ('#f2f4f7', '#d0d5dd', '#344054')}
STAGE_STATE_COLORS = {'PASSED': '#1f7a6d', 'PARTLY': '#b54708', 'OPEN': '#93370d', 'FAILED': '#b42318', 'NOT_RUN': '#667085', 'INVALID': '#344054'}
ORIGIN_BADGES = {'BLE-ABWEICHUNG': ('#fee4e2', '#b42318'), 'UNGUELTIG': ('#eaecf0', '#344054'), 'SUITE': ('#fee4e2', '#b42318'),
                 'PROVIDER': ('#fef0c7', '#b54708'), 'NICHT_AUSGEFUEHRT': ('#f2f4f7', '#475467'), 'VORSTUFE': ('#eff8ff', '#175cd3'),
                 'MODELL/SUITE': ('#fef0c7', '#b54708'), 'MODELL': ('#f2f4f7', '#344054'), 'UNKLAR': ('#f2f4f7', '#475467')}
KIND_SHORT = {'BENCHMARK': 'Benchmark', 'REHEARSAL': 'Probelauf', 'DRY_RUN': 'Trockenlauf'}
LEVEL_COLORS = {'critical': '#b42318', 'important': '#b54708', 'good': '#1f7a6d', 'note': '#475467'}
MARKS = {True: ('&#10003;', '#1f7a6d'), False: ('&#10007;', '#b42318'), 'warn': ('!', '#b54708'), None: ('&#8211;', '#98a2b3')}
SAVE_OUTCOMES = ('SAVED', 'SAVE_CLICK_REJECTED', 'NOT_SAVED_AFTER_ENTRY', 'NOT_SAVED_PARTIAL_ENTRY', 'NOT_REACHED')
SOFT_ORIGINS = ('MODELL', 'MODELL/SUITE', 'VORSTUFE', 'UNKLAR')


# ---- formatting -------------------------------------------------------------------------------------------------------------------------------

def _e(value):
    return '—' if value is None else html.escape(str(value), quote=True)


def _n(value, suffix=''):
    if value is None:
        return '—'
    if isinstance(value, float):
        return format(Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP), 'f').replace('.', ',') + suffix
    return format(value, ',').replace(',', '.') + suffix


def _date(iso):
    if not iso or len(str(iso)) < 16:
        return '—'
    text = str(iso)
    year, month, day, clock = int(text[0:4]), int(text[5:7]), int(text[8:10]), text[11:16]
    return f'{day}. {MONTHS[month - 1]} {year}, {clock} UTC'


def _short_date(iso):
    return '—' if not iso or len(str(iso)) < 10 else f'{str(iso)[8:10]}.{str(iso)[5:7]}.{str(iso)[0:4]}'


def _duration(seconds):
    if seconds is None:
        return '—'
    minutes = int(Decimal(seconds) / 60 + Decimal('0.5'))
    return f'{minutes // 60} Std. {minutes % 60} Min.' if minutes >= 60 else f'{minutes} Min.'


def _count(spec, word, n):
    singular, plural = spec['html']['words'][word]
    return f"{_n(n)} {singular if n == 1 else plural}"


def check_label(spec, check):
    label = spec['stage_labels'].get(check['stage'], check['stage'])
    return label if check['position'] is None else label + ' ' + check['position']


def comparability_group(card):
    values = {k: v for k, v in card['comparability'].items() if k != 'spec_version'}
    return 'unvollständig' if any(v is None for v in values.values()) else canonical_hash(values)[:8]


# ---- building blocks ------------------------------------------------------------------------------------------------------------------------

def _card(title, body, hint=None, *, hint_color='#667085', hint_weight=400):
    hint_html = f'<span style="font-size:13px;font-weight:{hint_weight};color:{hint_color};"> · {_e(hint)}</span>' if hint else ''
    return (f'<tr><td style="padding:0 28px 16px 28px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid #eaecf0;border-radius:8px;"><tr><td style="padding:18px 20px;">'
            f'<div style="{FONT}font-size:17px;font-weight:700;color:#101828;margin:0 0 12px 0;">{_e(title)}{hint_html}</div>{body}'
            f'</td></tr></table></td></tr>')


def _segments(colors, width=INNER - 40):
    count = len(colors)
    if not count:
        return ''
    size = (width - GAP * (count - 1)) // count
    cells = []
    for index, color in enumerate(colors):
        own = size if index < count - 1 else width - GAP * (count - 1) - size * (count - 1)
        cells.append(f'<td style="width:{own}px;height:8px;background:{color};font-size:0;line-height:0;border-radius:2px;">&nbsp;</td>')
        if index < count - 1:
            cells.append(f'<td style="width:{GAP}px;font-size:0;line-height:0;">&nbsp;</td>')
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="width:{width}px;border-collapse:separate;"><tr>'
            + ''.join(cells) + '</tr></table>')


def _badge(origin, spec):
    background, color = ORIGIN_BADGES.get(origin, ('#f2f4f7', '#344054'))
    return (f'<span style="{FONT}display:inline-block;padding:2px 8px;border-radius:4px;background:{background};color:{color};font-size:12px;'
            f'font-weight:700;white-space:nowrap;">{_e(spec["html"]["origin_short"].get(origin, origin))}</span>')


def stage_state(stage):
    counts = stage['counts']
    if counts['INVALID']:
        return 'INVALID'
    if counts['FAILED']:
        return 'FAILED'
    if counts['NOT_RUN'] == stage['checks']:
        return 'NOT_RUN'
    if counts['PASSED'] == stage['checks']:
        return 'PASSED'
    return 'PARTLY' if counts['PASSED'] else 'OPEN'


def _origin_counts(spec, checks):
    counts = {}
    for check in checks:
        if check['status'] != 'PASSED':
            counts[check['origin'] or 'UNKLAR'] = counts.get(check['origin'] or 'UNKLAR', 0) + 1
    order = spec['html']['origin_priority']
    return sorted(counts.items(), key=lambda item: order.index(item[0]) if item[0] in order else len(order))


def open_groups(spec, card):
    """Non-passed checks grouped by cause and stage, in the fixed priority of causes and the stage order."""
    groups = {}
    for check in card['checks']:
        if check['status'] != 'PASSED':
            groups.setdefault((check['origin'] or 'UNKLAR', check['stage']), []).append(check)
    priority, stages = spec['html']['origin_priority'], spec['stage_order']
    return sorted(groups.items(), key=lambda item: (priority.index(item[0][0]) if item[0][0] in priority else len(priority), stages.index(item[0][1])))


def checklist(spec, card, *, comparison=None, gates=None):
    """(id, done or None when not applicable, title, detail) in the fixed order of the specification."""
    gates = gates or {}
    counts, origins, run = card['counts'], card['origins'], card['run']
    stages_run = sum(1 for s in card['stages'] if s['stage_result'] != 'NOT_RUN')
    consistency = sum(card['consistency']['counts'].values())
    benchmark = run.get('kind', 'BENCHMARK') == 'BENCHMARK'
    if comparison is None:
        compared = (None, 'kein Vorlauf dieser Art')
    else:
        compared = (comparison['comparable'], 'ja' if comparison['comparable'] else 'abweichend: ' + ', '.join(comparison['differing_keys']))
    dry = gates.get('dry_runs')
    values = {
        'all_stages_run': (stages_run == len(card['stages']), {'stages_run': stages_run, 'stages': len(card['stages'])}),
        'no_invalid': (counts['INVALID'] == 0, {'count': _count(spec, 'check', counts['INVALID'])}),
        'no_suite_fault': (origins.get('SUITE', 0) == 0, {'count': _count(spec, 'check', origins.get('SUITE', 0))}),
        'no_provider_fault': (origins.get('PROVIDER', 0) == 0, {'count': _count(spec, 'check', origins.get('PROVIDER', 0))}),
        'consistent': (consistency == 0, {'findings': _count(spec, 'finding', consistency)}),
        'reviewer_complete': (card['reviewer_observations']['review_errors'] == 0 if benchmark else None,
                              {'reviews': _count(spec, 'review', card['reviewer_observations']['review_errors'])}),
        'comparable': (compared[0], {'comparison': compared[1]}),
        'dry_runs': (dry, {'dry_runs': {True: 'sauber und mit Fehlerinjektion bestanden', False: 'nicht bestanden', None: 'nicht erfasst'}[dry]}),
        'run_passed': (card['result']['bestanden'], {'points': card['points']['points'], 'max_points': card['points']['max_points']})}
    items = []
    for key, (title, detail) in spec['html']['checklist'].items():
        done, fields = values[key]
        items.append((key, done, title, detail.format(**fields)))
    return items


def next_steps(spec, card):
    texts, label = spec['html']['next_steps'], {s['stage']: s['label'] for s in card['stages']}
    steps = []
    failed = [check_label(spec, c) for c in card['checks'] if c['status'] == 'FAILED']
    if failed:
        steps.append(texts['failed'].format(checks=', '.join(failed)))
    for (origin, stage), checks in open_groups(spec, card):
        if origin == 'SUITE':
            details = ', '.join(dict.fromkeys(str(c['detail']) for c in checks if c['detail'])) or '—'
            steps.append(texts['suite'].format(stage=label[stage], detail=details, count=_count(spec, 'check', len(checks))))
    invalid = [s['label'] for s in card['stages'] if s['counts']['INVALID']]
    if invalid:
        steps.append(texts['invalid'].format(stages=', '.join(invalid)))
    if card['origins'].get('PROVIDER'):
        steps.append(texts['provider'].format(count=_count(spec, 'check', card['origins']['PROVIDER'])))
    not_run = [s['label'] for s in card['stages'] if s['stage_result'] == 'NOT_RUN']
    if not_run:
        steps.append(texts['not_run'].format(stages=', '.join(not_run)))
    unsaved = (card['operating']['saves'] or {}).get('NOT_SAVED_AFTER_ENTRY')
    if unsaved:
        steps.append(texts['unsaved'].format(tasks=_count(spec, 'task', unsaved)))
    if card['consistency']['findings']:
        steps.append(texts['consistency'].format(findings=_count(spec, 'finding', len(card['consistency']['findings']))))
    kind = card['run'].get('kind', 'BENCHMARK')
    final = texts['rehearsal'] if kind == 'REHEARSAL' else texts['next_benchmark'] if kind == 'BENCHMARK' and not card['result']['bestanden'] else None
    limit = spec['html']['next_steps_limit']
    if final:
        return steps[:limit - 1] + [final]
    return steps[:limit]


def anchor(stage):
    return 'stufe-' + stage.replace('NSN014-', '').lower()


def cause_key(spec, origin, detail):
    """The entry of the cause texts for an open check: origin with class first, then the class alone, then the origin."""
    causes = spec['html']['causes']
    code = str(detail).split(':')[0] if detail else None
    for key in ((origin + ':' + code) if code else None, code, origin):
        if key and key in causes:
            return key
    return 'UNKLAR'


def cause_groups(spec, card):
    """Open checks grouped by cause across the stages: ((origin, cause key), checks), in the fixed origin priority, then larger groups first."""
    groups = {}
    for check in card['checks']:
        if check['status'] != 'PASSED':
            origin = check['origin'] or 'UNKLAR'
            groups.setdefault((origin, cause_key(spec, origin, check['detail'])), []).append(check)
    priority, stages = spec['html']['origin_priority'], spec['stage_order']
    return sorted(groups.items(), key=lambda item: (priority.index(item[0][0]) if item[0][0] in priority else len(priority), -len(item[1]),
                                                     stages.index(item[1][0]['stage'])))


def where(spec, checks):
    """(stage, stage label with the positions of the checks) in stage order."""
    places = {}
    for check in checks:
        places.setdefault(check['stage'], []).append(check['position'])
    ordered = sorted(places.items(), key=lambda item: spec['stage_order'].index(item[0]))
    return [(stage, spec['stage_labels'][stage] + (' ' + ', '.join(p for p in positions if p) if any(positions) else '')) for stage, positions in ordered]


def summary_items(spec, card):
    """The critical, important and good points of the run by fixed rules, critical first: [(level, text)]."""
    texts, causes, counts, checks = spec['html']['summary'], spec['html']['causes'], card['counts'], card['checks']
    critical, important, good = [], [], []
    failed = [c for c in checks if c['status'] == 'FAILED']
    if failed:
        critical.append(texts['critical_failed'].format(count=_count(spec, 'check', len(failed)), checks=', '.join(check_label(spec, c) for c in failed)))
    invalid = [s['label'] for s in card['stages'] if s['counts']['INVALID']]
    if invalid:
        critical.append(texts['critical_invalid'].format(stages=', '.join(invalid)))
    suite = [c for c in checks if c['status'] != 'PASSED' and c['origin'] == 'SUITE']
    if suite:
        names = ', '.join(dict.fromkeys(causes[cause_key(spec, 'SUITE', c['detail'])]['name'] for c in suite))
        critical.append(texts['critical_suite'].format(count=_count(spec, 'check', len(suite)), where='; '.join(t for _, t in where(spec, suite)), causes=names))
    provider = [c for c in checks if c['status'] != 'PASSED' and c['origin'] == 'PROVIDER']
    if provider:
        critical.append(texts['critical_provider'].format(count=_count(spec, 'check', len(provider))))
    if counts['NOT_RUN']:
        critical.append(texts['critical_not_run'].format(count=_count(spec, 'check', counts['NOT_RUN']),
                                                         stages=', '.join(s['label'] for s in card['stages'] if s['counts']['NOT_RUN'])))
    soft = [(key, group) for key, group in cause_groups(spec, card) if key[0] in SOFT_ORIGINS]
    if soft:
        (origin, key), group = max(soft, key=lambda item: len(item[1]))  # among equal sizes the first in the fixed order
        important.append(texts['important_cause'].format(count=_count(spec, 'check', len(group)), cause=causes[key]['name'],
                                                         origin=spec['html']['origin_short'].get(origin, origin)))
    unsaved = (card['operating']['saves'] or {}).get('NOT_SAVED_AFTER_ENTRY')
    if unsaved:
        important.append(texts['important_saves'].format(tasks=_count(spec, 'task', unsaved), rate=_n(card['rates']['save_rate_percent'], ' %')))
    over = [s['label'] for s in card['stages'] if (s.get('time') or {}).get('over_time_mark')]
    if over:
        important.append(texts['important_marks'].format(count=len(over), stages=len(card['stages']), labels=', '.join(over)))
    if not failed:
        decided = counts['PASSED'] + counts['FAILED']
        good.append(texts['good_no_deviation'].format(decided=decided) if decided else texts['good_no_deviation_none'])
    full = [s['label'] for s in card['stages'] if stage_state(s) == 'PASSED']
    if full:
        good.append(texts['good_stages'].format(stages=', '.join(full)))
    note = texts['kind_note'].get(card['run'].get('kind', 'BENCHMARK'))
    items = ([('critical', t) for t in critical] + [('important', t) for t in important] + [('good', t) for t in good])
    return items[:texts['limit'] - (1 if note else 0)] + ([('note', note)] if note else [])


def _task_name(spec, check, task, several):
    kind = spec['html']['details']['kind_labels'].get(task.get('kind'), task.get('kind')) if several and task.get('kind') else None
    return ' '.join(x for x in (check['position'], kind) if x)


def _rejections(spec, tasks, limit=3):
    """Rejected actions as plain text with their count: Klick „label“ (reason)."""
    d = spec['html']['details']
    counted = {}
    for task in tasks:
        for item in task['rejected']:
            text = d['action_labels'].get(item['action'], item['action'] or '?')
            if item['label']:
                text += f' „{item["label"]}“'
            reason = d['rejection_reasons'].get(item['reason']) or d['rejection_labels'].get(item['code'], item['code'])
            text += f' ({reason})' if reason else ''
            counted[text] = counted.get(text, 0) + 1
    parts = [(f'{n}× ' if n > 1 else '') + text for text, n in counted.items()]
    return '; '.join(parts[:limit]) + (' …' if len(parts) > limit else '')


def _seconds(seconds):
    return '—' if seconds is None else f'{seconds} Sek.' if seconds < 60 else _duration(seconds)


def stage_criteria(spec, card, stage):
    """Criteria lines of one stage: (state, label, text) with state True, False, 'warn' or None (only shown).

    A passed check counts as fulfilled in every criterion: the independent Oracle confirmed its values in BLE, even where the harness saw a
    pre-filled field or no click on Speichern (live rehearsal lauf-09, Kornform P09 and P10)."""
    d = spec['html']['details']
    labels = d['criteria']
    checks = [c for c in card['checks'] if c['stage'] == stage['stage']]
    tasks = [(c, t) for c in checks for t in (c.get('criteria') or {}).get('tasks', [])]
    several = len({t.get('kind') for _, t in tasks}) > 1
    lines = []

    def add(label, items, note=None, open_text='open'):
        done = sum(1 for _, ok, _ in items if ok)
        text = d['of'].format(n=done, total=len(items))
        bad = [name + (f' ({why})' if why else '') for name, ok, why in items if not ok and name]
        if bad:
            text += ' · ' + d[open_text].format(items=', '.join(dict.fromkeys(bad)))
        elif done < len(items):
            text += ' · ' + '; '.join(dict.fromkeys(why for _, ok, why in items if not ok and why))
        lines.append((done == len(items), label, text + (f' · {note}' if note else '')))

    def judged(c, ok, why):
        return (True, None) if c['status'] == 'PASSED' else (ok, None if ok else why)

    finished = [(_task_name(spec, c, t, several),) + judged(c, t['finished'] == 'DONE', d['finished_labels'].get(t['finished'], t['finished']))
                for c, t in tasks if t['finished']]
    if finished:
        add(labels['finished'], finished)
    reached = [(_task_name(spec, c, t, several),) + judged(c, t['reached'], None) for c, t in tasks if t['reached'] is not None]
    if reached:
        add(labels['reached'], reached)
    entered = [(_task_name(spec, c, t, several),) + judged(c, t['entered'][0] >= t['entered'][1], f'{t["entered"][0]} von {t["entered"][1]}')
               for c, t in tasks if t['entered']]
    if entered:
        add(labels['entered'], entered)
    values = [(c['position'] or '', (c.get('criteria') or {}).get('values') == 'MATCH', None) for c in checks if (c.get('criteria') or {}).get('values')]
    if values:
        expected = any((c.get('criteria') or {}).get('values') == 'MISMATCH' and c['status'] != 'FAILED' for c in checks)
        add(labels['values'], values, d['mismatch_note'] if expected else None, 'deviating')
    saves = [(_task_name(spec, c, t, several),) + judged(c, t['saved'] == 'SAVED', spec['save_labels'].get(t['saved'], t['saved']))
             for c, t in tasks if t['saved'] in SAVE_OUTCOMES]
    if saves:
        add(labels['saved'], saves)
    if tasks:
        count = sum(len(t['rejected']) for _, t in tasks)
        lines.append((None, labels['rejected'], f'{count}: ' + _rejections(spec, [t for _, t in tasks]) if count else d['none']))
    time = stage.get('time')
    if time:
        for key, actual, mark, over in (('time', _seconds(time['seconds']), _seconds(time['mark_seconds']), time['over_time_mark']),
                                        ('actions', _n(time['actions']), _n(time['mark_actions']), time['over_action_mark'])):
            state = d['mark_states']['over' if over else 'within']
            lines.append(('warn' if over else None, labels[key], d['mark'].format(actual=actual, mark=mark, state=state)))
    return lines


def stage_fazit(spec, card, stage):
    """One fixed sentence per stage from its checks and its time."""
    d, causes = spec['html']['details'], spec['html']['causes']
    checks = [c for c in card['checks'] if c['stage'] == stage['stage']]
    open_ = [c for c in checks if c['status'] != 'PASSED']
    if not open_:
        text = d['fazit_all'].format(checks=len(checks)) if len(checks) > 1 else d['fazit_all_single']
    else:
        counted = {}
        for check in open_:
            key = cause_key(spec, check['origin'] or 'UNKLAR', check['detail'])
            counted[key] = counted.get(key, 0) + 1
        cause = causes[max(counted, key=counted.get)]['name']
        positions = ', '.join(c['position'] for c in open_ if c['position'])
        text = (d['fazit_open'].format(passed=stage['counts']['PASSED'], checks=len(checks), positions=positions, cause=cause) if positions
                else d['fazit_open_single'].format(cause=cause))
    failed = stage['counts']['FAILED']
    text += d['fazit_failed'].format(count=_count(spec, 'check', failed)) if failed else d['fazit_no_deviation']
    if (stage.get('time') or {}).get('over_time_mark'):
        text += d['fazit_over_mark']
    return text


def check_lines(spec, card, stage):
    """(state, text, detail lines) per not passed check of a stage, after one line with the passed ones."""
    d, causes = spec['html']['details'], spec['html']['causes']
    checks = [c for c in card['checks'] if c['stage'] == stage['stage']]
    passed = [c for c in checks if c['status'] == 'PASSED']
    several = len({t.get('kind') for c in checks for t in (c.get('criteria') or {}).get('tasks', [])}) > 1
    lines = []
    if passed:
        positions = ', '.join(c['position'] for c in passed if c['position'])
        lines.append((True, d['passed'].format(positions=positions) if positions else d['passed_single'], []))
    for check in checks:
        if check['status'] == 'PASSED':
            continue
        origin = check['origin'] or 'UNKLAR'
        text = d['check'].format(position=check['position'] or d['single_task'], status=spec['status_labels'][check['status']],
                                 origin=spec['html']['origin_short'].get(origin, origin), cause=causes[cause_key(spec, origin, check['detail'])]['name'])
        details = []
        for task in (check.get('criteria') or {}).get('tasks', []):
            parts = []
            if task['entered']:
                parts.append(d['entered'].format(done=task['entered'][0], required=task['entered'][1]))
            if task['saved'] in SAVE_OUTCOMES:
                parts.append(spec['save_labels'].get(task['saved'], task['saved']))
            if task['finished']:
                parts.append(d['finished_labels'].get(task['finished'], task['finished']))
            if task['actions'] is not None:
                parts.append(d['effort'].format(actions=task['actions'], scrolls=_n(task['scrolls'])))
            if task['rejected']:
                parts.append(d['rejected'].format(items=_rejections(spec, [task])))
            kind = d['kind_labels'].get(task.get('kind'), task.get('kind')) if several and task.get('kind') else None
            details.append((kind + ': ' if kind else '') + ' · '.join(parts))
        lines.append((False if check['status'] in ('FAILED', 'NOT_DECIDED', 'INVALID') else None, text, details))
    return lines


def _option(option):
    return (option, None) if isinstance(option, str) else (option.get('label'), option.get('effect'))


# ---- the report of one run ------------------------------------------------------------------------------------------------------------------

def render_report(card, *, spec=None, previous=None, decisions=None, gates=None, links=None):
    spec = spec or report_spec.load_spec()
    h, run, points, counts = spec['html'], card['run'], card['points'], card['counts']
    result = card['result']['run_result']
    kind = run.get('kind', 'BENCHMARK')
    titles = h['section_titles']
    comparison = report_spec.compare(previous, card) if previous else None
    links = links if links is not None else {'details': 'completion-report.md', 'points': 'punktebericht.md', 'scorecard': 'scorecard.json',
                                             'overview': '../uebersicht.html'}
    rows = []
    subtitle = f'Lauf {_e(run["run_id"])} · {_e(_date(run.get("completed_at")))} · Suite {_e(run.get("suite_version"))}'
    rows.append(f'<tr><td style="background:#0f1f33;padding:24px 28px;"><div style="{FONT}font-size:12px;letter-spacing:1.5px;font-weight:700;color:#5fd1c1;">'
                f'{_e(h["brand"])}</div><div style="{FONT}font-size:26px;font-weight:700;color:#ffffff;margin:6px 0 4px 0;">{_e(h["title"])}</div>'
                f'<div style="{FONT}font-size:13px;color:#cfd8e3;">{subtitle}</div>'
                f'<div style="{FONT}font-size:13px;color:#cfd8e3;">Executor {_e(run.get("executor_model"))} · Reviewer {_e(run.get("reviewer_model"))}</div></td></tr>')
    if kind != 'BENCHMARK':
        rows.append(f'<tr><td style="background:#fffaeb;padding:10px 28px;{FONT}font-size:13px;font-weight:700;color:#b54708;">'
                    f'{_e(spec["run_kinds"].get(kind, kind))}</td></tr>')
    rows.append('<tr><td style="height:20px;font-size:0;line-height:0;">&nbsp;</td></tr>')
    # status card
    background, border, color = RESULT_STYLES[result]
    stages_run = sum(1 for s in card['stages'] if s['stage_result'] != 'NOT_RUN')
    stop = ''
    if run.get('critical_stop'):
        stage_id, _, reason = str(run['critical_stop']).partition(': ')
        stop = h['stop_sentence'].format(stage=spec['stage_labels'].get(stage_id, stage_id), reason=reason or '—')
    sentence = h['result_sentences'][result].format(max_points=points['max_points'], failed=counts['FAILED'], stages_run=stages_run,
                                                    stages=len(card['stages']), stop=stop, open=counts['NOT_DECIDED'], invalid=counts['INVALID']).strip()
    sentence += ' ' + h['deviation_sentence'].format(failed=counts['FAILED'])
    rows.append(f'<tr><td style="padding:0 28px 16px 28px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                f'style="background:{background};border:1px solid {border};border-radius:8px;"><tr><td style="padding:16px 20px;">'
                f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
                f'<td style="{FONT}font-size:19px;font-weight:700;color:{color};">&#9679; {_e(spec["run_result"]["labels"][result].upper())}</td>'
                f'<td align="right" style="{FONT}font-size:14px;font-weight:700;color:{color};">{_n(points["points"])} von {_n(points["max_points"])} Punkten'
                f' · {_n(card["rates"]["points_percent"], " %")}</td></tr></table>'
                f'<div style="{FONT}font-size:14px;color:#344054;margin-top:8px;line-height:1.45;">{_e(sentence)}</div></td></tr></table></td></tr>')
    # the most important points
    levels = h['summary']['levels']
    body = ''.join(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid #f2f4f7;"><tr>'
                   f'<td valign="top" width="84" style="{FONT}padding:7px 8px 7px 0;"><span style="display:inline-block;padding:2px 7px;border-radius:4px;'
                   f'background:{LEVEL_COLORS[level]};color:#ffffff;font-size:11px;font-weight:700;">{_e(levels[level])}</span></td>'
                   f'<td style="{FONT}font-size:14px;color:#101828;padding:7px 0;line-height:1.45;">{_e(text)}</td></tr></table>'
                   for level, text in summary_items(spec, card))
    rows.append(_card(titles['summary'], body))
    # stages
    body = []
    for stage in card['stages']:
        state = stage_state(stage)
        checks = [c for c in card['checks'] if c['stage'] == stage['stage']]
        detail = h['stage_line'].format(passed=stage['counts']['PASSED'], checks=stage['checks'])
        open_ = _origin_counts(spec, checks)
        if open_:
            detail += ' · offen: ' + ', '.join(f'{n} {h["origin_short"].get(o, o)}' for o, n in open_)
        body.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 10px 0;"><tr>'
                    f'<td style="{FONT}font-size:14px;font-weight:700;color:#101828;padding-bottom:6px;"><a href="#{anchor(stage["stage"])}" '
                    f'style="color:#101828;text-decoration:none;">{_e(stage["label"])}</a></td>'
                    f'<td align="right" style="{FONT}font-size:13px;font-weight:700;color:{STAGE_STATE_COLORS[state]};padding-bottom:6px;">'
                    f'{_e(h["stage_states"][state])}</td></tr><tr><td colspan="2">{_segments([STATUS_COLORS[c["status"]] for c in checks])}</td></tr>'
                    f'<tr><td colspan="2" style="{FONT}font-size:12px;color:#667085;padding-top:5px;">{_e(detail)}</td></tr></table>')
    body.append(f'<div style="{FONT}font-size:11px;color:#98a2b3;border-top:1px solid #f2f4f7;padding-top:8px;">{_e(h["legend"])}</div>')
    rows.append(_card(titles['stages'], ''.join(body), titles['stages_hint']))
    # changes
    if comparison is None:
        body = f'<div style="{FONT}font-size:13px;color:#667085;">{_e(h["changes_none_previous"])}</div>'
    else:
        labels = {c['id']: check_label(spec, c) for c in card['checks']}
        gained = [labels[c['id']] for c in comparison['checks_changed'] if c['b'] == 'PASSED']
        lost = [labels[c['id']] for c in comparison['checks_changed'] if c['a'] == 'PASSED']
        note = (h['changes_comparable'].format(run=comparison['run_a']) if comparison['comparable']
                else h['changes_not_comparable'].format(run=comparison['run_a'], keys=', '.join(comparison['differing_keys'])))
        columns = ''.join(f'<td width="50%" valign="top" style="{FONT}padding-right:12px;"><div style="font-size:12px;font-weight:700;color:#475467;'
                          f'margin-bottom:4px;">{_e(title)}</div><div style="font-size:14px;color:#101828;line-height:1.5;">'
                          f'{"<br>".join(_e(x) for x in items) if items else "—"}</div></td>'
                          for title, items in zip(h['changes_columns'], (gained, lost)))
        body = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{columns}</tr></table>'
                f'<div style="{FONT}font-size:12px;color:#667085;margin-top:10px;">{_e(note)} Punkte: {_n(comparison["points_a"])} → '
                f'{_n(comparison["points_b"])}.</div>')
    rows.append(_card(titles['changes'], body))
    # open points by cause, in plain language
    items = []
    for (origin, key), checks in cause_groups(spec, card):
        info = h['causes'][key]
        places = ' · '.join(f'<a href="#{anchor(stage)}" style="color:#1f7a6d;">{_e(text)}</a>' for stage, text in where(spec, checks))
        codes = ', '.join(dict.fromkeys(str(c['detail']) for c in checks if c['detail']))
        explained = ''.join(f'<div style="font-size:13px;color:#344054;margin-top:3px;line-height:1.4;"><span style="font-weight:700;">{_e(h["cause_lines"][part])}:</span> '
                            f'{_e(info[part])}</div>' for part in ('meaning', 'if_kept', 'benefit'))
        code = f'<div style="font-size:11px;color:#98a2b3;margin-top:3px;">{_e(h["cause_code"])}: {_e(codes)}</div>' if codes else ''
        items.append(f'<tr><td valign="top" width="104" style="padding:10px 10px 10px 0;border-bottom:1px solid #f2f4f7;">{_badge(origin, spec)}</td>'
                     f'<td style="{FONT}padding:10px 0;border-bottom:1px solid #f2f4f7;"><div style="font-size:14px;font-weight:700;color:#101828;">'
                     f'{_e(_count(spec, "check", len(checks)))} · {_e(info["name"])}</div><div style="font-size:12px;margin-top:2px;">{places}</div>'
                     f'{explained}{code}</td></tr>')
    body = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(items)}</table>' if items
            else f'<div style="{FONT}font-size:13px;color:#667085;">{_e(h["open_none"])}</div>')
    rows.append(_card(titles['open_points'], body))
    # key figures
    operating, cost, findings = card['operating'], card['cost'], card['reviewer_observations']['findings']
    severe = sum(v['critical'] + v['major'] for v in findings.values())
    figures = [_n(card['rates']['save_rate_percent'], ' %'), _n((operating['saves'] or {}).get('NOT_SAVED_AFTER_ENTRY')),
               _n(operating['totals']['rejected']), _n(operating['totals']['scrolls_after_last_entry']), _n(cost['model_calls']),
               _duration(cost['elapsed_seconds']), _n(cost['tokens_known_sum']), _n(severe) if kind == 'BENCHMARK' else h['no_reviewer']]
    tiles = [f'<td width="50%" valign="top" style="{FONT}padding:8px 12px 8px 0;border-bottom:1px solid #f2f4f7;"><div style="font-size:12px;color:#667085;">'
             f'{_e(title)}</div><div style="font-size:18px;font-weight:700;color:#101828;margin-top:2px;">{_e(value)}</div></td>'
             for title, value in zip(h['operating'], figures)]
    body = ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            + ''.join('<tr>' + ''.join(tiles[i:i + 2]) + '</tr>' for i in range(0, len(tiles), 2)) + '</table>')
    rows.append(_card(titles['operating'], body))
    # decisions: question, background, options with their effect, recommendation and how to answer
    texts = h['decision_texts']
    open_decisions = sorted((d for d in (decisions or []) if d.get('status') == 'OPEN'), key=lambda d: d.get('priority', 9))
    blocks = []
    for d in open_decisions:
        now = d.get('priority', 9) == 1
        tag = (f' <span style="display:inline-block;padding:1px 6px;border-radius:4px;background:{"#b54708" if now else "#eaecf0"};'
               f'color:{"#ffffff" if now else "#475467"};font-size:11px;font-weight:700;">{_e(texts["now"] if now else texts["later"])}</span>')
        part = [f'<div style="font-size:14px;font-weight:700;color:#101828;">{_e(d.get("question") or d["title"])}{tag}</div>']
        if d.get('context'):
            part.append(f'<div style="font-size:12px;color:#667085;margin-top:3px;line-height:1.4;">{_e(texts["context"])}: {_e(d["context"])}</div>')
        options = [_option(o) for o in d.get('options', [])]
        if options and (now or not d.get('recommendation')):
            part.append(''.join(f'<div style="font-size:13px;color:#344054;margin-top:3px;line-height:1.4;">&#8226; <span style="font-weight:700;">{_e(label)}</span>'
                                + (f': {_e(effect)}' if effect else '') + '</div>' for label, effect in options))
        elif options:
            part.append(f'<div style="font-size:12px;color:#667085;margin-top:3px;">{_e(" · ".join(label for label, _ in options))}</div>')
        if d.get('recommendation'):
            part.append(f'<div style="font-size:13px;color:#1f7a6d;margin-top:4px;line-height:1.4;"><span style="font-weight:700;">{_e(texts["recommendation"])}:</span> '
                        f'{_e(d["recommendation"])}</div>')
        if d.get('answer'):
            part.append(f'<div style="font-size:12px;color:#475467;margin-top:3px;">{_e(texts["answer"])}: {_e(d["answer"])}</div>')
        elif d.get('next_step'):
            part.append(f'<div style="font-size:12px;color:#1f7a6d;margin-top:3px;">{_e(h["decisions_next"] + d["next_step"])}</div>')
        blocks.append(f'<div style="{FONT}padding:9px 0;border-bottom:1px solid #f2f4f7;">{"".join(part)}</div>')
    body = ''.join(blocks) or f'<div style="{FONT}font-size:13px;color:#667085;">{_e(h["decisions_none"])}</div>'
    rows.append(_card(titles['decisions'], body))
    # checklist
    items = checklist(spec, card, comparison=comparison, gates=gates)
    applicable = [i for i in items if i[1] is not None]
    done = sum(1 for i in applicable if i[1])
    marks = {True: ('&#9745;', '#1f7a6d'), False: ('&#9744;', '#b42318'), None: ('&#8211;', '#98a2b3')}
    body = ''.join(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid #f2f4f7;"><tr>'
                   f'<td valign="top" width="26" style="{FONT}font-size:16px;color:{marks[state][1]};padding:7px 0;">{marks[state][0]}</td>'
                   f'<td style="{FONT}padding:7px 0;"><div style="font-size:14px;font-weight:700;color:#101828;">{_e(title)}</div>'
                   f'<div style="font-size:12px;color:#667085;">{_e(detail)}</div></td></tr></table>' for _, state, title, detail in items)
    rows.append(_card(titles['checklist'], body, h['checklist_summary'].format(done=done, total=len(applicable)),
                      hint_color='#1f7a6d' if done == len(applicable) else '#b42318', hint_weight=600))
    # next steps
    steps = next_steps(spec, card)
    body = ''.join(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td valign="top" width="26" '
                   f'style="{FONT}font-size:15px;font-weight:700;color:#1f7a6d;padding:4px 0;">{index}.</td>'
                   f'<td style="{FONT}font-size:14px;color:#101828;padding:4px 0;line-height:1.45;">{_e(text)}</td></tr></table>'
                   for index, text in enumerate(steps, 1)) or f'<div style="{FONT}font-size:13px;color:#667085;">—</div>'
    rows.append(_card(titles['next_steps'], body))
    # every check per stage: what was tested, the criteria, the checks, a fixed conclusion
    details = h['details']
    blocks = []
    for stage in card['stages']:
        state = stage_state(stage)
        lines = stage_criteria(spec, card, stage) if state != 'PASSED' else [l for l in stage_criteria(spec, card, stage) if l[1] in (details['criteria']['time'], details['criteria']['actions'])]
        criteria = ''.join(f'<tr><td valign="top" width="18" style="{FONT}font-size:13px;font-weight:700;color:{MARKS[mark][1]};padding:2px 0;">{MARKS[mark][0]}</td>'
                           f'<td valign="top" width="200" style="{FONT}font-size:12px;color:#475467;padding:2px 8px 2px 0;">{_e(label)}</td>'
                           f'<td style="{FONT}font-size:12px;color:#101828;padding:2px 0;line-height:1.4;">{_e(text)}</td></tr>' for mark, label, text in lines)
        listed = ''.join(f'<tr><td valign="top" width="18" style="{FONT}font-size:13px;font-weight:700;color:{MARKS[mark][1]};padding:3px 0;">{MARKS[mark][0]}</td>'
                         f'<td colspan="2" style="{FONT}font-size:12px;color:#101828;padding:3px 0;line-height:1.4;">{_e(text)}'
                         + ''.join(f'<div style="color:#667085;margin-top:1px;">{_e(sub)}</div>' for sub in subs if sub) + '</td></tr>'
                         for mark, text, subs in check_lines(spec, card, stage))
        blocks.append(f'<a id="{anchor(stage["stage"])}" name="{anchor(stage["stage"])}"></a>'
                      f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid #eaecf0;margin-bottom:12px;"><tr>'
                      f'<td style="{FONT}font-size:14px;font-weight:700;color:#101828;padding-bottom:3px;">{_e(stage["label"])}</td>'
                      f'<td align="right" style="{FONT}font-size:13px;font-weight:700;color:{STAGE_STATE_COLORS[state]};padding-bottom:3px;">'
                      f'{_e(h["stage_states"][state])} · {_e(h["stage_line"].format(passed=stage["counts"]["PASSED"], checks=stage["checks"]))}</td></tr>'
                      f'<tr><td colspan="2" style="{FONT}font-size:12px;color:#667085;padding-bottom:6px;line-height:1.4;">{_e(details["test_label"])}: '
                      f'{_e(details["tests"][stage["stage"]])}</td></tr><tr><td colspan="2"><table role="presentation" width="100%" cellpadding="0" '
                      f'cellspacing="0">{criteria}{listed}</table></td></tr><tr><td colspan="2" style="{FONT}font-size:12px;font-weight:700;color:#344054;'
                      f'padding:6px 0 10px 0;">{_e(stage_fazit(spec, card, stage))}</td></tr></table>')
    blocks.append(f'<div style="{FONT}font-size:11px;color:#98a2b3;">{_e(details["marks_note"])}</div>')
    rows.append(_card(titles['details'], ''.join(blocks), titles['details_hint']))
    # glossary
    body = ''.join(f'<tr><td valign="top" width="120" style="{FONT}font-size:13px;font-weight:700;color:#101828;padding:5px 10px 5px 0;">{_e(term)}</td>'
                   f'<td style="{FONT}font-size:12px;color:#475467;padding:5px 0;line-height:1.4;">{_e(text)}</td></tr>' for term, text in h['glossary'])
    rows.append(_card(titles['glossary'], f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{body}</table>'))
    # links and footer
    button = (f'<a href="{_e(links["details"])}" style="{FONT}display:inline-block;background:#1f7a6d;color:#ffffff;font-size:14px;font-weight:700;'
              f'text-decoration:none;padding:11px 20px;border-radius:6px;">{_e(h["links"]["details"])} &#8599;</a>') if links.get('details') else ''
    small = ' · '.join(f'<a href="{_e(links[key])}" style="color:#1f7a6d;">{_e(h["links"][key])}</a>' for key in ('points', 'scorecard', 'overview') if links.get(key))
    footer = h['footer'].format(spec=f'{card["spec_id"]} {card["spec_version"]}')
    rows.append(f'<tr><td align="center" style="padding:8px 28px 6px 28px;">{button}<div style="{FONT}font-size:12px;margin-top:10px;">{small}</div></td></tr>'
                f'<tr><td align="center" style="{FONT}padding:10px 28px 24px 28px;font-size:11px;color:#98a2b3;line-height:1.5;">{_e(footer)}<br>'
                f'Prüfsumme der Punktekarte {_e(canonical_hash(card)[:16])} · Vergleichsgruppe {_e(comparability_group(card))}</td></tr>')
    title = f'{h["title"]} – Lauf {run["run_id"]}'
    return _page(title, rows)


def _page(title, rows):
    return ('<!DOCTYPE html>\n<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{_e(title)}</title></head>\n<body style="margin:0;padding:0;background:#f3f5f8;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f5f8;"><tr><td align="center" style="padding:24px 8px;">'
            f'<table role="presentation" width="{WIDTH}" cellpadding="0" cellspacing="0" style="width:{WIDTH}px;max-width:100%;background:#ffffff;'
            'border-radius:10px;overflow:hidden;">\n' + '\n'.join(rows) + '\n</table></td></tr></table></body></html>\n')


# ---- overview of all runs -----------------------------------------------------------------------------------------------------------------

def render_overview(entries, *, spec=None):
    """`entries`: list of (scorecard, href of its bericht.html), any order; shown newest first."""
    spec = spec or report_spec.load_spec()
    h = spec['html']
    entries = sorted(entries, key=lambda e: (e[0]['run'].get('completed_at') or '', e[0]['run']['run_id']), reverse=True)
    rows = [f'<tr><td style="background:#0f1f33;padding:24px 28px;"><div style="{FONT}font-size:12px;letter-spacing:1.5px;font-weight:700;color:#5fd1c1;">'
            f'{_e(h["brand"])}</div><div style="{FONT}font-size:26px;font-weight:700;color:#ffffff;margin:6px 0 4px 0;">{_e(h["overview_title"])}</div>'
            f'<div style="{FONT}font-size:13px;color:#cfd8e3;">{len(entries)} Läufe · neuester {_e(_date(entries[0][0]["run"].get("completed_at")) if entries else "—")}'
            f'</div></td></tr>', '<tr><td style="height:16px;font-size:0;line-height:0;">&nbsp;</td></tr>']
    head = ''.join(f'<td style="{FONT}font-size:11px;font-weight:700;color:#667085;padding:6px 6px 6px 0;border-bottom:1px solid #eaecf0;">{_e(c)}</td>'
                   for c in h['overview_columns'])
    lines = []
    for card, href in entries:
        result = card['result']['run_result']
        background, border, color = RESULT_STYLES[result]
        share = card['points']['points'] / card['points']['max_points'] if card['points']['max_points'] else 0
        filled = int(Decimal(110 * share).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        bar = (f'<table role="presentation" cellpadding="0" cellspacing="0" style="width:110px;"><tr>'
               + (f'<td style="width:{filled}px;height:8px;background:#1f7a6d;font-size:0;line-height:0;">&nbsp;</td>' if filled else '')
               + (f'<td style="width:{110 - filled}px;height:8px;background:#eaecf0;font-size:0;line-height:0;">&nbsp;</td>' if filled < 110 else '')
               + '</tr></table>')
        cell = f'style="{FONT}font-size:13px;color:#101828;padding:8px 6px 8px 0;border-bottom:1px solid #f2f4f7;"'
        lines.append(f'<tr><td {cell}>{_e(_short_date(card["run"].get("completed_at")))}</td>'
                     f'<td {cell}><a href="{_e(href)}" style="color:#1f7a6d;font-weight:700;">{_e(card["run"]["run_id"][:8])}</a></td>'
                     f'<td {cell}>{_e(KIND_SHORT.get(card["run"].get("kind", "BENCHMARK"), "?"))}</td>'
                     f'<td {cell}><span style="display:inline-block;padding:2px 7px;border-radius:4px;background:{background};color:{color};font-size:12px;'
                     f'font-weight:700;">{_e(spec["run_result"]["labels"][result])}</span></td>'
                     f'<td {cell}>{bar}<div style="font-size:12px;color:#475467;margin-top:3px;">{_n(card["points"]["points"])} / '
                     f'{_n(card["points"]["max_points"])}</div></td><td {cell}><span style="font-family:Consolas,monospace;font-size:12px;">'
                     f'{_e(comparability_group(card))}</span></td></tr>')
    table = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{head}</tr>{"".join(lines)}</table>'
             f'<div style="{FONT}font-size:11px;color:#98a2b3;margin-top:10px;">Läufe derselben Vergleichsgruppe haben gleiche Messbedingungen und '
             f'sind vergleichbar. Probe- und Trockenläufe sind keine Benchmark-Ergebnisse.</div>')
    rows.append(_card('Alle Läufe', table))
    return _page(h['overview_title'], rows)


# ---- files ----------------------------------------------------------------------------------------------------------------------------------

def load_decisions(path=DECISIONS_PATH):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))['decisions']
    except (OSError, ValueError, KeyError):
        return []


def _version_key(version):
    return tuple(int(part) for part in str(version).split('.'))


def find_runs(*roots, depth=3):
    """Run folders below the roots with their newest scorecard (scorecard.json or scorecard-<version>.json)."""
    found = {}
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for path in _walk(root, depth):
            try:
                card = json.loads(path.read_text(encoding='utf-8'))
                version = _version_key(card['spec_version'])
            except (OSError, ValueError, KeyError):
                continue
            current = found.get(path.parent)
            if current is None or version > current[0]:
                found[path.parent] = (version, card)
    return [(folder, card) for folder, (_, card) in sorted(found.items())]


def newest_scorecard(folder):
    """The scorecard of the newest specification version in a run folder (scorecard.json or scorecard-<version>.json), or None."""
    best = None
    for path in Path(folder).glob('scorecard*.json'):
        try:
            card = json.loads(path.read_text(encoding='utf-8'))
            version = _version_key(card['spec_version'])
        except (OSError, ValueError, KeyError):
            continue
        if best is None or version > best[0]:
            best = (version, card)
    return best[1] if best else None


def _walk(root, depth):
    for level in range(1, depth + 1):
        yield from root.glob('/'.join(['*'] * level) + '/scorecard*.json')


def previous_run(card, runs):
    """The newest earlier run of the same kind (by completion time), or None."""
    kind, done = card['run'].get('kind', 'BENCHMARK'), card['run'].get('completed_at') or ''
    earlier = [c for _, c in runs if c['run'].get('kind', 'BENCHMARK') == kind and (c['run'].get('completed_at') or '') < done
               and c['run']['run_id'] != card['run']['run_id']]
    return max(earlier, key=lambda c: c['run'].get('completed_at') or '') if earlier else None


def write_report(folder, card, *, history_roots=(), gates=None, decisions=None, links=None):
    runs = find_runs(*history_roots) if history_roots else []
    text = render_report(card, previous=previous_run(card, runs), decisions=load_decisions() if decisions is None else decisions,
                         gates=gates, links=links)
    target = Path(folder) / 'bericht.html'
    target.write_text(text, encoding='utf-8', newline='\n')
    return target


def write_overview(root, *extra_roots):
    root = Path(root)
    entries = []
    for folder, card in find_runs(root, *extra_roots):
        try:
            href = (folder / 'bericht.html').relative_to(root).as_posix()
        except ValueError:
            href = (folder / 'bericht.html').as_uri()
        entries.append((card, href))
    target = root / 'uebersicht.html'
    target.write_text(render_overview(entries), encoding='utf-8', newline='\n')
    return target

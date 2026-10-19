"""The measurement task in BLE's own words.

Live run 6c23f768 / fdea63ef: the task named modules and fields with the suite's internal names ("wash", "allocations", "main_input",
"sieve:31.5"). Models answered "there is no wash module" although BLE calls it "Abschlämmung / Feinanteil", and "there is no allocations
module" although the allocations are the "Entnahmen" inside the sieve analysis. That is a suite defect, not a finding about BLE. This module
translates between the internal names (which the guards and Oracles keep using) and the wording a laboratory worker sees on screen.

It names modules and fields the way BLE labels them. It never says where a control is or how to reach it; finding the save button, the module
cards and the fields stays part of what is measured.
"""
import re

MODULE_TITLES = {
    'allocations': 'Entnahmen (Feldgruppe der Siebanalyse)',
    'wash': 'Abschlämmung / Feinanteil',
    'sieve': 'Siebanalyse',
    'partial': 'Teilsiebung',
    'shape': 'Kornform',
    'boiling': 'Kochversuch',
    'sand': 'Sandäquivalent',
}
_KIND_BY_TITLE = {title: kind for kind, title in MODULE_TITLES.items()}

# Card labels BLE shows for the sample allocations (Entnahmen) of each test process.
ALLOCATION_LABELS = ('KF', 'Koch', 'SE', 'SL', 'Tro')


def german(number):
    """'31.5' -> '31,5' (BLE reads de-DE)."""
    return str(number).replace('.', ',')


def _internal_number(text):
    return str(text).replace(',', '.')


def module_title(kind):
    return MODULE_TITLES[kind]


def kind_of(title_or_kind):
    """The internal module kind for a task title (an internal kind passes through)."""
    if title_or_kind in MODULE_TITLES:
        return title_or_kind
    return _KIND_BY_TITLE[title_or_kind]


def display_label(kind, name):
    """What a worker reads on screen for the internal field name `name` of module `kind`."""
    if kind == 'sieve':
        if name == 'main_input':
            return 'Einwaage (g)'
        found = re.fullmatch(r'sieve:(.+)', name)
        if found:
            return 'Rückstand (g), Boden/Pfanne bzw. Anteile gesamt' if found.group(1) == '0' else 'Rückstand (g), Sieb %s mm' % german(found.group(1))
    elif kind == 'partial':
        found = re.fullmatch(r'partial:(.+):([AB])', name)
        if found:
            return 'Rückstand (g), Sieb %s mm, Siebturm %s' % (german(found.group(1)), found.group(2))
    elif kind == 'allocations':
        found = re.fullmatch(r'(%s):(.+)' % '|'.join(ALLOCATION_LABELS), name)
        if found:
            where = 'ohne Sieb' if found.group(2) == 'none' else 'Pfanne' if found.group(2) == '0' else 'Sieb %s mm' % german(found.group(2))
            return 'Entnahme %s, %s (g)' % (found.group(1), where)
    elif kind == 'shape':
        found = re.fullmatch(r'(.+):(\d+(?:\.\d+)?)', name)
        if found:
            return '%s, Fraktion %s mm' % (found.group(1), german(found.group(2)))
    elif kind == 'boiling':
        found = re.fullmatch(r'(.+):(\d+)', name)
        if found:
            return '%s, Wiederholung %s' % (found.group(1), found.group(2))
    elif kind == 'sand':
        found = re.fullmatch(r'(.+):([AB])', name)
        if found:
            return '%s, Prüfung %s' % (found.group(1), found.group(2))
    return name  # wash fields, the sieve tower weigh-ins and every other name already are BLE's own labels


def internal_name(kind, label):
    """Inverse of display_label (a label that is already an internal name passes through)."""
    if kind == 'sieve':
        if label == 'Einwaage (g)':
            return 'main_input'
        if label == 'Rückstand (g), Boden/Pfanne bzw. Anteile gesamt':
            return 'sieve:0'
        found = re.fullmatch(r'Rückstand \(g\), Sieb (.+) mm', label)
        if found:
            return 'sieve:' + _internal_number(found.group(1))
    elif kind == 'partial':
        found = re.fullmatch(r'Rückstand \(g\), Sieb (.+) mm, Siebturm ([AB])', label)
        if found:
            return 'partial:%s:%s' % (_internal_number(found.group(1)), found.group(2))
    elif kind == 'allocations':
        found = re.fullmatch(r'Entnahme (%s), (.+) \(g\)' % '|'.join(ALLOCATION_LABELS), label)
        if found:
            where = found.group(2)
            sieve = 'none' if where == 'ohne Sieb' else '0' if where == 'Pfanne' else _internal_number(re.fullmatch(r'Sieb (.+) mm', where).group(1))
            return '%s:%s' % (found.group(1), sieve)
    elif kind == 'shape':
        found = re.fullmatch(r'(.+), Fraktion (.+) mm', label)
        if found:
            return '%s:%s' % (found.group(1), _internal_number(found.group(2)))
    elif kind == 'boiling':
        found = re.fullmatch(r'(.+), Wiederholung (\d+)', label)
        if found:
            return '%s:%s' % (found.group(1), found.group(2))
    elif kind == 'sand':
        found = re.fullmatch(r'(.+), Prüfung ([AB])', label)
        if found:
            return '%s:%s' % (found.group(1), found.group(2))
    return label


def task_inputs(kind, values):
    """{internal name: German-notation value} -> {on-screen label: value}; labels must stay unique."""
    shown = {display_label(kind, name): value for name, value in values.items()}
    if len(shown) != len(values):
        raise ValueError('Task labels are not unique')
    return shown


def internal_inputs(kind, shown):
    """The inverse for a test double or a checker: {on-screen label: value} -> {internal name: value}."""
    return {internal_name(kind, label): value for label, value in shown.items()}

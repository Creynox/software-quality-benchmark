import importlib
import unittest

from test_measurement_guard import position
from test_suite_fixture import owned_fixture

vocabulary = importlib.import_module('projects.ble-elva.tools.task_vocabulary')
guard = importlib.import_module('projects.ble-elva.tools.measurement_guard')
PROBE = '11111111-1111-4111-8111-111111111111'

# The module titles BLE shows on the module cards of a sample page (read from a scratch clone, 19.10.2026).
BLE_CARD_TITLES = ('Siebanalyse', 'Kornform', 'Kochversuch', 'Sandäquivalent', 'Teilsiebung', 'Abschlämmung / Feinanteil')
INTERNAL_MARKERS = ('main_input', 'sieve:', 'partial:', 'wash', 'allocations', 'none')


class TaskVocabularyTests(unittest.TestCase):
    def contract(self, kind):
        return guard.make_contract(owned_fixture(), PROBE, position(), kind)

    def test_modules_carry_the_titles_bles_module_cards_show_and_the_allocations_the_entnahmen(self):
        self.assertTrue(set(BLE_CARD_TITLES) <= set(vocabulary.MODULE_TITLES.values()))
        self.assertEqual(vocabulary.module_title('wash'), 'Abschlämmung / Feinanteil')
        self.assertIn('Entnahmen', vocabulary.module_title('allocations'))
        for kind in vocabulary.MODULE_TITLES:
            self.assertEqual(vocabulary.kind_of(vocabulary.module_title(kind)), kind)
            self.assertEqual(vocabulary.kind_of(kind), kind)  # an internal kind passes through (test doubles)

    def test_every_field_of_every_contract_round_trips_stays_unique_and_names_no_internal_key(self):
        for kind in guard.ROUTES:
            fields = self.contract(kind)['fields']
            shown = vocabulary.task_inputs(kind, fields)
            self.assertEqual(len(shown), len(fields), kind)
            self.assertEqual(vocabulary.internal_inputs(kind, shown), fields, kind)
            for label in shown:
                for marker in INTERNAL_MARKERS:
                    self.assertNotIn(marker, label, (kind, label))
                self.assertNotRegex(label, r'\d\.\d', (kind, label))  # numbers inside labels are German too

    def test_the_labels_use_bles_words_and_german_notation(self):
        self.assertEqual(vocabulary.display_label('sieve', 'main_input'), 'Einwaage (g)')
        self.assertEqual(vocabulary.display_label('sieve', 'sieve:31.5'), 'Rückstand (g), Sieb 31,5 mm')
        self.assertEqual(vocabulary.display_label('sieve', 'sieve:0'), 'Rückstand (g), Boden/Pfanne bzw. Anteile gesamt')
        self.assertEqual(vocabulary.display_label('partial', 'partial:2:A'), 'Rückstand (g), Sieb 2 mm, Siebturm A')
        self.assertEqual(vocabulary.display_label('partial', 'Einwaage Siebturm B'), 'Einwaage Siebturm B')
        self.assertEqual(vocabulary.display_label('allocations', 'KF:31.5'), 'Entnahme KF, Sieb 31,5 mm (g)')
        self.assertEqual(vocabulary.display_label('allocations', 'SE:0'), 'Entnahme SE, Pfanne (g)')
        self.assertEqual(vocabulary.display_label('allocations', 'Koch:none'), 'Entnahme Koch, ohne Sieb (g)')
        self.assertEqual(vocabulary.display_label('shape', 'Einwaage gesamt (g):5.6'), 'Einwaage gesamt (g), Fraktion 5,6 mm')
        self.assertEqual(vocabulary.display_label('boiling', 'Einwaage vor Kochen:2'), 'Einwaage vor Kochen, Wiederholung 2')
        self.assertEqual(vocabulary.display_label('sand', 'Sandhöhe:A'), 'Sandhöhe, Prüfung A')
        self.assertEqual(vocabulary.display_label('wash', 'Probenmasse feucht'), 'Probenmasse feucht')  # BLE's own label already

    def test_two_fields_that_would_share_a_label_are_refused(self):
        with self.assertRaises(ValueError):
            vocabulary.task_inputs('sieve', {'sieve:1.5': '1', 'sieve:1,5': '2'})

    def test_the_vocabulary_never_says_where_a_control_is_or_how_to_reach_it(self):
        words = ' '.join(list(vocabulary.MODULE_TITLES.values()) + [vocabulary.display_label(k, n) for k in guard.ROUTES for n in self.contract(k)['fields']])
        import re
        for forbidden in ('speichern', 'erfassen', 'scroll', 'schaltfläche', 'button', 'klick'):
            self.assertNotIn(forbidden, words.lower())
        self.assertIsNone(re.search(r'\b(oben|unten|rechts|links)\b', words.lower()))  # "Probenmasse" contains "oben" as a word part only


if __name__ == '__main__':
    unittest.main()

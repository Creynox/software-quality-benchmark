import importlib
import copy
import unittest

math = importlib.import_module('projects.ble-elva.tools.reference_math')


class ReferenceMathTests(unittest.TestCase):
    def test_two_actual_sand_ratios_not_mean_height_ratio(self):
        rows = [{'sand_height': 9.5, 'suspension_height': 12.2},
                {'sand_height': 9.6, 'suspension_height': 12.1}]
        result = math.sand_equivalent(rows)
        self.assertAlmostEqual(float(result), 78.603847717, places=7)
        self.assertNotEqual(result, math.percent(9.55, 12.15))

    def test_report_ratios_and_consistent_unit_conversion(self):
        rows = [{'sand_height': 9.5, 'suspension_height': 12.2},
                {'sand_height': 9.6, 'suspension_height': 12.2}]
        expected = math.sand_equivalent(rows)
        self.assertAlmostEqual(float(expected), 78.2786885246, places=8)
        mm = [{key: value * 10 for key, value in row.items()} for row in rows]
        self.assertEqual(expected, math.sand_equivalent(mm))

    def test_known_original_particle_masses(self):
        self.assertEqual(math.percent(8.6, 80), math.number(10.75))
        result = math.pooled_particle_shape([{'total_g': 250, 'poor_g': 40},
                                            {'total_g': 350, 'poor_g': 84.2}])
        self.assertEqual(result, math.number(20.7))

    def test_confirmed_cm_projection_keeps_originals_and_two_repetitions(self):
        source = [{'sand_height': 9.5, 'suspension_height': 12.2},
                  {'sand_height': 9.6, 'suspension_height': 12.1}]
        original = copy.deepcopy(source)
        mm = math.sand_heights_mm(source, 'cm')
        self.assertEqual(source, original)
        self.assertEqual(mm, [{'sand_height': math.number(95), 'suspension_height': math.number(122)},
                              {'sand_height': math.number(96), 'suspension_height': math.number(121)}])
        self.assertEqual(math.sand_equivalent(source), math.sand_equivalent(mm))
        self.assertEqual(math.sand_heights_mm(source, 'mm')[0]['suspension_height'], math.number(12.2))

    def test_height_unit_is_never_guessed_from_legacy_field_name(self):
        rows = [{'sand_height': 9.5, 'suspension_height': 12.2},
                {'sand_height': 9.6, 'suspension_height': 12.1}]
        for unit in (None, '', 'unknown', 'sandHeightMm', 'm'):
            with self.assertRaises(ValueError): math.sand_heights_mm(rows, unit)

    def test_missing_or_impossible_inputs_block(self):
        for value in (None, True, 'NaN', 'Infinity', -1):
            with self.assertRaises(ValueError): math.number(value)
        for part, total in ((1, 0), (2, 1)):
            with self.assertRaises(ValueError): math.percent(part, total)
        with self.assertRaises(ValueError): math.sand_equivalent([])

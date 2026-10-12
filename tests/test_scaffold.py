"""Reusable project templates must be deterministic, empty and safe."""

import json
import tempfile
import unittest
from pathlib import Path

from sqbf.cli import main
from sqbf.models import Scenario
from sqbf.scaffold import create_project


class ScaffoldTests(unittest.TestCase):
    def test_two_fresh_locations_generate_identical_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = create_project(Path(tmp) / "one", "demo-app", 'Example "App"')
            two = create_project(Path(tmp) / "two", "demo-app", 'Example "App"')
            filenames_one = sorted(str(p.relative_to(one)) for p in one.rglob("*") if p.is_file())
            filenames_two = sorted(str(p.relative_to(two)) for p in two.rglob("*") if p.is_file())
            self.assertEqual(filenames_one, filenames_two)
            self.assertTrue(filenames_one)
            for name in filenames_one:
                self.assertEqual((one / name).read_bytes(), (two / name).read_bytes())
                self.assertNotIn(b"BLE", (one / name).read_bytes())
                self.assertNotIn(b"Enzberg", (one / name).read_bytes())
            manifest = json.loads((one / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["project_id"], "demo-app")
            self.assertEqual(manifest["display_name"], 'Example "App"')
            self.assertEqual(manifest["profile_status"], "UNCONFIGURED")
            self.assertEqual(manifest["scenarios"], ["scenarios/first-task.json"])

    def test_template_fails_closed_before_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = create_project(Path(tmp), "blank")
            with self.assertRaises(ValueError):
                Scenario.load(project / "scenarios" / "first-task.json")
            # A real URL override alone does not make the blank scenario runnable.
            with self.assertRaises(ValueError):
                Scenario.load(project / "scenarios" / "first-task.json", "http://127.0.0.1:5000/")

    def test_existing_project_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp)
            first = create_project(projects, "customer-app")
            marker = first / "manual-notes.txt"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_project(projects, "customer-app")
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_invalid_slugs_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "profiles"
            for slug in ("../ble-elva", "Bad_Name", "a/b", "-bad", "bad-", "", "a" * 50):
                with self.subTest(slug=slug), self.assertRaises(ValueError):
                    create_project(projects, slug)
            self.assertFalse(projects.exists())

    def test_cli_new_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = main([
                "new-project", "--slug", "new-test", "--name", "A clean profile",
                "--projects-dir", tmp,
            ])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "new-test" / "project.json").exists())


class BleProfileTests(unittest.TestCase):
    def test_ble_scenario_and_fixture_contract_match(self):
        root = Path(__file__).resolve().parents[1] / "projects" / "ble-elva"
        profile = json.loads((root / "project.json").read_text(encoding="utf-8"))
        scenario_path = root / profile["scenarios"][0]
        fixture_path = root / profile["fixtures"][0]
        self.assertTrue(scenario_path.is_file())
        self.assertTrue(fixture_path.is_file())
        scenario = Scenario.load(scenario_path)
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(profile["project_id"], "ble-elva")
        self.assertEqual(scenario.fixture_id, fixture["fixture_id"])
        self.assertEqual(fixture["status"], "NOT_PROVISIONED")
        self.assertTrue(fixture["isolation_required"])
        self.assertFalse(fixture["destructive_operations_permitted"])
        self.assertIn("Laborleitung", scenario.persona)
        self.assertIn("STS 0", scenario.task)
        self.assertIn("TL SoB-StB 20", scenario.task)
        self.assertIn("ETV-StB-BW", scenario.task)


if __name__ == "__main__":
    unittest.main()

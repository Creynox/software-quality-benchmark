"""Check local evidence, hashes and Markdown output."""

import json
import tempfile
import unittest
from pathlib import Path

from sqbf.reporting import Evidence


class EvidenceTests(unittest.TestCase):
    def test_creates_manifest_and_report_without_remote_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "some-run"
            ev = Evidence(folder)
            ev.snapshot(b"\x89PNG\r\nTEST", "first")
            ev.snapshot(b"\x89PNG\r\nFINAL", "last")
            ev.event("agent_decision", action="click", x=1, y=2)
            manifest = {
                "run_id": "some-run", "scenario_id": "ble.product",
                "persona": "Laborleitung", "executor_model": "mock:executor",
                "fixture_id": "fixture", "software_version": "test",
                "executor_status": "DONE", "actions": 2, "budget_actions": 150,
                "wall_seconds": 14.5,
            }
            ev.finish(manifest, {"verdict": "INCONCLUSIVE", "reason": "Cannot see norms", "findings": []}, "INCONCLUSIVE")
            self.assertTrue((folder / "report.md").exists())
            self.assertEqual(len(json.loads((folder / "evidence.json").read_text())), 2)
            self.assertIn("INCONCLUSIVE", (folder / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()

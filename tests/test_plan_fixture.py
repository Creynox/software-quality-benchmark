import importlib
import unittest
from test_suite_fixture import owned_fixture

module=importlib.import_module('projects.ble-elva.tools.plan_fixture')


class PlanFixtureTests(unittest.TestCase):
    def test_matches_existing_dotnet_guid_byte_order_and_preserves_zero_customer(self):
        self.assertEqual(module.default_project_id('3bf304e0-3c58-4c3a-8900-7c00bdbfd001'),'dbb58b0d-ac55-81b4-a60e-e0d1bc4304e1')
        f=owned_fixture();sql,project=module.prepare_default_project_sql(f)
        self.assertIn('Standardprojekt (Beprobungsplan)',sql)
        self.assertIn('00000000-0000-0000-0000-000000000000',sql)
        self.assertIn('(SELECT count(*) FROM samples)<>0',sql)
        for forbidden in ('INSERT INTO samples','DELETE ','DROP ','UPDATE ','identity_users'):
            self.assertNotIn(forbidden,sql)

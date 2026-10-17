"""Tests for the independent read-only LAB-01 persistence assertions."""

import unittest
from unittest.mock import patch

from sqbf.oracle import (
    ConnectionTarget,
    OracleError,
    validate_connection_target,
    verify_after,
    verify_before,
)
from sqbf.cli import main


FIXTURE = {
    "fixture_id": "lab01",
    "database": {"name": "ble_benchmark_20261012", "host_port": 55432, "oracle_role": "sqbf_oracle_ro"},
    "fixture_data": {"tenant_id": "tenant-1", "plant_id": "plant-1", "site_number": "SQBF-LAB01-ENZBERG"},
    "oracle_expectations": {
        "product_name": "STS 0–45",
        "material_class_id": "class-1",
        "material_class_code": "unbound_mix",
        "product_type_id": "type-1",
        "product_type_code": "sts",
        "category": "Gemisch",
        "use_area": "Unbound",
        "product_level": "mixture",
        "before_counts": {
            "products": 0, "samples": 0, "lims_samples": 0, "reports": 0,
            "product_norm_assignments": 0, "norm_standards": 15, "norm_versions": 15,
        },
    },
}


def snapshot(product=None):
    return {
        "database": "ble_benchmark_20261012",
        "plant": {"id": "plant-1", "tenant_id": "tenant-1", "name": "Enzberg",
                  "site_number": "SQBF-LAB01-ENZBERG", "is_active": True},
        "material_class": {"id": "class-1", "code": "unbound_mix", "is_active": True},
        "product_type": {"id": "type-1", "code": "sts", "material_class_id": "class-1", "is_active": True},
        "counts": dict(FIXTURE["oracle_expectations"]["before_counts"]),
        "target_product_name_count": 0 if product is None else 1,
        "target_product": product,
    }


class OracleTests(unittest.TestCase):
    def test_connection_requires_exact_local_target_and_role(self):
        validate_connection_target(ConnectionTarget("127.0.0.1", 55432, "ble_benchmark_20261012", "sqbf_oracle_ro"), FIXTURE["database"])
        for target in (
            ConnectionTarget("127.0.0.1", 5433, "ble_benchmark_20261012", "sqbf_oracle_ro"),
            ConnectionTarget("127.0.0.1", 55432, "postgres", "sqbf_oracle_ro"),
            ConnectionTarget("127.0.0.1", 55432, "ble_benchmark_20261012", "ble_benchmark"),
            ConnectionTarget("192.168.1.8", 55432, "ble_benchmark_20261012", "sqbf_oracle_ro"),
        ):
            with self.subTest(target=target), self.assertRaises(OracleError):
                validate_connection_target(target, FIXTURE["database"])

    def test_cli_requires_dsn_in_environment_never_as_argument(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(SystemExit) as missing:
            main(["oracle", "--phase", "before"])
        self.assertEqual(missing.exception.code, 2)
        with self.assertRaises(SystemExit) as argument:
            main(["oracle", "--phase", "before", "--dsn", "host=127.0.0.1"])
        self.assertEqual(argument.exception.code, 2)

    def test_before_requires_empty_product_process_baseline(self):
        report = verify_before(snapshot(), FIXTURE)
        self.assertEqual(report["phase"], "before")
        self.assertEqual(report["counts"]["norm_versions"], 15)
        contaminated = snapshot()
        contaminated["counts"]["products"] = 1
        with self.assertRaisesRegex(OracleError, "Baseline-Zähler products"):
            verify_before(contaminated, FIXTURE)

    def test_after_accepts_only_exact_norm_free_persisted_product(self):
        product = {
            "id": "product-1", "tenant_id": "tenant-1", "plant_id": "plant-1", "laboratory_id": None,
            "name": "STS 0–45", "category": "Gemisch", "material_class_id": "class-1",
            "product_type_id": "type-1", "material_class_code": "unbound_mix", "product_type_code": "sts",
            "use_area": "Unbound", "product_level": "mixture", "material_base": "Kies",
            "material_origin": "Enzberg", "grain_lower_mm": 0, "grain_upper_mm": 45,
            "sieve_range_text": "0/45", "product_group": "STS", "technical_label": "STS 0/45",
            "norm_limit_set_id": None, "product_norm_assignment_count": 0, "is_active": True,
        }
        baseline = verify_before(snapshot(), FIXTURE)
        after = snapshot(product)
        after["counts"]["products"] = 1
        result = verify_after(after, FIXTURE, baseline)
        self.assertEqual(result["phase"], "after")
        after["counts"]["norm_versions"] += 1
        with self.assertRaisesRegex(OracleError, "Normstammdaten"):
            verify_after(after, FIXTURE, baseline)

    def test_after_rejects_changed_database_or_invalid_product_fields(self):
        baseline = verify_before(snapshot(), FIXTURE)
        product = {"name": "STS 0–45"}
        after = snapshot(product)
        after["counts"]["products"] = 1
        after["database"] = "postgres"
        with self.assertRaisesRegex(OracleError, "database identity"):
            verify_after(after, FIXTURE, baseline)


if __name__ == "__main__":
    unittest.main()

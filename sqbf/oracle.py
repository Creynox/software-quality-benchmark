"""Read-only independent persistence oracle for the LAB-01 BLE product pilot.

This module deliberately has no browser, model, or write API. It verifies the
isolated Docker/PostgreSQL identity, opens a restricted PostgreSQL session in a
read-only transaction, and compares before/after state against the fixture.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_SELECT_TABLES = (
    "workspace_plants",
    "material_classes",
    "product_types",
    "workspace_products",
    "samples",
    "lims_sample",
    "ble_reports",
    "product_norm_version_assignments",
    "norm_standards",
    "norm_versions",
)
WRITE_PRIVILEGES = ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")


class OracleError(RuntimeError):
    """An isolation, privilege, or persistence assertion failed."""


@dataclass(frozen=True)
class ConnectionTarget:
    host: str
    port: int
    database: str
    username: str


def validate_connection_target(target: ConnectionTarget, expected: dict[str, Any]) -> None:
    """Fail closed unless the driver resolved the exact local benchmark endpoint."""
    failures = []
    if target.host not in {"127.0.0.1", "localhost"}:
        failures.append("database host is not loopback")
    if target.port != int(expected["host_port"]):
        failures.append("database host port does not match fixture")
    if target.database != expected["name"]:
        failures.append("database name does not match fixture")
    if target.username != expected["oracle_role"]:
        failures.append("login is not the dedicated Oracle role")
    if failures:
        raise OracleError("; ".join(failures))


def verify_docker_identity(fixture: dict[str, Any], run=subprocess.run) -> dict[str, str]:
    """Read Docker metadata and verify container, port, volume, and DB identity."""
    spec = fixture["database"]
    result = run(
        ["docker", "inspect", spec["container"]],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = json.loads(result.stdout)
    if len(rows) != 1:
        raise OracleError("Docker did not return exactly one benchmark container")
    container = rows[0]
    env = dict(item.split("=", 1) for item in container["Config"].get("Env", []) if "=" in item)
    ports = container["NetworkSettings"]["Ports"].get("5432/tcp") or []
    mounts = [m for m in container.get("Mounts", []) if m.get("Destination") == "/var/lib/postgresql/data"]
    checks = {
        "id": container.get("Id") == spec["container_id"],
        "name": container.get("Name") == f"/{spec['container']}",
        "running": container.get("State", {}).get("Status") == "running",
        "image": container.get("Config", {}).get("Image") == spec["image"],
        "port": len(ports) == 1
        and ports[0].get("HostIp") == "127.0.0.1"
        and ports[0].get("HostPort") == str(spec["host_port"]),
        "volume": len(mounts) == 1
        and mounts[0].get("Type") == "volume"
        and mounts[0].get("Name") == spec["volume"],
        "database": env.get("POSTGRES_DB") == spec["name"],
        "database_user": env.get("POSTGRES_USER") == spec["bootstrap_user"],
    }
    if not all(checks.values()):
        failed = ", ".join(key for key, passed in checks.items() if not passed)
        raise OracleError(f"Benchmark Docker identity mismatch: {failed}")

    # Protect the explicitly out-of-scope PostgreSQL instance from accidental aliasing.
    other = run(["docker", "inspect", "ble-postgres"], check=True, capture_output=True, text=True)
    other_rows = json.loads(other.stdout)
    if len(other_rows) != 1 or other_rows[0].get("Id") == container.get("Id"):
        raise OracleError("The existing ble-postgres container cannot be distinguished")
    other_ports = other_rows[0].get("NetworkSettings", {}).get("Ports", {}).get("5432/tcp") or []
    if not any(p.get("HostPort") == "5433" for p in other_ports):
        raise OracleError("The protected ble-postgres instance is not confirmed on port 5433")
    return {
        "container": spec["container"],
        "container_id": container["Id"],
        "image": spec["image"],
        "host_endpoint": f"127.0.0.1:{spec['host_port']}",
        "database": spec["name"],
        "volume": spec["volume"],
    }


def _fetchone(conn, sql: str, params: tuple = ()) -> dict[str, Any]:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        raise OracleError("Oracle query returned no row")
    return dict(row)


def collect_snapshot(dsn: str, fixture: dict[str, Any], connect=None) -> dict[str, Any]:
    """Collect a database snapshot using only SELECT in a read-only transaction."""
    if connect is None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - packaging error path
            raise OracleError("Install the declared psycopg dependency") from exc
        connect = lambda value: psycopg.connect(value, row_factory=dict_row, autocommit=False)

    conn = connect(dsn)
    try:
        conn.execute("SET TRANSACTION READ ONLY")
        expected = fixture["database"]
        identity = _fetchone(
            conn,
            """SELECT current_database() AS database, current_user AS username,
                      current_setting('transaction_read_only') AS transaction_read_only,
                      r.rolsuper AS is_superuser, r.rolcreatedb AS can_create_database,
                      r.rolcreaterole AS can_create_roles,
                      has_database_privilege(current_user, current_database(), 'CREATE') AS can_create_schema,
                      has_schema_privilege(current_user, 'public', 'CREATE') AS can_create_public_objects
                 FROM pg_roles r WHERE r.rolname = current_user"""
        )
        target = ConnectionTarget(
            host=conn.info.host,
            port=conn.info.port,
            database=identity["database"],
            username=identity["username"],
        )
        validate_connection_target(target, expected)
        if identity["transaction_read_only"] != "on":
            raise OracleError("PostgreSQL transaction is not read-only")
        if identity["is_superuser"] or identity["can_create_database"] or identity["can_create_roles"]:
            raise OracleError("Oracle role has elevated PostgreSQL privileges")
        if identity["can_create_schema"] or identity["can_create_public_objects"]:
            raise OracleError("Oracle role can create database objects")

        privilege_rows = conn.execute(
            """SELECT c.relname AS table_name, has_table_privilege(current_user, c.oid, 'SELECT') AS can_select,
                      has_table_privilege(current_user, c.oid, 'INSERT') OR has_any_column_privilege(current_user, c.oid, 'INSERT') AS can_insert,
                      has_table_privilege(current_user, c.oid, 'UPDATE') OR has_any_column_privilege(current_user, c.oid, 'UPDATE') AS can_update,
                      has_table_privilege(current_user, c.oid, 'DELETE') AS can_delete,
                      has_table_privilege(current_user, c.oid, 'TRUNCATE') AS can_truncate,
                      has_table_privilege(current_user, c.oid, 'REFERENCES') OR has_any_column_privilege(current_user, c.oid, 'REFERENCES') AS can_references,
                      has_table_privilege(current_user, c.oid, 'TRIGGER') AS can_trigger
                 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')"""
        ).fetchall()
        for row in privilege_rows:
            if any(row[f"can_{privilege.lower()}"] for privilege in WRITE_PRIVILEGES):
                raise OracleError(f"Oracle role has write privilege on {row['table_name']}")
        readable_tables = {row["table_name"] for row in privilege_rows if row["can_select"]}
        missing = set(REQUIRED_SELECT_TABLES) - readable_tables
        if missing:
            raise OracleError(f"Oracle role lacks SELECT on {', '.join(sorted(missing))}")

        plant = _fetchone(
            conn,
            """SELECT id::text AS id, tenant_id::text AS tenant_id, name, site_number, is_active
                 FROM workspace_plants WHERE id = %s""",
            (fixture["fixture_data"]["plant_id"],),
        )
        material_class = _fetchone(
            conn,
            """SELECT id::text AS id, code, display_name, is_active
                 FROM material_classes WHERE id = %s""",
            (fixture["oracle_expectations"]["material_class_id"],),
        )
        product_type = _fetchone(
            conn,
            """SELECT id::text AS id, code, display_name, material_class_id::text AS material_class_id, is_active
                 FROM product_types WHERE id = %s""",
            (fixture["oracle_expectations"]["product_type_id"],),
        )
        counts = {
            "products": _fetchone(conn, "SELECT count(*) AS value FROM workspace_products")["value"],
            "samples": _fetchone(conn, "SELECT count(*) AS value FROM samples")["value"],
            "lims_samples": _fetchone(conn, "SELECT count(*) AS value FROM lims_sample")["value"],
            "reports": _fetchone(conn, "SELECT count(*) AS value FROM ble_reports")["value"],
            "product_norm_assignments": _fetchone(
                conn, "SELECT count(*) AS value FROM product_norm_version_assignments"
            )["value"],
            "norm_standards": _fetchone(conn, "SELECT count(*) AS value FROM norm_standards")["value"],
            "norm_versions": _fetchone(conn, "SELECT count(*) AS value FROM norm_versions")["value"],
        }
        target_name = fixture["oracle_expectations"]["product_name"]
        target_products = conn.execute(
            "SELECT count(*) AS value FROM workspace_products WHERE name = %s",
            (target_name,),
        ).fetchone()["value"]
        target_product = None
        if target_products == 1:
            target_product = dict(_fetchone(
                conn,
                """SELECT p.id::text AS id, p.tenant_id::text AS tenant_id,
                          p.plant_id::text AS plant_id, p.laboratory_id::text AS laboratory_id,
                          p.name, p.category, p.material_class_id::text AS material_class_id,
                          p.product_type_id::text AS product_type_id, mc.code AS material_class_code,
                          pt.code AS product_type_code, p.use_area, p.product_level,
                          p.material_base, p.material_origin, p.grain_lower_mm, p.grain_upper_mm,
                          p.sieve_range_text, p.product_group, p.technical_label,
                          p.norm_limit_set_id, p.is_active,
                          (SELECT count(*) FROM product_norm_version_assignments a
                            WHERE a.product_id = p.id) AS product_norm_assignment_count
                     FROM workspace_products p
                     LEFT JOIN material_classes mc ON mc.id = p.material_class_id
                     LEFT JOIN product_types pt ON pt.id = p.product_type_id
                    WHERE p.name = %s""",
                (target_name,),
            ))
        return {
            "database": identity["database"],
            "username": identity["username"],
            "read_only_transaction": identity["transaction_read_only"] == "on",
            "elevated_privileges": False,
            "plant": dict(plant),
            "material_class": dict(material_class),
            "product_type": dict(product_type),
            "counts": counts,
            "target_product_name_count": target_products,
            "target_product": target_product,
        }
    finally:
        conn.rollback()
        conn.close()


def _problem_list(snapshot: dict[str, Any], fixture: dict[str, Any]) -> list[str]:
    expected = fixture["oracle_expectations"]
    plant = snapshot["plant"]
    material_class = snapshot["material_class"]
    product_type = snapshot["product_type"]
    errors = []
    if plant["id"] != fixture["fixture_data"]["plant_id"] or plant["tenant_id"] != fixture["fixture_data"]["tenant_id"]:
        errors.append("Enzberg Werk-/Tenant-Zuordnung stimmt nicht")
    if plant["name"] != "Enzberg" or plant["site_number"] != fixture["fixture_data"]["site_number"] or not plant["is_active"]:
        errors.append("Enzberg-Werk ist nicht aktiv oder hat falsche Fixture-Identität")
    if material_class["id"] != expected["material_class_id"] or material_class["code"] != expected["material_class_code"] or not material_class["is_active"]:
        errors.append("erforderliche aktive STS-Materialklasse fehlt")
    if product_type["id"] != expected["product_type_id"] or product_type["code"] != expected["product_type_code"]:
        errors.append("erforderliche STS-Produktklassifikation fehlt")
    if product_type["material_class_id"] != material_class["id"] or not product_type["is_active"]:
        errors.append("STS-Produkttyp ist inaktiv oder gehört nicht zur Materialklasse")
    return errors


def verify_before(snapshot: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    """Assert the exact clean baseline and return an immutable comparison record."""
    errors = _problem_list(snapshot, fixture)
    expected = fixture["oracle_expectations"]["before_counts"]
    for key, value in expected.items():
        if snapshot["counts"].get(key) != value:
            errors.append(f"Baseline-Zähler {key} ist {snapshot['counts'].get(key)}, erwartet {value}")
    if snapshot["target_product_name_count"] != 0:
        errors.append("STS-0/45-Zielprodukt ist bereits vorhanden")
    if errors:
        raise OracleError("; ".join(errors))
    return {
        "phase": "before",
        "fixture_id": fixture["fixture_id"],
        "database": snapshot["database"],
        "plant_id": snapshot["plant"]["id"],
        "tenant_id": snapshot["plant"]["tenant_id"],
        "material_class_id": snapshot["material_class"]["id"],
        "product_type_id": snapshot["product_type"]["id"],
        "counts": snapshot["counts"],
        "target_product_name_count": 0,
        "docker_container_id": snapshot.get("docker_container_id"),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def verify_after(snapshot: dict[str, Any], fixture: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Verify exactly one expected product and no sample/report/norm side effects."""
    if baseline.get("phase") != "before" or baseline.get("fixture_id") != fixture["fixture_id"]:
        raise OracleError("The supplied baseline does not belong to this fixture")
    if baseline.get("database") != fixture["database"]["name"] or snapshot["database"] != baseline["database"]:
        raise OracleError("Before/after database identity changed")
    errors = _problem_list(snapshot, fixture)
    counts = snapshot["counts"]
    old = baseline["counts"]
    if counts["products"] != old["products"] + 1:
        errors.append("Gesamtzahl Produkte ist nicht exakt um ein Produkt gestiegen")
    if snapshot["target_product_name_count"] != 1:
        errors.append("Zielprodukt ist nicht genau einmal vorhanden")
    unchanged_counts = ("samples", "lims_samples", "reports", "product_norm_assignments", "norm_standards", "norm_versions")
    if any(counts[key] != old[key] for key in unchanged_counts):
        errors.append("Probe, Bericht, Normzuordnung oder Normstammdaten wurden unerwartet verändert")

    product = snapshot.get("target_product")
    if product is None:
        errors.append("Zielprodukt konnte nicht eindeutig gelesen werden")
    else:
        e = fixture["oracle_expectations"]
        for field, expected in {
            "name": e["product_name"],
            "tenant_id": fixture["fixture_data"]["tenant_id"],
            "plant_id": fixture["fixture_data"]["plant_id"],
            "laboratory_id": None,
            "material_class_id": e["material_class_id"],
            "product_type_id": e["product_type_id"],
            "material_class_code": e["material_class_code"],
            "product_type_code": e["product_type_code"],
            "use_area": e["use_area"],
            "product_level": e["product_level"],
            "category": e["category"],
            "grain_lower_mm": 0,
            "grain_upper_mm": 45,
            "sieve_range_text": "0/45",
            "product_group": "STS",
            "technical_label": "STS 0/45",
            "norm_limit_set_id": None,
            "product_norm_assignment_count": 0,
            "is_active": True,
        }.items():
            actual = product.get(field)
            if field in {"grain_lower_mm", "grain_upper_mm"} and actual is not None:
                actual = float(actual)
            if actual != expected:
                errors.append(f"Gespeichertes Produktfeld {field} ist {actual!r}, erwartet {expected!r}")
        for field in ("material_base", "material_origin"):
            if not isinstance(product.get(field), str) or not product[field].strip():
                errors.append(f"Pflichtfeld {field} fehlt")
            elif field in e and product[field] != e[field]:
                errors.append(f"Gespeicherter synthetischer Fixture-Wert {field} stimmt nicht")
    if errors:
        raise OracleError("; ".join(errors))
    return {
        "phase": "after",
        "fixture_id": fixture["fixture_id"],
        "database": snapshot["database"],
        "product": snapshot["target_product"],
        "counts_before": old,
        "counts_after": counts,
        "delta": {key: counts[key] - old[key] for key in counts},
        "baseline_recorded_at_utc": baseline.get("recorded_at_utc"),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def verify_fixture(dsn: str, fixture_path: Path, phase: str, baseline_path: Path | None = None,
                   output_path: Path | None = None) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
    docker_identity = verify_docker_identity(fixture)
    snapshot = collect_snapshot(dsn, fixture)
    snapshot["docker_container_id"] = docker_identity["container_id"]
    if phase == "before":
        report = verify_before(snapshot, fixture)
        report["docker"] = docker_identity
        report["status"] = "BASELINE_READY"
    elif phase == "after":
        if baseline_path is None:
            raise OracleError("--baseline is required for after verification")
        baseline = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
        if baseline.get("docker", {}).get("container_id") != docker_identity["container_id"]:
            raise OracleError("Before/after Docker container identity changed")
        report = verify_after(snapshot, fixture, baseline)
        report["docker"] = docker_identity
        report["status"] = "PERSISTENCE_PASS"
    else:
        raise ValueError("phase must be before or after")
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report

"""Independent SELECT-only Docker/PostgreSQL oracle for read-only scenarios.

Uses the already existing sqbf_oracle_ro login through the container's local
socket. No password extraction, role creation, grants, resets, or mutations.
The Docker identity verifies the external 55432 mapping before every read.
"""
import json
import subprocess
import re

from .oracle import OracleError, verify_docker_identity


def snapshot(fixture, run=subprocess.run, enforce_counts=True):
    expected=fixture.get("read_only_oracle",{}).get("expected_counts")
    if not isinstance(expected,dict) or not expected or any(
            not re.fullmatch(r"[a-z][a-z0-9_]*",table) or type(count) is not int or count<0
            for table,count in expected.items()):
        raise OracleError("Project fixture must define safe protected table identifiers and expected counts")
    docker = verify_docker_identity(fixture, run=lambda *args, **kwargs: run(*args, timeout=5, **kwargs))
    spec = fixture["database"]
    statements = ["BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;",
                  "SET LOCAL statement_timeout='5s';",
                  "SELECT json_build_object('database',current_database(),'username',current_user,"
                  "'read_only',current_setting('transaction_read_only'),'superuser',rolsuper,"
                  "'createdb',rolcreatedb,'createrole',rolcreaterole,'bypassrls',rolbypassrls,"
                  "'create_schema',has_database_privilege(current_user,current_database(),'CREATE'),"
                  "'create_object',has_schema_privilege(current_user,'public','CREATE'))"
                  " FROM pg_roles WHERE rolname=current_user;",
                  "SELECT json_build_object('can_write',coalesce(bool_or("
                  "has_table_privilege(current_user,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')"
                  " OR has_any_column_privilege(current_user,c.oid,'INSERT,UPDATE,REFERENCES')),false))"
                  " FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace"
                  " WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f');"]
    for table in expected:
        statements.append(
            f"SELECT json_build_object('table','{table}','count',count(*),'hash',"
            f"md5(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text),''))) FROM {table} t;"
        )
    statements.append("ROLLBACK;")
    try:
        result = run(["docker", "exec", "-i", spec["container"], "psql", "-X", "-q", "-At",
                      "-U", spec["oracle_role"], "-d", spec["name"], "-v", "ON_ERROR_STOP=1"],
                     input="\n".join(statements), capture_output=True, text=True, check=True, timeout=10)
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        raise OracleError("Read-only snapshot failed; no credentials or DB writes attempted") from None
    identity = rows[0]
    if (identity["database"] != spec["name"] or identity["username"] != spec["oracle_role"]
            or identity["read_only"] != "on" or any(identity[k] for k in
                ("superuser", "createdb", "createrole", "bypassrls", "create_schema", "create_object"))
            or rows[1]["can_write"]):
        raise OracleError("Oracle identity, isolation, or SELECT-only privileges failed")
    tables = {row["table"]: {"count": row["count"], "hash": row["hash"]} for row in rows[2:]}
    if set(tables) != set(expected):
        raise OracleError("Oracle snapshot has missing protected tables")
    if enforce_counts and any(tables[table]["count"]!=count for table,count in expected.items()):
        raise OracleError("Protected table counts do not match the project fixture")
    return {"docker": docker, "identity": identity, "tables": tables}


def compare(before, after, observations, done):
    unchanged = before == after
    search = any(o.get("query_visible") and o.get("empty_visible") for o in observations)
    final = observations[-1] if observations else {}
    reset = search and final.get("target_page") and final.get("filter_cleared") and final.get("empty_visible")
    return {"database_unchanged": unchanged, "search_empty_verified": search,
            "filter_reset_verified": bool(reset), "completed_signal": done,
            "status": "PASS" if unchanged and search and reset and done else "FAIL",
            "limitations": ["Visible query/reset evidence does not establish filtering of populated data unless separately covered by the fixture."]}

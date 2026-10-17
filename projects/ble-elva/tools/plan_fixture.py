"""The existing BLE plan workflow's neutral default project, in the fixture only."""
import hashlib
from uuid import UUID
from .suite_fixture import validate_target


def default_project_id(plant):
    plant=str(UUID(plant))
    raw=bytearray(hashlib.sha256(('ble:sampling-default-project:v1:werk:'+plant).encode('utf-8')).digest()[:16])
    raw[7]=(raw[7]&15)|128;raw[8]=(raw[8]&63)|128
    return str(UUID(bytes_le=bytes(raw)))


def prepare_default_project_sql(fixture):
    validate_target(fixture)
    project=default_project_id(fixture['fixture_data']['plant_id'])
    sql="""BEGIN; SET LOCAL statement_timeout='5s';
DO $$ BEGIN IF (SELECT count(*) FROM samples)<>0 OR (SELECT count(*) FROM lims_sample)<>0
OR (SELECT count(*) FROM ble_reports)<>0 OR (SELECT count(*) FROM projects)<>1
THEN RAISE EXCEPTION 'UNUSED_SOURCE_FIXTURE_REQUIRED'; END IF; END $$;
INSERT INTO projects(id,customer_id,name,created_at)
VALUES('__PROJECT__'::uuid,'00000000-0000-0000-0000-000000000000'::uuid,'Standardprojekt (Beprobungsplan)',now());
COMMIT;""".replace('__PROJECT__',project)
    return sql,project

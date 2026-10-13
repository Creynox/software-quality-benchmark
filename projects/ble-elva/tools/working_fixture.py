"""Create a new private working copy; never drop/reset/reuse a database."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from uuid import uuid4

from sqbf.no_write_oracle import snapshot
from sqbf.oracle import verify_docker_identity
from sqbf.reporting import Evidence
from sqbf.artifact_privacy import create_private_file
from sqbf.scope_check import verify_runtime
from sqbf.session_credentials import load_credentials


def start_working_web(fixture_path, application_root):
    """Restart only the owned clone using its user-bound controller credential."""
    from .lab_guard import validate_target
    from sqbf.models import Scenario
    import socket
    fixture_path=Path(fixture_path)
    fixture=json.loads(fixture_path.read_text(encoding='utf-8-sig'))
    scenario=Scenario.load('projects/ble-elva/scenarios/sts-0-45-product-core-v0.3.json')
    validate_target(scenario,fixture)
    verify_docker_identity(fixture)
    exe=Path(application_root)/fixture['identity_scope_check']['executable']
    dll=Path(application_root)/fixture['identity_scope_check']['assembly']
    expected=fixture['working_copy']['runtime']
    if hashlib.sha256(dll.read_bytes()).hexdigest()!=expected['sha256']:
        raise ValueError('Build changed; re-acceptance required')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',5081))
    credentials=load_credentials(fixture_path.parent/'controller-credentials.dpapi.json',fixture['database']['bootstrap_user'])
    connection=f'Host=127.0.0.1;Port=55433;Database={fixture["database"]["name"]};Username={credentials["username"]};Password={credentials["password"]}'
    env={k:v for k,v in os.environ.items() if k not in ('OPENAI_API_KEY','ANTHROPIC_API_KEY')}
    env.update(ASPNETCORE_ENVIRONMENT='Development',Ble__DisableStartupSeeding='true',
               ConnectionStrings__DefaultConnection=connection,ConnectionStrings__DevelopmentCloneConnection=connection)
    with (fixture_path.parent/'web.stdout.log').open('ab') as stdout,(fixture_path.parent/'web.stderr.log').open('ab') as stderr:
        process=subprocess.Popen([str(exe),'--urls',fixture['target_url'].rstrip('/')],cwd=application_root,env=env,
             stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    fixture['working_copy']['web_pid']=process.pid
    fixture_path.write_text(json.dumps(fixture,indent=2),encoding='utf-8')
    return process.pid


def create_working_fixture(source_path, output, application_root):
    source=json.loads(Path(source_path).read_text(encoding='utf-8-sig'))
    from .lab_guard import validate_source
    validate_source(source)
    before=snapshot(source)
    verify_docker_identity(source)
    runtime=verify_runtime(source['target_url'],application_root,source['identity_scope_check'])
    directory=Path(output);Evidence(directory)
    suffix=uuid4().hex[:12]
    name='sqbf-lab01-'+suffix;database='sqbf_lab01_'+suffix;volume=name+'-data'
    dbport,webport=55433,5081
    # Explicit new destination only; any existing listener or name blocks.
    import socket
    for port in (dbport,webport):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',port))
    def command(args,**kwargs):
        try:
            return subprocess.run(args,capture_output=True,check=True,timeout=60,**kwargs)
        except Exception:
            raise RuntimeError('WORKING_FIXTURE_FAILED; no reset/fallback') from None
    existing=command(['docker','ps','-a','--format','{{.Names}}']).stdout.decode().splitlines()
    volumes=command(['docker','volume','ls','--format','{{.Name}}']).stdout.decode().splitlines()
    if name in existing or volume in volumes:raise ValueError('Destination already exists')
    dump=command(['docker','exec',source['database']['container'],'pg_dump','-Fc','-U',source['database']['bootstrap_user'],'-d',source['database']['name']]).stdout
    (directory/'golden.dump').write_bytes(dump)
    os.chmod(directory/'golden.dump',0o400)
    admin_password=secrets.token_hex(32);oracle_password=secrets.token_hex(32)
    envfile=directory/'container.env'
    envfile.write_text('POSTGRES_USER='+source['database']['bootstrap_user']+'\nPOSTGRES_DB='+database+'\nPOSTGRES_PASSWORD='+admin_password+'\n',encoding='utf-8')
    command(['docker','volume','create',volume])
    result=command(['docker','run','-d','--name',name,'--env-file',str(envfile),'-p',f'127.0.0.1:{dbport}:5432','-v',volume+':/var/lib/postgresql/data',source['database']['image']])
    envfile.unlink()
    container_id=result.stdout.decode().strip()
    (directory/'provisioning-state.json').write_text(json.dumps({'container':name,'container_id':container_id,
        'database':database,'volume':volume,'stage':'new_container_created','recovery':'Inspect exact identity; never reset or reuse'},indent=2),encoding='utf-8')
    for _ in range(30):
        ready=subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U',source['database']['bootstrap_user'],'-d',database],capture_output=True,timeout=5)
        if ready.returncode==0:break
        time.sleep(0.5)
    else:raise RuntimeError('WORKING_FIXTURE_NOT_READY')
    fixture=json.loads(json.dumps(source))
    fixture['database'].update(container=name,container_id=container_id,name=database,volume=volume,host_port=dbport,host_binding=f'127.0.0.1:{dbport}')
    fixture['fixture_id']='lab01-working-'+suffix;fixture['target_url']=f'http://127.0.0.1:{webport}/'
    fixture['oracle_expectations'].update(material_base='Kalkstein',material_origin='gebrochen')
    verify_docker_identity(fixture)
    # Only the brand-new empty clone receives these role/restore operations.
    sql="CREATE ROLE sqbf_oracle_ro LOGIN PASSWORD '"+oracle_password+"';"
    command(['docker','exec','-i',name,'psql','-X','-q','-U',source['database']['bootstrap_user'],'-d',database,'-v','ON_ERROR_STOP=1'],input=sql.encode())
    command(['docker','exec','-i',name,'pg_restore','--exit-on-error','--no-owner','-U',source['database']['bootstrap_user'],'-d',database],input=dump)
    copied=snapshot(fixture)
    if copied['tables']!=before['tables']:raise RuntimeError('WORKING_COPY_MISMATCH')
    if snapshot(source)!=before:raise RuntimeError('SOURCE_CHANGED')
    fixture['working_copy']={'source_fixture':str(Path(source_path).resolve()),'source_snapshot':before,
        'golden_sha256':hashlib.sha256(dump).hexdigest(),'disposable':True,'never_reset':True,'runtime':runtime}
    # Password is DPAPI-bound, captured in a pipe, never printed or committed.
    script=r"$c=[Console]::In.ReadToEnd()|ConvertFrom-Json;@{username=$c.username;password_dpapi=(ConvertTo-SecureString $c.password -AsPlainText -Force|ConvertFrom-SecureString)}|ConvertTo-Json -Compress"
    for filename,username,password in [('oracle-credentials.dpapi.json','sqbf_oracle_ro',oracle_password),
                                       ('controller-credentials.dpapi.json',source['database']['bootstrap_user'],admin_password)]:
        protected=command(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
            input=json.dumps({'username':username,'password':password}).encode(),
            env={k:v for k,v in os.environ.items() if k.lower()!='psmodulepath'}).stdout
        create_private_file(directory/filename)
        (directory/filename).write_bytes(protected)
    fixture['oracle_credential_file']=str((directory/'oracle-credentials.dpapi.json').resolve())
    exe=Path(application_root)/source['identity_scope_check']['executable']
    env={k:v for k,v in os.environ.items() if k not in ('OPENAI_API_KEY','ANTHROPIC_API_KEY')}
    connection=f'Host=127.0.0.1;Port={dbport};Database={database};Username={source["database"]["bootstrap_user"]};Password={admin_password}'
    env.update(ASPNETCORE_ENVIRONMENT='Development',Ble__DisableStartupSeeding='true',
               ConnectionStrings__DefaultConnection=connection,ConnectionStrings__DevelopmentCloneConnection=connection)
    with (directory/'web.stdout.log').open('wb') as stdout,(directory/'web.stderr.log').open('wb') as stderr:
        process=subprocess.Popen([str(exe),'--urls',fixture['target_url'].rstrip('/')],cwd=application_root,env=env,stdout=stdout,stderr=stderr,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    fixture['working_copy']['web_pid']=process.pid
    (directory/'fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
    return directory/'fixture.json'

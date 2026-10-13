"""Controller-only signed identity and read-only authorization gate; no fallback."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
from uuid import UUID

from .oracle import verify_docker_identity
from .session_check import check_session


def evaluate(ticket, scope, fixture):
    """Return fixed identifiers only; never echo external query/helper fields."""
    f = fixture['fixture_data']
    checks = {
        'signed_session': ticket.get('valid') is True,
        'account': ticket.get('username') == f['laboratory_lead_account']
                   and scope.get('username') == f['laboratory_lead_account']
                   and ticket.get('user_id') == scope.get('user_id') == f['laboratory_lead_user_id']
                   and scope.get('users') == 1,
        'active': scope.get('active') is True and scope.get('admin') is False,
        'tenant': scope.get('tenant_id') == f['tenant_id'] and scope.get('tenant_active') is True,
        'role': scope.get('laboratory_role') is True,
        'permission': scope.get('product_permission') is True,
        'plant': scope.get('plant_valid') is True and scope.get('expected_plant_scopes') == 1
                 and scope.get('plant_scopes') == 1,
        'no_global_scope': scope.get('global_scopes') == 0,
        'scope_set': scope.get('tenant_scopes') == 1 and scope.get('all_scopes') == 2,
        'read_only_identity': scope.get('database') == fixture['database']['name']
                              and scope.get('role') == fixture['database']['bootstrap_user']
                              and scope.get('read_only') == 'on',
    }
    return {'status': 'SCOPE_VERIFIED' if all(checks.values()) else 'BLOCKED_SCOPE_VERIFICATION',
            'checks': checks, 'model_calls': 0, 'ui_actions': 0}


def verify_runtime(url, application_root, config, run=subprocess.run):
    """Bind the supplied cookie discriminator to the actual loopback process."""
    parsed = urlsplit(url)
    if os.name != 'nt' or parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.path != '/' or parsed.query or parsed.fragment or parsed.username:
        raise ValueError()
    root = Path(application_root).resolve(strict=True)
    script = r'''
$ErrorActionPreference='Stop'
$c=[Console]::In.ReadToEnd() | ConvertFrom-Json
$l=@(Get-NetTCPConnection -State Listen -LocalPort $c.port | Where-Object LocalAddress -eq '127.0.0.1')
if ($l.Count -ne 1) {throw 'Invalid listener'}
$p=Get-CimInstance Win32_Process -Filter ("ProcessId="+$l[0].OwningProcess)
$exe=Join-Path $c.root $c.executable
if ($p.ExecutablePath -ne $exe) {throw 'Unexpected process'}
$dll=Join-Path $c.root $c.assembly
$f=Get-Item -LiteralPath $dll
if ($f.LastWriteTime -gt $p.CreationDate) {throw 'Build changed after launch'}
@{pid=$p.ProcessId;assembly=$f.VersionInfo.ProductVersion;sha256=(Get-FileHash -LiteralPath $dll).Hash.ToLower()} | ConvertTo-Json -Compress
'''
    r = run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
            input=json.dumps({'root':str(root),'port':parsed.port,'executable':config['executable'],
                              'assembly':config['assembly']}),capture_output=True,text=True,check=True,timeout=15,
            env={k:v for k,v in os.environ.items() if k.lower() != 'psmodulepath'})
    data=json.loads(r.stdout)
    return {k:data[k] for k in ('pid','assembly','sha256')}


def check_scope(url, storage_state, policy, fixture, application_root, verifier, *,
                run=subprocess.run, session_fn=check_session, runtime_fn=verify_runtime):
    """Explicit existing fixture-controller role, NOT an Oracle privilege fallback.

    The isolated Docker identity is verified BEFORE selecting this role. Only
    a repository-owned fixed projection is executed in READ ONLY/ROLLBACK.
    Exceptions/credentials/query output never enter the result or model IPC.
    """
    blocked={'status':'BLOCKED_SCOPE_VERIFICATION','model_calls':0,'ui_actions':0}
    try:
        if url != fixture['target_url'] or not application_root or not verifier:
            return dict(blocked,reason='CONFIGURATION_MISSING')
        f=fixture['fixture_data']
        for key in ('tenant_id','plant_id','laboratory_lead_user_id'):
            if str(UUID(f[key])) != f[key]: raise ValueError()
        config=fixture['identity_scope_check']
        if config['access'] != 'verified_fixture_controller_read_only' or config['role'] != fixture['database']['bootstrap_user']:
            raise ValueError()
        docker=verify_docker_identity(fixture,run=run)
        runtime=runtime_fn(url,application_root,config)
        session=session_fn(url,storage_state,policy)
        if session['status'] != 'SESSION_RESTORED':
            return dict(blocked,reason='SESSION_INVALID')
        request={'storage_state':str(Path(storage_state).resolve()),'application_root':str(Path(application_root).resolve())}
        ticket_result=run(['dotnet',str(Path(verifier).resolve(strict=True))],input=json.dumps(request),
                          capture_output=True,text=True,check=True,timeout=15)
        ticket=json.loads(ticket_result.stdout)
        if ticket.get('valid') is not True or ticket.get('username') != f['laboratory_lead_account'] or ticket.get('user_id') != f['laboratory_lead_user_id']:
            return dict(blocked,reason='SIGNED_IDENTITY_INVALID')
        sql=Path(config['projection']).read_text(encoding='utf-8')
        if hashlib.sha256(sql.encode('utf-8')).hexdigest() != config['projection_sha256']:
            return dict(blocked,reason='PROJECTION_MISMATCH')
        command=['docker','exec','-i',docker['container_id'],'psql','-X','-q','-At','-U',config['role'],
                 '-d',fixture['database']['name'],'-v','ON_ERROR_STOP=1']
        for name,value in {'username':f['laboratory_lead_account'],'tenant_id':f['tenant_id'],'plant_id':f['plant_id'],
                           'plant_name':f['plant_name'],'site_number':f['site_number']}.items():
            command.extend(['-v',name+'='+value])
        scope_result=run(command,input=sql,capture_output=True,text=True,check=True,timeout=10)
        scope=json.loads(scope_result.stdout)
        result=evaluate(ticket,scope,fixture)
        result['runtime']=runtime
        result['access']='VERIFIED_EXISTING_CONTROLLER_READ_ONLY'
        return result
    except Exception:
        return dict(blocked,reason='EVIDENCE_UNAVAILABLE')

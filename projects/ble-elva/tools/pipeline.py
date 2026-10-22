"""NSN014 run dossier (Lauf-Akte): one fixed procedure from A to Z that every agent can follow (PO decision 2026-10-21).

A dossier is a folder <dossiers_root>/<name>/ with dossier.json; every step records its status, time and outputs there, always in this order:

  dry_run_clean   scratch clone + sessions + scripted dry run                       no model request
  dry_run_faults  scratch clone + sessions + scripted dry run with provider faults  no model request
  rehearsal       optional: scratch clone + sessions + Claude executor              Claude Code login; never a benchmark result
  fixture         run fixture clone + sessions                                      no model request
  probe           provider probe: two synthetic ChatGPT-plan requests
  approval        only on an explicit PO order: approval copy bound to commit, fixture and budget
  run             readiness, exactly one live run (no retry), reports

`status` shows the checklist and the next command. The steps call the existing, tested functions (fixture_clone, suite_sessions, dry_run,
provider_probe, regular_runner); nothing here bypasses a gate. What used to live in private helper scripts is decided here, from facts:
which fixture holds the ports 5082/55434 (container name and web process recorded in its manifest) and which session files are the newest
ones that may still be renewed once (no login-attempt marker). Private paths (golden source, controller credentials, data) stay in a local
configuration outside the public repository: %LOCALAPPDATA%/SQBF/nsn014-pipeline.json (template: projects/ble-elva/pipeline.example.json).
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

STEPS = ('dry_run_clean', 'dry_run_faults', 'rehearsal', 'fixture', 'probe', 'approval', 'run')
OPTIONAL = {'rehearsal'}
STEP_LABELS = {'dry_run_clean': 'Trockenlauf sauber', 'dry_run_faults': 'Trockenlauf mit Fehlerinjektion', 'rehearsal': 'Probelauf mit Claude-Executor',
               'fixture': 'Fixture für den Lauf', 'probe': 'Provider-Probe', 'approval': 'Freigabe des PO', 'run': 'Benchmark-Lauf'}
STEP_COMMANDS = {'dry_run_clean': 'dry-run', 'dry_run_faults': 'dry-run-faults', 'rehearsal': 'rehearse', 'fixture': 'fixture', 'probe': 'probe',
                 'approval': 'approve --statement "<Wortlaut der Freigabe des PO>"', 'run': 'run'}
DONE = {'dry_run_clean': 'PASSED', 'dry_run_faults': 'PASSED', 'rehearsal': 'RECORDED', 'fixture': 'READY', 'probe': 'PASSED', 'approval': 'APPROVED',
        'run': 'RECORDED'}
DEFAULT_FAULTS = {9: 'raise', 40: 'not_object', 150: 'raise'}
PROBE_HOURS = 12
SESSION_PERSONAS = ('laboratory_lead', 'laboratory_staff', 'wpk_lead', 'plant_lead')
CONFIG_KEYS = ('suite', 'dataset', 'projection', 'allocations', 'golden_source', 'golden_tree_sha256', 'controller_credentials', 'fixtures_root',
               'dossiers_root', 'runs_root', 'probes_root', 'executor_model', 'reviewer_model', 'rehearsal_model')


class PipelineError(RuntimeError):
    def __init__(self, code, hint=''):
        super().__init__(code + (': ' + hint if hint else ''))
        self.code, self.hint = code, hint


def config_path(environ=None):
    environ = os.environ if environ is None else environ
    if environ.get('SQBF_NSN014_CONFIG'):
        return Path(environ['SQBF_NSN014_CONFIG'])
    return Path(environ.get('LOCALAPPDATA', str(Path.home()))) / 'SQBF' / 'nsn014-pipeline.json'


def load_config(path=None):
    path = Path(path) if path else config_path()
    if not path.is_file():
        raise PipelineError('CONFIG_MISSING', f'{path} anlegen (Vorlage projects/ble-elva/pipeline.example.json)')
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    missing = [key for key in CONFIG_KEYS if not config.get(key)]
    if missing:
        raise PipelineError('CONFIG_INCOMPLETE', ', '.join(missing))
    return config


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


# ---- the dossier --------------------------------------------------------------------------------------------------------------------------

class Dossier:
    def __init__(self, config, name):
        if not name or any(ch in name for ch in '/\\:*?"<>|') or name in ('.', '..'):
            raise PipelineError('INVALID_NAME', name)
        self.config, self.name = config, name
        self.path = Path(config['dossiers_root']) / name
        self.file = self.path / 'dossier.json'
        self.data = json.loads(self.file.read_text(encoding='utf-8')) if self.file.is_file() else {'name': name, 'created_at': now(), 'steps': {}}

    def save(self):
        self.path.mkdir(parents=True, exist_ok=True)
        temporary = self.file.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, self.file)

    def step(self, key):
        return self.data['steps'].get(key) or {}

    def done(self, key):
        return self.step(key).get('status') == DONE[key]

    def record(self, key, status, **outputs):
        entry = dict(self.step(key), status=status, finished_at=now(), **outputs)
        entry.setdefault('started_at', entry['finished_at'])
        self.data['steps'][key] = entry
        self.save()
        return entry

    def start(self, key, *, alive=None):
        """Marks the step RUNNING with the PID of this process. A step left RUNNING by a process that no longer lives (it was killed, live
        dossier lauf-09 on 2026-10-21) is kept as ABORTED in the history and may start again; a living one is never started twice."""
        alive = alive or process_alive
        entry = self.step(key)
        if entry.get('status') == 'RUNNING' and not entry.get('finished_at'):
            if entry.get('pid') and alive(entry['pid']):
                raise PipelineError('STEP_ALREADY_RUNNING', f"{key} (PID {entry['pid']})")
            self.data.setdefault('history', []).append(dict(entry, step=key, status='ABORTED', noticed_at=now()))
        self.data['steps'][key] = {'status': 'RUNNING', 'started_at': now(), 'pid': os.getpid()}
        self.save()

    def next_step(self):
        for key in STEPS:
            if key in OPTIONAL:
                continue
            if not self.done(key):
                return key
        return None


def checklist(dossier):
    """(step, label, status, done) for the status display; the rehearsal is shown only when it was started."""
    items = []
    for key in STEPS:
        entry = dossier.step(key)
        if key in OPTIONAL and not entry:
            continue
        items.append((key, STEP_LABELS[key], entry.get('status', 'OFFEN'), dossier.done(key)))
    return items


# ---- facts about the machine ----------------------------------------------------------------------------------------------------------------

def process_alive(pid):
    """True if a process with this PID is still running (Windows: OpenProcess and GetExitCodeProcess; never a signal that could stop it)."""
    if os.name != 'nt':
        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            return False
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    handle = kernel.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
    finally:
        kernel.CloseHandle(handle)


def _run(args, run=subprocess.run, timeout=60):
    return run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)


def docker_ready(run=subprocess.run):
    try:
        return _run(['docker', 'info', '--format', '{{.ServerVersion}}'], run).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def running_containers(run=subprocess.run):
    done = _run(['docker', 'ps', '--format', '{{.Names}}\t{{.Ports}}'], run)
    if done.returncode != 0:
        raise PipelineError('DOCKER_NOT_READY', 'Docker Desktop starten und auf `docker info` warten')
    rows = {}
    for line in done.stdout.splitlines():
        name, _, ports = line.partition('\t')
        rows[name.strip()] = ports.strip()
    return rows


def listening_pid(port, run=subprocess.run):
    """PID listening on 127.0.0.1:<port>, from netstat (the state column is localised, so only address and PID are read)."""
    done = _run(['netstat', '-ano', '-p', 'tcp'], run)
    for line in done.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == 'TCP' and parts[1].endswith(':' + str(port)) and parts[2] in ('0.0.0.0:0', '[::]:0'):
            if parts[-1].isdigit():
                return int(parts[-1])
    return None


def manifests(config):
    """Every fixture manifest below the fixture and dossier roots: (path, manifest), newest file first."""
    roots = [Path(config['fixtures_root']), Path(config['dossiers_root'])]
    found = []
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        for pattern in ('sqbf-nsn014-*/*.json', '*/*/*.json'):
            for path in root.glob(pattern):
                if path in seen or path.stat().st_size > 2_000_000:
                    continue
                seen.add(path)
                try:
                    data = json.loads(path.read_text(encoding='utf-8-sig'))
                except (OSError, ValueError):
                    continue
                if isinstance(data, dict) and {'fixture_id', 'suite_copy', 'database', 'personas'} <= set(data):
                    found.append((path, data))
    return sorted(found, key=lambda item: item[0].stat().st_mtime, reverse=True)


def occupant(config, containers, web_pid):
    """The manifest of the fixture that holds the ports: its container runs and its recorded web process listens on 5082."""
    running = {name for name in containers if name.startswith('sqbf-nsn014-')}
    for path, data in manifests(config):
        if data['database'].get('container') in running and data['suite_copy'].get('web_pid') == web_pid:
            return path
    return None


def _marker(session_file, persona):
    key = hashlib.sha256(Path(session_file).read_bytes()).hexdigest()
    return Path(session_file).parent / f'login-attempt-{persona}-{key}.json'


def session_seed(config):
    """The manifest whose four session files are the newest and none of which was used for a renewal yet (one renewal per old file)."""
    best = None
    for path, data in manifests(config):
        files = []
        for persona in SESSION_PERSONAS:
            actor = data['personas'].get(persona) or {}
            state = Path(actor.get('storage_state') or '')
            if not state.is_absolute():
                state = path.parent / state
            files.append((persona, state))
        if not all(state.is_file() for _, state in files) or any(_marker(state, persona).exists() for persona, state in files):
            continue
        newest = min(state.stat().st_mtime for _, state in files)
        if best is None or newest > best[0]:
            best = (newest, path)
    return best[1] if best else None


def ports_state(config, run=subprocess.run):
    containers = running_containers(run)
    pid = listening_pid(5082, run)
    holder = occupant(config, containers, pid) if pid else None
    ours = [name for name in containers if name.startswith('sqbf-nsn014-')]
    return {'web_pid': pid, 'containers': ours, 'occupant': str(holder) if holder else None,
            'free': pid is None and not any('55434' in containers[name] for name in ours)}


def probe_state(config, commit=None, clock=None):
    """Newest provider probe: passed, younger than PROBE_HOURS and (if given) from this commit."""
    clock = clock or datetime.now(timezone.utc)
    root = Path(config['probes_root'])
    probes = sorted(root.glob('provider-probe-*.json'), key=lambda p: p.stat().st_mtime, reverse=True) if root.is_dir() else []
    for path in probes:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            created = datetime.fromisoformat(data['created_at'])
        except (OSError, ValueError, KeyError):
            continue
        fresh = clock - created < timedelta(hours=PROBE_HOURS)
        valid = data.get('verdict') == 'PROBE_PASS' and fresh and (commit is None or data.get('sqbf_commit') == commit)
        return {'path': str(path), 'valid': valid, 'created_at': data['created_at'], 'commit': data.get('sqbf_commit')}
    return None


# ---- the steps -----------------------------------------------------------------------------------------------------------------------------

def _inputs(config, fixture_path):
    from . import regular_runner
    return regular_runner.load_inputs(config['suite'], config['dataset'], str(fixture_path), config['projection'], config['allocations'])


def attempt_folder(dossier, base):
    """A new folder per attempt: a repeated step never reuses (or fails on) the folders of an earlier, failed or aborted attempt."""
    if not (dossier.path / base).exists():
        return base
    number = 2
    while (dossier.path / f'{base}-{number}').exists():
        number += 1
    return f'{base}-{number}'


def _error_fields(error):
    fields = {'error': getattr(error, 'code', None) or type(error).__name__}
    phase, reason = getattr(error, 'phase', None), getattr(error, 'reason', None)
    if phase or reason:
        fields['error_detail'] = f'{phase}:{reason}'
    if getattr(error, 'hint', None):
        fields['hint'] = error.hint
    return fields


def clone_with_sessions(config, dossier, folder_name, purpose, *, clone=None, sessions=None, run=subprocess.run):
    """New clone from the stopped golden source (the port holder is stopped and kept), then the four persona sessions. Returns the sessions manifest."""
    from . import fixture_clone, suite_sessions
    clone = clone or fixture_clone.clone_fixture
    sessions = sessions or suite_sessions.write_prepared_sessions
    if not docker_ready(run):
        raise PipelineError('DOCKER_NOT_READY', 'Docker Desktop starten und auf `docker info` warten')
    state = ports_state(config, run)
    if state['web_pid'] and not state['occupant']:
        raise PipelineError('PORT_5082_HELD_BY_UNKNOWN_PROCESS', f"PID {state['web_pid']}: kein Manifest beschreibt diesen Prozess; zuerst prüfen und beenden")
    if not state['web_pid']:
        # One of our own clone containers can be left holding 55434 after its web died: stop (never remove) it, then clone without occupant.
        containers = running_containers(run)
        for name in state['containers']:
            if '55434' in containers.get(name, ''):
                done = _run(['docker', 'stop', '-t', '120', name], run, timeout=180)
                if done.returncode != 0:
                    raise PipelineError('STRAY_CONTAINER_NOT_STOPPED', name)
                dossier.data.setdefault('history', []).append({'event': 'stray_container_stopped', 'container': name, 'at': now()})
                dossier.save()
    output = dossier.path / attempt_folder(dossier, folder_name)
    seed = session_seed(config) or (Path(state['occupant']) if state['occupant'] else None)
    manifest = clone(config['golden_source'], config['controller_credentials'], str(output), source_stopped=True,
                     expected_tree_sha256=config['golden_tree_sha256'], occupant_path=state['occupant'], purpose=purpose,
                     session_seed_path=str(seed) if seed else None)
    prepared = output / 'fixture-sessions.json'
    result = sessions(str(manifest), str(prepared), str(output / 'sessions-report.json'))
    if result.get('status') != 'SESSIONS_VERIFIED':
        raise PipelineError('SESSIONS_NOT_VERIFIED', result.get('reason', ''))
    return prepared


def dry_run(config, dossier, *, faults=False, rehearsal_model=None, clone=None, sessions=None, run_dry=None, executor_factory=None):
    from . import dry_run as dry
    key = 'rehearsal' if rehearsal_model else 'dry_run_faults' if faults else 'dry_run_clean'
    dossier.start(key)
    try:
        prepared = clone_with_sessions(config, dossier, {'dry_run_clean': 'scratch-clean', 'dry_run_faults': 'scratch-faults',
                                                         'rehearsal': 'scratch-rehearsal'}[key], 'scratch', clone=clone, sessions=sessions)
        inputs = _inputs(config, prepared)
        executor = None
        if rehearsal_model:
            from .claude_executor import ClaudeCliExecutor
            executor = (executor_factory or ClaudeCliExecutor)(rehearsal_model)
        folder = dossier.path / attempt_folder(dossier, {'dry_run_clean': 'dry-run-clean', 'dry_run_faults': 'dry-run-faults', 'rehearsal': 'rehearsal'}[key])
        report = (run_dry or dry.run_dry)(*inputs, str(folder), faults=DEFAULT_FAULTS if faults else None, executor=executor)
    except Exception as error:
        return dossier.record(key, 'FAILED', **_error_fields(error))
    if rehearsal_model:
        status = 'RECORDED' if report['status'] == 'REHEARSAL_COMPLETED' else 'FAILED'
    else:
        status = 'PASSED' if report['status'] == 'DRY_RUN_COMPLETED' else 'FAILED'
    return dossier.record(key, status, folder=str(folder), fixture=str(prepared), report_status=report['status'], points=report.get('points'),
                          harness_stops=report.get('harness_stops'), rejected_actions=report.get('rejected_actions'), executor=report.get('executor'))


def prepare(config, dossier, *, rehearse=False, step=None):
    """The preparation in one go: dry run, dry run with faults and (optional) the rehearsal. Passed steps are kept, the first failed step ends it."""
    step = step or dry_run
    plan = [('dry_run_clean', {}), ('dry_run_faults', {'faults': True})]
    if rehearse:
        plan.append(('rehearsal', {'rehearsal_model': config['rehearsal_model']}))
    results = {}
    for key, options in plan:
        if dossier.done(key):
            results[key] = dossier.step(key)
            continue
        results[key] = step(config, dossier, **options)
        if results[key]['status'] != DONE[key]:
            break
    return results


def fixture(config, dossier, *, clone=None, sessions=None, ready=None):
    from . import regular_runner
    dossier.start('fixture')
    try:
        prepared = clone_with_sessions(config, dossier, 'fixture', 'fixture', clone=clone, sessions=sessions)
        report = (ready or regular_runner.check_ready)(*_inputs(config, prepared), executor_id=config['executor_model'], reviewer_id=config['reviewer_model'])
    except Exception as error:
        return dossier.record('fixture', 'FAILED', **_error_fields(error))
    # Before the approval the readiness can only end with "every other gate passed, the PO's budget decision is outstanding".
    ready_now = ready_without_approval(report)
    return dossier.record('fixture', 'READY' if ready_now else 'FAILED', fixture=str(prepared), readiness=report.get('status'),
                          readiness_reason=report.get('reason'))


def ready_without_approval(report):
    return report.get('status') == 'READY_FOR_SINGLE_SUITE_RUN' or (report.get('reason') == 'BUDGET_APPROVAL_MISSING' and report.get('other_gates') == 'PASSED')


def _blocking(report):
    return [] if report.get('status') == 'READY_FOR_SINGLE_SUITE_RUN' else [str(report.get('reason') or report.get('status'))]


def probe(config, dossier, *, provider_probe=None):
    from sqbf.write_profile import load_suite_profile
    dossier.start('probe')
    try:
        suite = json.loads(Path(config['suite']).read_text(encoding='utf-8-sig'))
        report = (provider_probe or load_suite_profile(suite.get('adapter_contract')).provider_probe)(
            suite, config['probes_root'], config['executor_model'], config['reviewer_model'], execute=True)
    except Exception as error:
        return dossier.record('probe', 'FAILED', error=type(error).__name__)
    passed = report.get('status') == 'PROBE_RECORDED' and report.get('verdict') == 'PROBE_PASS'
    return dossier.record('probe', 'PASSED' if passed else 'FAILED', path=report.get('path'), commit=report.get('sqbf_commit'),
                          created_at=report.get('created_at'), verdict=report.get('verdict'))


def approve(config, dossier, statement, *, approved_by='PO', approved_at=None, source=None):
    """Writes the approval copy of the run fixture: only on an explicit PO order, exactly one run, bound to the commit, the fixture and the budget."""
    from sqbf.suites import canonical_hash
    from . import regular_runner
    if not statement or len(statement.strip()) < 10:
        raise PipelineError('STATEMENT_REQUIRED', 'den Wortlaut der Freigabe des PO angeben')
    if not dossier.done('fixture'):
        raise PipelineError('FIXTURE_NOT_READY', 'zuerst `fixture`')
    source = source or regular_runner.source_state()
    if not source['clean']:
        raise PipelineError('SOURCE_NOT_CLEAN', 'SQBF-Quellen haben lokale Änderungen; zuerst committen')
    prepared = Path(dossier.step('fixture')['fixture'])
    data = json.loads(prepared.read_text(encoding='utf-8-sig'))
    if 'budget_approval' in data['suite_copy']:
        raise PipelineError('ALREADY_APPROVED')
    if (Path(data['suite_copy']['application_root']).parent / 'benchmark-consumed.json').exists():
        raise PipelineError('FIXTURE_ALREADY_CONSUMED')
    suite = json.loads(Path(config['suite']).read_text(encoding='utf-8-sig'))
    policy = suite['resource_policy']
    data['suite_copy']['budget_approval'] = {
        'approved_by': approved_by, 'approved_at': approved_at or datetime.now(timezone.utc).date().isoformat(), 'statement': statement.strip(),
        'profile': policy.get('profile'), 'suite_sha256': canonical_hash(suite),
        'hard_seconds': policy['hard_seconds'], 'hard_model_calls': policy['hard_model_calls'], 'approved_commit': source['commit'], 'runs_approved': 1}
    target = prepared.with_name('fixture-approved.json')
    if target.exists():
        raise PipelineError('APPROVAL_FILE_EXISTS')
    target.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return dossier.record('approval', 'APPROVED', fixture=str(target), approved_commit=source['commit'], statement=statement.strip())


def run(config, dossier, *, ready=None, run_suite=None, write_report=None):
    from . import regular_runner, report_html
    for key in ('dry_run_clean', 'dry_run_faults', 'fixture', 'probe', 'approval'):
        if not dossier.done(key):
            raise PipelineError('STEP_MISSING', STEP_LABELS[key])
    if dossier.step('run').get('status') in ('RUNNING', 'RECORDED'):
        raise PipelineError('RUN_ALREADY_STARTED', 'eine Freigabe gilt für genau einen Lauf')
    fixture_path, probe_path = dossier.step('approval')['fixture'], dossier.step('probe')['path']
    inputs = _inputs(config, fixture_path)
    report = (ready or regular_runner.check_ready)(*inputs, provider_probe=probe_path, executor_id=config['executor_model'],
                                                     reviewer_id=config['reviewer_model'])
    if report.get('status') != 'READY_FOR_SINGLE_SUITE_RUN':
        return dossier.record('run', 'NOT_READY', readiness=report.get('status'), reasons=_blocking(report))
    dossier.start('run')
    try:
        result = (run_suite or regular_runner.run_suite)(*inputs, config['runs_root'], config['executor_model'], config['reviewer_model'],
                                                           provider_probe=probe_path)
    except Exception as error:
        return dossier.record('run', 'FAILED', error=type(error).__name__)
    entry = dossier.record('run', 'RECORDED', run_id=result.get('run_id'), path=result.get('path'), verdict=result.get('verdict'),
                           technical_status=result.get('technical_status'))
    if result.get('path'):
        try:
            folder = Path(result['path'])
            card = json.loads((folder / 'scorecard.json').read_text(encoding='utf-8'))
            (write_report or report_html.write_report)(folder, card, history_roots=(config['runs_root'],), gates={'dry_runs': True})
        except Exception as error:
            entry = dossier.record('run', 'RECORDED', report_html_error=type(error).__name__)
    return entry


def detached_command(arguments, log_path, *, python=None, environ=None, which=None):
    """The command line that runs `python -m sqbf.cli <arguments>` on its own, writing to `log_path`.

    Long steps (prepare, rehearse, run) take one to three hours. Started inside an agent session they die with it: the dry run of dossier
    lauf-09 was terminated after ten minutes by the session's command timeout. A process created through WMI belongs to no session process tree.
    Only the variables the steps need are passed on (the new process starts with the user's default environment)."""
    import shutil
    import sys
    environ = os.environ if environ is None else environ
    which = which or shutil.which
    python = python or sys.executable
    for value in [python, str(log_path)] + list(arguments):
        if any(ch in str(value) for ch in '"&|<>^%') or ' ' in str(value):
            raise PipelineError('DETACH_UNSAFE_ARGUMENT', str(value))
    tools = [str(Path(path).parent) for path in (which('docker'), which('git')) if path]
    sets = ['PYTHONIOENCODING=utf-8', 'SQBF_NSN014_CONFIG=' + str(config_path(environ))]
    for key in ('SQBF_CLAUDE_CLI',):
        if environ.get(key):
            sets.append(f'{key}={environ[key]}')
    if not environ.get('SQBF_CLAUDE_CLI'):
        try:
            from .claude_executor import cli_path
            sets.append('SQBF_CLAUDE_CLI=' + cli_path(environ))
        except Exception:
            pass
    sets.append('PATH=' + ';'.join(dict.fromkeys(tools)) + ';%PATH%')
    prefix = '&& '.join('set ' + item for item in sets)
    return f'cmd.exe /c "{prefix}&& {python} -u -m sqbf.cli {" ".join(arguments)} > {log_path} 2>&1"'


def detach(arguments, log_path, cwd, *, run=subprocess.run, **options):
    """Starts the command through WMI (Windows) and returns the PID of the started cmd.exe."""
    command = detached_command(arguments, log_path, **options)
    script = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='" + command.replace("'", "''")
              + "'; CurrentDirectory='" + str(cwd).replace("'", "''") + "'}; if ($r.ReturnValue -ne 0) { exit 3 }; $r.ProcessId")
    done = _run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script], run, timeout=60)
    pid = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ''
    if done.returncode != 0 or not pid.isdigit():
        raise PipelineError('DETACH_FAILED', f'returncode {done.returncode}')
    return int(pid)


def status(config, name=None, *, run=subprocess.run):
    """Everything an agent needs to know before the next step: the machine, the dossier checklist and the next command."""
    from . import regular_runner
    facts = {'docker': docker_ready(run)}
    try:
        facts['ports'] = ports_state(config, run) if facts['docker'] else None
    except PipelineError as error:
        facts['ports'] = {'error': error.code}
    try:
        source = regular_runner.source_state()
        facts['source'] = {'commit': source['commit'][:7], 'clean': source['clean']}
    except Exception:
        source, facts['source'] = None, None
    facts['probe'] = probe_state(config, source['commit'] if source else None)
    seed = session_seed(config)
    facts['session_seed'] = str(seed) if seed else None
    if not name:
        root = Path(config['dossiers_root'])
        facts['dossiers'] = sorted(p.name for p in root.iterdir() if (p / 'dossier.json').is_file()) if root.is_dir() else []
        return facts
    dossier = Dossier(config, name)
    facts['dossier'] = {'name': name, 'path': str(dossier.path), 'checklist': checklist(dossier)}
    step = dossier.next_step()
    facts['next'] = None if step is None else {'step': step, 'label': STEP_LABELS[step],
                                               'command': f'python -m sqbf.cli nsn014 {STEP_COMMANDS[step]} --name {name}'}
    return facts


def render_status(facts):
    """Short, human-readable text for the terminal."""
    lines = []
    ports = facts.get('ports') or {}
    lines.append('Docker: ' + ('bereit' if facts.get('docker') else 'NICHT bereit (Docker Desktop starten)'))
    if ports.get('error'):
        lines.append('Ports: ' + ports['error'])
    elif ports:
        holder = ports.get('occupant') or ('frei' if ports.get('free') else f"belegt (PID {ports.get('web_pid')}, ohne Manifest)")
        lines.append('Ports 5082/55434: ' + holder)
    source = facts.get('source') or {}
    lines.append(f"SQBF-Stand: {source.get('commit', '?')} " + ('(sauber)' if source.get('clean') else '(LOKALE ÄNDERUNGEN – vor einem Lauf committen)'))
    probe_ = facts.get('probe')
    lines.append('Provider-Probe: ' + ('gültig' if probe_ and probe_['valid'] else 'nicht gültig für diesen Stand' if probe_ else 'keine'))
    lines.append('Neueste Sitzungen: ' + (facts.get('session_seed') or 'keine'))
    if 'dossiers' in facts:
        lines.append('Lauf-Akten: ' + (', '.join(facts['dossiers']) or 'keine'))
    if 'dossier' in facts:
        lines.append('')
        lines.append(f"Lauf-Akte {facts['dossier']['name']} ({facts['dossier']['path']})")
        for _, label, state, done in facts['dossier']['checklist']:
            lines.append(f"  [{'x' if done else ' '}] {label}: {state}")
        nxt = facts.get('next')
        lines.append('')
        lines.append('Nächster Schritt: ' + (f"{nxt['label']} → {nxt['command']}" if nxt else 'keiner, Lauf abgeschlossen'))
    return '\n'.join(lines)

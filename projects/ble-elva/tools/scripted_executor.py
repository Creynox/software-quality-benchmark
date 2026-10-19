"""Scripted stand-in for the executor model, used only by the modelless dry run (dry_run.py).

The first live run (413f7abe) showed that a dry run which bypasses the guards proves nothing about them: it entered the module pages by
URL and clicked a menu entry through Playwright, while the model starts on the sample page and can only act through the guard.
This executor returns the same kind of strict JSON action a model returns (click at coordinates, type, key, scroll, done, blocked),
decided from the live page like a careful user would, so every action passes the real validate_action and the real guards.
It reads only the DOM it needs for coordinates; it never writes anything itself.
"""
import json
import re

from .measurement_guard import CLASSIFY, ROUTES
from .task_vocabulary import internal_inputs, kind_of

SETUPS = {'allocations': ['Entwurf anlegen'], 'sieve': ['Entwurf anlegen'], 'partial': ['Teilsiebung starten', 'Sieb-Konfiguration anlegen'],
          'shape': [], 'boiling': [], 'sand': [], 'wash': []}
VIEWPORT = (1280, 800)

PAGE_INFO = r"""({config})=>{__C__
 const nm=s=>(s||'').replace(/\s+/g,' ').trim();
 const vis=r=>r.width>1&&r.height>1&&r.bottom>0&&r.top<innerHeight;
 const centred=r=>{const cy=r.y+r.height/2;return cy>=60&&cy<=innerHeight-10;};
 const fields={};
 document.querySelectorAll('input').forEach(i=>{const n=field(i,true);if(n&&!(n in fields)){const r=i.getBoundingClientRect();
   const cx=r.x+r.width/2,cy=r.y+r.height/2;const hit=document.elementFromPoint(cx,cy);
   fields[n]={x:cx,y:cy,visible:vis(r),reachable:vis(r)&&!!hit&&(hit===i||!!hit.closest('.mud-input-control')&&hit.closest('.mud-input-control')===i.closest('.mud-input-control')),value:i.value};}});
 const controls=[];
 document.querySelectorAll('a,button,[role=tab],.mud-menu-item,[role=menuitem],.mud-expand-panel-header').forEach(e=>{const r=e.getBoundingClientRect();if(!vis(r)||!centred(r))return;
   const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);if(!hit||!(hit===e||e.contains(hit)))return;
   controls.push({tag:e.tagName.toLowerCase(),text:nm(e.innerText).slice(0,60),aria:e.getAttribute('aria-label'),href:e.getAttribute('href'),role:e.getAttribute('role'),
     disabled:!!e.disabled||e.getAttribute('aria-disabled')==='true',x:r.x+r.width/2,y:r.y+r.height/2,panel:(e.closest('.mud-expand-panel')?.querySelector('.kf-panel-label')?.innerText||'')});});
 const rows=document.querySelectorAll('.kv-rep-row').length;
 const panels=[...document.querySelectorAll('.mud-expand-panel')].map(p=>({label:nm(p.querySelector('.kf-panel-label')?.innerText),
   header:(()=>{const h=p.querySelector('.mud-expand-panel-header');const r=h?.getBoundingClientRect();return r?{x:r.x+r.width/2,y:r.y+r.height/2,visible:vis(r)}:null;})()}));
 return {path:location.pathname,fields,controls,rows,panels,focused:field(document.activeElement,true),height:innerHeight,scrollable:document.documentElement.scrollHeight>innerHeight};}""".replace('__C__', CLASSIFY)


def german_fraction(label):
    m = re.search(r'\d+(?:[.,]\d+)?', label or '')
    return str(float(m.group(0).replace(',', '.'))).rstrip('0').rstrip('.') if m else None


class ScriptedExecutor:
    """Callable that replaces ask_calibrated for the executor role. `page_fn()` returns the page the runner currently drives."""

    def __init__(self, page_fn, case_fn, faults=None):
        self.page_fn, self.case_fn = page_fn, case_fn
        self.state, self.log = {}, []
        # Provider faults to replay: {n: 'raise' | 'not_object'} for the n-th executor request. They exercise the controller's handling of a
        # failed request (live run 083896e6), which a careful scripted user never causes on its own.
        self.faults, self.calls = dict(faults or {}), 0

    # --- ask_calibrated signature -------------------------------------------------------------------------------------------------
    def __call__(self, model, prompt, images, budget, role):
        from sqbf.providers import ModelResponse
        if role != 'executor':
            return ModelResponse({'verdict': 'INCONCLUSIVE', 'reason': 'scripted dry run', 'scores': dict.fromkeys(
                ('findability', 'clarity', 'task_progress', 'error_recovery'), None), 'findings': []}, {})
        self.calls += 1
        fault = self.faults.get(self.calls)
        if fault == 'raise':
            from sqbf.bounded import WorkerFailed
            raise WorkerFailed('SIMULATED_PROVIDER_FAULT')
        if fault == 'not_object':
            return ModelResponse(None, {})
        history = self.history(prompt)
        if not history:
            self.state = {}
        action = self.decide(prompt, history)
        action = {'action': action.pop('action'), 'x': action.pop('x', None), 'y': action.pop('y', None), 'text': action.pop('text', None),
                  'key': action.pop('key', None), 'amount': action.pop('amount', None), 'seconds': action.pop('seconds', None),
                  'reason': action.pop('reason', 'scripted')}
        self.log.append({k: v for k, v in action.items() if k != 'text' and v is not None})
        return ModelResponse(action, {})

    @staticmethod
    def history(prompt):
        tail = prompt.rsplit('Previous visible actions:\n', 1)[-1].strip()
        try:
            value = json.loads(tail)
        except ValueError:
            return []
        return value if isinstance(value, list) else []

    # --- decisions ----------------------------------------------------------------------------------------------------------------------
    def decide(self, prompt, history):
        case = self.case_fn()
        task = self.task(prompt)
        if task is not None:
            return self.measurement(task)
        return self.inspection(case, prompt)

    @staticmethod
    def task(prompt):
        marker = 'Task:\n'
        if marker not in prompt:
            return None
        body = prompt.split(marker, 1)[1].split('\nPrevious visible actions:', 1)[0].strip()
        try:
            value = json.loads(body)
        except ValueError:
            return None
        return value if isinstance(value, dict) and 'source_inputs' in value else None

    def info(self, config):
        return self.page_fn().evaluate(PAGE_INFO, {'config': config})

    @staticmethod
    def click(x, y, reason):
        return {'action': 'click', 'x': round(x), 'y': round(y), 'reason': reason}

    def scroll(self, state, key, amount, reason, limit=6):
        """A scroll action, at most `limit` times for one purpose (None when used up). The x coordinate varies so that a page that
        cannot scroll further is not mistaken for a stalled executor by the controller."""
        used = state.setdefault('scrolls', {})
        if used.get(key, 0) >= limit:
            return None
        used[key] = used.get(key, 0) + 1
        return {'action': 'scroll', 'x': 1190 + 12 * (used[key] % 6), 'y': 420, 'amount': amount, 'reason': reason}

    def in_view(self, state, key, y):
        """None when y is in the comfortable part of the viewport (below the sticky header), else a bounded scroll towards it."""
        if 150 <= y <= 700:
            return None
        return self.scroll(state, key, max(-1400, min(1400, round(y - 420))), 'bring the control into view')

    @staticmethod
    def clamp(y):
        return max(20, min(VIEWPORT[1] - 20, y))

    def find(self, info, pattern, *, href=None):
        regex = re.compile(pattern)
        for control in info['controls']:
            label = control['aria'] or control['text']
            if regex.search(label or '') and (href is None or (control['href'] or '').endswith(href)) and not control['disabled']:
                return control
        return None

    def measurement(self, task):
        page = self.page_fn()
        # The task speaks BLE's words (module titles, on-screen field labels); the contract and the guards keep the internal names.
        kind = kind_of(task['module'])
        task = dict(task, module=kind, source_inputs=internal_inputs(kind, task['source_inputs']))
        root = re.match(r'^(/samples/[0-9a-f-]{36})', page.evaluate('()=>location.pathname')).group(1)
        config = {'origin': '', 'root': root, 'path': root + '/' + ROUTES[kind], 'kind': kind, 'fields': task['source_inputs'],
                  'max_repetitions': len({k.split(':')[-1] for k in task['source_inputs'] if k.startswith('Einwaage vor Kochen:')})}
        info = self.info(config)
        state = self.state
        if info['path'] == root:
            # BLE's own guidance first: the sample page asks for a test order; then the module card's Erfassen button.
            order = self.find(info, r'^Testauftrag erzeugen$')
            if order and not state.get('ordered'):
                state['ordered'] = True
                return self.click(order['x'], order['y'], 'create the test order the page asks for')
            # The card's button reads Erfassen, Öffnen or Ergebnis prüfen depending on the module state: the route is what identifies it.
            module_link = self.find(info, r'.', href='/' + ROUTES[kind])
            if module_link:
                return self.click(module_link['x'], self.clamp(module_link['y']), 'open the module with its Erfassen button')
            more = self.scroll(state, 'root', 500, 'look for the module card') if info['scrollable'] else None
            return more or {'action': 'blocked', 'reason': 'no way to the module is visible'}
        if info['path'] != config['path']:
            return {'action': 'blocked', 'reason': 'unexpected page'}
        done_setups = state.setdefault('setup', [])
        for label in SETUPS[kind]:
            button = self.find(info, '^' + re.escape(label) + '$')
            if button and label not in done_setups:
                done_setups.append(label)
                return self.click(button['x'], button['y'], 'set up the module: ' + label)
        if kind == 'boiling':
            wanted = config['max_repetitions']
            add = self.find(info, '^Wiederholung hinzufügen$')
            if info['rows'] < wanted and add and state.get('adds', 0) < wanted:
                state['adds'] = state.get('adds', 0) + 1
                return self.click(add['x'], add['y'], 'add a repetition row')
        typed = state.setdefault('typed', [])
        # A click already focused a field: type its approved value, then Tab.
        if state.get('focus'):
            name = state['focus']
            field = info['fields'].get(name)
            if field is None:
                state.pop('focus')  # the field is gone (panel re-rendered or collapsed): decide again from the current page
            elif info['focused'] != name:
                # BLE re-renders the neighbouring field when one is left, which drops the focus; a user clicks again.
                attempts = state.setdefault('refocus', {})
                attempts[name] = attempts.get(name, 0) + 1
                if attempts[name] <= 3:
                    return self.click(field['x'], self.clamp(field['y']), 'focus ' + name + ' again')
                state.pop('focus')
                return {'action': 'blocked', 'reason': 'the field ' + name + ' does not take the focus'}
            elif not state.get('selected'):
                # Fields can be pre-filled (a shape weight from the allocation, the remainder of a sieve row): replace, never append.
                state['selected'] = True
                return {'action': 'key', 'key': 'ControlOrMeta+A', 'reason': 'select the content of ' + name}
            else:
                state.pop('focus')
                state.pop('selected', None)
                state['tab'] = True
                typed.append(name)
                return {'action': 'type', 'text': task['source_inputs'][name], 'reason': 'enter the recorded value for ' + name}
        if state.pop('tab', False) and info['focused']:
            state['settle'] = True
            return {'action': 'key', 'key': 'Tab', 'reason': 'leave the field'}
        if state.pop('settle', False):
            # BLE recalculates when a field is left and shifts the layout; a user waits for the screen to settle before the next click.
            return {'action': 'wait', 'seconds': 1, 'reason': 'wait for BLE to recalculate'}
        offered = [n for n in task['source_inputs'] if n in info['fields']]
        pending = [n for n in offered if n not in typed]
        if kind == 'shape':
            return self.shape(info, task, state, pending)
        if not offered and not typed and info['scrollable']:
            more = self.scroll(state, 'discover', 500, 'look further down the page for the entry controls')
            if more:
                return more
        if pending:
            name = pending[0]
            field = info['fields'][name]
            more = self.in_view(state, 'field:' + name, field['y'])
            if more:
                return more
            state['focus'] = name
            return self.click(field['x'], self.clamp(field['y']), 'focus ' + name)
        if kind != 'allocations' and typed and not state.get('saved'):
            save = self.find(info, '^Speichern$')
            if save:
                state['saved'] = True
                return self.click(save['x'], save['y'], 'save the module once')
            more = (self.scroll(state, 'save_up', -1400, 'scroll up to the save button', limit=1)
                    or self.scroll(state, 'save_down', 500, 'look for the save button', limit=5))
            return more or {'action': 'blocked', 'reason': 'the save button is not visible'}
        return {'action': 'done', 'reason': 'entered %d of %d approved fields that the page offers' % (len(typed), len(task['source_inputs']))}

    def shape(self, info, task, state, pending):
        # Each fraction is a collapsed panel: expand it, enter its two values, save that fraction once.
        saved = state.setdefault('saved_fractions', [])
        fractions = sorted({n.split(':')[-1] for n in task['source_inputs'] if n in info['fields']})
        for fraction in fractions:
            if fraction in saved:
                continue
            own = [n for n in pending if n.endswith(':' + fraction)]
            if own:
                field = info['fields'][own[0]]
                if not field['reachable']:
                    panel = next((p for p in info['panels'] if german_fraction(p['label']) == fraction and p['header']), None)
                    if panel is None:
                        return {'action': 'blocked', 'reason': 'fraction panel %s not found' % fraction}
                    more = self.in_view(state, 'panel:' + fraction, panel['header']['y'])
                    if more:
                        return more
                    if state.get('expanded_' + fraction):
                        return {'action': 'blocked', 'reason': 'fraction panel %s did not open' % fraction}
                    state['expanded_' + fraction] = True
                    return self.click(panel['header']['x'], self.clamp(panel['header']['y']), 'expand the fraction ' + fraction)
                more = self.in_view(state, 'field:' + own[0], field['y'])
                if more:
                    return more
                state['focus'] = own[0]
                return self.click(field['x'], self.clamp(field['y']), 'focus ' + own[0])
            save = next((c for c in info['controls'] if c['text'] == 'Speichern' and german_fraction(c['panel']) == fraction and not c['disabled']), None)
            if save is None:
                more = self.scroll(state, 'save:' + fraction, 400, 'look for the save button of the fraction', limit=4)
                return more or {'action': 'blocked', 'reason': 'no save button for fraction ' + fraction}
            saved.append(fraction)
            return self.click(save['x'], self.clamp(save['y']), 'save fraction ' + fraction + ' once')
        if not fractions:
            return {'action': 'blocked', 'reason': 'the page offers no fraction'}
        return {'action': 'done', 'reason': 'entered and saved the offered fractions'}

    # Read-only exploration of the inspection stages: the controls a user looks at first. A control that the guard rejects shows up
    # as a rejected action in the stage record, i.e. as a coverage gap of the allow list.
    EXPLORE = {
        'NSN014-RECEIPT': [r'^Offen$', r'^Tabelle$', r'^Nach Probencode sortieren$', r'^ENZBERG-\d{8}-NSN-014-01$'],
        'NSN014-ASSESS': [r'^Alle$', r'^Nach Plan$', r'^ENZBERG-\d{8}-NSN-014-02$', r'^Zu den Modulen$'],
        'NSN014-WPK': [r'^Zum Plan$', r'^Erste offene$', r'^Zu den Modulen$'],
        'NSN014-ANALYSIS': [r'^Proben-Auswertung$', r'^Qualitätsmonitoring$', r'^Monat$', r'^Übersicht$'],
        'NSN014-RIGHTS': [r'^Zum Plan$', r'^Zu den Modulen$'],
    }

    def inspection(self, case, prompt):
        page = self.page_fn()
        path = page.evaluate('()=>location.pathname')
        state = self.state
        info = self.info({'origin': '', 'root': path, 'path': path, 'kind': 'inspection', 'fields': {}, 'max_repetitions': 0})
        if case == 'NSN014-PLAN':
            if state.get('clicked'):
                return {'action': 'done', 'reason': 'the plan samples were created once'}
            button = self.find(info, r'^Proben anlegen / nachanlegen$')
            if not button:
                return {'action': 'blocked', 'reason': 'plan sample creation not offered'}
            state['clicked'] = True
            return self.click(button['x'], button['y'], 'create the plan samples once')
        if case == 'NSN014-REPORT':
            return self.report(info, path)
        steps = self.EXPLORE.get(case, [])
        index = state.get('step', 0)
        while index < len(steps):
            state['step'] = index + 1
            control = self.find(info, steps[index])
            if control:
                return self.click(control['x'], control['y'], 'look at ' + steps[index])
            index += 1
        return {'action': 'done', 'reason': 'explored the visible read-only controls'}

    def report(self, info, path):
        state = self.state
        if path.startswith('/reports/'):
            if state.get('downloaded'):
                return {'action': 'done', 'reason': 'report generated and downloaded once'}
            button = self.find(info, r'^PDF herunterladen$')
            if not button:
                # BLE builds the report page asynchronously (the first position of a clean dry run met the page before its menu was rendered).
                state['pdf_waits'] = state.get('pdf_waits', 0) + 1
                if state['pdf_waits'] <= 5:
                    return {'action': 'wait', 'seconds': 2, 'reason': 'wait for the report page to offer the PDF download'}
                return {'action': 'blocked', 'reason': 'PDF download not offered'}
            state['downloaded'] = True
            return self.click(button['x'], button['y'], 'download the PDF once')
        entry = self.find(info, r'^Prüfbericht$')
        if entry:
            state['generated'] = True
            return self.click(entry['x'], entry['y'], 'generate the non-official report')
        if state.get('generated'):
            return {'action': 'wait', 'seconds': 2, 'reason': 'wait for the report to open'}
        menu = self.find(info, r'^Weitere Aktionen$')
        if not menu or state.get('opened', 0) >= 2:
            return {'action': 'blocked', 'reason': 'report entry not found'}
        state['opened'] = state.get('opened', 0) + 1
        return self.click(menu['x'], menu['y'], 'open the sample actions')

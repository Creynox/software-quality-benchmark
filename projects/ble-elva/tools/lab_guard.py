"""Controller-only LAB-01 guard: one synthetic creation in a disposable clone."""
import json
import re
from urllib.parse import urlsplit

from sqbf.read_only import ReadOnlyViolation, request_allowed

FIELDS = {
    'Werk': 'Enzberg (Enzberg)',
    'Produktname': 'STS 0–45',
    'Oberkategorie / Materialklasse': 'Ungebundenes Gemisch',
    'Kategorie': 'Gemisch', 'Produkttyp': 'STS',
    'Verwendungsbereich': 'Ungebundenes Gemisch',
    'Produktstufe': 'Fertiges Gemisch',
    'Materialbasis / Gesteinsart': 'Kalkstein',
    'Materialherkunft': 'gebrochen',
    'Siebbereich von [mm]': '0', 'Siebbereich bis [mm]': '45',
}
EDITABLE = {'Produktname', 'Siebbereich von [mm]', 'Siebbereich bis [mm]'}
KEYS = ('ControlOrMeta+A', 'Backspace', 'Delete', 'Escape')


def validate_source(source):
    db=source['database']
    if (source['target_url']!='http://127.0.0.1:5080/' or db['host_port']!=55432
            or db['name']!='ble_benchmark_20261012' or db['container']!='ble-benchmark-pg-20261012'
            or db['container_id']!='90603c3389acca27a4ff023afd2174e2cf393d94d2164915cdc1d456f9159354'):
        raise ReadOnlyViolation('GOLDEN_SOURCE_IDENTITY_DENIED')


def validate_target(scenario, fixture):
    working = fixture.get('working_copy', {})
    url = urlsplit(scenario.url)
    db = fixture['database']
    if (scenario.write_policy != {'contract': 'LAB-01-SINGLE-PRODUCT-v1'}
            or scenario.scenario_id != 'LAB-01' or not scenario.read_only_policy
            or scenario.url != fixture['target_url'] or url.scheme != 'http'
            or url.hostname != '127.0.0.1' or url.port != 5081 or url.path != '/'
            or url.username or url.query or url.fragment
            or db['host_port'] != 55433 or not db['container'].startswith('sqbf-lab01-')
            or not db['name'].startswith('sqbf_lab01_')
            or working.get('disposable') is not True or working.get('never_reset') is not True
            or not working.get('source_fixture') or not working.get('source_snapshot')
            or not re.fullmatch('[a-f0-9]{64}', working.get('golden_sha256', ''))
            or not 1 <= scenario.max_minutes <= 25 or not 1 <= scenario.max_actions <= 150
            or not 2 <= scenario.max_model_calls <= 152
            or fixture['oracle_expectations'].get('material_base') != 'Kalkstein'
            or fixture['oracle_expectations'].get('material_origin') != 'gebrochen'):
        raise ReadOnlyViolation('LAB-01 working-copy contract not verified')


def allowed_path(path):
    return path in ('/', '/products', '/products/new') or bool(re.fullmatch(
        r'/products/[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', path))


def transport_allowed(url, method, origin, policy):
    parsed = urlsplit(url)
    if method in ('GET', 'HEAD') and f'{parsed.scheme}://{parsed.netloc}' == origin and allowed_path(parsed.path):
        return True
    return request_allowed(url, method, origin, policy)


# One implementation classifies both native events and controller hit tests.
# Never exposed to executor/reviewer. No labels, selectors or values are hidden.
CLASSIFY = r"""
const label=e=>e?.closest('.mud-input-control')?.querySelector('label')?.innerText.replace(/\s*\*\s*$/,'').trim();
const path=location.pathname;
const creating=path==='/products/new';
const product=/^\/products\/[a-f0-9-]{36}$/.test(path);
const field=e=>label(e);
const classify=e=>{
 if(!e)return {kind:'blocked'};
 if(e.closest('a[href="/products"]'))return {kind:'navigation'};
 const button=e.closest('button');
 const text=button?.innerText.trim();
 if(path==='/products'&&text==='Neues Produkt'&&!window.__sqbfSaveCount)return {kind:'new'};
 if((creating||product)&&text==='Zurueck')return {kind:'back'};
 if(creating&&text==='Speichern'&&!window.__sqbfSaveCount)return {kind:'save'};
 const search=e.closest('input');
 if(path==='/products'&&search?.placeholder==='Produkt, Code, Werk oder Kunde')return {kind:'search',field:'search'};
 if(path==='/products'&&window.__sqbfSaveCount&&e.closest('.products-table tbody tr')?.innerText.includes('STS 0–45'))return {kind:'reopen'};
 if(path==='/products'&&window.__sqbfSaveCount&&button?.title==='Produkt bearbeiten'&&document.body.innerText.includes('STS 0–45'))return {kind:'inspect'};
 if(creating){
  const option=e.closest('.mud-list-item');
  if(option&&option.innerText.trim()===config.fields[window.__sqbfDropdown])return {kind:'option'};
  const control=e.closest('.mud-input-control');
  const name=field(control);
  if(name in config.fields && !control.querySelector('input')?.disabled)return {kind:'field',field:name};
 }
 return {kind:'blocked'};
};
const complete=()=>Object.entries(config.fields).every(([name,value])=>{
 const controls=[...document.querySelectorAll('.mud-input-control')].filter(e=>field(e)===name);
 return controls.length===1&&controls[0].querySelector('input')?.value===value;
});
"""


def event_guard():
    return """(() => {const config=__CONFIG__;window.__sqbfSaveCount=0;
    __CLASSIFY__
    const stop=e=>{e.preventDefault();e.stopImmediatePropagation();};
    document.addEventListener('click',e=>{
      const t=classify(e.target);
      if(t.kind==='blocked')return stop(e);
      if(t.kind==='field')window.__sqbfDropdown=t.field;
      if(t.kind==='save'){
        if(!complete())return stop(e);
        window.__sqbfSaveCount=1;
      }
    },true);
    for(const kind of ['input','change'])document.addEventListener(kind,e=>{
      const t=classify(e.target);
      if(t.kind!=='field'&&t.kind!=='search')stop(e);
    },true);
    document.addEventListener('submit',stop,true);
    document.addEventListener('keydown',e=>{
      const t=classify(e.target);
      const editable=t.kind==='search'||t.kind==='field'&&config.editable.includes(t.field);
      if(e.key==='Escape')return;
      if(!editable||e.altKey||e.metaKey||(e.ctrlKey&&e.key.toLowerCase()!=='a')||e.key==='Enter'||e.key==='Tab')stop(e);
    },true);
    })()""".replace('__CONFIG__', json.dumps({'fields': FIELDS, 'editable': sorted(EDITABLE)})).replace('__CLASSIFY__', CLASSIFY)


def allow_operation(action, state):
    kind = action['action']
    if kind in ('done', 'blocked', 'wait', 'scroll'):
        return
    if kind == 'click' and state['target']['kind'] in ('navigation','new','back','search','reopen','inspect','option','field'):
        return
    if kind == 'click' and state['target']['kind'] == 'save' and state['complete'] and not state['saved']:
        return
    focused = state['focused']
    name = focused.get('field')
    editable = focused['kind'] == 'search' or focused['kind'] == 'field' and name in EDITABLE
    if kind == 'type' and editable and action['text'] == ('STS 0–45' if name == 'search' else FIELDS[name]):
        return
    if kind == 'key' and action['key'] in KEYS and (editable or action['key'] == 'Escape'):
        return
    raise ReadOnlyViolation('LAB_ACTION_SCOPE_DENIED')


def check_action(page, action):
    if not allowed_path(urlsplit(page.url).path):
        raise ReadOnlyViolation('LAB_PAGE_SCOPE_DENIED')
    state = page.evaluate("""({x,y,config})=>{__CLASSIFY__
      return {target:classify(Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null),
       focused:classify(document.activeElement), complete:complete(),saved:!!window.__sqbfSaveCount};
    }""".replace('__CLASSIFY__', CLASSIFY), {'x': action.get('x'), 'y': action.get('y'),
         'config': {'fields': FIELDS}})
    allow_operation(action, state)
    return state

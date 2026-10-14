"""One source-bound probe creation; screenshot executor gets no controller state."""
import json
from urllib.parse import urlsplit

from sqbf.read_only import ReadOnlyViolation, request_allowed
from .suite_fixture import validate_target

KEYS = ('ControlOrMeta+A', 'Backspace', 'Delete', 'Escape')


def make_contract(fixture, position, sampling_date):
    validate_target(fixture)
    context = fixture['suite_copy']['preparation_context']
    if context['sample_owner'] != 'Werk Enzberg':
        raise ValueError('Exact plant-owned receipt profile required')
    date = sampling_date.split('-')
    if len(date) != 3 or len(sampling_date) != 10:
        raise ValueError('Exact reviewed sampling date required')
    return {'contract': 'NSN014-RECEIPT-v1', 'case_position': position['position_id'],
            'fields': {'Kunde': context['customer'], 'Projekt': context['project'],
                       'Werk / Standort': 'Enzberg (Enzberg)', 'Produkt': position['product'],
                       'Probencode': position['inputs']['sample_code'],
                       'Entnahmedatum': '.'.join(reversed(date))},
            'editable': ['Probencode', 'Entnahmedatum'], 'sample_code': position['inputs']['sample_code']}


CLASSIFY = r"""
const label=e=>e?.closest('.mud-input-control')?.querySelector('label')?.innerText.replace(/\s*\*+\s*$/,'').trim();
const complete=()=>Object.entries(config.fields).every(([name,value])=>{
 const controls=[...document.querySelectorAll('.mud-input-control')].filter(e=>label(e)===name);
 return controls.length===1&&controls[0].querySelector('input')?.value===value;
});
const classify=e=>{
 if(!e)return {kind:'blocked'};
 const path=location.pathname;
 const anchor=e.closest('a');
 if(anchor&&['/samples','/samples/create'].includes(new URL(anchor.href,location.href).pathname))return {kind:'navigation'};
 if(path==='/samples'&&e.closest('button')?.innerText.trim()==='Neue Probe'&&!window.__sqbfReceiptSaved)return {kind:'new'};
 if(path==='/samples/create'&&!window.__sqbfReceiptSaved){
  const button=e.closest('button');
  if(button?.innerText.trim()==='Probe anlegen')return {kind:'save'};
  const name=label(e);
  if(name in config.fields)return {kind:'field',field:name};
  const option=e.closest('.mud-list-item');
  if(option&&option.innerText.trim()===config.fields[window.__sqbfReceiptDropdown])return {kind:'option'};
  if(window.__sqbfReceiptDropdown==='Entnahmedatum'&&e.closest('.mud-picker-calendar'))return {kind:'calendar'};
 }
 return {kind:'blocked'};
};
"""


def event_guard(contract):
    return r"""(()=>{const config=__CONFIG__;const saveKey='sqbf-receipt-save:'+config.sample_code;
window.__sqbfReceiptSaved=sessionStorage.getItem(saveKey)==='attempted';
__CLASSIFY__
const stop=e=>{e.preventDefault();e.stopImmediatePropagation();};
document.addEventListener('click',e=>{
 const t=classify(e.target);
 if(t.kind==='blocked')return stop(e);
 if(t.kind==='field')window.__sqbfReceiptDropdown=t.field;
 if(t.kind==='save'){
  if(!complete()||window.__sqbfReceiptSaved)return stop(e);
  window.__sqbfReceiptSaved=true;
  sessionStorage.setItem(saveKey,'attempted');
 }
},true);
for(const kind of ['input','change'])document.addEventListener(kind,e=>{
 const t=classify(e.target);
 if(t.kind!=='field'||!config.editable.includes(t.field))stop(e);
},true);
document.addEventListener('submit',stop,true);
document.addEventListener('keydown',e=>{
 if(e.key==='Escape')return;
 const t=classify(e.target);
 const editable=t.kind==='field'&&config.editable.includes(t.field);
 if(!editable||e.altKey||e.metaKey||(e.ctrlKey&&e.key.toLowerCase()!=='a')||e.key==='Enter'||e.key==='Tab')stop(e);
},true);
})()""".replace('__CONFIG__',json.dumps(contract)).replace('__CLASSIFY__',CLASSIFY)


def allow_operation(action, state, contract, *, controller_saved):
    kind = action['action']; target = state['target']
    if kind in ('done','blocked','wait','scroll'):
        return
    if kind == 'click' and target['kind'] in ('navigation','new','field','option','calendar'):
        return
    if kind == 'click' and target['kind'] == 'save' and state['complete'] and not state['saved'] and not controller_saved:
        return
    focus = state['focused']; field = focus.get('field')
    editable = focus['kind'] == 'field' and field in contract['editable']
    if kind == 'type' and editable and action.get('text') == contract['fields'][field]:
        return
    if kind == 'key' and action.get('key') in KEYS and (editable or action['key'] == 'Escape'):
        return
    raise ReadOnlyViolation('RECEIPT_ACTION_SCOPE_DENIED')


def check_action(page, action, contract, *, controller_saved):
    if urlsplit(page.url).path not in ('/samples','/samples/create'):
        raise ReadOnlyViolation('RECEIPT_PAGE_SCOPE_DENIED')
    state = page.evaluate(r"""({x,y,config})=>{__CLASSIFY__
return {target:classify(Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null),
focused:classify(document.activeElement),complete:complete(),saved:!!window.__sqbfReceiptSaved};
}""".replace('__CLASSIFY__',CLASSIFY),{'x':action.get('x'),'y':action.get('y'),'config':contract})
    allow_operation(action,state,contract,controller_saved=controller_saved)
    return state


def transport_allowed(url, method, origin, policy):
    parsed=urlsplit(url)
    if method in ('GET','HEAD') and f'{parsed.scheme}://{parsed.netloc}'==origin and parsed.path in ('/samples','/samples/create'):
        return True
    return request_allowed(url,method,origin,policy)

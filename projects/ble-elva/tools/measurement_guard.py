"""Numeric-input-only write profiles on one independently identified probe.

Unknown controls fail closed. Source fields and source values are allowlisted;
there is no permission for master data, release, signature, delivery or delete.
"""
import json
from decimal import Decimal
from uuid import UUID
from urllib.parse import urlsplit
from sqbf.read_only import ReadOnlyViolation, request_allowed
from .suite_fixture import validate_target

ROUTES={'allocations':'sieve-analysis','wash':'uf-fine','sieve':'sieve-analysis','partial':'partial-sieve',
        'shape':'kornform','boiling':'kochversuch','sand':'sand-equivalent'}


def number(value):
    n=Decimal(str(value))
    if not n.is_finite() or n<0:raise ValueError('Recorded finite nonnegative input required')
    return format(n.normalize(),'f')


def make_contract(fixture,probe_id,position,kind):
    validate_target(fixture)
    if kind not in ROUTES:raise ValueError('Unknown module')
    probe_id=str(UUID(probe_id));raw=position['measurements'];fields={}
    if kind=='allocations':
        labels={'Kornform':'KF','Kochversuch':'Koch','SandAequivalent':'SE','Siebanalyse':'SL','Trocknung':'Tro'}
        for row in position['allocations']:
            if row['actual_amount_g'] is None:continue
            sieve='none' if row['target_sieve_mm'] is None else number(row['target_sieve_mm'])
            key=labels[row['target_process']]+':'+sieve
            if key in fields:raise ValueError('Ambiguous original allocation control')
            fields[key]=number(row['actual_amount_g'])
    elif kind=='wash':
        if len(raw['wash'])!=1:raise ValueError('One recorded wash required')
        r=raw['wash'][0]
        fields={'Probenmasse feucht':number(Decimal(r['container_wet_g'])-Decimal(r['container_g'])),
                'Schale + Probe feucht':number(r['container_wet_g']),
                'Schale + Probe trocken':number(r['container_dry_g']),
                'Schale + gewaschene Probe trocken':number(r['container_washed_g'])}
    elif kind=='sand':
        if len(raw['sand'])!=2:raise ValueError('Two recorded sand repetitions required')
        for letter,row in zip(('A','B'),raw['sand']):
            # Reference projection heights are already millimetres.
            fields['Sandhöhe:'+letter]=number(row['sand_height'])
            fields['Suspensionshöhe:'+letter]=number(row['suspension_height'])
    elif kind=='boiling':
        for row in raw['boiling_repetitions']:
            order=str(row['order'])
            fields.update({'Einwaage vor Kochen:'+order:number(row['initial_g']),
                           'Rückwaage nach Kochen:'+order:number(row['final_g']),
                           'Kochzeit:'+order:number(row['minutes'])})
        if len(raw['boiling'])==1:fields['Geschaedigte Koerner / Mergelmasse']=number(raw['boiling'][0]['marl_g'])
    elif kind=='shape':
        for row in raw['shape']:
            fraction=number(row['fraction'].split()[0].replace(',','.'))
            fields['Einwaage gesamt (g):'+fraction]=number(row['total_g'])
            fields['Schlecht geformt (g):'+fraction]=number(row['poor_g'])
    elif kind=='sieve':
        if len(raw['sieves'])!=1:raise ValueError('One recorded main sieve required')
        row=raw['sieves'][0];fields['main_input']=number(row['input_g'])
        for point in row['points']:
            if not point['partial'] and point['retained_g'] is not None:
                fields['sieve:'+number(point['sieve_mm'])]=number(point['retained_g'])
    elif kind=='partial':
        series=raw['partial_series']
        if len(series)!=2:raise ValueError('Two recorded partial towers required')
        # BLE derives the K basis (read-only, "automatisch aus Feuchte/Abschlaemmung") and the pan loss of each tower (not stored,
        # shown as "Siebverlust"); neither is an input control (dry run 15.10.2026), so they are neither approved fields nor typed.
        for tower,row in zip(('A','B'),series):
            fields['Einwaage Siebturm '+tower]=number(row['initial_g'])
            for point in row['points']:
                if point['pan']:continue
                fields['partial:'+number(point['sieve_mm'])+':'+tower]=number(point['retained_g'])
    if not fields:raise ValueError('No approved inputs for this module')
    root='/samples/'+probe_id
    return {'origin':fixture['target_url'].rstrip('/'),'root':root,'path':root+'/'+ROUTES[kind],
            'kind':kind,'position_id':position['position_id'],'fields':fields,
            'max_repetitions':len(raw['boiling_repetitions']) if kind=='boiling' else 0}


CLASSIFY=r"""
const norm=s=>(s||'').replace(/\s+/g,' ').replace(/\s*\*+$/,'').trim();
const num=s=>{const m=(s||'').match(/\d+(?:[.,]\d+)?/);return m?String(Number(m[0].replace(',','.'))):null;};
// Text and layout that does nothing when clicked (PO decision 2026-10-19, live run b7a34e94: about 14 harmless text clicks were rejected and tasks ended
// on them). Passive means: no interactive element around it and no pointer cursor; the cursor is inherited, so a clickable container shows through.
// A card title in BLE has cursor auto and a click on it does nothing (checked on a scratch clone, 19.10.2026).
const INTERACTIVE='a,button,input,select,textarea,summary,label,[role="button"],[role="link"],[role="tab"],[role="menuitem"],[role="option"],[role="checkbox"],'
  +'[role="switch"],[role="combobox"],[role="listbox"],[tabindex]:not([tabindex="-1"]),[onclick],.mud-button-root,.mud-chip,.mud-list-item,.mud-menu-item,.mud-select,'
  +'.mud-expand-panel-header,.mud-nav-link,.mud-icon-button,.mud-tab,.mud-table-sort-label,.mud-input-control,.sa-kpi-editable';
const passive=e=>{if(!e||e.nodeType!==1||e.closest(INTERACTIVE))return false;try{return getComputedStyle(e).cursor!=='pointer';}catch(_){return false;}};
const field=(e,ignoreSaveLatch)=>{
 // The main weigh-in (Einwaage) is a KPI box that holds one input; a click anywhere in that box is a click on the field (live run fdea63ef: a click on
 // the box was rejected and the executor gave up, although BLE would simply not focus the input - which is what has to be observed).
 const input=e?.matches('input')?e:(e?.closest('.mud-input-control')||e?.closest('.sa-kpi-editable'))?.querySelector('input');
 if(!input||input.disabled||input.readOnly||['password','file','hidden'].includes(input.type))return null;
 let name=norm(input.closest('.mud-input-control')?.querySelector('label')?.innerText);
 if(config.kind==='sand'){const letter=norm(input.closest('.se-best-card')?.querySelector('.se-best-letter')?.innerText);name+=':'+letter;}
 if(config.kind==='boiling'&&input.closest('.kv-rep-row'))name+=':'+norm(input.closest('.kv-rep-row').querySelector('.kv-rep-num')?.innerText);
 if(config.kind==='shape')name+=':'+num(input.closest('.kf-panel')?.querySelector('.kf-panel-label')?.innerText);
 if(config.kind==='sieve'){
   if(input.closest('.sa-kpi-einwaage'))name='main_input';
   else if(input.closest('.sieve-residue-input')){
     // The pan row is labelled "Boden", "Pfanne" or "Anteile gesamt < x mm"; the reference stores it as sieve 0 (#21 dry run, 15.10.2026).
     const label=norm(input.closest('tr')?.querySelector('[data-label="Sieb"]')?.innerText);
     name='sieve:'+(/boden|pfanne|anteile gesamt/i.test(label)?'0':num(label));
   }
 }
 if(config.kind==='allocations'&&input.closest('.sa-ec')){
   const card=input.closest('.sa-ec'),s=norm(card.querySelector('.sa-ec-sieb')?.innerText);
   name=norm(card.querySelector('.sa-ec-label')?.innerText)+':'+(s?(s==='Pfanne'?'0':num(s)):'none');
 }
 if(config.kind==='partial'&&input.closest('tr')){
   const row=input.closest('tr'),s=norm(row.querySelector('[data-label="Sieb"]')?.innerText);
   const tower=input.closest('[data-label="Siebturm A"]')?'A':input.closest('[data-label="Siebturm B"]')?'B':null;
   if(tower)name='partial:'+(/boden|pfanne/i.test(s)?'pan':num(s))+':'+tower;
 }
 const scope=config.kind==='shape'?name.split(':').at(-1):'module';
 if(!ignoreSaveLatch&&sessionStorage.getItem('sqbf-module-save:'+config.path+':'+scope))return null;
 return Object.hasOwn(config.fields,name)?name:null;
};
const classify=e=>{
 if(location.pathname!==config.path&&location.pathname!==config.root)return {kind:'blocked'};
 // BLE's "Zu den Modulen" (href="#module-bereich") is not a same-page anchor: the page has <base href="/">, so the browser resolves it to
 // /#module-bereich and the click leaves the sample for the start page (reproduced on a scratch clone, 16.10.2026; live run 6c23f768 rejected it
 // sixteen times). It stays blocked: it would take the executor out of the task scope.
 const a=e?.closest('a');if(a){let u=new URL(a.href,location.href);if(u.origin===config.origin&&[config.root,config.path].includes(u.pathname)&&!u.search&&!u.hash)return {kind:'navigation'};}
 // BLE's own first step of module work: the sample page offers "Testauftrag erzeugen" as its primary action (it writes only the work items
 // of the sample and its status; live run 413f7abe, dry run 16.10.2026). Allowed once per sample, on the sample page only.
 if(location.pathname===config.root&&norm(e?.closest('button')?.innerText)==='Testauftrag erzeugen')return {kind:'setup',scope:'test_order'};
 if(passive(e))return {kind:'passive'};
 if(location.pathname!==config.path)return {kind:'blocked'};
 const name=field(e);if(name&&!e?.closest('button'))return {kind:'field',field:name};
 // The boiling module asks which allocation ("Fraktion / Entnahme") the test belongs to as soon as one exists. Choosing it writes nothing
 // (no table changed on a scratch clone, 19.10.2026); live run b7a34e94 lost two boiling positions to its rejection.
 if(config.kind==='boiling'&&(e?.closest('.mud-select')||e?.closest('.mud-popover .mud-list-item,.mud-popover [role="option"]')))return {kind:'select'};
 if(e?.closest('.mud-expand-panel-header'))return {kind:'expand'};
 const b=e?.closest('button'),text=norm(b?.innerText);
 // Allocations are persisted when their field is left; the module's Save then only repeats that (on a scratch clone only workspace_sampling_info
 // changed, 19.10.2026), so the allocation task may use it once like every other module (live run b7a34e94: four rejected save clicks).
 if(text==='Speichern'){
   const scope=config.kind==='shape'?num(b.closest('.kf-panel')?.querySelector('.kf-panel-label')?.innerText):'module';
   if(scope&&(config.kind!=='shape'||Object.hasOwn(config.fields,'Einwaage gesamt (g):'+scope)))return {kind:'save',scope:scope};
 }
 if(text==='Wiederholung hinzufügen'&&config.kind==='boiling'&&document.querySelectorAll('.kv-rep-row').length<config.max_repetitions)return {kind:'add_repetition'};
 if(['sieve','allocations'].includes(config.kind)&&text==='Entwurf anlegen')return {kind:'setup',scope:'draft'};
 if(config.kind==='partial'&&text==='Teilsiebung starten')return {kind:'setup',scope:'partial_start'};
 if(config.kind==='partial'&&text==='Sieb-Konfiguration anlegen')return {kind:'setup',scope:'partial_config'};
 return {kind:'blocked'};
};
"""


def event_guard(contract):
    return r"""(()=>{const config=__CONFIG__;__CLASSIFY__
const key=s=>'sqbf-module-save:'+config.path+':'+s;
const stop=e=>{e.preventDefault();e.stopImmediatePropagation();};
document.addEventListener('click',e=>{
 const t=classify(e.target);if(t.kind==='blocked')return stop(e);
 if(['save','setup'].includes(t.kind)){
   if(sessionStorage.getItem(key(t.scope)))return stop(e);
   sessionStorage.setItem(key(t.scope),'attempted');
 }
},true);
document.addEventListener('submit',stop,true);
document.addEventListener('keydown',e=>{
 if(e.key==='Escape')return;
 if(!field(e.target)||e.altKey||e.metaKey||(e.ctrlKey&&e.key.toLowerCase()!=='a')||e.key==='Enter')stop(e);
},true);
for(const kind of ['input','change','beforeinput'])document.addEventListener(kind,e=>{if(!field(e.target))stop(e);},true);
// The wheel must not change a value, but it must still scroll the page: only the focused field is protected. Blocking every field made the
// page unscrollable whenever the pointer was over the (wide) input column, which stalled the scripted executor and would stall a model.
document.addEventListener('wheel',e=>{if(field(e.target)&&e.target===document.activeElement)stop(e);},{capture:true,passive:false});
})()""".replace('__CONFIG__',json.dumps(contract)).replace('__CLASSIFY__',CLASSIFY)


def german(value):
    """BLE parses de-DE: ',' is the decimal mark and '.' a thousands separator, so '1.250' silently becomes 1250.
    The approved values therefore reach the executor, and are accepted from it, only in German notation."""
    return value.replace('.',',')


def offered_fields(page,contract):
    """Approved fields the page offers as enabled inputs right now (independent of the save latch).
    Evidence only: a field BLE does not offer is not an executor fault."""
    names=page.evaluate(r"""({config})=>{__CLASSIFY__
const names=new Set();document.querySelectorAll('input').forEach(i=>{const n=field(i,true);if(n)names.add(n);});return [...names];
}""".replace('__CLASSIFY__',CLASSIFY),{'config':contract})
    return {name for name in names if name in contract['fields']}


def focused_field(page,contract):
    """Name of the approved field that still has the focus, else None. BLE persists a typed value when the field is left, so a value typed into a
    field that is still focused at the end of a task is not yet committed (live run 6c23f768, P09: typed, the next request failed, nothing persisted,
    the controller reported a persisted-value FAIL). Evidence only; an unreadable page counts as no focus."""
    try:
        name=page.evaluate(r"""({config})=>{__CLASSIFY__return field(document.activeElement,true);}""".replace('__CLASSIFY__',CLASSIFY),{'config':contract})
    except Exception:
        return None
    return name if isinstance(name,str) else None


def check_action(page,action,contract,saved):
    parsed=urlsplit(page.url)
    if f'{parsed.scheme}://{parsed.netloc}'!=contract['origin'] or parsed.path not in (contract['root'],contract['path']):
        raise ReadOnlyViolation('MEASUREMENT_PAGE_SCOPE_DENIED')
    state=page.evaluate(r"""({config,x,y})=>{__CLASSIFY__
return {target:classify(Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null),focused:field(document.activeElement)};
}""".replace('__CLASSIFY__',CLASSIFY),{'config':contract,'x':action.get('x'),'y':action.get('y')})
    target=state['target'];kind=action['action']
    if kind in ('done','blocked','wait','scroll'):return state
    if kind=='click' and target['kind'] in ('navigation','expand','field','add_repetition','passive','select'):return state
    if kind=='click' and target['kind'] in ('save','setup') and target['scope'] not in saved:return state
    focused=state['focused']
    if kind=='type' and focused in contract['fields'] and action.get('text')==german(contract['fields'][focused]):
        return state
    if kind=='key' and action.get('key') in ('ControlOrMeta+A','Backspace','Delete','Tab','Escape') and (focused or action['key']=='Escape'):
        return state
    raise ReadOnlyViolation('MEASUREMENT_ACTION_SCOPE_DENIED')


def transport_allowed(url,method,contract,policy):
    p=urlsplit(url)
    if method in ('GET','HEAD') and f'{p.scheme}://{p.netloc}'==contract['origin'] and p.path in (contract['root'],contract['path']) and not p.query:
        return True
    return request_allowed(url,method,contract['origin'],policy)

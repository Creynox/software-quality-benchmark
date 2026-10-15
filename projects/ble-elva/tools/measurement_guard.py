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
const field=(e,ignoreSaveLatch)=>{
 const input=e?.matches('input')?e:e?.closest('.mud-input-control')?.querySelector('input');
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
 const a=e?.closest('a');if(a){let u=new URL(a.href,location.href);if(u.origin===config.origin&&[config.root,config.path].includes(u.pathname)&&!u.search&&!u.hash)return {kind:'navigation'};}
 if(location.pathname!==config.path)return {kind:'blocked'};
 const name=field(e);if(name&&!e?.closest('button'))return {kind:'field',field:name};
 if(e?.closest('.mud-expand-panel-header'))return {kind:'expand'};
 const b=e?.closest('button'),text=norm(b?.innerText);
 if(text==='Speichern'&&config.kind!=='allocations'){
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
document.addEventListener('wheel',e=>{if(field(e.target))stop(e);},{capture:true,passive:false});
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


def check_action(page,action,contract,saved):
    parsed=urlsplit(page.url)
    if f'{parsed.scheme}://{parsed.netloc}'!=contract['origin'] or parsed.path not in (contract['root'],contract['path']):
        raise ReadOnlyViolation('MEASUREMENT_PAGE_SCOPE_DENIED')
    state=page.evaluate(r"""({config,x,y})=>{__CLASSIFY__
return {target:classify(Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null),focused:field(document.activeElement)};
}""".replace('__CLASSIFY__',CLASSIFY),{'config':contract,'x':action.get('x'),'y':action.get('y')})
    target=state['target'];kind=action['action']
    if kind in ('done','blocked','wait','scroll'):return state
    if kind=='click' and target['kind'] in ('navigation','expand','field','add_repetition'):return state
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

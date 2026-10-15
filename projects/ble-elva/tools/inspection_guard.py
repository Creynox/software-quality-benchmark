"""Read-only navigation, plus a distinct non-official report/PDF capability."""
import json
import re
from urllib.parse import urlsplit
from sqbf.read_only import ReadOnlyViolation, request_allowed
from .suite_fixture import validate_target

REPORT_PATH=re.compile(r'/reports/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def contract(fixture,paths,*,report=False,plan_samples=False):
    validate_target(fixture)
    if not paths or any(not isinstance(p,str) or not p.startswith('/') or '?' in p or '#' in p for p in paths):
        raise ValueError('Explicit inspected paths required')
    if type(report) is not bool or type(plan_samples) is not bool or report and plan_samples:raise ValueError('One explicit capability required')
    return {'origin':fixture['target_url'].rstrip('/'),'paths':list(paths),'report':report,
            'plan_samples':plan_samples,'plan_path':'/beprobung/'+fixture['suite_copy']['mapping']['plan_id'] if plan_samples else None}


CLASSIFY=r"""
const allowed=p=>config.paths.includes(p)||(config.report&&/^\/reports\/[0-9a-f-]{36}$/.test(p));
const norm=e=>(e?.innerText||'').replace(/\s+/g,' ').trim();
const classify=e=>{
 if(!allowed(location.pathname))return {kind:'blocked'};
 const a=e?.closest('a');if(a){
   if(config.report&&a.download&&a.href.startsWith('blob:'+config.origin+'/')&&window.__sqbfPdfDownload===location.pathname)return {kind:'blob_download'};
   const u=new URL(a.href,location.href);if(u.origin===config.origin&&!u.search&&!u.hash&&allowed(u.pathname))return {kind:'navigation'};
 }
 if(e?.closest('.mud-expand-panel-header')||e?.closest('.mud-tabs-toolbar [role="tab"]')||e?.closest('.mud-table-pagination button'))return {kind:'read_control'};
 const b=e?.closest('button');
 if(config.plan_samples&&location.pathname===config.plan_path&&norm(b)==='Proben anlegen / nachanlegen')return {kind:'plan_samples',scope:location.pathname};
 if(location.pathname==='/samples'&&e?.closest('tr[aria-selected][aria-label^="Probe "]'))return {kind:'read_control'};
 if(b?.getAttribute('title')==='Probe oeffnen'&&location.pathname.startsWith('/beprobung/'))return {kind:'read_control'};
 if(location.pathname==='/samples'&&['Detail anzeigen','Probe vollständig öffnen'].includes(norm(b)))return {kind:'read_control'};
 if(b?.getAttribute('aria-label')==='Weitere Aktionen')return {kind:'read_control'};
 if(config.report){
   const item=e?.closest('button,.mud-list-item');
   if(norm(item)==='Prüfbericht'&&config.paths.includes(location.pathname))return {kind:'generate',scope:location.pathname};
   if(norm(item)==='PDF herunterladen'&&/^\/reports\/[0-9a-f-]{36}$/.test(location.pathname))return {kind:'download',scope:location.pathname};
 }
 return {kind:'blocked'};
};
"""


def event_guard(config):
    return r"""(()=>{const config=__CONFIG__;__CLASSIFY__
const stop=e=>{e.preventDefault();e.stopImmediatePropagation();};
document.addEventListener('click',e=>{
 const t=classify(e.target);if(t.kind==='blocked')return stop(e);
 if(t.kind==='download')window.__sqbfPdfDownload=location.pathname;
 if(t.kind==='blob_download')window.__sqbfPdfDownload=null;
 if(t.kind==='generate'||t.kind==='plan_samples'){
   const key='sqbf-'+t.kind+'-attempt:'+t.scope;
   if(sessionStorage.getItem(key))return stop(e);
   sessionStorage.setItem(key,'attempted');
 }
},true);
for(const kind of ['input','change','submit','beforeinput'])document.addEventListener(kind,stop,true);
document.addEventListener('keydown',e=>{if(e.key!=='Escape')stop(e);},true);
})()""".replace('__CONFIG__',json.dumps(config)).replace('__CLASSIFY__',CLASSIFY)


def check_action(page,action,config,generated):
    p=urlsplit(page.url)
    if (f'{p.scheme}://{p.netloc}'!=config['origin'] or
            (p.path not in config['paths'] and not (config['report'] and REPORT_PATH.fullmatch(p.path)))):
        raise ReadOnlyViolation('INSPECTION_PAGE_SCOPE_DENIED')
    state=page.evaluate(r"""({config,x,y})=>{__CLASSIFY__
return classify(Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null);
}""".replace('__CLASSIFY__',CLASSIFY),{'config':config,'x':action.get('x'),'y':action.get('y')})
    if action['action'] in ('done','blocked','wait','scroll'):return state
    if action['action']=='key' and action.get('key')=='Escape':return state
    if action['action']=='click' and state['kind'] in ('navigation','read_control'):return state
    if config['report'] and action['action']=='click' and state['kind']=='download':return state
    if config['report'] and action['action']=='click' and state['kind']=='generate' and state['scope'] not in generated:return state
    if config['plan_samples'] and action['action']=='click' and state['kind']=='plan_samples' and state['scope'] not in generated:return state
    raise ReadOnlyViolation('INSPECTION_ACTION_SCOPE_DENIED')


def transport_allowed(url,method,config,policy):
    p=urlsplit(url)
    if method in ('GET','HEAD') and f'{p.scheme}://{p.netloc}'==config['origin'] and not p.query:
        if p.path in config['paths'] or (config['report'] and REPORT_PATH.fullmatch(p.path)):return True
    return request_allowed(url,method,config['origin'],policy)

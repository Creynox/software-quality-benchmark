"""Native non-saving form audit; no field filling, Save or model invocation."""
import re
from sqbf.no_write_oracle import snapshot
from .receipt_guard import make_contract, event_guard, transport_allowed


def check_receipt_form(fixture,dataset,policy):
    if fixture['suite_copy'].get('receipt_entrypoint')=='plan_replenish_once':
        return check_plan_form(fixture,dataset,policy)
    from playwright.sync_api import sync_playwright
    contract=make_contract(fixture,dataset['positions'][0],dataset['reference']['sampling_date'])
    result={'status':'BLOCKED_RECEIPT_UI_CONTRACT','model_calls':0,'save_attempts':0,'fields':{}}
    step='BASELINE'
    try:
        before=snapshot(fixture)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,timeout=15000)
            try:
                context=browser.new_context(storage_state=fixture['personas']['laboratory_staff']['storage_state'],
                    viewport={'width':1280,'height':800},service_workers='block',accept_downloads=False)
                context.add_init_script(event_guard(contract))
                context.route('**/*',lambda route:route.continue_() if transport_allowed(route.request.url,route.request.method,contract['origin'],policy) else route.abort())
                page=context.new_page();page.set_default_timeout(3000)
                page.goto(contract['origin']+'/samples/create',wait_until='domcontentloaded',timeout=15000)
                page.wait_for_timeout(800)
                if page.url!=contract['origin']+'/samples/create':return dict(result,reason='FORM_NOT_REACHABLE')
                for name in contract['fields']:
                    control=page.locator('.mud-input-control').filter(has=page.locator('label').filter(has_text=re.compile('^'+re.escape(name)+r'\s*\*?\s*$')))
                    result['fields'][name]=control.count()==1 and control.locator('input').count()==1
                if not all(result['fields'].values()):return dict(result,reason='FIELD_CONTRACT_MISMATCH')
                product=page.locator('.mud-input-control').filter(has=page.locator('label').filter(has_text=re.compile(r'^Produkt\s*\*?\s*$')))
                step='OPEN_PRODUCT_MENU'
                product.scroll_into_view_if_needed();box=product.locator('.mud-input-slot.mud-select-input:visible').bounding_box()
                page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);page.wait_for_timeout(250)
                option=page.locator('.mud-list-item').filter(has_text=contract['fields']['Produkt'])
                result['source_product_option_visible']=option.count()==1 and option.is_visible()
                page.keyboard.press('Escape')
                step='OPEN_DATE_CALENDAR'
                date=page.locator('.mud-input-control').filter(has=page.locator('label').filter(has_text=re.compile(r'^Entnahmedatum\s*\*?\s*$')))
                date.scroll_into_view_if_needed();box=date.locator('input').bounding_box()
                page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);page.wait_for_timeout(250)
                result['calendar_contract_visible']=page.locator('.mud-picker-calendar:visible').count()==1
                page.keyboard.press('Escape')
                result['save_control_present']=page.get_by_role('button',name='Probe anlegen',exact=True).count()==1
                context.close()
            finally:browser.close()
        result['protected_data_unchanged']=snapshot(fixture)==before
        if (result['source_product_option_visible'] and result['calendar_contract_visible']
                and result['save_control_present'] and result['protected_data_unchanged']):
            result['status']='RECEIPT_UI_CONTRACT_VERIFIED'
        return result
    except Exception as error:
        return dict(result,reason='NATIVE_FORM_CHECK_FAILED',step=step,error_type=type(error).__name__)


def check_plan_form(fixture,dataset,policy):
    from playwright.sync_api import sync_playwright
    from .inspection_guard import contract,event_guard,transport_allowed
    path='/beprobung/'+fixture['suite_copy']['mapping']['plan_id']
    config=contract(fixture,[path],plan_samples=True)
    result={'status':'BLOCKED_RECEIPT_UI_CONTRACT','model_calls':0,'save_attempts':0}
    try:
        before=snapshot(fixture)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,timeout=15000)
            try:
                context=browser.new_context(storage_state=fixture['personas']['laboratory_lead']['storage_state'],service_workers='block')
                context.add_init_script(event_guard(config))
                context.route('**/*',lambda route:route.continue_() if transport_allowed(route.request.url,route.request.method,config,policy) else route.abort())
                page=context.new_page();page.goto(config['origin']+path,wait_until='domcontentloaded',timeout=15000);page.wait_for_timeout(800)
                result['designated_plan_reached']=page.url==config['origin']+path
                button=page.get_by_role('button',name='Proben anlegen / nachanlegen',exact=True)
                result['creation_control_present']=button.count()==1 and button.is_enabled()
                result['all_source_products_visible']=all(page.get_by_text(row['product'],exact=True).count()>=1 for row in dataset['positions'])
                context.close()
            finally:browser.close()
        result['protected_data_unchanged']=snapshot(fixture)==before
        if all(result[k] for k in ('designated_plan_reached','creation_control_present','all_source_products_visible','protected_data_unchanged')):
            result['status']='RECEIPT_UI_CONTRACT_VERIFIED'
        return result
    except Exception as error:
        return dict(result,reason='PLAN_FORM_CHECK_FAILED',error_type=type(error).__name__)


ACCESS_DENIED_TITLE='Kein Zugriff auf diesen Bereich'


def check_entry_routes(fixture,policy,probes):
    """Model-free GET probe of each stage entry route per persona; no click, input or save.

    A route counts as reachable when the persona stays on the exact path, is not sent
    to /login and BLE does not render its access-denied state.
    """
    from playwright.sync_api import sync_playwright
    from .inspection_guard import contract,event_guard,transport_allowed
    result={'status':'BLOCKED_ENTRY_ROUTE_CONTRACT','model_calls':0,'save_attempts':0,'routes':[]}
    try:
        before=snapshot(fixture)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,timeout=15000)
            try:
                for persona,path,stages in probes:
                    config=contract(fixture,[path])
                    context=browser.new_context(storage_state=fixture['personas'][persona]['storage_state'],
                        viewport={'width':1280,'height':800},service_workers='block',accept_downloads=False)
                    try:
                        context.add_init_script(event_guard(config))
                        context.route('**/*',lambda route,config=config:route.continue_() if transport_allowed(
                            route.request.url,route.request.method,config,policy) else route.abort())
                        page=context.new_page();page.set_default_timeout(3000)
                        page.goto(config['origin']+path,wait_until='domcontentloaded',timeout=15000);page.wait_for_timeout(800)
                        reached=page.url==config['origin']+path
                        denied=page.get_by_text(ACCESS_DENIED_TITLE,exact=True).count()>0
                        result['routes'].append({'persona':persona,'stages':list(stages),'route':'plan' if path.startswith('/beprobung/') else path,
                                                 'reached':reached,'access_denied_shown':denied})
                    finally:context.close()
            finally:browser.close()
        result['protected_data_unchanged']=snapshot(fixture)==before
        if result['protected_data_unchanged'] and result['routes'] and all(
                r['reached'] and not r['access_denied_shown'] for r in result['routes']):
            result['status']='ENTRY_ROUTES_VERIFIED'
        else:result['reason']='ENTRY_ROUTE_UNREACHABLE_OR_DENIED'
        return result
    except Exception as error:
        return dict(result,reason='ENTRY_ROUTE_CHECK_FAILED',error_type=type(error).__name__)

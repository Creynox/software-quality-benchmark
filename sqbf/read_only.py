"""Controller-only semantic action gate; no DOM information reaches the agent."""
from urllib.parse import urlsplit


SEARCH_PLACEHOLDER = "Produkt, Code, Werk oder Kunde"
SEARCH_SELECTOR = f'input[placeholder="{SEARCH_PLACEHOLDER}"]'


class ReadOnlyViolation(RuntimeError):
    pass


def allow_operation(action, target, focused_search, policy):
    kind = action["action"]
    if kind in {"done", "blocked", "wait", "scroll"}:
        return
    if kind == "click" and target in {"products-navigation", "product-search"}:
        return
    if kind == "type" and focused_search and action.get("text") == policy["query"]:
        return
    if kind == "key" and focused_search and action.get("key") in {"ControlOrMeta+A", "Backspace", "Delete", "Enter"}:
        return
    raise ReadOnlyViolation("Action target or input is outside the approved read-only contract")


def request_allowed(url, method, origin):
    parsed = urlsplit(url)
    if f"{parsed.scheme}://{parsed.netloc}" != origin:
        return False
    path = parsed.path
    if method == "POST":
        return path in {"/_blazor/negotiate", "/_blazor"}
    if method not in {"GET", "HEAD"}:
        return False
    return (path in {"/", "/products", "/_blazor", "/_blazor/initializers", "/_blazor/disconnect"}
            or path.startswith(("/_framework/", "/_content/", "/css/", "/js/", "/images/", "/fonts/", "/assets/"))
            or path in {"/app.css", "/BLE.Web.styles.css", "/favicon.ico"})


def check_action(page, action, policy):
    if urlsplit(page.url).path not in {"/", "/products"}:
        raise ReadOnlyViolation("Navigation left the approved read-only pages")
    state = page.evaluate("""({x,y,placeholder}) => {
        const active=document.activeElement;
        const hit=Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null;
        const element=hit?.closest('a,button,input');
        let target='blocked';
        if(element?.matches('a[href="/products"]')) target='products-navigation';
        if(element?.tagName==='INPUT'&&element.placeholder===placeholder) target='product-search';
        return {target, focused:active?.tagName==='INPUT'&&active.placeholder===placeholder};
    }""", {"x": action.get("x"), "y": action.get("y"), "placeholder": SEARCH_PLACEHOLDER})
    allow_operation(action, state["target"], state["focused"], policy)


def observation(page, query):
    """Independent read of rendered UI, retained locally and never in prompts."""
    on_products = urlsplit(page.url).path == "/products"
    result = {"products_page": on_products, "query_visible": False, "empty_visible": False,
              "filter_cleared": False}
    if on_products:
        field = page.locator(SEARCH_SELECTOR)
        if field.count() == 1 and field.is_visible():
            value = field.input_value()
            result["query_visible"] = value == query
            result["filter_cleared"] = value == ""
        result["empty_visible"] = page.get_by_text("Keine Produkte gefunden", exact=True).is_visible()
    return result


# Defense in depth: reject events from every other control before Blazor's
# delegated handlers can receive them. The UI is not changed or hidden.
EVENT_GUARD = """(() => {
 const search=e=>e?.tagName==='INPUT'&&e.placeholder==='Produkt, Code, Werk oder Kunde';
 const stop=e=>{e.preventDefault(); e.stopImmediatePropagation();};
 document.addEventListener('click',e=>{
   const t=e.target.closest('a,button,input');
   if(!(t?.matches('a[href="/products"]')||search(t))) stop(e);
 },true);
 for(const event of ['input','change']) document.addEventListener(event,e=>{if(!search(e.target))stop(e);},true);
 document.addEventListener('submit',stop,true);
 document.addEventListener('keydown',e=>{
   if(!search(e.target)||e.altKey||e.metaKey||(e.ctrlKey&&e.key.toLowerCase()!=='a'))stop(e);
 },true);
})()"""

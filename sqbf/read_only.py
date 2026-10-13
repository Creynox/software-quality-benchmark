"""Controller-only semantic action gate; no DOM information reaches the agent."""
from urllib.parse import urlsplit
import json


class ReadOnlyViolation(RuntimeError):
    pass


def validate_policy(policy):
    required={"query","search_placeholder","target_path","navigation_selector","empty_text",
              "allowed_paths","transport_post_paths","asset_prefixes","asset_paths"}
    if not isinstance(policy,dict) or set(policy)!=required:
        raise ReadOnlyViolation("Read-only profile is incomplete")
    for key in ["query","search_placeholder","target_path","navigation_selector","empty_text"]:
        if not isinstance(policy[key],str) or not policy[key] or len(policy[key])>500:
            raise ReadOnlyViolation("Invalid read-only profile value")
    for key in ["allowed_paths","transport_post_paths","asset_prefixes","asset_paths"]:
        if not isinstance(policy[key],list) or any(not isinstance(path,str) or not path.startswith('/')
                or path.startswith('//') for path in policy[key]):
            raise ReadOnlyViolation("Read-only profile paths must be relative to the exact origin")
    if policy["target_path"] not in policy["allowed_paths"]:
        raise ReadOnlyViolation("Read-only target must be an allowed page")


def allow_operation(action, target, focused_search, policy):
    kind = action["action"]
    if kind in {"done", "blocked", "wait", "scroll"}:
        return
    if kind == "click" and target in {"navigation", "search"}:
        return
    if kind == "type" and focused_search and action.get("text") == policy["query"]:
        return
    if kind == "key" and focused_search and action.get("key") in {"ControlOrMeta+A", "Backspace", "Delete", "Enter"}:
        return
    raise ReadOnlyViolation("Action target or input is outside the approved read-only contract")


def request_allowed(url, method, origin, policy):
    parsed = urlsplit(url)
    if f"{parsed.scheme}://{parsed.netloc}" != origin:
        return False
    path = parsed.path
    if method == "POST":
        return path in policy["transport_post_paths"]
    if method not in {"GET", "HEAD"}:
        return False
    return (path in policy["allowed_paths"]+policy["asset_paths"]
            or path.startswith(tuple(policy["asset_prefixes"])))


def check_action(page, action, policy):
    if urlsplit(page.url).path not in policy["allowed_paths"]:
        raise ReadOnlyViolation("Navigation left the approved read-only pages")
    state = page.evaluate("""({x,y,placeholder,navigation}) => {
        const active=document.activeElement;
        const hit=Number.isFinite(x)&&Number.isFinite(y)?document.elementFromPoint(x,y):null;
        const element=hit?.closest('a,button,input');
        let target='blocked';
        if(element?.matches(navigation)) target='navigation';
        if(element?.tagName==='INPUT'&&element.placeholder===placeholder) target='search';
        return {target, focused:active?.tagName==='INPUT'&&active.placeholder===placeholder};
    }""", {"x": action.get("x"), "y": action.get("y"), "placeholder": policy["search_placeholder"],
            "navigation":policy["navigation_selector"]})
    allow_operation(action, state["target"], state["focused"], policy)


def observation(page, policy):
    """Independent read of rendered UI, retained locally and never in prompts."""
    on_products = urlsplit(page.url).path == policy["target_path"]
    result = {"target_page": on_products, "query_visible": False, "empty_visible": False,
              "filter_cleared": False}
    if on_products:
        field = page.get_by_placeholder(policy["search_placeholder"],exact=True)
        if field.count() == 1 and field.is_visible():
            value = field.input_value()
            result["query_visible"] = value == policy["query"]
            result["filter_cleared"] = value == ""
        result["empty_visible"] = page.get_by_text(policy["empty_text"], exact=True).is_visible()
    return result


# Defense in depth: reject events from every other control before Blazor's
# delegated handlers can receive them. The UI is not changed or hidden.
def event_guard(policy):
 return """(() => {
 const config=__POLICY__;
 const search=e=>e?.tagName==='INPUT'&&e.placeholder===config.placeholder;
 const stop=e=>{e.preventDefault(); e.stopImmediatePropagation();};
 document.addEventListener('click',e=>{
   const t=e.target.closest('a,button,input');
   if(!(t?.matches(config.navigation)||search(t))) stop(e);
 },true);
 for(const event of ['input','change']) document.addEventListener(event,e=>{if(!search(e.target))stop(e);},true);
 document.addEventListener('submit',stop,true);
 document.addEventListener('keydown',e=>{
   if(!search(e.target)||e.altKey||e.metaKey||(e.ctrlKey&&e.key.toLowerCase()!=='a'))stop(e);
 },true);
})()""".replace('__POLICY__',json.dumps({"placeholder":policy["search_placeholder"],"navigation":policy["navigation_selector"]}))

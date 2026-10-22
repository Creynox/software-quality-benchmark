"""Model-free session restoration check; no input dispatch or state persistence."""
from pathlib import Path
from urllib.parse import urlsplit

from .read_only import event_guard, request_allowed, validate_policy


def check_session(url, storage_state, policy, *, expected_products=None):
    validate_policy(policy)
    parsed = urlsplit(url)
    result = {"status": "BLOCKED_SESSION", "model_calls": 0, "ui_actions": 0,
              "checks": [], "identity_verified": False}
    # A populated fixture needs an explicit controller-owned expectation. The
    # original CORE empty-state contract remains the default and is never inferred.
    if expected_products is not None and (
            not isinstance(expected_products, list) or not expected_products
            or len(expected_products) > 100
            or any(not isinstance(name, str) or not name or len(name) > 500 for name in expected_products)
            or len(set(expected_products)) != len(expected_products)):
        return dict(result, reason="INVALID_PRODUCT_EXPECTATION")
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path != "/"):
        return dict(result, reason="UNAPPROVED_ORIGIN")
    if not Path(storage_state).is_file():
        return dict(result, reason="MISSING_SESSION")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=15000)
            try:
                for context_number in (1, 2):
                    context = browser.new_context(storage_state=str(storage_state),
                                                  service_workers="block", accept_downloads=False)
                    try:
                        context.add_init_script(event_guard(policy))
                        def guard(route):
                            if request_allowed(route.request.url, route.request.method, origin, policy):
                                route.continue_()
                            else:
                                route.abort()
                        context.route("**/*", guard)
                        page = context.new_page()
                        page.set_default_timeout(3000)
                        for stage, path in (("home", "/"), ("products", policy["target_path"]),
                                            ("reload", policy["target_path"])):
                            response = (page.reload(wait_until="domcontentloaded", timeout=15000)
                                        if stage == "reload" else
                                        page.goto(origin + path, wait_until="domcontentloaded", timeout=15000))
                            page.wait_for_timeout(700)
                            actual = urlsplit(page.url)
                            check = {"context": context_number, "stage": stage,
                                     "path": actual.path, "http_status": response.status if response else None}
                            result["checks"].append(check)
                            if actual.netloc != parsed.netloc or actual.path != path:
                                return dict(result, reason="UNEXPECTED_PAGE")
                            if not response or response.status != 200:
                                return dict(result, reason="HTTP_FAILURE")
                            if stage != "home":
                                check["search_visible"] = page.get_by_placeholder(policy["search_placeholder"], exact=True).is_visible()
                                check["empty_visible"] = page.get_by_text(policy["empty_text"], exact=True).is_visible()
                                if expected_products is None:
                                    expected_visible = check["empty_visible"]
                                else:
                                    check["expected_products_visible"] = all(
                                        page.locator('table tbody tr').filter(has=page.get_by_text(name, exact=True)).count() == 1
                                        and page.locator('table tbody tr').filter(has=page.get_by_text(name, exact=True)).is_visible()
                                        for name in expected_products)
                                    expected_visible = (not check["empty_visible"]
                                                        and check["expected_products_visible"])
                                if not check["search_visible"] or not expected_visible:
                                    return dict(result, reason="MISSING_EXPECTED_UI")
                    finally:
                        context.close()
                return dict(result, status="SESSION_RESTORED", reason=None)
            finally:
                browser.close()
    except Exception as error:
        # Never emit Playwright exception text, URLs with query strings, or cookies.
        return dict(result, reason="BROWSER_FAILURE", error_type=type(error).__name__)

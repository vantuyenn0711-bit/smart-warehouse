"""Browser proof for public demo. No passwords and no business writes are used."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8010")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if urlparse(base).hostname not in {"127.0.0.1", "localhost"}:
        parser.error("This QA script is restricted to the local app.")
    screenshots = ROOT / "docs/screenshots/public-demo"
    screenshots.mkdir(parents=True, exist_ok=True)
    checks, errors, external = [], [], set()
    with sync_playwright() as automation:
        browser = automation.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh", reduced_motion="reduce")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: external.add(request.url) if urlparse(request.url).hostname not in {urlparse(base).hostname, None} else None)
        for width, label in ((1440, "desktop"), (768, "tablet"), (375, "mobile")):
            page.set_viewport_size({"width": width, "height": 1000 if width > 375 else 812})
            page.goto(base + "/login/")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_role("button", name="Xem Demo", exact=True)).to_be_visible()
            expect(page.locator('input[name="username"]')).to_be_visible()
            page.screenshot(path=str(screenshots / f"login-{label}.png"), full_page=True)
            page.get_by_role("button", name="Xem Demo", exact=True).click()
            page.wait_for_url(base + "/")
            expect(page.locator(".public-demo-banner")).to_be_visible()
            checks.append(f"anonymous-entry:{width}")
            for name, path in (("dashboard", "/"), ("products", "/products/"), ("stock", "/stock/"), ("documents", "/documents/"), ("report", "/reports/")):
                response = page.goto(base + path)
                assert response and response.status == 200
                page.wait_for_load_state("networkidle")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (name, width)
                expect(page.locator(".public-demo-banner")).to_contain_text("Chỉ xem")
                assert page.locator('a[href="/users/"]').count() == 0
                assert page.locator('a[href="/products/new/"]').count() == 0
                assert page.locator('a[href^="/documents/new/"]').count() == 0
                checks.append(f"read-only-page:{name}:{width}")
                if name in {"dashboard", "products", "report"}:
                    page.screenshot(path=str(screenshots / f"{name}-{label}.png"), full_page=True)
            page.get_by_role("button", name="Thoát Demo", exact=True).click()
            page.wait_for_url(base + "/login/")
            assert context.request.get(base + "/", max_redirects=0).status == 302
            checks.append(f"exit-requires-login:{width}")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("button", name="Xem Demo", exact=True).click()
        page.wait_for_url(base + "/")
        page.wait_for_function("window.Chart && Chart.getChart(document.getElementById('movement-chart'))")
        checks.append("demo-chart-loaded")
        for path in ("/products/new/", "/documents/new/", "/users/new/", "/api/stock/confirm/"):
            assert context.request.post(base + path, form={"role": "ADMIN", "quantity": "999"}).status == 403
            checks.append(f"direct-write-denied:{path}")
        page.goto(base + "/reports/")
        with page.expect_download() as download:
            page.get_by_role("link", name="Xuất Excel", exact=True).click()
        assert download.value.suggested_filename.endswith(".xlsx")
        checks.append("demo-excel-download")
        page.get_by_role("button", name=re.compile("Đăng nhập quản trị")).click()
        page.wait_for_url(base + "/login/")
        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        assert context.request.get(base + "/users/", max_redirects=0).status == 302
        checks.append("admin-link-requires-authentication")
        browser.close()
    assert not errors, errors
    assert not external, external
    result = {"time": datetime.now().astimezone().isoformat(), "base_url": base,
              "checks_passed": len(checks), "checks": checks, "javascript_errors": errors,
              "external_requests": sorted(external), "business_writes": 0}
    (ROOT / "docs/public-demo-smoke-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks_passed": len(checks), "javascript_errors": errors, "external_requests": sorted(external)}))


if __name__ == "__main__":
    main()

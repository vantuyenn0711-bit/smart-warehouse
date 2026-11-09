"""Exercise the local demo through Chrome; record screenshots and verifiable results.

Creates one clearly labelled QA SKU and three demo documents via the UI. It never
deletes records, changes live services, or prints credentials. Requires demo mode.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "docs" / "screenshots"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--chrome", default=os.environ.get("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
    parser.add_argument("--skip-workflow", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    parsed = urlparse(base)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("This script only operates on the local demo server.")
    settings = dotenv_values(ROOT / ".env")
    password = os.environ.get("DEMO_PASSWORD") or settings.get("DEMO_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_PASSWORD must be configured locally.")
    if str(settings.get("DEMO_MODE", "")).lower() != "true":
        raise RuntimeError("Browser workflow requires DEMO_MODE=true in the local .env.")
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    checks: list[str] = []
    javascript_errors: list[str] = []
    external_requests: set[str] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chrome, headless=True)

        def session(role: str):
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh", reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: javascript_errors.append(str(error)))
            page.on("request", lambda request: external_requests.add(request.url) if urlparse(request.url).hostname not in {parsed.hostname, None} else None)
            response = page.goto(base + "/login/")
            assert response and response.status == 200
            assert "Smart Warehouse" in page.title(), "Refusing to interact with an unrelated local app."
            expect(page.locator(".demo-badge, .login-demo-note")).to_have_count(1)
            page.locator("input[name=username]").fill(f"demo_{role}")
            page.locator("input[name=password]").fill(password)
            page.get_by_role("button", name="Đăng nhập", exact=True).click()
            page.wait_for_url(base + "/")
            page.wait_for_load_state("networkidle")
            checks.append(f"login:{role}")
            return context, page

        context, page = session("manager")
        page.wait_for_function("window.Chart && Chart.getChart(document.getElementById('movement-chart'))")
        checks.append("dashboard:real-chart-initialized")
        assert page.evaluate("document.fonts.check(\"500 12px 'Be Vietnam Pro'\")")
        checks.append("assets:local-font-loaded")

        pages = [
            ("dashboard", "/"), ("products", "/products/"),
            ("stock", "/stock/"), ("documents", "/documents/"),
            ("report", "/reports/"), ("movements", "/movements/"),
            ("new-document", "/documents/new/?type=IN"),
            ("categories", "/categories/"), ("suppliers", "/suppliers/"),
            ("warehouses", "/warehouses/"), ("audit", "/audit/"), ("help", "/help/"),
        ]
        for width, suffix in [(1440, "desktop"), (768, "tablet"), (375, "mobile")]:
            page.set_viewport_size({"width": width, "height": 1000 if width > 375 else 812})
            for name, path in pages:
                response = page.goto(base + path)
                assert response and response.status == 200, (name, response.status if response else None)
                page.wait_for_load_state("networkidle")
                overflow = page.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth})")
                assert overflow["scroll"] <= overflow["width"] + 1, (name, width, overflow)
                checks.append(f"responsive:{name}:{width}")
                if name in {"dashboard", "products", "report", "new-document"}:
                    page.screenshot(path=str(SCREENSHOTS / f"{name}-{suffix}.png"), full_page=True)
            if width == 375:
                page.get_by_role("button", name="Mở menu", exact=True).click()
                expect(page.locator("#sidebar")).to_have_class(re.compile("is-open"))
                page.keyboard.press("Escape")
                expect(page.locator("#sidebar")).not_to_have_class(re.compile("is-open"))
                checks.append("mobile:menu-open-close-keyboard")

        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(base + "/products/")
        print("Responsive checks passed at 1440, 768 and 375 px.", flush=True)
        page.locator('#main-content input[name="q"]').fill("ZZZ-NO-MATCH-UI-QA")
        with page.expect_response(lambda response: "/products/?" in response.url and response.request.headers.get("hx-request") == "true") as received:
            page.get_by_role("button", name="Lọc dữ liệu", exact=True).click()
        assert received.value.status == 200
        expect(page.locator(".empty-state")).to_be_visible()
        assert "ZZZ-NO-MATCH-UI-QA" in page.url
        page.screenshot(path=str(SCREENSHOTS / "empty-state-desktop.png"), full_page=True)
        checks.append("htmx:filter-empty-push-url")

        page.goto(base + "/reports/?start=2026-11-09&end=2026-01-01")
        expect(page.locator(".form-nonfield-errors")).to_contain_text("Bộ lọc chưa hợp lệ")
        checks.append("report:invalid-date-error-visible")
        page.goto(base + "/products/")
        context.set_offline(True)
        expect(page.locator("#offline-banner")).to_be_visible()
        checks.append("connection:offline-state")
        context.set_offline(False)
        expect(page.locator("#offline-banner")).not_to_be_visible()

        created: dict[str, object] = {}
        if not args.skip_workflow:
            sku = "UI-QA-" + uuid4().hex[:8].upper()
            created["sku"] = sku
            print("Starting isolated demo SKU workflow through the UI.", flush=True)
            page.goto(base + "/products/new/")
            page.locator("input[name=sku]").fill(sku)
            page.locator("input[name=name]").fill("DEMO · Linh kiện kiểm thử trình duyệt")
            category_options = page.locator("select[name=category] option").evaluate_all("options => options.filter(option => option.value).map(option=>option.value)")
            page.locator("select[name=category]").select_option(category_options[0])
            page.locator("input[name=unit]").fill("Cái")
            page.locator("input[name=min_stock]").fill("10")
            page.locator("input[name=default_cost]").fill("12000")
            page.locator("input[name=is_active]").check()
            page.get_by_role("button", name="Lưu thông tin", exact=True).click()
            page.wait_for_url(base + "/products/")
            checks.append("workflow:create-product-ui")

            def create_document(kind: str, quantity: str) -> str:
                page.goto(base + f"/documents/new/?type={kind}")
                options = page.locator("select[name=warehouse] option").evaluate_all("options => options.filter(option => option.value).map(option=>option.value)")
                page.locator("select[name=warehouse]").select_option(options[0])
                page.locator("textarea[name=notes]").fill(f"DEMO browser QA · {sku} · {kind} {quantity}")
                selector = page.locator("select[name=items-0-product]")
                value = selector.locator("option").evaluate_all("(options, sku) => options.find(option=>option.textContent.includes(sku))?.value", sku)
                assert value
                created["product_id"] = value
                selector.select_option(value)
                page.locator("input[name=items-0-quantity]").fill(quantity)
                page.locator("input[name=items-0-unit_cost]").fill("12000")
                page.get_by_role("button", name="Lưu phiếu nháp", exact=True).click()
                page.wait_for_url(re.compile(re.escape(base) + r"/documents/\d+/$"))
                path = urlparse(page.url).path
                expect(page.locator(".confirmation-strip")).to_be_visible()
                return path

            def confirm() -> None:
                page.once("dialog", lambda dialog: dialog.accept())
                page.get_by_role("button", name=re.compile("Xác nhận (nhập|xuất) kho")).click()
                page.wait_for_load_state("networkidle")

            inbound = create_document("IN", "1000")
            confirm()
            expect(page.locator(".detail-card .badge-success")).to_be_visible()
            created["inbound"] = inbound
            checks.append("workflow:confirm-in-1000")
            outbound = create_document("OUT", "600")
            confirm()
            expect(page.locator(".detail-card .badge-success")).to_be_visible()
            created["outbound"] = outbound
            checks.append("workflow:confirm-out-600")
            blocked = create_document("OUT", "401")
            confirm()
            expect(page.locator(".notice-error")).to_be_visible()
            expect(page.locator(".detail-card .badge-warning")).to_be_visible()
            created["blocked"] = blocked
            checks.append("workflow:reject-out-401")
            page.goto(base + "/stock/?q=" + sku)
            expect(page.locator("tbody tr")).to_have_count(1)
            expect(page.locator("tbody tr td").nth(3)).to_contain_text("400")
            checks.append("workflow:balance-400")
            page.goto(base + "/movements/?q=" + sku)
            expect(page.locator("tbody tr")).to_have_count(2)
            checks.append("workflow:exactly-two-movements")
            page.goto(base + inbound)
            csrf = page.locator('form[action="/logout/"] input[name=csrfmiddlewaretoken]').input_value()
            result = context.request.post(base + inbound + "confirm/", form={"csrfmiddlewaretoken": csrf}, headers={"Referer": base + inbound})
            assert result.status == 200
            assert "đã xác nhận" in result.text().lower()
            page.goto(base + "/movements/?q=" + sku)
            expect(page.locator("tbody tr")).to_have_count(2)
            checks.append("workflow:duplicate-confirm-no-extra-movement")
            page.goto(base + "/reports/?q=" + sku)
            expect(page.locator(".report-table tbody tr")).to_have_count(1)
            expect(page.locator(".report-table tbody tr td").nth(6)).to_have_text("400")
            with page.expect_download() as download:
                page.get_by_role("link", name="Xuất Excel", exact=True).click()
            assert download.value.suggested_filename.endswith(".xlsx")
            checks.append("workflow:report-400-excel-download")
            page.goto(base + outbound)
            page.screenshot(path=str(SCREENSHOTS / "confirmed-document-desktop.png"), full_page=True)

        context.close()
        staff_context, staff_page = session("staff")
        staff_page.goto(base + "/documents/new/?type=OUT")
        expect(staff_page.get_by_role("button", name="Lưu phiếu nháp", exact=True)).to_be_visible()
        assert staff_context.request.get(base + "/products/new/").status == 403
        assert staff_context.request.get(base + "/users/").status == 403
        checks.append("permissions:staff-draft-allowed-catalog-and-users-denied")
        staff_context.close()
        viewer_context, viewer_page = session("viewer")
        assert viewer_context.request.get(base + "/documents/new/").status == 403
        assert viewer_page.get_by_role("link", name="Tạo phiếu nhập", exact=True).count() == 0
        if created.get("blocked"):
            viewer_page.goto(base + str(created["blocked"]))
            assert viewer_page.get_by_role("button", name=re.compile("Xác nhận (nhập|xuất) kho")).count() == 0
            csrf = viewer_page.locator('form[action="/logout/"] input[name=csrfmiddlewaretoken]').input_value()
            result = viewer_context.request.post(base + str(created["blocked"]) + "confirm/", form={"csrfmiddlewaretoken": csrf}, headers={"Referer": base + str(created["blocked"])})
            assert result.status == 403
        checks.append("permissions:viewer-mutation-endpoints-denied")
        viewer_context.close()
        browser.close()

    assert not javascript_errors, javascript_errors
    assert not external_requests, external_requests
    report = {"time": datetime.now().astimezone().isoformat(), "base_url": base, "checks_passed": len(checks), "checks": checks, "javascript_errors": javascript_errors, "external_requests": sorted(external_requests), "created_demo_records": created}
    filename = "browser-smoke-readonly-results.json" if args.skip_workflow else "browser-smoke-results.json"
    destination = ROOT / "docs" / filename
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks_passed": len(checks), "screenshots": str(SCREENSHOTS), "result": str(destination), "javascript_errors": javascript_errors, "external_requests": sorted(external_requests)}, ensure_ascii=True))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

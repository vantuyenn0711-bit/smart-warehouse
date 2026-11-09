"""Read-only checks against a running local Django server; prints no credentials."""
import argparse
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

from dotenv import dotenv_values
from openpyxl import load_workbook


class TokenParser(HTMLParser):
    token = ""

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "input" and data.get("name") == "csrfmiddlewaretoken":
            self.token = data.get("value", "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8010")
    args = parser.parse_args()
    if urllib.parse.urlparse(args.url).hostname not in {"127.0.0.1", "localhost"}:
        parser.error("Only a loopback local server is allowed.")
    env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
    password = env.get("DEMO_PASSWORD")
    if not password:
        parser.error("DEMO_PASSWORD is required in the ignored local .env.")
    checked = 0
    for role in ("admin", "manager", "staff", "viewer"):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        page = opener.open(args.url + "/login/", timeout=15).read().decode()
        tokens = TokenParser()
        tokens.feed(page)
        body = urllib.parse.urlencode({"username": f"demo_{role}", "password": password, "csrfmiddlewaretoken": tokens.token}).encode()
        request = urllib.request.Request(args.url + "/login/", data=body, headers={"Referer": args.url + "/login/"})
        response = opener.open(request, timeout=15)
        assert response.status == 200 and "/login/" not in response.url, f"Login {role} failed"
        paths = ["/", "/products/", "/categories/", "/warehouses/", "/suppliers/", "/documents/", "/stock/", "/movements/", "/reports/", "/help/"]
        if role in ("admin", "manager"):
            paths.append("/audit/")
        if role == "admin":
            paths.append("/users/")
        for path in paths:
            response = opener.open(args.url + path, timeout=15)
            assert response.status == 200, f"{role} {path} returned {response.status}"
            assert "Smart Warehouse" in response.read().decode(), f"Missing app layout {path}"
            checked += 1
        response = opener.open(args.url + "/reports/export/?q=DEMO", timeout=15)
        workbook = load_workbook(BytesIO(response.read()), read_only=True)
        assert workbook.active.max_row > 6
        checked += 1
        if role == "viewer":
            for path in ("/products/new/", "/documents/new/", "/users/", "/audit/"):
                try:
                    opener.open(args.url + path, timeout=15)
                except urllib.error.HTTPError as exc:
                    assert exc.code == 403, f"Permission response {exc.code} for {path}"
                else:
                    raise AssertionError(f"Viewer unexpectedly accessed {path}")
                checked += 1
    print(f"PASS: {checked} authenticated HTTP checks across all four roles, pages and XLSX.")


if __name__ == "__main__":
    main()

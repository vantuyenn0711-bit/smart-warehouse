from io import BytesIO
from unittest.mock import patch

import pytest
from django.contrib.auth import SESSION_KEY
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import DatabaseError, connections
from django.test import Client
from django.urls import reverse
from openpyxl import load_workbook

from accounts.models import User
from catalog.models import Category, Product
from core.demo import DEMO_SESSION_KEY, dataset_ready, public_demo_queries, viewer_principal
from core.models import AuditLog
from inventory.models import StockBalance, StockDocument, StockMovement
from inventory.services import confirm_document

pytestmark = pytest.mark.django_db(transaction=True, databases=["default", "demo"])


@pytest.fixture(scope="module")
def demo_dataset(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("prepare_public_demo", verbosity=0)
        assert dataset_ready()
    return True


@pytest.fixture
def live_data(stock_env, document_factory):
    stock_env.product.sku = "PRIVATE-LIVE-CANARY"
    stock_env.product.name = "REAL-PRIVATE-NOT-FOR-DEMO"
    stock_env.product.save()
    document = document_factory(quantity="25", confirm=True)
    return stock_env, document


@pytest.fixture
def demo_client(demo_dataset):
    browser = Client()
    assert browser.post(reverse("demo_enter")).status_code == 302
    return browser


def live_snapshot():
    return {
        "products": list(Product.objects.order_by("pk").values()),
        "documents": list(StockDocument.objects.order_by("pk").values()),
        "balances": list(StockBalance.objects.order_by("pk").values()),
        "movements": list(StockMovement.objects.order_by("pk").values()),
        "audit": list(AuditLog.objects.order_by("pk").values()),
        "users": list(User.objects.order_by("pk").values()),
    }


def test_demo_entry_creates_only_a_rotated_viewer_session(demo_dataset, live_data):
    env, _ = live_data
    browser = Client()
    browser.force_login(env.admin)
    old_cookie = browser.cookies["sessionid"].value
    before = live_snapshot()
    response = browser.post(reverse("demo_enter"), {"role": "ADMIN", "is_superuser": "1"})
    assert response.status_code == 302
    assert browser.cookies["sessionid"].value != old_cookie
    assert browser.session[DEMO_SESSION_KEY] is True
    assert SESSION_KEY not in browser.session
    assert browser.session.get_expiry_age() <= 3600
    page = browser.get(reverse("dashboard"))
    assert page.status_code == 200
    assert page.wsgi_request.user.role == "VIEWER"
    assert page.wsgi_request.user.pk is None
    assert not page.wsgi_request.user.is_superuser
    assert not page.context["can_write"] and not page.context["can_admin"]
    assert live_snapshot() == before


@pytest.mark.parametrize("route", ["dashboard", "product_list", "category_list", "supplier_list", "warehouse_list", "stock_list", "document_list", "movement_list", "report", "help"])
def test_demo_pages_use_synthetic_data_and_never_expose_live_catalog(demo_client, live_data, route):
    response = demo_client.get(reverse(route))
    assert response.status_code == 200
    assert b"PRIVATE-LIVE-CANARY" not in response.content
    assert b"REAL-PRIVATE-NOT-FOR-DEMO" not in response.content
    assert response.context["is_public_demo"] is True
    assert "no-store" in response["Cache-Control"]
    assert "Cookie" in response["Vary"]


def test_demo_report_and_csv_export_are_isolated(demo_client, live_data):
    response = demo_client.get(reverse("report_export"))
    assert response.status_code == 200
    sheet = load_workbook(BytesIO(response.content)).active
    values = [str(cell.value) for row in sheet for cell in row if cell.value is not None]
    assert any("DEMO-" in value for value in values)
    assert not any("PRIVATE-LIVE-CANARY" in value for value in values)
    response = demo_client.get(reverse("product_export"))
    assert b"DEMO-" in response.content
    assert b"PRIVATE-LIVE-CANARY" not in response.content


def test_demo_detail_cannot_use_live_document_object(demo_client, live_data):
    _, live = live_data
    response = demo_client.get(reverse("doc_detail", args=[live.pk]))
    assert response.status_code in (200, 404)
    assert live.document_no.encode() not in response.content
    if response.status_code == 200:
        assert response.context["document"]._state.db == "demo"
        assert not response.context["can_edit"] and not response.context["can_confirm"]


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("path", ["/", "/products/new/", "/products/import/", "/documents/new/", "/users/new/", "/reports/", "/api/stock/confirm/"])
def test_every_unsafe_demo_request_is_denied(demo_client, live_data, method, path):
    before = live_snapshot()
    response = getattr(demo_client, method)(path, data={"role": "ADMIN", "quantity": 999}, HTTP_X_ROLE="ADMIN")
    assert response.status_code == 403
    assert live_snapshot() == before


def test_direct_confirm_cancel_and_edit_urls_are_denied(demo_client, live_data):
    env, document = live_data
    before = live_snapshot()
    for name in ("doc_confirm", "doc_cancel", "doc_edit", "product_edit", "user_edit"):
        pk = env.product.pk if name == "product_edit" else env.admin.pk if name == "user_edit" else document.pk
        response = demo_client.post(reverse(name, args=[pk]), {"role": "ADMIN"})
        assert response.status_code == 403
    assert live_snapshot() == before


@pytest.mark.parametrize("route", ["user_list", "audit_list", "product_create", "doc_create"])
def test_demo_cannot_open_privileged_or_write_forms(demo_client, route):
    assert demo_client.get(reverse(route)).status_code == 403


def test_orm_router_and_services_reject_escalated_writes(demo_dataset, live_data):
    env, document = live_data
    before = live_snapshot()
    with public_demo_queries():
        with pytest.raises(PermissionDenied):
            Product.objects.create(sku="WRITE", name="Forbidden", category=env.category)
        with pytest.raises(PermissionDenied):
            confirm_document(document.pk, env.admin)
        with pytest.raises(PermissionDenied):
            Product.objects.using("default").all().count()
        with pytest.raises(PermissionDenied):
            Category.objects.using("demo").filter(code="DEMO-LK").update(name="Forbidden")
    assert live_snapshot() == before


def test_postgresql_demo_connection_is_read_only_even_outside_request(demo_dataset):
    with pytest.raises(DatabaseError):
        Category.objects.using("demo").filter(code="DEMO-LK").update(name="Forbidden")
    assert Category.objects.using("demo").get(code="DEMO-LK").name == "Linh kiện điện tử"


def test_buggy_allowed_view_cannot_query_the_primary_database(demo_client, live_data):
    with patch("catalog.views._query", return_value=Product.objects.using("default").all()):
        response = demo_client.get(reverse("product_list"))
    assert response.status_code == 403
    assert b"PRIVATE-LIVE-CANARY" not in response.content


def test_buggy_allowed_view_cannot_write_with_explicit_database(demo_client, live_data):
    before = live_snapshot()
    def unsafe_query(*args, **kwargs):
        Category.objects.using("default").create(code="UNSAFE", name="Forbidden")
        return Product.objects.none()
    with patch("catalog.views._query", side_effect=unsafe_query):
        assert demo_client.get(reverse("product_list")).status_code == 403
    assert live_snapshot() == before


@pytest.mark.parametrize("sql", ["SELECT * FROM public.catalog_product", 'SELECT * FROM "public"."accounts_user"', "SELECT set_config('search_path', 'public', false)"])
def test_explicit_schema_or_configuration_escape_is_denied(demo_dataset, sql):
    assert dataset_ready()
    with public_demo_queries(), pytest.raises(PermissionDenied), connections["demo"].cursor() as cursor:
        cursor.execute(sql)


def test_missing_verified_dataset_fails_closed(demo_dataset, live_data):
    browser = Client()
    with patch("accounts.demo_views.dataset_ready", return_value=False):
        response = browser.post(reverse("demo_enter"))
    assert response.status_code == 503
    assert DEMO_SESSION_KEY not in browser.session
    assert b"PRIVATE-LIVE-CANARY" not in response.content


def test_disabled_feature_does_not_expose_real_data(demo_client, live_data, settings):
    settings.PUBLIC_DEMO_ENABLED = False
    assert Client().post(reverse("demo_enter")).status_code == 404
    assert demo_client.get(reverse("dashboard")).status_code == 403
    assert DEMO_SESSION_KEY not in demo_client.session


def test_demo_entry_and_exit_require_post_and_csrf(demo_dataset):
    browser = Client(enforce_csrf_checks=True)
    assert browser.get(reverse("demo_enter")).status_code == 405
    assert browser.post(reverse("demo_enter")).status_code == 403
    browser.get(reverse("login"))
    token = browser.cookies["csrftoken"].value
    assert browser.post(reverse("demo_enter"), {"csrfmiddlewaretoken": token}).status_code == 302
    assert browser.post(reverse("demo_exit")).status_code == 403
    assert browser.get(reverse("demo_exit")).status_code == 405
    token = browser.cookies["csrftoken"].value
    assert browser.post(reverse("demo_exit"), {"csrfmiddlewaretoken": token}).status_code == 302
    assert DEMO_SESSION_KEY not in browser.session


@pytest.mark.parametrize("route", ["demo_exit", "demo_admin_login"])
def test_exit_requires_fresh_authentication(demo_client, route):
    response = demo_client.post(reverse(route))
    assert response.status_code == 302 and response.url == reverse("login")
    assert DEMO_SESSION_KEY not in demo_client.session
    assert demo_client.get(reverse("dashboard")).status_code == 302
    page = demo_client.get(reverse("login"))
    assert page.status_code == 200


def test_demo_preparation_is_idempotent_and_does_not_change_live_data(demo_dataset, live_data):
    before = live_snapshot()
    count = Product.objects.using("demo").count()
    call_command("prepare_public_demo", verbosity=0)
    assert dataset_ready()
    assert Product.objects.using("demo").count() == count == 16
    assert live_snapshot() == before


def test_virtual_viewer_has_no_credentials_or_privileges():
    user = viewer_principal()
    assert user.is_authenticated and user.role == "VIEWER"
    assert not user.has_usable_password() and user.pk is None
    assert not user.can_manage and not user.can_write and not user.can_admin

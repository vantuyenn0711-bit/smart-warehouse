import csv
import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from accounts.models import User
from catalog.models import Product
from core.models import AuditLog
from inventory.models import StockBalance, StockDocument, StockMovement

pytestmark = pytest.mark.django_db


def document_payload(stock_env, *, kind="IN", quantity="1000", product=None):
    return {
        "type": kind, "warehouse": stock_env.warehouse.pk,
        "supplier": stock_env.supplier.pk if kind == "IN" else "",
        "notes": "Nhập liệu qua HTTP",
        "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "1", "items-MAX_NUM_FORMS": "100",
        "items-0-product": (product or stock_env.product).pk,
        "items-0-quantity": quantity, "items-0-unit_cost": "10.50",
    }


@pytest.mark.parametrize("name", ["dashboard", "product_list", "document_list", "stock_list", "movement_list", "report", "product_export", "report_export", "user_list"])
def test_anonymous_users_are_redirected_to_login(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_health_is_read_only_and_available_without_login(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("name", ["dashboard", "product_list", "category_list", "warehouse_list", "supplier_list", "document_list", "stock_list", "movement_list", "report", "help"])
def test_viewer_can_read_business_screens(client, stock_env, document_factory, name):
    document_factory(confirm=True)
    client.force_login(stock_env.viewer)
    assert client.get(reverse(name)).status_code == 200


@pytest.mark.parametrize("name", ["product_create", "category_create", "supplier_create", "warehouse_create", "product_import", "doc_create", "user_create"])
def test_viewer_cannot_post_write_endpoints(client, stock_env, name):
    client.force_login(stock_env.viewer)
    response = client.post(reverse(name), {"name": "Không được phép"})
    assert response.status_code == 403
    assert not StockDocument.objects.exists()
    assert not AuditLog.objects.exists()


@pytest.mark.parametrize("name", ["doc_confirm", "doc_cancel", "doc_edit"])
def test_viewer_direct_document_urls_are_forbidden(client, stock_env, document_factory, name):
    document = document_factory()
    client.force_login(stock_env.viewer)
    response = client.post(reverse(name, args=[document.pk]), document_payload(stock_env))
    assert response.status_code == 403
    assert not StockBalance.objects.exists()
    assert not StockMovement.objects.exists()


@pytest.mark.parametrize("name", ["product_create", "category_create", "supplier_create", "warehouse_create", "user_list", "audit_list"])
def test_staff_cannot_access_master_write_or_admin_screens(client, stock_env, name):
    client.force_login(stock_env.staff)
    assert client.get(reverse(name)).status_code == 403


def test_staff_can_only_edit_own_drafts(client, stock_env, document_factory):
    own = document_factory(actor=stock_env.staff)
    other = document_factory(actor=stock_env.manager)
    client.force_login(stock_env.staff)
    assert client.get(reverse("doc_edit", args=[own.pk])).status_code == 200
    assert client.get(reverse("doc_edit", args=[other.pk])).status_code == 403
    assert client.post(reverse("doc_cancel", args=[other.pk])).status_code == 403


def test_http_full_1000_in_600_out_and_401_rejection(client, stock_env):
    client.force_login(stock_env.staff)
    response = client.post(reverse("doc_create"), document_payload(stock_env))
    assert response.status_code == 302
    inbound = StockDocument.objects.get(type="IN")
    assert inbound.status == "DRAFT"
    assert not StockBalance.objects.exists()
    assert client.post(reverse("doc_confirm", args=[inbound.pk])).status_code == 403
    client.force_login(stock_env.manager)
    assert client.post(reverse("doc_confirm", args=[inbound.pk])).status_code == 302
    assert StockBalance.objects.get().quantity_on_hand == Decimal("1000")
    client.post(reverse("doc_confirm", args=[inbound.pk]))
    assert StockBalance.objects.get().quantity_on_hand == Decimal("1000")
    assert StockMovement.objects.count() == 1
    assert client.post(reverse("doc_create"), document_payload(stock_env, kind="OUT", quantity="600")).status_code == 302
    outbound = StockDocument.objects.get(type="OUT")
    client.post(reverse("doc_confirm", args=[outbound.pk]))
    assert StockBalance.objects.get().quantity_on_hand == Decimal("400")
    assert client.get(reverse("document_print", args=[outbound.pk])).status_code == 200
    assert client.post(reverse("doc_create"), document_payload(stock_env, kind="OUT", quantity="401")).status_code == 302
    rejected = StockDocument.objects.filter(type="OUT", status="DRAFT").get()
    response = client.post(reverse("doc_confirm", args=[rejected.pk]), follow=True)
    assert "Không đủ tồn" in response.content.decode()
    assert StockBalance.objects.get().quantity_on_hand == Decimal("400")
    assert StockMovement.objects.count() == 2


@pytest.mark.parametrize("quantity", ["0", "-5", "0.0001", "bad", "NaN"])
def test_http_rejects_invalid_item_quantity(client, stock_env, quantity):
    client.force_login(stock_env.staff)
    response = client.post(reverse("doc_create"), document_payload(stock_env, quantity=quantity))
    assert response.status_code == 200
    assert not StockDocument.objects.exists()


def test_confirmation_requires_post_and_csrf(stock_env, document_factory, client):
    document = document_factory()
    client.force_login(stock_env.manager)
    assert client.get(reverse("doc_confirm", args=[document.pk])).status_code == 405
    secure_client = Client(enforce_csrf_checks=True)
    secure_client.force_login(stock_env.manager)
    assert secure_client.post(reverse("doc_confirm", args=[document.pk])).status_code == 403
    assert not StockMovement.objects.exists()


def test_manager_product_create_validate_and_archive(client, stock_env):
    client.force_login(stock_env.manager)
    values = {"sku": "NEW-001", "name": "Sản phẩm mới", "category": stock_env.category.pk,
              "unit": "Cái", "default_cost": "100.25", "min_stock": "5.125", "is_active": "on"}
    assert client.post(reverse("product_create"), values).status_code == 302
    created = Product.objects.get(sku="NEW-001")
    assert created.default_cost == Decimal("100.25")
    assert created.min_stock == Decimal("5.125")
    values["sku"] = "new-001"
    assert client.post(reverse("product_create"), values).status_code == 200
    assert Product.objects.filter(sku__iexact="NEW-001").count() == 1
    values["sku"] = "NEW-001"
    values.pop("is_active")
    assert client.post(reverse("product_edit", args=[created.pk]), values).status_code == 302
    created.refresh_from_db()
    assert not created.is_active
    assert AuditLog.objects.filter(model_name="Product", object_id=str(created.pk)).count() == 2


def test_csv_import_is_atomic_on_invalid_second_row(client, stock_env):
    client.force_login(stock_env.manager)
    content = ("sku,name,category,unit,default_cost,min_stock\n"
               "CSV-OK,Hàng hợp lệ,CAT-01,Cái,12.50,2\n"
               "CSV-FAIL,Hàng sai,NO-CATEGORY,Cái,10,1\n")
    response = client.post(reverse("product_import"), {"file": SimpleUploadedFile("products.csv", content.encode("utf-8"), "text/csv")})
    assert response.status_code == 200
    assert not Product.objects.filter(sku__startswith="CSV-").exists()
    assert not AuditLog.objects.filter(action="IMPORT").exists()


def test_csv_import_valid_and_duplicate_do_not_overwrite(client, stock_env):
    client.force_login(stock_env.manager)
    content = "sku,name,category,unit,default_cost,min_stock\nCSV-OK,Hàng nhập,CAT-01,Cái,12.50,2\n"
    response = client.post(reverse("product_import"), {"file": SimpleUploadedFile("products.csv", content.encode("utf-8"), "text/csv")})
    assert response.status_code == 302
    assert Product.objects.get(sku="CSV-OK").default_cost == Decimal("12.50")
    assert client.post(reverse("product_import"), {"file": SimpleUploadedFile("products.csv", content.encode("utf-8"), "text/csv")}).status_code == 200
    assert Product.objects.filter(sku="CSV-OK").count() == 1


@pytest.mark.parametrize("filename,content", [("unsafe.xlsx", b"not csv"), ("broken.csv", b"\xff\xfeinvalid")])
def test_csv_import_rejects_wrong_format(client, stock_env, filename, content):
    client.force_login(stock_env.manager)
    assert client.post(reverse("product_import"), {"file": SimpleUploadedFile(filename, content)}).status_code == 200
    assert not AuditLog.objects.filter(action="IMPORT").exists()


def test_product_csv_export_escapes_spreadsheet_formula_and_filters(client, stock_env):
    stock_env.product.name = '=HYPERLINK("https://example.com")'
    stock_env.product.save()
    client.force_login(stock_env.viewer)
    response = client.get(reverse("product_export"), {"q": stock_env.product.sku})
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == 2
    assert rows[1][1].startswith("'=")
    assert rows[1][0] == stock_env.product.sku


def test_only_admin_can_manage_accounts(client, stock_env):
    client.force_login(stock_env.manager)
    assert client.get(reverse("user_list")).status_code == 403
    assert client.post(reverse("user_create"), {"username": "unauthorized"}).status_code == 403
    assert not User.objects.filter(username="unauthorized").exists()


def test_admin_create_user_hashes_password_without_audit_secret(client, stock_env):
    client.force_login(stock_env.admin)
    password = "only-a-test-secret-12345"
    response = client.post(reverse("user_create"), {
        "username": "new_viewer", "first_name": "Người dùng", "last_name": "Test",
        "email": "test@example.com", "role": "VIEWER", "is_active": "on", "password": password,
    })
    assert response.status_code == 302
    created = User.objects.get(username="new_viewer")
    assert created.password != password
    assert created.check_password(password)
    audit = AuditLog.objects.get(model_name="User", object_id=str(created.pk))
    assert password not in str(audit.changes)
    assert created.password not in str(audit.changes)


def test_last_admin_cannot_be_deactivated(client, stock_env):
    client.force_login(stock_env.admin)
    response = client.post(reverse("user_edit", args=[stock_env.admin.pk]), {
        "username": stock_env.admin.username, "first_name": "", "last_name": "", "email": "",
        "role": "VIEWER", "password": "",
    })
    assert response.status_code == 200
    stock_env.admin.refresh_from_db()
    assert stock_env.admin.role == "ADMIN"
    assert stock_env.admin.is_active


def test_search_ignores_unapproved_sort_field(client, stock_env):
    client.force_login(stock_env.viewer)
    response = client.get(reverse("product_list"), {"q": "SKU-001", "sort": "password;DROP TABLE"})
    assert response.status_code == 200
    assert len(response.context["records"]) == 1

from decimal import Decimal
from types import SimpleNamespace

import pytest

from accounts.models import User
from catalog.models import Category, Product
from inventory.models import Warehouse
from inventory.services import confirm_document, create_document
from partners.models import Supplier


@pytest.fixture(autouse=True)
def local_test_settings(settings):
    # Faster Django password hashing in isolated test data only.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
    settings.SECURE_SSL_REDIRECT = False
    settings.SESSION_COOKIE_SECURE = False
    settings.CSRF_COOKIE_SECURE = False
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def users():
    return {
        role.lower(): User.objects.create_user(
            username=f"test_{role.lower()}", password="test-only-password-12345", role=role,
        )
        for role in User.Role.values
    }


@pytest.fixture
def stock_env(users):
    category = Category.objects.create(code="CAT-01", name="Linh kiện điện tử")
    product = Product.objects.create(
        sku="SKU-001", name="Cảm biến kiểm thử", category=category,
        unit="Cái", min_stock=Decimal("5"), default_cost=Decimal("10.50"),
    )
    second_product = Product.objects.create(
        sku="SKU-002", name="Đầu nối kiểm thử", category=category,
        unit="Cái", min_stock=Decimal("2"), default_cost=Decimal("25"),
    )
    return SimpleNamespace(
        users=users, category=category, product=product, second_product=second_product,
        warehouse=Warehouse.objects.create(code="WH-A", name="Kho A"),
        other_warehouse=Warehouse.objects.create(code="WH-B", name="Kho B"),
        supplier=Supplier.objects.create(code="SUP-01", name="Nhà cung cấp thử nghiệm"),
        **users,
    )


@pytest.fixture
def document_factory(stock_env):
    def make(*, type="IN", quantity="20", product=None, warehouse=None, actor=None,
             items=None, confirm=False, supplier=None):
        document = create_document(
            actor=actor or stock_env.staff, type=type,
            warehouse=warehouse or stock_env.warehouse,
            supplier=supplier or (stock_env.supplier if type == "IN" else None),
            notes="Tài liệu kiểm thử tự động",
            items=items if items is not None else [{
                "product": product or stock_env.product,
                "quantity": Decimal(quantity), "unit_cost": Decimal("10.50"),
            }],
        )
        if confirm:
            document = confirm_document(document.pk, stock_env.manager)
        return document
    return make

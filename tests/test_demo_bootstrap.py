import pytest
from django.core.management import call_command
from django.test import override_settings

from accounts.models import User
from catalog.models import Category, Product
from inventory.models import StockDocument

pytestmark = pytest.mark.django_db


@override_settings(DEMO_MODE=False)
def test_launcher_does_not_seed_when_demo_mode_disabled():
    call_command("seed_demo", if_empty=True)
    assert not User.objects.exists()
    assert not Product.objects.exists()
    assert not StockDocument.objects.exists()


@override_settings(DEMO_MODE=True)
def test_launcher_preserves_existing_database(stock_env):
    before_users = list(User.objects.order_by("pk").values("pk", "username", "role", "password"))
    before_products = Product.objects.count()
    call_command("seed_demo", if_empty=True)
    assert list(User.objects.order_by("pk").values("pk", "username", "role", "password")) == before_users
    assert Product.objects.count() == before_products
    assert not StockDocument.objects.exists()


@override_settings(DEMO_MODE=True)
def test_launcher_preserves_catalog_even_without_accounts():
    Category.objects.create(code="EXISTING", name="Danh mục hiện hữu")
    call_command("seed_demo", if_empty=True)
    assert not User.objects.exists()
    assert list(Category.objects.values_list("code", flat=True)) == ["EXISTING"]
    assert not Product.objects.exists()
    assert not StockDocument.objects.exists()

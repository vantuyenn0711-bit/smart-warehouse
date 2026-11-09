from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import IntegrityError, close_old_connections, connections
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from inventory.models import StockBalance, StockDocument, StockMovement
from reports.services import inventory_report

pytestmark = pytest.mark.django_db


def test_product_ranking_combines_same_sku_across_warehouses(stock_env, document_factory):
    document_factory(quantity="10", confirm=True)
    document_factory(quantity="15", warehouse=stock_env.other_warehouse, confirm=True)
    result = inventory_report({"start": timezone.localdate(), "end": timezone.localdate()})
    assert len(result["top_products"]) == 1
    assert result["top_products"][0]["inbound"] == Decimal("25")


def test_history_date_filters_exclude_older_movements(client, stock_env, document_factory):
    old = document_factory(quantity="10", confirm=True)
    StockMovement.objects.filter(document=old).update(created_at=timezone.now() - timedelta(days=3))
    current = document_factory(quantity="7", confirm=True)
    client.force_login(stock_env.viewer)
    response = client.get(reverse("movement_list"), {"start": str(timezone.localdate()), "end": str(timezone.localdate())})
    assert response.status_code == 200
    assert [movement.document_id for movement in response.context["movements"]] == [current.pk]


def test_empty_post_returns_required_field_errors(client, stock_env):
    client.force_login(stock_env.manager)
    response = client.post(reverse("product_create"), {})
    assert response.status_code == 200
    assert "sku" in response.context["form"].errors
    response = client.post(reverse("doc_create"), {})
    assert response.status_code == 200
    assert response.context["form"].errors
    assert response.context["formset"].non_form_errors()


def test_racing_user_name_returns_form_error_instead_of_500(client, stock_env):
    client.force_login(stock_env.admin)
    with patch("accounts.views.UserForm.save", side_effect=IntegrityError("race")):
        response = client.post(reverse("user_create"), {
            "username": "racing-user", "password": "A-different-strong-demo-password-719",
            "role": "VIEWER", "is_active": "on",
        })
    assert response.status_code == 200
    assert "username" in response.context["form"].errors


@pytest.mark.django_db(transaction=True)
def test_two_http_confirmation_requests_cannot_oversell(stock_env, document_factory):
    document_factory(quantity="10", confirm=True)
    drafts = [document_factory(type="OUT", quantity="8") for _ in range(2)]
    barrier = Barrier(2)

    def request_confirm(document):
        close_old_connections()
        try:
            browser = Client()
            browser.force_login(stock_env.manager)
            barrier.wait(timeout=10)
            return browser.post(reverse("doc_confirm", args=[document.pk])).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(request_confirm, draft) for draft in drafts]
        assert [future.result(timeout=30) for future in futures] == [302, 302]
    assert StockBalance.objects.get().quantity_on_hand == Decimal("2")
    assert StockMovement.objects.count() == 2
    assert StockDocument.objects.filter(type="OUT", status="CONFIRMED").count() == 1

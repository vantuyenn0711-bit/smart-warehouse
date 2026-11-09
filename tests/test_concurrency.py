from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, connections

from accounts.models import User
from inventory.models import StockBalance, StockDocument, StockMovement
from inventory.services import confirm_document

pytestmark = pytest.mark.django_db(transaction=True)


def race_confirm(document_ids, actor_id):
    assert connection.vendor == "postgresql", "These tests require real PostgreSQL row locks."
    barrier = Barrier(len(document_ids))

    def worker(document_id):
        close_old_connections()
        try:
            actor = User.objects.get(pk=actor_id)
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout = '10s'")
                cursor.execute("SET statement_timeout = '15s'")
            barrier.wait(timeout=10)
            try:
                confirm_document(document_id, actor)
                return "confirmed"
            except ValidationError:
                return "rejected"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(document_ids)) as pool:
        futures = [pool.submit(worker, document_id) for document_id in document_ids]
        return [future.result(timeout=30) for future in futures]


def test_concurrent_outbounds_cannot_make_stock_negative(stock_env, document_factory):
    document_factory(quantity="10", confirm=True)
    documents = [document_factory(type="OUT", quantity="8") for _ in range(2)]
    outcomes = race_confirm([document.pk for document in documents], stock_env.manager.pk)
    assert sorted(outcomes) == ["confirmed", "rejected"]
    assert StockBalance.objects.get().quantity_on_hand == Decimal("2")
    assert StockMovement.objects.count() == 2
    assert StockDocument.objects.filter(type="OUT", status="CONFIRMED").count() == 1
    assert StockDocument.objects.filter(type="OUT", status="DRAFT").count() == 1


def test_concurrent_duplicate_confirmation_posts_once(stock_env, document_factory):
    document = document_factory(quantity="20")
    outcomes = race_confirm([document.pk, document.pk], stock_env.manager.pk)
    assert sorted(outcomes) == ["confirmed", "rejected"]
    assert StockBalance.objects.get().quantity_on_hand == Decimal("20")
    assert StockMovement.objects.count() == 1


def test_concurrent_first_inbound_creates_one_balance(stock_env, document_factory):
    documents = [document_factory(quantity=quantity) for quantity in ("10", "20")]
    assert not StockBalance.objects.exists()
    assert race_confirm([document.pk for document in documents], stock_env.manager.pk) == ["confirmed", "confirmed"]
    assert StockBalance.objects.count() == 1
    assert StockBalance.objects.get().quantity_on_hand == Decimal("30")
    assert StockMovement.objects.count() == 2


def test_concurrent_missing_balance_outbounds_leave_no_partial_rows(stock_env, document_factory):
    documents = [document_factory(type="OUT", quantity="1") for _ in range(2)]
    assert race_confirm([document.pk for document in documents], stock_env.manager.pk) == ["rejected", "rejected"]
    assert not StockBalance.objects.exists()
    assert not StockMovement.objects.exists()
    assert StockDocument.objects.filter(status="DRAFT").count() == 2

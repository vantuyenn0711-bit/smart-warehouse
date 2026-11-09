from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from catalog.models import Product
from core.models import AuditLog
from inventory.models import StockBalance, StockDocument, StockMovement
from inventory.services import cancel_document, confirm_document, create_document, update_document

pytestmark = pytest.mark.django_db


def test_draft_has_no_effect_on_stock(stock_env, document_factory):
    document = document_factory()
    assert document.status == "DRAFT"
    assert document.items.count() == 1
    assert not StockBalance.objects.exists()
    assert not StockMovement.objects.exists()
    audit = AuditLog.objects.get(action="CREATE", model_name="StockDocument")
    assert audit.actor == stock_env.staff
    assert audit.changes["after"]["items"][0]["quantity"] == "20.000"


def test_inbound_20_then_outbound_5_is_15(stock_env, document_factory):
    inbound = document_factory(confirm=True)
    outbound = document_factory(type="OUT", quantity="5", confirm=True)
    assert StockBalance.objects.get().quantity_on_hand == Decimal("15")
    assert list(StockMovement.objects.order_by("pk").values_list("signed_qty", flat=True)) == [Decimal("20"), Decimal("-5")]
    assert inbound.confirmed_by == stock_env.manager
    assert inbound.confirmed_at is not None
    assert outbound.status == "CONFIRMED"
    assert AuditLog.objects.filter(action="CONFIRM").count() == 2


def test_outbound_above_balance_rolls_back(stock_env, document_factory):
    document_factory(confirm=True)
    document_factory(type="OUT", quantity="5", confirm=True)
    rejected = document_factory(type="OUT", quantity="16")
    movements_before = StockMovement.objects.count()
    with pytest.raises(ValidationError, match="Không đủ tồn"):
        confirm_document(rejected.pk, stock_env.manager)
    rejected.refresh_from_db()
    assert rejected.status == "DRAFT"
    assert rejected.confirmed_by_id is None
    assert StockBalance.objects.get().quantity_on_hand == Decimal("15")
    assert StockMovement.objects.count() == movements_before
    assert not AuditLog.objects.filter(action="CONFIRM", object_id=str(rejected.pk)).exists()


def test_multiline_failure_undoes_previous_line_and_new_balance(stock_env, document_factory):
    document_factory(confirm=True)
    document = document_factory(type="OUT", items=[
        {"product": stock_env.product, "quantity": Decimal("5"), "unit_cost": 0},
        {"product": stock_env.second_product, "quantity": Decimal("1"), "unit_cost": 0},
    ])
    with pytest.raises(ValidationError):
        confirm_document(document.pk, stock_env.manager)
    assert StockBalance.objects.get(product=stock_env.product).quantity_on_hand == Decimal("20")
    assert not StockBalance.objects.filter(product=stock_env.second_product).exists()
    assert not StockMovement.objects.filter(document=document).exists()


def test_duplicate_confirmation_does_not_post_twice(stock_env, document_factory):
    document = document_factory(confirm=True)
    with pytest.raises(ValidationError, match="Không thể xác nhận lại"):
        confirm_document(document.pk, stock_env.manager)
    assert StockBalance.objects.get().quantity_on_hand == Decimal("20")
    assert document.movements.count() == 1
    assert AuditLog.objects.filter(action="CONFIRM", object_id=str(document.pk)).count() == 1


@pytest.mark.parametrize("quantity", ["0", "-1", "1.0001", "1000000000000000", "NaN", "Infinity", "invalid"])
def test_invalid_quantities_never_create_documents(stock_env, quantity):
    with pytest.raises(ValidationError):
        create_document(actor=stock_env.staff, type="IN", warehouse=stock_env.warehouse,
                        items=[{"product": stock_env.product, "quantity": quantity, "unit_cost": "0"}])
    assert not StockDocument.objects.exists()
    assert not AuditLog.objects.exists()


@pytest.mark.parametrize("cost", ["-1", "0.001", "10000000000000000", "NaN", "Infinity"])
def test_invalid_costs_never_create_documents(stock_env, cost):
    with pytest.raises(ValidationError):
        create_document(actor=stock_env.staff, type="IN", warehouse=stock_env.warehouse,
                        items=[{"product": stock_env.product, "quantity": "1", "unit_cost": cost}])
    assert not StockDocument.objects.exists()


def test_empty_or_duplicate_items_are_rejected(stock_env, document_factory):
    with pytest.raises(ValidationError):
        document_factory(items=[])
    item = {"product": stock_env.product, "quantity": 1, "unit_cost": 0}
    with pytest.raises(ValidationError, match="xuất hiện nhiều lần"):
        document_factory(items=[item, item])
    assert not StockDocument.objects.exists()


@pytest.mark.parametrize("entity", ["product", "category", "warehouse", "supplier"])
def test_archived_entities_cannot_be_confirmed(stock_env, document_factory, entity):
    document = document_factory()
    archived = getattr(stock_env, entity)
    archived.is_active = False
    archived.save()
    with pytest.raises(ValidationError):
        confirm_document(document.pk, stock_env.manager)
    assert not StockMovement.objects.exists()
    assert not StockBalance.objects.exists()
    document.refresh_from_db()
    assert document.status == "DRAFT"


def test_only_managers_can_confirm(stock_env, document_factory):
    document = document_factory()
    for actor in (stock_env.staff, stock_env.viewer):
        with pytest.raises(PermissionDenied):
            confirm_document(document.pk, actor)
    assert not StockMovement.objects.exists()


def test_viewer_cannot_create_or_modify_documents(stock_env, document_factory):
    with pytest.raises(PermissionDenied):
        document_factory(actor=stock_env.viewer)
    draft = document_factory()
    with pytest.raises(PermissionDenied):
        cancel_document(draft.pk, stock_env.viewer)
    with pytest.raises(PermissionDenied):
        update_document(draft.pk, actor=stock_env.viewer, warehouse=stock_env.warehouse,
                        items=[{"product": stock_env.product, "quantity": 1, "unit_cost": 0}])


def test_staff_cannot_edit_or_cancel_another_users_draft(stock_env, document_factory):
    document = document_factory(actor=stock_env.manager)
    with pytest.raises(PermissionDenied):
        cancel_document(document.pk, stock_env.staff)
    with pytest.raises(PermissionDenied):
        update_document(document.pk, actor=stock_env.staff, warehouse=stock_env.warehouse,
                        items=[{"product": stock_env.product, "quantity": 1, "unit_cost": 0}])


def test_manager_edit_replaces_draft_items_without_changing_stock(stock_env, document_factory):
    document = document_factory()
    update_document(document.pk, actor=stock_env.manager, warehouse=stock_env.other_warehouse,
                    notes="Đã thay đổi", items=[{"product": stock_env.second_product, "quantity": "2.500", "unit_cost": "17.25"}])
    document.refresh_from_db()
    assert document.warehouse == stock_env.other_warehouse
    assert document.items.get().product == stock_env.second_product
    assert document.total_value == Decimal("43.12500")
    assert not StockBalance.objects.exists()
    assert AuditLog.objects.filter(action="UPDATE", object_id=str(document.pk)).exists()


def test_cancel_retains_draft_history_and_cannot_be_reconfirmed(stock_env, document_factory):
    document = document_factory()
    cancel_document(document.pk, stock_env.staff)
    document.refresh_from_db()
    assert document.status == "CANCELLED"
    assert document.items.exists()
    with pytest.raises(ValidationError):
        confirm_document(document.pk, stock_env.manager)
    with pytest.raises(ValidationError):
        cancel_document(document.pk, stock_env.manager)
    assert not StockMovement.objects.exists()


def test_confirmed_document_and_items_are_immutable(stock_env, document_factory):
    document = document_factory()
    stale_item = document.items.get()
    draft = document_factory()
    confirm_document(document.pk, stock_env.manager)
    with pytest.raises(ValidationError):
        update_document(document.pk, actor=stock_env.manager, warehouse=stock_env.warehouse,
                        items=[{"product": stock_env.product, "quantity": 1, "unit_cost": 0}])
    with pytest.raises(ValidationError):
        cancel_document(document.pk, stock_env.manager)
    document.notes = "Không được phép"
    with pytest.raises(ValidationError):
        document.save()
    with pytest.raises(ValidationError):
        stale_item.delete()
    stale_item.document = draft
    with pytest.raises(ValidationError):
        stale_item.save()
    assert StockMovement.objects.count() == 1


def test_movement_and_audit_instance_history_is_immutable(document_factory):
    document_factory(confirm=True)
    for history in (StockMovement.objects.first(), AuditLog.objects.first()):
        with pytest.raises(ValidationError):
            history.save()
        with pytest.raises(ValidationError):
            history.delete()


def test_product_unit_cannot_change_after_first_movement(stock_env, document_factory):
    document_factory(confirm=True)
    stock_env.product.unit = "Thùng"
    with pytest.raises(ValidationError):
        stock_env.product.save()
    stock_env.product.refresh_from_db()
    assert stock_env.product.unit == "Cái"


def test_balance_database_constraints_prevent_negative_or_duplicate(stock_env, document_factory):
    document_factory(confirm=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        StockBalance.objects.update(quantity_on_hand=Decimal("-1"))
    with pytest.raises(IntegrityError), transaction.atomic():
        StockBalance.objects.create(warehouse=stock_env.warehouse, product=stock_env.product)
    assert StockBalance.objects.get().quantity_on_hand == Decimal("20")


def test_sku_database_uniqueness_is_case_insensitive(stock_env):
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(sku=stock_env.product.sku.lower(), name="Trùng", category=stock_env.category)


def test_referenced_master_data_is_protected(stock_env, document_factory):
    document_factory(confirm=True)
    for referenced in (stock_env.product, stock_env.category, stock_env.warehouse, stock_env.supplier):
        with pytest.raises(ProtectedError):
            referenced.delete()


def test_zero_cost_and_fractional_quantity_are_supported(stock_env, document_factory):
    document_factory(confirm=True, items=[{"product": stock_env.product, "quantity": Decimal("0.125"), "unit_cost": Decimal("0")}])
    assert StockBalance.objects.get().quantity_on_hand == Decimal("0.125")

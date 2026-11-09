"""The only application write path for stock documents and balances.

Each confirmation locks its document and then its warehouse. Serializing writers
per warehouse also protects a balance that does not exist yet. Row locks on
existing balances and database constraints provide additional safeguards.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from catalog.models import Category, Product
from core.models import AuditLog
from inventory.models import (
    StockBalance,
    StockDocument,
    StockDocumentItem,
    StockMovement,
    Warehouse,
)
from partners.models import Supplier


def _authorize(actor, *, manager=False):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Bạn cần đăng nhập bằng tài khoản đang hoạt động.")
    if not (actor.can_manage if manager else actor.can_write):
        raise PermissionDenied("Vai trò của bạn không được thực hiện thao tác này.")


def _editable(document, actor):
    _authorize(actor)
    if document.status != StockDocument.Status.DRAFT:
        raise ValidationError("Chỉ có thể thao tác với chứng từ đang ở trạng thái bản nháp.")
    if not actor.can_manage and document.created_by_id != actor.pk:
        raise PermissionDenied("Nhân viên chỉ được sửa hoặc hủy phiếu nháp do mình tạo.")


def _number(value, *, places, positive=False):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Số lượng hoặc đơn giá không hợp lệ.") from None
    if not number.is_finite() or number < 0 or (positive and number <= 0):
        raise ValidationError("Số lượng phải lớn hơn 0; đơn giá phải không âm.")
    if abs(number) >= Decimal(10) ** (18 - places):
        raise ValidationError("Số lượng hoặc đơn giá vượt giới hạn cho phép.")
    if number.as_tuple().exponent < -places:
        raise ValidationError(f"Giá trị chỉ được có tối đa {places} chữ số thập phân.")
    return number


def _validate_entities(warehouse, supplier, items):
    warehouse = Warehouse.objects.get(pk=warehouse.pk)
    if not warehouse.is_active:
        raise ValidationError("Kho đã được lưu trữ, không thể lập hoặc xác nhận chứng từ.")
    if supplier:
        supplier = Supplier.objects.get(pk=supplier.pk)
        if not supplier.is_active:
            raise ValidationError("Nhà cung cấp đã được lưu trữ.")
    if not items:
        raise ValidationError("Chứng từ phải có ít nhất một sản phẩm.")
    if len(items) > 100:
        raise ValidationError("Mỗi chứng từ được có tối đa 100 sản phẩm.")
    normalized = []
    seen = set()
    for item in items:
        product = Product.objects.select_related("category").get(pk=item["product"].pk)
        if product.pk in seen:
            raise ValidationError(f"SKU {product.sku} xuất hiện nhiều lần. Hãy gộp số lượng vào một dòng.")
        if not product.is_active or not product.category.is_active:
            raise ValidationError(f"Sản phẩm {product.sku} hoặc danh mục đã được lưu trữ.")
        seen.add(product.pk)
        normalized.append({"product": product, "quantity": _number(item["quantity"], places=3, positive=True), "unit_cost": _number(item["unit_cost"], places=2)})
    return warehouse, supplier, normalized


def _snapshot(document):
    return {
        "document_no": document.document_no,
        "type": document.type,
        "warehouse_id": document.warehouse_id,
        "supplier_id": document.supplier_id,
        "status": document.status,
        "notes": document.notes,
        "items": [{"product_id": item.product_id, "quantity": str(item.quantity), "unit_cost": str(item.unit_cost)} for item in document.items.all()],
    }


def _audit(actor, action, document, changes):
    AuditLog.objects.create(actor=actor, action=action, model_name="StockDocument", object_id=str(document.pk), changes=changes)


@transaction.atomic
def create_document(*, actor, type, warehouse, supplier=None, notes="", items):
    _authorize(actor)
    if type not in StockDocument.Type.values:
        raise ValidationError("Loại chứng từ không hợp lệ.")
    warehouse, supplier, items = _validate_entities(warehouse, supplier, items)
    if len(notes) > 5000:
        raise ValidationError("Ghi chú không được dài quá 5.000 ký tự.")
    document = StockDocument.objects.create(type=type, warehouse=warehouse, supplier=supplier, notes=notes, created_by=actor)
    for item in items:
        StockDocumentItem.objects.create(document=document, **item)
    _audit(actor, "CREATE", document, {"after": _snapshot(document)})
    return document


@transaction.atomic
def update_document(document_id, *, actor, warehouse, supplier=None, notes="", items):
    _authorize(actor)
    document = StockDocument.objects.select_for_update().get(pk=document_id)
    _editable(document, actor)
    warehouse, supplier, items = _validate_entities(warehouse, supplier, items)
    if len(notes) > 5000:
        raise ValidationError("Ghi chú không được dài quá 5.000 ký tự.")
    before = _snapshot(document)
    document.warehouse = warehouse
    document.supplier = supplier
    document.notes = notes
    document.save()
    document.items.all().delete()
    for item in items:
        StockDocumentItem.objects.create(document=document, **item)
    _audit(actor, "UPDATE", document, {"before": before, "after": _snapshot(document)})
    return document


@transaction.atomic
def confirm_document(document_id, actor):
    _authorize(actor, manager=True)
    document = StockDocument.objects.select_for_update().get(pk=document_id)
    if document.status != StockDocument.Status.DRAFT:
        raise ValidationError("Chứng từ đã được xử lý. Không thể xác nhận lại hoặc thay đổi tồn lần nữa.")
    warehouse = Warehouse.objects.select_for_update().get(pk=document.warehouse_id)
    raw_items = list(document.items.select_related("product").order_by("product_id"))
    # Lock products in one consistent order before validating activity/unit.
    locked_products = list(Product.objects.select_for_update().filter(pk__in=[item.product_id for item in raw_items]).order_by("pk"))
    list(Category.objects.select_for_update().filter(pk__in={product.category_id for product in locked_products}).order_by("pk"))
    if document.supplier_id:
        Supplier.objects.select_for_update().get(pk=document.supplier_id)
    _validate_entities(warehouse, document.supplier, [{"product": item.product, "quantity": item.quantity, "unit_cost": item.unit_cost} for item in raw_items])
    before = _snapshot(document)
    for item in raw_items:
        balance, _ = StockBalance.objects.get_or_create(warehouse=warehouse, product=item.product)
        balance = StockBalance.objects.select_for_update().get(pk=balance.pk)
        signed_qty = item.quantity if document.type == StockDocument.Type.IN else -item.quantity
        new_quantity = balance.quantity_on_hand + signed_qty
        if new_quantity < 0:
            raise ValidationError(f"Không đủ tồn cho {item.product.sku}: hiện có {balance.quantity_on_hand:g} {item.product.unit}, cần xuất {item.quantity:g}.")
        if new_quantity >= Decimal("1000000000000000"):
            raise ValidationError(f"Tồn kho của {item.product.sku} vượt giới hạn cho phép.")
        balance.quantity_on_hand = new_quantity
        balance.save(update_fields=["quantity_on_hand", "updated_at"])
        StockMovement.objects.create(document=document, product=item.product, warehouse=warehouse, signed_qty=signed_qty, unit_cost=item.unit_cost)
    document.status = StockDocument.Status.CONFIRMED
    document.confirmed_by = actor
    document.confirmed_at = timezone.now()
    document.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])
    _audit(actor, "CONFIRM", document, {"before": before, "after": _snapshot(document)})
    return document


@transaction.atomic
def cancel_document(document_id, actor):
    _authorize(actor)
    document = StockDocument.objects.select_for_update().get(pk=document_id)
    _editable(document, actor)
    before = _snapshot(document)
    document.status = StockDocument.Status.CANCELLED
    document.save(update_fields=["status", "updated_at"])
    _audit(actor, "CANCEL", document, {"before": before, "after": _snapshot(document)})
    return document

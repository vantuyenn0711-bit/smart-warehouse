import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Warehouse(models.Model):
    code = models.CharField("Mã kho", max_length=40, unique=True)
    name = models.CharField("Tên kho", max_length=160)
    address = models.TextField("Địa chỉ", blank=True)
    contact = models.CharField("Người liên hệ / điện thoại", max_length=160, blank=True)
    is_active = models.BooleanField("Đang sử dụng", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code", "pk"]
        verbose_name = "Kho"
        verbose_name_plural = "Kho"
        constraints = [models.UniqueConstraint(Lower("code"), name="warehouse_code_ci_unique")]

    def __str__(self):
        return self.name


class StockDocument(models.Model):
    class Type(models.TextChoices):
        IN = "IN", "Nhập kho"
        OUT = "OUT", "Xuất kho"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Bản nháp"
        CONFIRMED = "CONFIRMED", "Đã xác nhận"
        CANCELLED = "CANCELLED", "Đã hủy"

    document_no = models.CharField("Số chứng từ", max_length=60, unique=True, blank=True)
    type = models.CharField("Loại phiếu", max_length=3, choices=Type.choices, db_index=True)
    warehouse = models.ForeignKey(Warehouse, verbose_name="Kho", on_delete=models.PROTECT, related_name="documents")
    supplier = models.ForeignKey("partners.Supplier", verbose_name="Nhà cung cấp", null=True, blank=True, on_delete=models.PROTECT, related_name="documents")
    status = models.CharField("Trạng thái", max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    notes = models.TextField("Ghi chú", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_documents")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="confirmed_documents")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Chứng từ kho"
        verbose_name_plural = "Chứng từ kho"
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(status="CONFIRMED", confirmed_by__isnull=False, confirmed_at__isnull=False) | (~models.Q(status="CONFIRMED") & models.Q(confirmed_by__isnull=True, confirmed_at__isnull=True))),
                name="document_confirmation_metadata_consistent",
            ),
        ]
        indexes = [models.Index(fields=["warehouse", "status", "created_at"])]

    def save(self, *args, **kwargs):
        if self.pk:
            old_status = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            if old_status and old_status != self.Status.DRAFT:
                raise ValidationError("Chứng từ đã xác nhận hoặc đã hủy không thể chỉnh sửa.")
        if not self.document_no:
            prefix = "PN" if self.type == self.Type.IN else "PX"
            self.document_no = f"{prefix}-{timezone.localdate():%y%m%d}-{uuid.uuid4().hex[:10].upper()}"
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Không xóa chứng từ kho; hãy hủy phiếu nháp để giữ lịch sử.")

    @property
    def total_value(self):
        return sum((item.quantity * item.unit_cost for item in self.items.all()), Decimal("0"))

    @property
    def total_quantity(self):
        return sum((item.quantity for item in self.items.all()), Decimal("0"))

    def __str__(self):
        return self.document_no


class StockDocumentItem(models.Model):
    document = models.ForeignKey(StockDocument, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey("catalog.Product", verbose_name="Sản phẩm", on_delete=models.PROTECT, related_name="document_items")
    quantity = models.DecimalField("Số lượng", max_digits=18, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    unit_cost = models.DecimalField("Đơn giá (₫)", max_digits=18, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["document", "product"], name="document_product_unique"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="document_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_cost__gte=0), name="document_item_cost_nonnegative"),
        ]

    def save(self, *args, **kwargs):
        previous_document_id = type(self).objects.filter(pk=self.pk).values_list("document_id", flat=True).first() if self.pk else None
        document_ids = [self.document_id, previous_document_id]
        if StockDocument.objects.exclude(status=StockDocument.Status.DRAFT).filter(pk__in=[pk for pk in document_ids if pk]).exists():
            raise ValidationError("Không sửa dòng của chứng từ đã khóa.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if StockDocument.objects.exclude(status=StockDocument.Status.DRAFT).filter(pk=self.document_id).exists():
            raise ValidationError("Không xóa dòng của chứng từ đã khóa.")
        return super().delete(*args, **kwargs)

    @property
    def line_total(self):
        return self.quantity * self.unit_cost


class StockBalance(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="balances")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="balances")
    quantity_on_hand = models.DecimalField("Tồn hiện tại", max_digits=18, decimal_places=3, default=Decimal("0"), validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__sku", "warehouse__code"]
        constraints = [
            models.UniqueConstraint(fields=["warehouse", "product"], name="warehouse_product_balance_unique"),
            models.CheckConstraint(condition=models.Q(quantity_on_hand__gte=0), name="stock_quantity_nonnegative"),
        ]

    @property
    def is_low(self):
        return self.quantity_on_hand < self.product.min_stock

    @property
    def estimated_value(self):
        return self.quantity_on_hand * self.product.default_cost


class StockMovement(models.Model):
    document = models.ForeignKey(StockDocument, on_delete=models.PROTECT, related_name="movements")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="movements")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    signed_qty = models.DecimalField(max_digits=18, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["document", "product"], name="movement_document_product_unique"),
            models.CheckConstraint(condition=~models.Q(signed_qty=0), name="movement_quantity_nonzero"),
            models.CheckConstraint(condition=models.Q(unit_cost__gte=0), name="movement_cost_nonnegative"),
        ]
        indexes = [models.Index(fields=["warehouse", "product", "created_at"])]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Lịch sử kho là bất biến, không thể chỉnh sửa.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Lịch sử kho là bất biến, không thể xóa.")

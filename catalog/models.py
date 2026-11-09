from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models.functions import Lower


class Category(models.Model):
    code = models.CharField("Mã danh mục", max_length=40, unique=True)
    name = models.CharField("Tên danh mục", max_length=160)
    is_active = models.BooleanField("Đang sử dụng", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"
        constraints = [models.UniqueConstraint(Lower("code"), name="category_code_ci_unique")]

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField("Mã SKU", max_length=40, unique=True)
    name = models.CharField("Tên sản phẩm", max_length=200, db_index=True)
    category = models.ForeignKey(Category, verbose_name="Danh mục", on_delete=models.PROTECT, related_name="products")
    unit = models.CharField("Đơn vị tính", max_length=24, default="Cái")
    min_stock = models.DecimalField("Tồn tối thiểu", max_digits=18, decimal_places=3, default=Decimal("0"), validators=[MinValueValidator(0)])
    default_cost = models.DecimalField("Giá vốn tham khảo (₫)", max_digits=18, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    is_active = models.BooleanField("Đang sử dụng", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sku", "pk"]
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"
        constraints = [
            models.UniqueConstraint(Lower("sku"), name="product_sku_ci_unique"),
            models.CheckConstraint(condition=models.Q(min_stock__gte=0), name="product_min_stock_nonnegative"),
            models.CheckConstraint(condition=models.Q(default_cost__gte=0), name="product_cost_nonnegative"),
        ]

    def clean(self):
        super().clean()
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.unit != self.unit and self.movements.exists():
                raise ValidationError({"unit": "Không thể đổi đơn vị của SKU đã có giao dịch kho."})

    def save(self, *args, **kwargs):
        # Use the same product lock as confirmation so unit changes cannot race
        # the first stock movement for this SKU.
        with transaction.atomic():
            if self.pk:
                type(self).objects.select_for_update().filter(pk=self.pk).first()
            self.clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sku} · {self.name}"


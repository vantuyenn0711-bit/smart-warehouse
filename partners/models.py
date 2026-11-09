from django.db import models
from django.db.models.functions import Lower


class Supplier(models.Model):
    code = models.CharField("Mã nhà cung cấp", max_length=40, unique=True)
    name = models.CharField("Tên nhà cung cấp", max_length=200)
    phone = models.CharField("Điện thoại", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    address = models.TextField("Địa chỉ", blank=True)
    is_active = models.BooleanField("Đang sử dụng", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "Nhà cung cấp"
        verbose_name_plural = "Nhà cung cấp"
        constraints = [models.UniqueConstraint(Lower("code"), name="supplier_code_ci_unique")]

    def __str__(self):
        return self.name


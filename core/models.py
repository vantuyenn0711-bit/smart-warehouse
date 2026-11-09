from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=40, db_index=True)
    model_name = models.CharField(max_length=80)
    object_id = models.CharField(max_length=64)
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Nhật ký thao tác"
        verbose_name_plural = "Nhật ký thao tác"

    def __str__(self):
        return f"{self.action} · {self.model_name} #{self.object_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Nhật ký thao tác là bất biến, không thể chỉnh sửa.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Nhật ký thao tác là bất biến, không thể xóa.")


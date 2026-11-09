from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Quản trị viên"
        MANAGER = "MANAGER", "Quản lý kho"
        STAFF = "STAFF", "Nhân viên kho"
        VIEWER = "VIEWER", "Người xem báo cáo"

    role = models.CharField("Vai trò", max_length=12, choices=Role.choices, default=Role.VIEWER)

    @property
    def can_manage(self):
        return self.is_active and (self.is_superuser or self.role in (self.Role.ADMIN, self.Role.MANAGER))

    @property
    def can_write(self):
        return self.is_active and (self.can_manage or self.role == self.Role.STAFF)

    @property
    def can_admin(self):
        return self.is_active and (self.is_superuser or self.role == self.Role.ADMIN)


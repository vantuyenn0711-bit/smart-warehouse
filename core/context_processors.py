from django.conf import settings

from core.permissions import has_role


def workspace(request):
    return {
        "can_admin": has_role(request.user, "ADMIN"),
        "can_manage": has_role(request.user, "ADMIN", "MANAGER"),
        "can_write": has_role(request.user, "ADMIN", "MANAGER", "STAFF"),
        "is_demo": settings.DEMO_MODE,
    }

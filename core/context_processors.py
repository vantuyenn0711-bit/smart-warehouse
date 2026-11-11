from django.conf import settings

from core.permissions import has_role


def workspace(request):
    return {
        "can_admin": has_role(request.user, "ADMIN"),
        "can_manage": has_role(request.user, "ADMIN", "MANAGER"),
        "can_write": has_role(request.user, "ADMIN", "MANAGER", "STAFF"),
        "is_demo": settings.DEMO_MODE or getattr(request, "is_public_demo", False),
        "is_public_demo": getattr(request, "is_public_demo", False),
        "public_demo_enabled": settings.PUBLIC_DEMO_ENABLED,
    }

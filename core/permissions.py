from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def has_role(user, *roles):
    return user.is_authenticated and user.is_active and (user.is_superuser or user.role in roles)


def roles_required(*roles):
    def decorate(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not has_role(request.user, *roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorate

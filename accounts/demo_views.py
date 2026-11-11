from django.conf import settings
from django.http import Http404
from django.middleware.csrf import rotate_token
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.demo import DEMO_SESSION_KEY, dataset_ready, private_response


@require_POST
def enter_demo(request):
    if not settings.PUBLIC_DEMO_ENABLED:
        raise Http404
    if not dataset_ready():
        return private_response(render(request, "registration/demo_unavailable.html", status=503))
    # Discard any previous authenticated identity and defeat session fixation.
    request.session.flush()
    rotate_token(request)
    request.session[DEMO_SESSION_KEY] = True
    request.session.set_expiry(3600)
    return private_response(redirect("dashboard"))


@require_POST
def exit_demo(request):
    request.session.flush()
    rotate_token(request)
    return private_response(redirect("login"))

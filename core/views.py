from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from core.models import AuditLog
from core.permissions import roles_required


def paginated(request, queryset, per_page=15):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


@roles_required("ADMIN", "MANAGER")
def audit_list(request):
    logs = AuditLog.objects.select_related("actor").order_by("-created_at", "-pk")
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        logs = logs.filter(Q(action__icontains=q) | Q(model_name__icontains=q) | Q(actor__username__icontains=q))
    page = paginated(request, logs)
    return render(request, "common/audit_list.html", {
        "logs": page, "page_obj": page, "q": q, "nav_active": "audit",
        "page_title": "Nhật ký hệ thống", "page_subtitle": "Truy vết người thực hiện và những thay đổi quan trọng.",
    })


@login_required
def help_page(request):
    return render(request, "common/help.html", {"page_title": "Hướng dẫn sử dụng", "nav_active": "help"})

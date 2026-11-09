from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.forms import UserForm
from accounts.models import User
from core.models import AuditLog
from core.permissions import roles_required
from core.views import paginated


@roles_required("ADMIN")
def user_list(request):
    users = User.objects.order_by("username")
    q = request.GET.get("q", "").strip()
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(email__icontains=q))
    status = request.GET.get("status", "all")
    if status in ("active", "inactive"):
        users = users.filter(is_active=status == "active")
    sort = {"name": "username", "-name": "-username", "-created_at": "-date_joined"}
    users = users.order_by(sort.get(request.GET.get("sort"), "username"), "pk")
    page = paginated(request, users)
    return render(request, "common/list.html", {
        "records": [{"cells": [u.username, u.get_full_name() or "—", u.email or "—", u.get_role_display()],
                     "is_active": u.is_active, "edit_url": reverse("user_edit", args=[u.pk])} for u in page],
        "headers": ["Tên đăng nhập", "Họ tên", "Email", "Vai trò"], "page_obj": page,
        "create_url": reverse("user_create"), "model_label": "Tài khoản", "kind": "user",
        "page_title": "Người dùng & phân quyền", "page_subtitle": "Quản lý quyền truy cập hệ thống.",
        "nav_active": "users", "q": q, "status": status,
    })


@roles_required("ADMIN")
def user_form(request, pk=None):
    obj = get_object_or_404(User, pk=pk) if pk else None
    form = UserForm(request.POST if request.method == "POST" else None, instance=obj)
    if request.method == "POST" and form.is_valid():
        # Serialize account administration so the last administrator stays available.
        with transaction.atomic():
            list(User.objects.select_for_update().filter(Q(role="ADMIN") | Q(is_superuser=True)).order_by("pk"))
            old = User.objects.select_for_update().get(pk=pk) if pk else None
            demoted = not form.cleaned_data["is_active"] or form.cleaned_data["role"] != "ADMIN"
            other_admins = User.objects.filter(is_active=True).filter(Q(role="ADMIN") | Q(is_superuser=True)).exclude(pk=pk)
            if old and old.can_admin and demoted and not other_admins.exists():
                form.add_error(None, "Phải giữ ít nhất một quản trị viên đang hoạt động.")
            elif old and old.pk == request.user.pk and demoted:
                form.add_error(None, "Không thể tự vô hiệu hóa hoặc hạ quyền tài khoản đang sử dụng.")
            elif old and old.is_superuser and (not form.cleaned_data["is_active"] or form.cleaned_data["role"] != old.role):
                form.add_error(None, "Tài khoản superuser được quản lý qua lệnh quản trị an toàn.")
            else:
                try:
                    with transaction.atomic():
                        user = form.save()
                        AuditLog.objects.create(actor=request.user, action="UPDATE" if pk else "CREATE", model_name="User", object_id=str(user.pk), changes={
                            "username": user.username, "role": user.role, "is_active": user.is_active,
                            "password_changed": bool(form.cleaned_data.get("password")),
                        })
                except IntegrityError:
                    form.add_error("username", "Tên đăng nhập vừa được sử dụng. Hãy chọn tên khác.")
                else:
                    if user.pk == request.user.pk and form.cleaned_data.get("password"):
                        update_session_auth_hash(request, user)
                    messages.success(request, "Đã lưu tài khoản.")
                    return redirect("user_list")
    return render(request, "common/form.html", {
        "form": form, "title": "Cập nhật tài khoản" if pk else "Thêm tài khoản",
        "page_title": "Cập nhật tài khoản" if pk else "Thêm tài khoản", "nav_active": "users",
        "back_url": reverse("user_list"), "submit_label": "Lưu tài khoản",
    })

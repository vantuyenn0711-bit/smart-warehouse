import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from catalog.forms import CategoryForm, ImportForm, ProductForm, SupplierForm, WarehouseForm
from catalog.models import Category, Product
from core.models import AuditLog
from core.permissions import has_role, roles_required
from core.views import paginated
from inventory.models import Warehouse
from partners.models import Supplier

ENTITIES = {
    "product": (Product, ProductForm, "Sản phẩm", ["SKU / Mã hàng", "Tên sản phẩm", "Danh mục", "Đơn vị", "Giá vốn tham khảo", "Tồn tối thiểu"]),
    "category": (Category, CategoryForm, "Danh mục", ["Mã danh mục", "Tên danh mục"]),
    "supplier": (Supplier, SupplierForm, "Nhà cung cấp", ["Mã NCC", "Tên nhà cung cấp", "Điện thoại", "Email"]),
    "warehouse": (Warehouse, WarehouseForm, "Kho hàng", ["Mã kho", "Tên kho", "Địa chỉ", "Liên hệ"]),
}


def _query(request, kind):
    model = ENTITIES[kind][0]
    objects = model.objects.all()
    if kind == "product":
        objects = objects.select_related("category")
    q = request.GET.get("q", "").strip()
    if q:
        code = "sku" if kind == "product" else "code"
        objects = objects.filter(Q(**{f"{code}__icontains": q}) | Q(name__icontains=q))
    status = request.GET.get("status", "active")
    if status in ("active", "inactive"):
        objects = objects.filter(is_active=status == "active")
    category = request.GET.get("category", "")
    if kind == "product" and category.isdigit():
        objects = objects.filter(category_id=category)
    sort = request.GET.get("sort", "code")
    allowed = {"code": "sku" if kind == "product" else "code", "name": "name", "-name": "-name", "-code": "-sku" if kind == "product" else "-code", "-created_at": "-created_at"}
    return objects.order_by(allowed.get(sort, allowed["code"]), "pk")


def _cells(obj, kind):
    if kind == "product":
        from core.templatetags.warehouse_tags import money, vn_num
        return [obj.sku, obj.name, obj.category.name, obj.unit, money(obj.default_cost), vn_num(obj.min_stock)]
    if kind == "supplier":
        return [obj.code, obj.name, obj.phone or "—", obj.email or "—"]
    if kind == "warehouse":
        return [obj.code, obj.name, obj.address or "—", obj.contact or "—"]
    return [obj.code, obj.name]


@login_required
def entity_list(request, kind):
    model, _, label, headers = ENTITIES[kind]
    page = paginated(request, _query(request, kind))
    can_manage = has_role(request.user, "ADMIN", "MANAGER")
    records = [{"obj": obj, "cells": _cells(obj, kind), "is_active": obj.is_active,
                "edit_url": reverse(f"{kind}_edit", args=[obj.pk]) if can_manage else ""}
               for obj in page]
    return render(request, "common/list.html", {
        "records": records, "headers": headers, "page_obj": page, "model_label": label,
        "create_url": reverse(f"{kind}_create") if can_manage else "",
        "page_title": label, "page_subtitle": f"Quản lý và tra cứu thông tin {label.lower()} của bạn.",
        "nav_active": kind, "kind": kind, "q": request.GET.get("q", ""),
        "status": request.GET.get("status", "active"), "category": request.GET.get("category", ""),
        "categories": Category.objects.filter(is_active=True) if kind == "product" else [],
        "total_count": model.objects.count(),
    })


def _snapshot(obj):
    return {field.name: str(getattr(obj, field.attname)) for field in obj._meta.fields if field.name not in {"password"}}


@roles_required("ADMIN", "MANAGER")
def entity_form(request, kind, pk=None):
    model, form_class, label, _ = ENTITIES[kind]
    obj = get_object_or_404(model, pk=pk) if pk else None
    form = form_class(request.POST if request.method == "POST" else None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                # Same product/warehouse locks as confirmation protect unit and archival updates.
                old = model.objects.select_for_update().get(pk=pk) if pk else None
                if kind == "product" and old and old.unit != form.cleaned_data["unit"] and old.movements.exists():
                    form.add_error("unit", "Không đổi đơn vị của SKU đã có giao dịch.")
                else:
                    before = _snapshot(old) if old else None
                    saved = form.save()
                    AuditLog.objects.create(actor=request.user, action="UPDATE" if pk else "CREATE",
                                            model_name=model.__name__, object_id=str(saved.pk),
                                            changes={"before": before, "after": _snapshot(saved)})
                    messages.success(request, f"Đã lưu {label.lower()} thành công.")
                    return redirect(f"{kind}_list")
        except IntegrityError:
            form.add_error(None, "Mã đã được sử dụng. Hãy chọn mã khác.")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "common/form.html", {
        "form": form, "title": f"{'Cập nhật' if pk else 'Thêm'} {label.lower()}",
        "page_title": f"{'Cập nhật' if pk else 'Thêm'} {label.lower()}", "nav_active": kind,
        "back_url": reverse(f"{kind}_list"), "submit_label": "Lưu thông tin",
    })


def safe_cell(value):
    # Prevent spreadsheet formula execution for user-controlled text exports.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@login_required
def product_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="san-pham.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["sku", "name", "category", "unit", "default_cost", "min_stock"])
    for obj in _query(request, "product").iterator():
        writer.writerow([safe_cell(value) for value in [obj.sku, obj.name, obj.category.code, obj.unit, obj.default_cost, obj.min_stock]])
    return response


@roles_required("ADMIN", "MANAGER")
def product_import(request):
    form = ImportForm(request.POST if request.method == "POST" else None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            content = form.cleaned_data["file"].read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            expected = {"sku", "name", "category", "unit", "default_cost", "min_stock"}
            if set(reader.fieldnames or []) != expected:
                raise ValidationError("Header không đúng. Dùng file xuất sản phẩm làm mẫu.")
            rows = list(reader)
            if not 1 <= len(rows) <= 500:
                raise ValidationError("File phải chứa từ 1 đến 500 dòng dữ liệu.")
            with transaction.atomic():
                for number, data in enumerate(rows, start=2):
                    category = Category.objects.filter(code__iexact=data.get("category", ""), is_active=True).first()
                    values = dict(data, category=category.pk if category else "", is_active=True)
                    row_form = ProductForm(values)
                    if not row_form.is_valid():
                        detail = "; ".join(f"{field}: {', '.join(errors)}" for field, errors in row_form.errors.items())
                        raise ValidationError(f"Dòng {number}: {detail}. Chưa nhập bất kỳ dòng nào.")
                    product = row_form.save()
                    AuditLog.objects.create(actor=request.user, action="IMPORT", model_name="Product", object_id=str(product.pk), changes={"after": _snapshot(product)})
            messages.success(request, f"Đã nhập {len(rows)} sản phẩm.")
            return redirect("product_list")
        except (UnicodeDecodeError, csv.Error):
            form.add_error("file", "Không đọc được file CSV UTF-8.")
        except (ValidationError, IntegrityError) as exc:
            form.add_error("file", exc if isinstance(exc, ValidationError) else "Có mã SKU trùng. Toàn bộ file đã được hoàn tác.")
    return render(request, "common/import.html", {
        "form": form, "page_title": "Nhập danh sách sản phẩm", "nav_active": "product",
        "back_url": reverse("product_list"),
    })

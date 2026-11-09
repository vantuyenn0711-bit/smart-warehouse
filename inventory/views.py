from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import DecimalField, ExpressionWrapper, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalog.models import Category
from core.permissions import has_role, roles_required
from core.views import paginated
from inventory.forms import DocumentForm, DocumentItemFormSet
from inventory.models import StockBalance, StockDocument, StockMovement, Warehouse
from inventory.services import cancel_document, confirm_document, create_document, update_document


def documents_queryset():
    return StockDocument.objects.select_related("warehouse", "supplier", "created_by", "confirmed_by").prefetch_related("items__product")


@login_required
def document_list(request):
    documents = documents_queryset()
    q = request.GET.get("q", "").strip()
    if q:
        documents = documents.filter(Q(document_no__icontains=q) | Q(notes__icontains=q) | Q(warehouse__name__icontains=q))
    for field, values in (("type", StockDocument.Type.values), ("status", StockDocument.Status.values)):
        value = request.GET.get(field)
        if value in values:
            documents = documents.filter(**{field: value})
    warehouse = request.GET.get("warehouse", "")
    if warehouse.isdigit():
        documents = documents.filter(warehouse_id=warehouse)
    order = {"date": "created_at", "-date": "-created_at", "number": "document_no", "-number": "-document_no"}
    documents = documents.order_by(order.get(request.GET.get("sort"), "-created_at"), "-pk")
    page = paginated(request, documents)
    return render(request, "inventory/document_list.html", {
        "documents": page, "page_obj": page, "q": q,
        "type": request.GET.get("type", ""), "status": request.GET.get("status", ""),
        "warehouses": Warehouse.objects.all(), "warehouse": warehouse,
        "page_title": "Chứng từ kho", "page_subtitle": "Theo dõi mọi lượt nhập, xuất và trạng thái xử lý.",
        "nav_active": "documents",
    })


@roles_required("ADMIN", "MANAGER", "STAFF")
def document_form(request, pk=None):
    document = get_object_or_404(documents_queryset(), pk=pk) if pk else None
    if document:
        if document.status != StockDocument.Status.DRAFT:
            messages.error(request, "Chứng từ đã được xử lý và không thể chỉnh sửa.")
            return redirect("doc_detail", pk=pk)
        if not request.user.can_manage and document.created_by_id != request.user.pk:
            raise PermissionDenied
    doc_type = document.type if document else request.GET.get("type", request.POST.get("type", "IN"))
    if doc_type not in StockDocument.Type.values:
        doc_type = "IN"
    posted = request.POST if request.method == "POST" else None
    form = DocumentForm(posted, instance=document)
    initial = [{"product": item.product_id, "quantity": item.quantity, "unit_cost": item.unit_cost}
               for item in document.items.all()] if document else None
    formset = DocumentItemFormSet(posted, initial=initial, prefix="items")
    if request.method == "POST":
        form_valid, items_valid = form.is_valid(), formset.is_valid()
        if form_valid and items_valid:
            items = [{key: item.cleaned_data[key] for key in ("product", "quantity", "unit_cost")}
                     for item in formset.forms if item.cleaned_data and not item.cleaned_data.get("DELETE")]
            try:
                params = dict(actor=request.user, **form.cleaned_data, items=items)
                saved = update_document(pk, **params) if pk else create_document(type=doc_type, **params)
                messages.success(request, "Đã lưu bản nháp. Tồn kho chỉ thay đổi khi quản lý xác nhận.")
                return redirect("doc_detail", pk=saved.pk)
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(request, "inventory/document_form.html", {
        "form": form, "formset": formset, "document": document, "type": doc_type,
        "page_title": f"{'Cập nhật' if pk else 'Tạo'} phiếu {'nhập' if doc_type == 'IN' else 'xuất'} kho",
        "nav_active": "documents", "back_url": reverse("doc_detail", args=[pk]) if pk else reverse("document_list"),
    })


@login_required
def document_detail(request, pk, printing=False):
    document = get_object_or_404(documents_queryset(), pk=pk)
    editable = document.status == "DRAFT" and has_role(request.user, "ADMIN", "MANAGER", "STAFF") and (request.user.can_manage or document.created_by_id == request.user.pk)
    return render(request, "inventory/document_print.html" if printing else "inventory/document_detail.html", {
        "document": document, "items": document.items.all(), "total": document.total_value,
        "can_edit": editable, "can_cancel": editable,
        "can_confirm": document.status == "DRAFT" and request.user.can_manage,
        "page_title": document.document_no, "nav_active": "documents",
        "page_subtitle": f"{document.get_type_display()} · {document.warehouse.name}",
    })


@roles_required("ADMIN", "MANAGER")
@require_POST
def document_confirm(request, pk):
    get_object_or_404(StockDocument, pk=pk)
    try:
        confirm_document(pk, request.user)
        messages.success(request, "Đã xác nhận chứng từ và cập nhật tồn kho.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("doc_detail", pk=pk)


@roles_required("ADMIN", "MANAGER", "STAFF")
@require_POST
def document_cancel(request, pk):
    get_object_or_404(StockDocument, pk=pk)
    try:
        cancel_document(pk, request.user)
        messages.success(request, "Đã hủy phiếu nháp. Lịch sử vẫn được giữ lại.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("doc_detail", pk=pk)


@login_required
def stock_list(request):
    stocks = StockBalance.objects.select_related("product__category", "warehouse").annotate(
        value=ExpressionWrapper(F("quantity_on_hand") * F("product__default_cost"), output_field=DecimalField(max_digits=36, decimal_places=5)),
    )
    q = request.GET.get("q", "").strip()
    if q:
        stocks = stocks.filter(Q(product__sku__icontains=q) | Q(product__name__icontains=q))
    for key, field in (("warehouse", "warehouse_id"), ("category", "product__category_id")):
        value = request.GET.get(key, "")
        if value.isdigit():
            stocks = stocks.filter(**{field: value})
    if request.GET.get("low") == "1" or request.GET.get("status") == "low":
        stocks = stocks.filter(quantity_on_hand__lt=F("product__min_stock"))
    order = {"sku": "product__sku", "-sku": "-product__sku", "quantity": "quantity_on_hand", "-quantity": "-quantity_on_hand", "value": "value", "-value": "-value"}
    stocks = stocks.order_by(order.get(request.GET.get("sort"), "product__sku"), "warehouse__code")
    page = paginated(request, stocks)
    return render(request, "inventory/stock_list.html", {
        "stocks": page, "page_obj": page, "q": q,
        "warehouses": Warehouse.objects.all(), "categories": Category.objects.all(),
        "warehouse": request.GET.get("warehouse", ""), "category": request.GET.get("category", ""),
        "page_title": "Tồn kho", "page_subtitle": "Số lượng hiện có theo từng sản phẩm và kho.",
        "nav_active": "stock",
    })


@login_required
def movement_list(request):
    movements = StockMovement.objects.select_related("product", "warehouse", "document__confirmed_by")
    q = request.GET.get("q", "").strip()
    if q:
        movements = movements.filter(Q(product__sku__icontains=q) | Q(product__name__icontains=q) | Q(document__document_no__icontains=q))
    warehouse = request.GET.get("warehouse", "")
    if warehouse.isdigit():
        movements = movements.filter(warehouse_id=warehouse)
    if request.GET.get("type") in ("IN", "OUT"):
        movements = movements.filter(document__type=request.GET["type"])
    from reports.forms import filter_form
    dates = filter_form(request.GET)
    valid = dates.is_valid()
    if valid:
        movements = movements.filter(created_at__date__gte=dates.cleaned_data["start"], created_at__date__lte=dates.cleaned_data["end"])
    else:
        movements = movements.none()
    page = paginated(request, movements.order_by("-created_at", "-pk"))
    return render(request, "inventory/movement_list.html", {
        "movements": page, "page_obj": page, "q": q, "warehouses": Warehouse.objects.all(),
        "warehouse": warehouse, "page_title": "Lịch sử biến động", "filter_form": dates,
        "start": dates.data.get("start", ""), "end": dates.data.get("end", ""),
        "page_subtitle": "Nhật ký bất biến của các chứng từ đã xác nhận.", "nav_active": "movements",
    }, status=200 if valid else 400)

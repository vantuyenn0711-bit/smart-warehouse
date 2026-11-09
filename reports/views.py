import csv
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from catalog.models import Category
from catalog.views import safe_cell
from core.views import paginated
from inventory.models import Warehouse
from partners.models import Supplier
from reports.forms import filter_form
from reports.services import dashboard_data, inventory_report


def _filter_context(form):
    return {
        "filter_form": form, "form": form,
        "start": form.data.get("start", ""), "end": form.data.get("end", ""),
        "warehouse": form.data.get("warehouse", ""), "current_warehouse": form.data.get("warehouse", ""),
        "category": form.data.get("category", ""), "supplier": form.data.get("supplier", ""),
        "q": form.data.get("q", ""),
        "warehouses": Warehouse.objects.all(), "categories": Category.objects.all(),
        "suppliers": Supplier.objects.all(),
    }


@login_required
def dashboard(request):
    form = filter_form(request.GET)
    valid = form.is_valid()
    context = {"page_title": "Tổng quan kho hàng", "page_subtitle": "Mọi chuyển động trong kho, trong một góc nhìn.", "nav_active": "dashboard", **_filter_context(form)}
    if valid:
        context.update(dashboard_data(form.cleaned_data))
    return render(request, "dashboard.html", context, status=200 if valid else 400)


@login_required
def report(request):
    form = filter_form(request.GET)
    valid = form.is_valid()
    context = {"page_title": "Báo cáo nhập · xuất · tồn", "page_subtitle": "Đối soát số lượng và giá trị ước tính theo kỳ.", "nav_active": "reports", **_filter_context(form)}
    if valid:
        result = inventory_report(form.cleaned_data)
        page = paginated(request, result["rows"])
        result.update(rows=page, page_obj=page)
        context.update(result)
    return render(request, "reports/report.html", context, status=200 if valid else 400)


@login_required
def report_export(request):
    form = filter_form(request.GET)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    data = form.cleaned_data
    result = inventory_report(data)
    headers = ["SKU", "Tên sản phẩm", "Kho", "Đơn vị", "Tồn đầu kỳ", "Nhập trong kỳ", "Xuất trong kỳ", "Tồn cuối kỳ", "Giá trị tham khảo (₫)"]
    rows = [[safe_cell(row["product"].sku), safe_cell(row["product"].name), safe_cell(row["warehouse"].name), safe_cell(row["product"].unit), row["opening"], row["inbound"], row["outbound"], row["closing"], row["value"]] for row in result["rows"]]
    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="bao-cao-nhap-xuat-ton.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([f"Từ {data['start']} đến {data['end']}"])
        writer.writerow([f"Kho: {data.get('warehouse') or 'Tất cả'}; Danh mục: {data.get('category') or 'Tất cả'}; NCC: {data.get('supplier') or 'Tất cả'}; Tìm kiếm: {data.get('q') or '—'}"])
        writer.writerow(headers)
        writer.writerows(rows)
        return response
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Nhập xuất tồn"
    sheet.append(["SMART WAREHOUSE · BÁO CÁO NHẬP XUẤT TỒN"])
    sheet.append(["Từ ngày", data["start"], "Đến ngày", data["end"]])
    sheet.append(["Kho", safe_cell(str(data.get("warehouse") or "Tất cả")), "Danh mục", safe_cell(str(data.get("category") or "Tất cả"))])
    sheet.append(["Tìm kiếm", safe_cell(data.get("q", "")), "Nhà cung cấp (lọc SKU)", safe_cell(str(data.get("supplier") or "Tất cả"))])
    sheet.append(["Giá trị tham khảo = tồn cuối kỳ × giá vốn tham khảo hiện tại. Không phải định giá kế toán."])
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    last_data_row = sheet.max_row
    sheet.append(["TỔNG", "", "", "", *[result["totals"][key] for key in ("opening", "inbound", "outbound", "closing", "value")]])
    for cell in sheet[6]:
        cell.fill = PatternFill("solid", fgColor="183B52")
        cell.font = Font(color="FFFFFF", bold=True)
    for row in sheet.iter_rows(min_row=7, min_col=5, max_col=9):
        for cell in row:
            cell.number_format = '#,##0.###' if cell.column < 9 else '#,##0.00 "₫"'
    for cell in (sheet["B2"], sheet["D2"]):
        cell.number_format = "dd/mm/yyyy"
    for column in ("A", "C", "D"):
        sheet.column_dimensions[column].width = 22
    sheet.column_dimensions["B"].width = 40
    for column in ("E", "F", "G", "H", "I"):
        sheet.column_dimensions[column].width = 24
    sheet.freeze_panes = "E7"
    sheet.auto_filter.ref = f"A6:I{max(last_data_row, 6)}"
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="bao-cao-nhap-xuat-ton.xlsx"'
    return response


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)

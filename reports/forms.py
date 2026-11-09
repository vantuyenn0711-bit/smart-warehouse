from datetime import timedelta

from django import forms
from django.utils import timezone

from catalog.models import Category
from inventory.models import Warehouse
from partners.models import Supplier


class ReportFilterForm(forms.Form):
    start = forms.DateField(label="Từ ngày", widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(label="Đến ngày", widget=forms.DateInput(attrs={"type": "date"}))
    warehouse = forms.ModelChoiceField(label="Kho", queryset=Warehouse.objects.all(), required=False, empty_label="Tất cả kho")
    category = forms.ModelChoiceField(label="Danh mục", queryset=Category.objects.all(), required=False, empty_label="Tất cả danh mục")
    supplier = forms.ModelChoiceField(label="Nhà cung cấp", queryset=Supplier.objects.all(), required=False, empty_label="Tất cả nhà cung cấp")
    q = forms.CharField(label="Mã / tên sản phẩm", max_length=200, required=False)

    def clean(self):
        data = super().clean()
        start, end = data.get("start"), data.get("end")
        if start and end:
            if start > end:
                self.add_error("end", "Ngày kết thúc phải từ ngày bắt đầu trở đi.")
            elif (end - start).days > 365:
                self.add_error("end", "Chọn khoảng thời gian tối đa 366 ngày.")
        return data


def filter_form(query):
    data = query.copy()
    today = timezone.localdate()
    data.setdefault("start", str(today - timedelta(days=29)))
    data.setdefault("end", str(today))
    return ReportFilterForm(data)

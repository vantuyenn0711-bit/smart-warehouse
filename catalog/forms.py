from django import forms

from catalog.models import Category, Product
from inventory.models import Warehouse
from partners.models import Supplier


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["code", "name", "is_active"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "category", "unit", "default_cost", "min_stock", "is_active"]
        help_texts = {
            "default_cost": "Giá vốn tham khảo dùng ước tính giá trị tồn (₫).",
            "min_stock": "Cảnh báo khi tồn của SKU tại một kho thấp hơn ngưỡng này.",
            "unit": "Mỗi SKU có một đơn vị. Không đổi đơn vị sau khi đã có giao dịch.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        if self.instance.pk and self.instance.movements.exists():
            self.fields["unit"].disabled = True


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["code", "name", "phone", "email", "address", "is_active"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ["code", "name", "address", "contact", "is_active"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


class ImportForm(forms.Form):
    file = forms.FileField(
        label="File CSV sản phẩm",
        help_text="UTF-8; tối đa 1 MB, 500 dòng. Header: sku,name,category,unit,default_cost,min_stock. category là mã danh mục đang hoạt động.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv"}),
    )

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if not upload.name.lower().endswith(".csv") or upload.size > 1024 * 1024:
            raise forms.ValidationError("Chọn file .csv không quá 1 MB.")
        return upload

from decimal import Decimal

from django import forms
from django.forms import BaseFormSet, formset_factory

from catalog.models import Product
from inventory.models import StockDocument, Warehouse
from partners.models import Supplier


class DocumentForm(forms.ModelForm):
    class Meta:
        model = StockDocument
        fields = ["warehouse", "supplier", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3, "maxlength": 5000})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = Warehouse.objects.filter(is_active=True)
        self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True)
        self.fields["notes"].max_length = 5000


class ItemForm(forms.Form):
    product = forms.ModelChoiceField(
        label="Sản phẩm", queryset=Product.objects.filter(is_active=True, category__is_active=True),
    )
    quantity = forms.DecimalField(
        label="Số lượng", max_digits=18, decimal_places=3, min_value=Decimal("0.001"),
        widget=forms.NumberInput(attrs={"step": "0.001", "min": "0.001"}),
    )
    unit_cost = forms.DecimalField(
        label="Đơn giá (₫)", max_digits=18, decimal_places=2, min_value=0, initial=0,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )


class ItemFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        seen = set()
        for form in self.forms:
            data = form.cleaned_data
            if not data or data.get("DELETE"):
                continue
            product = data.get("product")
            if product.pk in seen:
                raise forms.ValidationError("Một SKU chỉ xuất hiện một lần. Hãy gộp số lượng.")
            seen.add(product.pk)


DocumentItemFormSet = formset_factory(
    ItemForm, formset=ItemFormSet, extra=1, can_delete=True,
    min_num=1, validate_min=True, max_num=100, validate_max=True, absolute_max=101,
)

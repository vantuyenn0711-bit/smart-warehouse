from django import forms
from django.contrib.auth import password_validation

from accounts.models import User


class UserForm(forms.ModelForm):
    password = forms.CharField(
        label="Mật khẩu mới", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Bắt buộc khi tạo mới; để trống khi sửa để giữ mật khẩu hiện tại.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "is_active"]

    def clean_password(self):
        value = self.cleaned_data.get("password", "")
        if not self.instance.pk and not value:
            raise forms.ValidationError("Nhập mật khẩu cho tài khoản mới.")
        if value:
            password_validation.validate_password(value, self.instance)
        return value

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import demo_views
from accounts import views as account_views
from catalog import views as catalog_views
from core import views as core_views
from inventory import views as inventory_views
from reports import views as report_views

urlpatterns = [
    path("", report_views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("demo/enter/", demo_views.enter_demo, name="demo_enter"),
    path("demo/exit/", demo_views.exit_demo, name="demo_exit"),
    path("demo/admin-login/", demo_views.exit_demo, name="demo_admin_login"),
    path("health/", report_views.health, name="health"),
    path("products/import/", catalog_views.product_import, name="product_import"),
    path("products/export/", catalog_views.product_export, name="product_export"),
    path("documents/", inventory_views.document_list, name="document_list"),
    path("documents/new/", inventory_views.document_form, name="doc_create"),
    path("documents/<int:pk>/", inventory_views.document_detail, name="doc_detail"),
    path("documents/<int:pk>/edit/", inventory_views.document_form, name="doc_edit"),
    path("documents/<int:pk>/confirm/", inventory_views.document_confirm, name="doc_confirm"),
    path("documents/<int:pk>/cancel/", inventory_views.document_cancel, name="doc_cancel"),
    path("documents/<int:pk>/print/", inventory_views.document_detail, {"printing": True}, name="document_print"),
    path("stock/", inventory_views.stock_list, name="stock_list"),
    path("movements/", inventory_views.movement_list, name="movement_list"),
    path("reports/", report_views.report, name="report"),
    path("reports/export/", report_views.report_export, name="report_export"),
    path("audit/", core_views.audit_list, name="audit_list"),
    path("users/", account_views.user_list, name="user_list"),
    path("users/new/", account_views.user_form, name="user_create"),
    path("users/<int:pk>/edit/", account_views.user_form, name="user_edit"),
    path("help/", core_views.help_page, name="help"),
]

for kind, prefix in (("product", "products"), ("category", "categories"), ("supplier", "suppliers"), ("warehouse", "warehouses")):
    urlpatterns += [
        path(f"{prefix}/", catalog_views.entity_list, {"kind": kind}, name=f"{kind}_list"),
        path(f"{prefix}/new/", catalog_views.entity_form, {"kind": kind}, name=f"{kind}_create"),
        path(f"{prefix}/<int:pk>/edit/", catalog_views.entity_form, {"kind": kind}, name=f"{kind}_edit"),
    ]

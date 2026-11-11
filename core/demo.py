"""Isolated, read-only browsing. Session/auth data always stays in default."""
import re
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, connections, transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import Resolver404, resolve
from django.utils.cache import patch_cache_control, patch_vary_headers

DEMO_SESSION_KEY = "public_demo_v1"
DATASET_VERSION = "smart-warehouse-public-demo-v1"
_mode = ContextVar("warehouse_database_mode", default=None)
READ_ROUTES = frozenset({
    "dashboard", "product_list", "category_list", "supplier_list", "warehouse_list",
    "document_list", "doc_detail", "document_print", "stock_list", "movement_list",
    "report", "report_export", "product_export", "help",
})
CONTROL_ROUTES = frozenset({"demo_enter", "demo_exit", "demo_admin_login"})


def in_public_demo():
    return _mode.get() == "public"


@contextmanager
def demo_bootstrap():
    token = _mode.set("bootstrap")
    try:
        yield
    finally:
        _mode.reset(token)


class DemoRouter:
    def db_for_read(self, model, **hints):
        if _mode.get() in {"public", "bootstrap"} and model._meta.app_label != "sessions":
            return "demo"
        return None

    def db_for_write(self, model, **hints):
        if in_public_demo():
            raise PermissionDenied("Phiên demo chỉ được xem dữ liệu.")
        if _mode.get() == "bootstrap" and model._meta.app_label != "sessions":
            return "demo"
        return None

    def allow_relation(self, first, second, **hints):
        if _mode.get() == "bootstrap":
            return first._state.db in {None, "demo"} and second._state.db in {None, "demo"}
        return None


def demo_transaction(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        with transaction.atomic(using="demo" if in_public_demo() else "default"):
            return view(*args, **kwargs)
    return wrapped


def dataset_ready():
    try:
        with connections["demo"].cursor() as cursor:
            cursor.execute("SELECT version, ready FROM _public_demo_dataset WHERE id = 1")
            return cursor.fetchone() == (DATASET_VERSION, True)
    except DatabaseError:
        return False


def _deny_primary(execute, sql, params, many, context):
    raise PermissionDenied("Phiên demo không được truy cập cơ sở dữ liệu nghiệp vụ.")


def _read_only(execute, sql, params, many, context):
    statement = str(sql).lstrip().upper()
    allowed = ("SELECT ", "SHOW ", "SAVEPOINT ", "RELEASE SAVEPOINT ", "ROLLBACK TO SAVEPOINT ")
    forbidden = re.search(r'\b(?:PUBLIC|PG_CATALOG|INFORMATION_SCHEMA)"?\s*\.', statement)
    unsafe_function = re.search(r"\b(?:SET_CONFIG|DBLINK|PG_READ_FILE|PG_READ_BINARY_FILE)\s*\(", statement)
    if ";" in statement or forbidden or unsafe_function or not statement.startswith(allowed):
        raise PermissionDenied("Phiên demo không được thay đổi dữ liệu.")
    return execute(sql, params, many, context)


@contextmanager
def public_demo_queries():
    token = _mode.set("public")
    try:
        with connections["default"].execute_wrapper(_deny_primary), connections["demo"].execute_wrapper(_read_only):
            yield
    finally:
        _mode.reset(token)


def viewer_principal():
    from accounts.models import User
    # A virtual principal, never authenticated against an administrative account.
    user = User(username="khach_demo", first_name="Khách xem Demo", role=User.Role.VIEWER,
                is_active=True, is_staff=False, is_superuser=False)
    user.set_unusable_password()
    return user


def private_response(response):
    patch_cache_control(response, private=True, no_store=True, no_cache=True, must_revalidate=True)
    patch_vary_headers(response, ("Cookie",))
    return response


class PublicDemoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_public_demo = False
        active = request.session.get(DEMO_SESSION_KEY) is True
        if not active:
            response = self.get_response(request)
            return private_response(response) if request.user.is_authenticated else response
        try:
            route = resolve(request.path_info).url_name
        except Resolver404:
            route = None
        if route in CONTROL_ROUTES:
            return private_response(self.get_response(request))
        if not settings.PUBLIC_DEMO_ENABLED:
            request.session.flush()
            return private_response(HttpResponseForbidden("Chế độ demo đã được tắt."))
        if request.method not in {"GET", "HEAD", "OPTIONS"} or route not in READ_ROUTES:
            return private_response(HttpResponseForbidden("Demo chỉ được xem; thao tác này không được phép."))
        if not dataset_ready():
            return private_response(render(request, "registration/demo_unavailable.html", status=503))
        request.is_public_demo = True
        request.user = viewer_principal()
        request._cached_user = request.user
        request._acached_user = request.user
        with public_demo_queries():
            response = self.get_response(request)
        return private_response(response)

import getpass
import os
import sys
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Category, Product
from core.models import AuditLog
from inventory.models import StockDocument, StockMovement, Warehouse
from inventory.services import confirm_document, create_document
from partners.models import Supplier


class Command(BaseCommand):
    help = "Thêm dữ liệu DEMO an toàn, không xóa dữ liệu và không đổi mật khẩu tài khoản đã có."

    def add_arguments(self, parser):
        parser.add_argument("--if-empty", action="store_true", help="Only bootstrap an empty database when DEMO_MODE is enabled.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("if_empty"):
            if not settings.DEMO_MODE:
                self.stdout.write("Demo bootstrap skipped: DEMO_MODE is disabled.")
                return
            if any(model.objects.exists() for model in (User, Category, Product, Supplier, Warehouse, StockDocument, StockMovement, AuditLog)):
                self.stdout.write("Demo bootstrap skipped: accounts or business data already exist. Existing data was left unchanged.")
                return
        roles = {
            "demo_admin": (User.Role.ADMIN, "Quản trị Demo"),
            "demo_manager": (User.Role.MANAGER, "Nguyễn Minh Anh"),
            "demo_staff": (User.Role.STAFF, "Trần Hải Nam"),
            "demo_viewer": (User.Role.VIEWER, "Lê Thu Hà"),
        }
        needs_password = any(not User.objects.filter(username=username).exists() for username in roles)
        password = os.environ.get("DEMO_PASSWORD", "")
        if needs_password and not password:
            if not sys.stdin.isatty():
                raise CommandError("Hãy đặt DEMO_PASSWORD trong môi trường hoặc chạy lệnh trong terminal tương tác.")
            password = getpass.getpass("Mật khẩu cho các tài khoản demo mới (không hiển thị): ")
        if needs_password and len(password) < 12:
            raise CommandError("DEMO_PASSWORD phải có ít nhất 12 ký tự; không ghi mật khẩu vào mã nguồn.")
        users = {}
        for username, (role, name) in roles.items():
            user, created = User.objects.get_or_create(username=username, defaults={"role": role, "first_name": name})
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
            # Never elevate an existing account or reset a password on reruns.
            users[username] = user
        manager = users["demo_manager"]
        staff = users["demo_staff"]
        if not manager.can_manage or not staff.can_write:
            raise CommandError("Tài khoản demo đã tồn tại với quyền khác; không tự ý nâng quyền. Hãy kiểm tra người dùng.")

        category_rows = [("DEMO-LK", "Linh kiện điện tử"), ("DEMO-VT", "Vật tư sản xuất"), ("DEMO-TB", "Thiết bị & dụng cụ"), ("DEMO-PK", "Đóng gói & phụ kiện")]
        categories = {}
        for code, name in category_rows:
            categories[code], _ = Category.objects.get_or_create(code=code, defaults={"name": name})
        warehouses = []
        for code, name, address, contact in [
            ("DEMO-BN", "Kho Bắc Ninh", "KCN Quế Võ, Bắc Ninh · Khu A1", "Nguyễn Minh Anh · Nội bộ 101"),
            ("DEMO-HP", "Kho Hải Phòng", "KCN Tràng Duệ, Hải Phòng · Khu B2", "Trần Hải Nam · Nội bộ 102"),
        ]:
            warehouse, _ = Warehouse.objects.get_or_create(code=code, defaults={"name": name, "address": address, "contact": contact})
            warehouses.append(warehouse)
        suppliers = []
        for code, name, email, address in [
            ("DEMO-NCC01", "Công ty Linh kiện An Phát", "anphat@example.com", "Bắc Ninh · Dữ liệu demo"),
            ("DEMO-NCC02", "Điện tử Minh Long", "minhlong@example.com", "Hải Phòng · Dữ liệu demo"),
            ("DEMO-NCC03", "Vật tư Công nghiệp Đông Á", "donga@example.com", "Hà Nội · Dữ liệu demo"),
        ]:
            supplier, _ = Supplier.objects.get_or_create(code=code, defaults={"name": name, "email": email, "address": address})
            suppliers.append(supplier)
        product_rows = [
            ("DEMO-LK001", "Vi điều khiển STM32F103C8T6", "DEMO-LK", "Cái", "80", "28500", 1000),
            ("DEMO-LK002", "Cảm biến tiệm cận Omron E2E", "DEMO-LK", "Cái", "60", "185000", 260),
            ("DEMO-LK003", "Điện trở SMD 10kΩ 0603", "DEMO-LK", "Cái", "500", "120", 650),
            ("DEMO-LK004", "Tụ điện gốm 100nF", "DEMO-LK", "Cái", "300", "250", 480),
            ("DEMO-LK005", "Đầu nối JST XH 2P", "DEMO-LK", "Cái", "150", "1800", 720),
            ("DEMO-LK006", "Module Bluetooth HC-05", "DEMO-LK", "Cái", "40", "65000", 190),
            ("DEMO-LK007", "Dây tín hiệu 24AWG", "DEMO-LK", "Mét", "100", "4200", 380),
            ("DEMO-LK008", "Mạch PCB hai lớp 50×70 mm", "DEMO-LK", "Cái", "80", "12500", 310),
            ("DEMO-VT001", "Găng tay chống tĩnh điện ESD", "DEMO-VT", "Đôi", "100", "6500", 420),
            ("DEMO-VT002", "Băng dính chịu nhiệt Kapton", "DEMO-VT", "Cuộn", "30", "32000", 46),
            ("DEMO-VT003", "Thiếc hàn Sn63/Pb37 0.8 mm", "DEMO-VT", "Cuộn", "25", "245000", 110),
            ("DEMO-VT004", "Túi chống tĩnh điện 15×20 cm", "DEMO-VT", "Cái", "300", "850", 1300),
            ("DEMO-TB001", "Trạm hàn Hakko FX-888D", "DEMO-TB", "Bộ", "8", "2850000", 22),
            ("DEMO-TB002", "Đồng hồ đo Fluke 17B+", "DEMO-TB", "Cái", "6", "2150000", 18),
            ("DEMO-TB003", "Máy quét mã Zebra DS2208", "DEMO-TB", "Cái", "5", "1950000", 14),
            ("DEMO-PK001", "Thùng carton 40×30×25 cm", "DEMO-PK", "Cái", "100", "12500", 500),
        ]
        products = []
        opening = []
        for sku, name, category, unit, min_stock, cost, quantity in product_rows:
            product, _ = Product.objects.get_or_create(sku=sku, defaults={"name": name, "category": categories[category], "unit": unit, "min_stock": Decimal(min_stock), "default_cost": Decimal(cost)})
            products.append(product)
            opening.append(Decimal(quantity))

        def seed_document(key, kind, warehouse, lines, days_ago, supplier=None, draft=False):
            document_no = f"DEMO-{key}"
            if StockDocument.objects.filter(document_no=document_no).exists():
                return
            document = create_document(actor=staff, type=kind, warehouse=warehouse, supplier=supplier, notes="DỮ LIỆU DEMO · Chỉ dùng để học tập và trình diễn.", items=[{"product": product, "quantity": quantity, "unit_cost": product.default_cost} for product, quantity in lines])
            document.document_no = document_no
            document.save(update_fields=["document_no"])
            if not draft:
                document = confirm_document(document.pk, manager)
            historical_time = timezone.now() - timedelta(days=days_ago)
            # Only shift this newly generated demo document, never business data.
            timestamp_fields = {"created_at": historical_time, "updated_at": historical_time}
            if not draft:
                timestamp_fields["confirmed_at"] = historical_time
            StockDocument.objects.filter(pk=document.pk).update(**timestamp_fields)
            StockMovement.objects.filter(document=document).update(created_at=historical_time)
            AuditLog.objects.filter(model_name="StockDocument", object_id=str(document.pk)).update(created_at=historical_time)

        for index, warehouse in enumerate(warehouses):
            seed_document(f"OPEN-{index + 1:02}", "IN", warehouse, [(product, quantity if index == 0 else max(Decimal(1), quantity // 3)) for product, quantity in zip(products, opening, strict=True)], 27, suppliers[index])
        for day in range(24, -1, -1):
            warehouse = warehouses[day % 2]
            start = (day * 3) % len(products)
            lines = [(products[(start + offset) % len(products)], Decimal(2 + (day + offset) % 5)) for offset in range(3)]
            kind = "IN" if day % 4 == 0 else "OUT"
            seed_document(f"{kind}-{day:02}", kind, warehouse, lines, day, suppliers[day % 3] if kind == "IN" else None)
        # A visible pending task; draft documents never change stock.
        seed_document("DRAFT-01", "IN", warehouses[0], [(products[0], Decimal("200")), (products[4], Decimal("500"))], 0, suppliers[0], draft=True)
        seed_document("DRAFT-02", "OUT", warehouses[1], [(products[8], Decimal("20"))], 0, draft=True)
        self.stdout.write(self.style.SUCCESS("Đã sẵn sàng dữ liệu DEMO: 16 SKU, 2 kho, lịch sử giao dịch 28 ngày. Lệnh có thể chạy lại và không nhân đôi dữ liệu."))
        self.stdout.write("Tài khoản: demo_admin, demo_manager, demo_staff, demo_viewer. Mật khẩu lấy từ DEMO_PASSWORD khi tạo mới; mật khẩu hiện có được giữ nguyên.")

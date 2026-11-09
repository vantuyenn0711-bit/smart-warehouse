# Smart Warehouse — kết quả nghiệm thu MVP

Kiểm tra ngày **09/11/2026**, múi giờ Việt Nam. Bản bàn giao chạy **Docker local**;
launcher đã build, migrate, seed DB trống và đợi app/PostgreSQL healthy thành công.
**113 test PostgreSQL trong Docker đạt**, cùng 51 kiểm tra HTTP trên cổng 8010.
P2 và production không nằm trong kết luận nghiệm thu này.

Kết quả native 110 test và browser 55/47 checks bên dưới là bằng chứng của lần
chạy trước. Khi mở lại, Windows Application Control chặn DLL của psycopg_binary;
native hiện không khởi động được. Không thay đổi policy: launcher Windows mặc
định dùng Docker, giữ nguyên database native 55433 và tạo volume Docker riêng.

## Chức năng đã kiểm chứng

| Hạng mục | Kết quả / bằng chứng |
| --- | --- |
| Nền tảng | Python 3.13.13 local / 3.13.18 Docker; Django 5.2.19; PostgreSQL 17.11; migrate DB trống thành công ở cả hai môi trường |
| Đăng nhập / quyền | Admin, Manager, Staff, Viewer; backend chặn URL ghi trực tiếp; CSRF, POST; Staff chỉ sửa/hủy nháp của mình |
| Danh mục | Sản phẩm, danh mục, nhà cung cấp, kho: tạo/sửa/lưu trữ, mã không phân biệt hoa thường, validation, tìm/lọc/phân trang/sắp xếp |
| CSV sản phẩm | Giới hạn file/dòng; lỗi một dòng hoàn tác cả file; xuất giữ bộ lọc và chống công thức bảng tính |
| Chứng từ | Nhiều dòng; nháp → xác nhận/hủy; tăng/trừ tồn atomic, lưu actor/thời gian/audit; in chứng từ |
| Toàn vẹn | Chặn vượt tồn/xác nhận lại; đa dòng lỗi rollback; API ứng dụng khóa chứng từ đã xử lý và lịch sử |
| Đồng thời | 4 test service bằng kết nối PostgreSQL riêng và thread barrier; thêm test hai HTTP POST đồng thời; bảo vệ cả dòng StockBalance chưa có |
| Dashboard / báo cáo | Số liệu và biểu đồ từ DB; lọc ngày/kho/danh mục/SKU/NCC; đối soát NXT; top SKU gộp các kho; Excel/CSV giữ bộ lọc |
| UI | 12 màn hình × 375/768/1440; không tràn ngang trang; menu bàn phím, form lỗi, trống/offline/loading; font và JS local |
| Tài khoản / audit | Chỉ Admin quản lý user; giữ ít nhất một Admin hoạt động; không ghi password/hash vào audit |
| Backup / restore | Native đã kiểm chứng trước lỗi policy; Docker hiện đã backup/restore vào DB riêng, đối chiếu 29 chứng từ và 0 số dư âm; không sửa nguồn |
| Docker | Launcher một bước build/migrate/seed DB trống, app/DB healthy; 113 test PostgreSQL và 51 HTTP checks đạt |
| Secret | Kiểm tra cuối 117 file source không có giá trị secret local; .env không có trong image, runtime/backup bị ignore |

## Lệnh thực tế và kết quả cuối

Lệnh chạy từ thư mục dự án; không có password/URL chứa credential trong báo cáo.

| Lệnh | Kết quả |
| --- | --- |
| `uv sync --python .runtime/python-official/python.exe` | Cài dependencies thành công, tạo uv.lock |
| `.venv/Scripts/python.exe scripts/local_postgres.py start` | PostgreSQL riêng tại 127.0.0.1:55433 |
| `manage.py makemigrations accounts catalog partners inventory core` | Tạo migrations ban đầu |
| `manage.py migrate --noinput` | Tất cả migrations OK trên DB local trống |
| `manage.py seed_demo` (2 lần) | Thành công, không nhân đôi/đổi password đã có |
| `manage.py check` | Không lỗi/cảnh báo |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `.venv/Scripts/python.exe -m ruff check .` | All checks passed |
| `.venv/Scripts/python.exe -m pytest -q` (trước lỗi policy) | **110 passed in 12.20s**, DB test PostgreSQL riêng, không skip cạnh tranh |
| `.venv/Scripts/python.exe scripts/start.py --docker` | Launcher thành công: build, DB mới migrate, bootstrap demo, app/DB healthy tại 8010 |
| Launcher chạy lần hai khi app đang mở | Nhận ra đúng Smart Warehouse, trả URL và không tạo thêm container/dữ liệu |
| `docker compose run --rm app python manage.py seed_demo --if-empty` | Bỏ qua vì đã có tài khoản; vẫn 29 chứng từ, không đổi dữ liệu |
| `docker compose run --rm --user root app uv run --frozen --group dev pytest -q` | **112 passed in 7.04s**, PostgreSQL trong Docker, gồm 2 test bootstrap an toàn mới |
| Container test cuối: uv export --frozen --group dev → uv pip install pytest/pytest-django với constraints đã export → python -m pytest -q | **113 passed in 6.32s**, cùng phiên bản lockfile; thêm kiểm tra giữ danh mục có sẵn dù chưa có tài khoản |
| `docker compose exec -T app python manage.py check` | Không lỗi/cảnh báo |
| `docker compose exec -T app python manage.py makemigrations --check --dry-run` | No changes detected |
| `docker compose run --rm -e DJANGO_DEBUG=false app python manage.py check --deploy` | Không lỗi/cảnh báo; không deploy |
| `scripts/http_smoke.py --url http://127.0.0.1:8010` sau launcher Docker | **51** HTTP checks đạt, đủ 4 vai trò và Excel |
| `manage.py collectstatic --noinput` | Thành công, 29 static files cùng biến thể hash/nén |
| `DJANGO_DEBUG=false` + `manage.py check --deploy` | Không lỗi/cảnh báo; chỉ kiểm tra cấu hình, không deploy |
| `scripts/http_smoke.py --url http://127.0.0.1:8010` | **51** authenticated HTTP checks đạt, đủ 4 vai trò và XLSX |
| `scripts/browser_smoke.py` | **55** checks đạt; JS errors `[]`, external requests `[]` |
| `scripts/browser_smoke.py --skip-workflow` | **47** checks bổ sung đạt, ảnh không bị hiệu ứng che biểu đồ, không tạo thêm dữ liệu |
| Node `--check` app.js/charts.js; `npm run build:css` | Thành công; Tailwind biên dịch sẵn, không cần Node khi chạy app |
| `docker --config .runtime/docker-config compose config --quiet` | Compose hợp lệ |
| `docker --config .runtime/docker-config compose --progress plain build` | Image smart-warehouse-app build thành công sau khi sửa source map |
| Compose QA `run --rm app python manage.py migrate --noinput` | Tất cả migrations OK trên PostgreSQL container trống |
| Compose QA `run --rm app python manage.py seed_demo` | Seed thành công trong DB container riêng |
| Compose QA `up -d --wait --wait-timeout 60 app` | App và DB healthy |
| `scripts/http_smoke.py --url http://127.0.0.1:8011` | **51** HTTP checks đạt trên image Docker cuối |
| Compose QA `exec -T app python manage.py check` | Không lỗi/cảnh báo |
| Compose QA `exec -T db psql -U warehouse -d warehouse -tAc 'SHOW server_version'` | PostgreSQL 17.11 Debian |
| `scripts/db_maintenance.py backup --file backups/verification-second.dump` | Thành công; không ghi đè backup |
| `.runtime/verify_backup_restore.py` | Restore/đối chiếu thành công vào warehouse_restore_check_3a9d741a, giữ nguyên nguồn |
| Docker pg_dump → compose cp → createdb mới → pg_restore | Thành công, database phục hồi có 29 chứng từ và 0 số dư âm; nguồn giữ nguyên |
| `.runtime/check_source_secrets.py` (cuối) | 117 file kiểm tra, không phát hiện giá trị secret local |
| `docker compose exec -T app sh -c 'test ! -f /app/.env'` | Thành công, image không chứa file .env |

Các dòng native `manage.py` dùng `.venv/Scripts/python.exe` ở lần kiểm tra ban đầu;
hiện cần dùng Docker như các lệnh mới ở trên. Compose QA
dùng `.runtime/compose.verify.yaml`, `--env-file .env -p smartwarehouse-qa-20261109`,
volume riêng; DB không publish port, app dùng 8011. Compose chính dùng `APP_PORT`
(mặc định 8010), mạng DB nội bộ và volume `smart-warehouse_warehouse_data` riêng.

## Bằng chứng giao diện và nghiệp vụ

- [55 checks đầy đủ](docs/browser-smoke-results.json) và
  [47 checks chỉ xem](docs/browser-smoke-readonly-results.json).
- [Dashboard desktop](docs/screenshots/dashboard-desktop.png),
  [tablet](docs/screenshots/dashboard-tablet.png),
  [mobile](docs/screenshots/dashboard-mobile.png).
- [Sản phẩm](docs/screenshots/products-desktop.png),
  [báo cáo](docs/screenshots/report-desktop.png),
  [form nhiều dòng mobile](docs/screenshots/new-document-mobile.png),
  [phiếu đã xác nhận](docs/screenshots/confirmed-document-desktop.png),
  [trạng thái trống](docs/screenshots/empty-state-desktop.png).

Browser ở lần chạy native tạo SKU DEMO `UI-QA-4CD7D5A8`: nhập ID 59 lượng 1000, xuất ID 60 lượng 600,
nháp ID 61 lượng 401 bị chặn. Tồn **400**, đúng **hai movement**; xác nhận lại
phiếu nhập không sinh movement mới. Báo cáo hiển thị 400, tải Excel thành công.
Các bản ghi QA được giữ trong database native để truy vết; không xóa sau kiểm tra.
Volume Docker mới có bộ demo riêng, không tự sao chép các bản ghi QA này. Bộ 14
ảnh trong docs/screenshots đi cùng bằng chứng browser native đã lưu.

## Lỗi đã phát hiện và sửa

- Windows chặn Python unsigned từ uv: dùng Python chính thức có chữ ký.
- PostgreSQL client đọc sai đường dẫn tiếng Việt: helper kiểm tra/dùng drive ASCII,
  không di chuyển dữ liệu gốc.
- Cổng 8000/55432 có ứng dụng khác: dùng 8010/55433 cho Warehouse local.
- Console Windows cp1252 làm seed lỗi tại thông báo cuối: entry point dùng UTF-8;
  lần lỗi rollback, sau đó seed chạy lại hai lần đạt.
- Source map Chart.js bị thiếu gây collectstatic/build lỗi: bỏ riêng directive map,
  giữ license, collectstatic và Docker build chạy lại thành công.
- Header/nhãn form tràn ngang 375px: sửa co giãn và vùng cuộn bảng; 36 tổ hợp
  màn hình/độ rộng chạy lại đều đạt.
- Smoke quá sớm khi recreate container: đợi health bằng `up --wait`; kiểm tra cuối
  đủ 51 HTTP checks đạt.

Không phát hiện lỗi chặn trong các kịch bản MVP đã chạy bằng Docker. Native vẫn
bị Windows chặn driver; bản bàn giao sử dụng launcher Docker đã kiểm chứng.

## Giới hạn còn lại

- P2 chuyển kho, kiểm kê, barcode/lô, cách ly, API và PDF chuyên dụng chưa triển khai.
  In phiếu dùng chức năng in trình duyệt. Smart Sales/đơn hàng/thanh toán ngoài phạm vi.
- Chưa có FIFO/bình quân; tồn giá trị là ước tính bằng giá vốn tham khảo hiện tại.
  Cảnh báo tồn thấp áp dụng các cặp SKU/kho đã có StockBalance.
- Đã kiểm tra Chrome/Chromium; chưa chứng nhận Safari/Firefox hoặc tải lớn.
- Native hiện bị Windows Application Control chặn psycopg_binary; helper backup
  native cũng bị ảnh hưởng. Dùng Docker, không tắt hoặc sửa policy của Windows.
- Cài sạch được kiểm chứng bằng Docker image và DB container trống; chưa cài toàn
  bộ Docker Desktop trên một máy vật lý mới.
- Local DEBUG bật; DEBUG=false qua deploy checks nhưng chưa triển khai production,
  kiểm tra TLS/proxy, backup tự động hay vận hành 24/7.
- Không push Git, deploy hosting, tích hợp thanh toán, dùng dữ liệu thật hoặc tạo
  dịch vụ trả phí. DB/volume/backup kiểm thử được giữ, không reset/xóa dữ liệu.

Mở lại bằng `start.cmd` hoặc `.venv/Scripts/python.exe scripts/start.py --docker`;
hướng dẫn trong README.md. start.cmd mở trình duyệt mặc định khi người dùng chạy.
PowerShell execution policy chặn .ps1; launcher không thay đổi policy. Ảnh và JSON là chứng cứ
giao diện; pytest PostgreSQL là chứng cứ nghiệp vụ/khóa.

Sau nghiệm thu, container app/DB của hai project Warehouse đã được dừng sạch.
Volume `smart-warehouse_warehouse_data`, database native và các backup được giữ
nguyên. Chạy start.cmd để mở lại; không cần tạo lại dữ liệu.

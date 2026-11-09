PROJECT BLUEPRINT   /   PYTHON • DJANGO • POSTGRESQL

HỒ SƠ DỰ ÁN SỐ 01

SMART WAREHOUSE

ĐẶC TẢ V2 ĐÃ RÀ SOÁT • Website quản lý kho bằng Python/Django • Dùng để giao ChatGPT triển khai từng giai đoạn • Kèm quy trình tự động cho Codex

MỤC TIÊU

Xây dựng phần mềm quản lý kho cho doanh nghiệp nhỏ với nhập – xuất – chuyển – kiểm kê – tồn kho – báo cáo. Dự án đặc biệt phù hợp để giới thiệu khả năng quản lý dữ liệu, quy trình vật tư và truy xuất lịch sử khi xin thực tập PE/IT MES.

Thông tin

Nội dung

Sản phẩm

Ứng dụng web nội bộ với dashboard, đăng nhập, phân quyền và cơ sở dữ liệu thật.

Đối tượng

Admin, quản lý kho, nhân viên kho, người xem báo cáo.

Phạm vi MVP

Sản phẩm, danh mục, kho, nhà cung cấp, chứng từ nhập/xuất, tồn kho, báo cáo, kiểm thử.

Mở rộng P2

Chuyển kho, kiểm kê, barcode, theo dõi lô, kho cách ly/hàng lỗi, API tích hợp.

Nguyên tắc

Hệ thống phải chạy thật và giải thích được; tính năng mở rộng chỉ làm sau MVP ổn định.

1. Nền tảng kỹ thuật và cấu trúc dự án

Hạng mục

Lựa chọn

Ngôn ngữ và backend

Python 3.13 + Django 5.2 LTS; dùng Django ORM và hệ thống migrations.

Cơ sở dữ liệu

PostgreSQL; dùng Decimal cho tiền, khóa ngoại và index cho trường tìm kiếm.

Frontend

Django Templates + Tailwind CSS + HTMX + JavaScript; Chart.js cho biểu đồ.

Báo cáo

openpyxl cho Excel; thư viện PDF phù hợp khi hoàn thành chức năng cốt lõi.

Kiểm thử

pytest + pytest-django; tích hợp test nghiệp vụ, quyền và các trường hợp lỗi.

Phát triển / triển khai

Git, Docker Compose, .env.example, README; chạy local trước, triển khai sau.

Chọn kiến trúc Django nguyên khối (monolith) để học và triển khai nhanh, giảm độ phức tạp so với tách frontend/backend ngay từ đầu. Không dùng Django Admin làm giao diện nghiệp vụ chính.

NGUYÊN TẮC THỰC HIỆN

Không sử dụng dữ liệu giả để giả mạo chức năng đã chạy. Dữ liệu mẫu phải được tạo trong database; dashboard, bảng và báo cáo đều truy xuất dữ liệu thật.

Cấu trúc Django đề xuất

smart_warehouse/
  config/              # settings, urls, wsgi/asgi
  accounts/            # users, roles, authentication
  catalog/             # product, category, unit
  partners/            # supplier
  inventory/           # warehouse, movements, documents, stock
  reports/             # dashboard, Excel/PDF exports
  core/                # common utilities, audit, permissions
  templates/  static/  tests/
  compose.yaml  Dockerfile  .env.example  README.md

Phân quyền và nhật ký thao tác

Vai trò

Quyền điển hình

Admin

Quản lý người dùng, quyền, cấu hình, xem toàn bộ báo cáo.

Manager

Duyệt chứng từ, duyệt kiểm kê, xem báo cáo, không quản lý hệ thống.

Staff

Tạo phiếu nháp, xem tồn và thực hiện thao tác được giao.

Viewer

Chỉ xem dữ liệu được phép, không tạo hoặc xác nhận chứng từ.

Kiểm tra quyền tại backend cho mọi request; không dùng việc ẩn nút giao diện để thay cho phân quyền.

Ghi nhật ký tối thiểu: người thao tác, thời điểm, loại hành động, đối tượng, dữ liệu thay đổi quan trọng.

2. Danh mục chức năng / màn hình

Module

Màn hình / chức năng

Ưu tiên

Dashboard

Tổng SKU, mặt hàng tồn thấp, tổng giá trị tồn, nhập/xuất theo thời gian, hoạt động mới.

MVP

Sản phẩm

SKU duy nhất; tên, danh mục, đơn vị, giá vốn, tồn tối thiểu; tìm/lọc/import/export.

MVP

Danh mục & nhà cung cấp

Tạo/cập nhật/lưu trữ thông tin; tra cứu theo mã và tên.

MVP

Kho

Danh sách kho và thông tin liên hệ/vị trí; trạng thái sử dụng.

MVP

Nhập kho

Phiếu nháp → xác nhận; tăng tồn một lần; lưu người thao tác, thời điểm.

MVP

Xuất kho

Phiếu nháp → xác nhận; chặn xuất vượt tồn khả dụng; xuất phiếu.

MVP

Tồn kho & lịch sử

Tồn theo SKU/kho, toàn bộ biến động, cảnh báo dưới ngưỡng.

MVP

Báo cáo

Nhập – xuất – tồn, top hàng di chuyển, tồn thấp, giá trị tồn; xuất Excel/CSV.

MVP

Chuyển kho

Điều chuyển giữa hai kho; cập nhật nguyên tử; không tăng tổng tồn.

P2

Kiểm kê

Ghi tồn đếm thực tế, chênh lệch, lý do, duyệt điều chỉnh.

P2

Barcode / lô hàng

Tìm kiếm/quét mã, theo dõi mã lô và lịch sử (truy xuất nguồn gốc).

P2

Quy chuẩn UI/UX

Thanh menu trái và header; giao diện tiếng Việt, bố cục rõ ràng, màu xanh navy – trắng – xám, hỗ trợ mobile.

Bảng dữ liệu có tìm kiếm, lọc, phân trang, sắp xếp; trạng thái hiển thị bằng nhãn dễ phân biệt.

Form có hướng dẫn, thông báo lỗi theo từng trường, xác nhận khi thao tác ảnh hưởng dữ liệu.

Dashboard có số liệu thực và biểu đồ lọc theo thời gian, không dùng biểu đồ trang trí cố định.

Hiệu ứng vừa phải; ưu tiên tốc độ tải, dễ sử dụng và khả năng truy cập bằng bàn phím.

3. Thiết kế database (bản đầu tiên)

Bảng / Model

Trường trọng tâm và ghi chú

User / Role

Thông tin đăng nhập, vai trò, trạng thái, created_at.

Category

id, code, name, is_active; không xóa nếu còn dữ liệu tham chiếu.

Product

sku (unique), name, category_id, unit, min_stock, default_cost, is_active.

Supplier

code (unique), name, phone, email, address, is_active.

Warehouse

code, name, address, is_active; mã kho unique.

StockDocument

document_no, type (IN/OUT/TRANSFER/ADJUST), warehouse, supplier?, status, created_by, confirmed_by, timestamps.

StockDocumentItem

document_id, product_id, quantity, unit_cost; quantity > 0.

StockBalance

warehouse_id + product_id unique, quantity_on_hand; row lock khi cập nhật.

StockMovement

document_id, product_id, warehouse_id, signed_qty, unit_cost, created_at; không sửa lịch sử.

StockCount / Item [P2]

Đợt kiểm kê, tồn hệ thống, tồn đếm, chênh lệch, trạng thái duyệt.

AuditLog

actor, action, model_name, object_id, changes, created_at.

Ràng buộc: mã sản phẩm/mã kho/mã nhà cung cấp là duy nhất; không dùng float cho tiền; các quan hệ được bảo vệ phù hợp; tạo index theo mã, trạng thái, ngày chứng từ và (warehouse, product).

4. Quy trình nghiệp vụ cốt lõi

4.1 Nhập kho

Tạo phiếu nhập nháp, chọn kho, nhà cung cấp, sản phẩm, số lượng (>0) và đơn giá (>=0).

Manager xác nhận: kiểm tra trạng thái, khóa bản ghi phù hợp, tạo StockMovement và cộng StockBalance trong transaction.atomic().

Đánh dấu đã xác nhận, ghi người/thời điểm; xác nhận lặp lại không được cộng tồn lần thứ hai.

Phiếu đã xác nhận không chỉnh/xóa trực tiếp; thay đổi phải bằng nghiệp vụ điều chỉnh hoặc chứng từ đảo phù hợp.

4.2 Xuất kho

Nhân viên tạo phiếu nháp, chọn kho và sản phẩm, số lượng cần xuất.

Khi xác nhận, kiểm tra tồn khả dụng dưới khóa dữ liệu; nếu thiếu thì từ chối và giải thích rõ.

Trừ tồn đúng một lần, tạo bản ghi biến động âm và lưu nhật ký; không cho trạng thái mâu thuẫn.

4.3 Chuyển kho / kiểm kê (giai đoạn mở rộng)

Chuyển kho: trừ nguồn và cộng đích nguyên tử, ngăn cùng kho nguồn/đích; giữ tổng tồn toàn hệ thống không đổi.

Kiểm kê: lưu số lượng đếm, chênh lệch và lý do; chỉ khi quản lý duyệt mới sinh chứng từ điều chỉnh tồn.

4.4 Công thức và định nghĩa số liệu

Chỉ số

Cách tính/diễn giải

Tồn hiện tại

Tổng số lượng đầu kỳ + nhập đã xác nhận – xuất đã xác nhận ± điều chỉnh/chuyển hợp lệ.

Cảnh báo tồn thấp

StockBalance.quantity_on_hand < Product.min_stock (từng kho theo cấu hình).

Giá trị tồn

Số lượng tồn × giá vốn theo quy tắc nhất quán được lựa chọn và ghi rõ; MVP có thể dùng giá vốn tham khảo.

Nhập/xuất trong kỳ

Tổng các dòng StockMovement đã xác nhận trong khoảng thời gian được chọn.

5. Trang báo cáo và tình huống demo

Bộ lọc theo ngày bắt đầu/kết thúc, kho, danh mục, mã hàng và nhà cung cấp khi phù hợp.

Biểu đồ cột nhập/xuất theo thời gian; biểu đồ hàng tồn thấp; bảng lịch sử di chuyển theo sản phẩm.

Xuất Excel lưu các bộ lọc đang chọn; cột số lượng, giá trị và thời gian có định dạng rõ.

Dữ liệu demo: nhập 1.000 linh kiện, xuất 600, kiểm kê đếm 395 thay vì 400, duyệt điều chỉnh chênh lệch 5 (sau khi hoàn thành module kiểm kê).

Bảo mật, vận hành và chất lượng

Mật khẩu được lưu theo cơ chế hash của Django; có CSRF, session an toàn, xác thực và ủy quyền theo quyền.

Tất cả secret lấy từ biến môi trường; không commit .env thật, khóa bí mật, dữ liệu khách hàng lên GitHub.

Validate dữ liệu cả phía trình duyệt và server; chống nhập số âm, giá trị vượt giới hạn và dữ liệu trùng.

Dùng transaction.atomic(), điều kiện trạng thái và row lock phù hợp trong các nghiệp vụ cập nhật tồn kho/tiền.

Có trang lỗi 403/404/500 và logging phù hợp; không lộ stack trace trên môi trường production.

Viết unit/integration tests cho các nghiệp vụ rủi ro, kiểm tra quyền, dữ liệu sai và tình huống đồng thời.

Tối ưu truy vấn bằng select_related/prefetch_related, phân trang và index, tránh N+1 query khi hiển thị bảng.

Docker Compose cho app + PostgreSQL; chuẩn bị backup/restore, migrations và dữ liệu demo qua management command.

6. Ma trận kiểm thử bắt buộc

Kịch bản

Kết quả mong đợi

Nhập 20; xuất 5

Tồn từ 0 lên 20 rồi về 15; có đủ chứng từ và movement.

Xuất 16 khi tồn 15

Bị chặn; tồn và lịch sử không thay đổi.

Xác nhận phiếu nhập lần hai

Không cộng tồn trùng; trả lỗi trạng thái phù hợp.

Hai người đồng thời xuất cùng SKU

Không thể làm tồn âm; transaction/locking bảo toàn dữ liệu.

Viewer gọi URL xác nhận

Bị từ chối 403; database không thay đổi.

Chuyển 7 giữa kho A/B [P2]

A giảm 7, B tăng 7, tổng tồn giữ nguyên.

Báo cáo tồn và lịch sử

Số liệu thống nhất với các giao dịch được xác nhận.

7. Kế hoạch triển khai theo giai đoạn

Giai đoạn

Công việc / đầu ra

Hoàn thành khi

0 – Chuẩn bị

Thiết kế UI mẫu, ERD, Django project, Postgres, Docker, auth, roles.

Chạy local, đăng nhập và migration thành công.

1 – Danh mục

Kho, sản phẩm, danh mục, nhà cung cấp, CRUD, lọc.

Form validate; test tạo/sửa/xem và quyền.

2 – Nghiệp vụ kho

Phiếu nhập/xuất, tồn, lịch sử, khóa khi xác nhận.

Test quy tắc tồn, xác nhận trùng, cạnh tranh.

3 – Báo cáo

Dashboard, tìm kiếm, thống kê, Excel.

Số liệu giao dịch và báo cáo khớp.

4 – Hoàn thiện

UI responsive, test, README, demo data, triển khai.

Chạy theo README và có demo đầu-cuối.

5 – Mở rộng

Chuyển kho, kiểm kê, barcode, lot trace.

Mỗi tính năng có test và giao diện hoạt động.

Tiêu chí nghiệm thu và sản phẩm bàn giao

Có mã nguồn chạy được và cấu trúc thư mục Django rõ ràng; không chỉ có ảnh chụp màn hình.

Cài đặt từ đầu theo README thành công; migration chạy trên PostgreSQL trống, tạo dữ liệu demo bằng một lệnh.

Luồng nghiệp vụ cốt lõi hoạt động trọn vẹn từ giao diện đến database, có kiểm tra quyền và xử lý lỗi.

Có test tự động cho các quy tắc dữ liệu quan trọng; README ghi chính xác những test đã chạy.

Dashboard và báo cáo phản ánh cùng dữ liệu với chứng từ nguồn; không có số liệu giả cố định.

Có ảnh chụp các màn hình chính, sơ đồ ERD, hướng dẫn sử dụng, danh sách chức năng đã/đang/chưa hoàn thành.

Có Docker Compose, .env.example, .gitignore, tài khoản demo được tạo an toàn (không ghi mật khẩu thật lên repo).

Không dùng bất kỳ tích hợp thanh toán/ngân hàng hay dữ liệu nhạy cảm thật nếu chưa triển khai bảo mật phù hợp.

8. Câu lệnh khởi đầu cho Codex (bản ngắn)

HƯỚNG DẪN SỬ DỤNG

Sao chép phần dưới và gửi kèm file Word này sang cuộc trò chuyện lập trình. ChatGPT cần bắt đầu với thiết kế và module nền tảng, không cố đổ toàn bộ source code trong một lần.

CODEX — HÃY XÂY DỰNG WEBSITE THEO TOÀN BỘ ĐẶC TẢ NÀY.
Mở SPEC.md và AGENTS.md trong thư mục dự án. Nếu chưa có repository, tạo Django project từ đầu. Viết PLAN.md với các milestone nhỏ có tiêu chí hoàn thành; sau đó trực tiếp tạo và sửa source code, migrations, Docker Compose, giao diện, dữ liệu demo và tài liệu.
Sau mỗi milestone hãy chạy lint, Django checks, pytest và smoke test; nếu có công cụ browser, kiểm tra desktop/mobile. Tự sửa lỗi rồi chạy test lại; tiếp tục milestone kế tiếp nếu đã đạt. Ghi bằng chứng kết quả vào IMPLEMENTATION_STATUS.md. Chỉ báo hoàn thành khi toàn bộ mục MUST-HAVE được kiểm chứng.
Không tự push, deploy production, xóa dữ liệu ngoài repository, phát sinh chi phí hoặc sử dụng secrets không được cấp phép. Nếu bị chặn vì quyền, môi trường hoặc tài khoản, báo rõ blocker.
Bản prompt vận hành đầy đủ ở START_CODEX_PROMPT.txt trong bộ file ZIP.

9. Rà soát V2: các tiêu chí chất lượng không thể bỏ qua

9.1. Chuẩn giao diện “cao cấp nhưng dễ sử dụng”

Trang điều khiển, danh sách, form, chi tiết và báo cáo dùng cùng hệ thống màu, typography, khoảng cách và trạng thái. Giao diện tiếng Việt rõ ràng, không lạm dụng hiệu ứng.

Thử tối thiểu các độ rộng 375 px, 768 px và 1440 px; không vỡ layout, không cuộn ngang vô lý; bảng dài có chiến lược hiển thị trên mobile.

Mọi màn hình phải có trạng thái loading, dữ liệu trống, lỗi kết nối và thao tác thành công; form chỉ rõ trường bị lỗi; kiểm tra focus bàn phím, tương phản và nhãn nhập liệu.

Không dùng bảng số liệu, biểu đồ, hoạt động “gần đây” giả trong bản thật; dữ liệu demo phải được đánh dấu demo.

9.2. Chuẩn mã nguồn, vận hành và an toàn

Tách nghiệp vụ vào service layer; views mỏng; ràng buộc database; migrations có thể chạy từ database trống. Không viết logic trừ tồn/tính tiền phân tán ở nhiều view.

Tạo trang lỗi 403/404/500, log có ngữ cảnh nhưng không lộ mật khẩu/token, cấu hình production tắt DEBUG; giới hạn upload loại file và dung lượng nếu có ảnh.

Thiết lập kiểm tra tự động: ruff, pytest/pytest-django, Django system checks, smoke test qua HTTP, kiểm thử luồng chính bằng trình duyệt nếu công cụ sẵn có.

README có cách cài trên máy mới, lệnh chạy, file .env.example, migrations, seed data, tạo tài khoản demo và cách chạy test; Docker Compose chỉ dùng dịch vụ cần thiết.

Đối với mọi nâng cấp vượt MVP: giữ phạm vi rõ ràng, không làm hỏng nghiệp vụ đã hoạt động; ưu tiên hiệu năng, tính nhất quán dữ liệu và khả năng trình diễn trước hiệu ứng.

9.3. Chứng cứ trước khi báo “hoàn tất”

Codex phải thực sự chạy các lệnh khi môi trường hỗ trợ, lưu lại lệnh và kết quả vào IMPLEMENTATION_STATUS.md; không tự nhận “pass” khi chưa kiểm thử.

Có màn hình chụp/smoke test của luồng quan trọng, danh sách lỗi còn tồn tại, đường dẫn và bước demo; chụp màn hình là minh chứng, không thay thế test backend.

Có bản tự đánh giá dựa trên checklist chức năng, đúng dữ liệu, phân quyền, UI/UX, test và tài liệu. Chỉ tuyên bố hoàn thành khi tất cả mục bắt buộc thực sự đạt.

10. Bổ sung riêng cho Smart Warehouse

Đối với điều chuyển kho: document hoặc model phải có cả source_warehouse và destination_warehouse, không dùng trường “warehouse” duy nhất cho hai chiều.

Nếu hai yêu cầu xuất kho đồng thời và dòng StockBalance chưa tồn tại, phải khởi tạo/khóa bản ghi an toàn bằng unique constraint + xử lý tranh chấp; không chỉ khóa những dòng đã có.

Một chứng từ đã xác nhận không được xác nhận lại, kể cả người dùng bấm đôi hoặc gửi HTTP request lặp; dùng state guard và idempotency nếu cần.

Nhập/xuất theo đơn vị đo thống nhất; nếu chưa xây dựng quy đổi đơn vị thì giới hạn mỗi SKU một đơn vị và nói rõ phạm vi.

Tồn giá trị = số lượng × giá vốn tham khảo ở MVP chỉ là giá trị ước tính; không gọi là định giá kế toán chuẩn nếu chưa xây FIFO/giá bình quân và kiểm thử.

P2: kiểm kê và hàng lỗi/cách ly theo lô phải có lý do, người duyệt và lịch sử; không ghi đè nhật ký gốc.

10.1. Demo nghiệm thu bắt buộc

1. Đăng nhập Manager, Staff và Viewer; kiểm tra quyền truy cập màn hình và endpoint.

2. Tạo SKU mới, kho A, nhà cung cấp; nhập 1.000 đơn vị bằng phiếu đã xác nhận.

3. Xuất 600 đơn vị, xem tồn 400 và lịch sử gồm hai biến động.

4. Thử xuất 401 đơn vị bị chặn, tồn vẫn giữ 400.

5. Thử xác nhận lại phiếu nhập/xuất đã hoàn thành; không phát sinh biến động trùng.

6. Xem dashboard/báo cáo nhận đúng số liệu và xuất Excel thành công.

7. Nếu triển khai kiểm kê P2: đếm 395, quản lý duyệt điều chỉnh −5, tồn còn 395 và có đầy đủ nhật ký.

11. Bảng kiểm nghiệm thu bắt buộc (Release Gate)

Codex chỉ đánh dấu từng hàng ĐẠT sau khi có bằng chứng kiểm tra được lưu trong IMPLEMENTATION_STATUS.md. Tính năng P2 là mở rộng, không được giả mạo thành đã hoàn tất ở bản MVP.

TIÊU CHÍ

ĐIỀU KIỆN ĐẠT

Môi trường

Cài dependencies và Docker Compose trên máy mới; migrate database PostgreSQL trống thành công.

Đăng nhập / quyền

Admin, Manager, Staff, Viewer chỉ thao tác đúng quyền; URL gọi thẳng vẫn bị chặn.

Dữ liệu thật

Mọi dashboard, bảng và báo cáo đều truy vấn DB; không có số liệu hiển thị giả dạng kết quả thật.

Nghiệp vụ

Tất cả luồng MVP chạy end-to-end; trường hợp lỗi không làm dữ liệu sai/nhân đôi.

Đồng thời

Thử hai request cùng thay đổi tồn và giao dịch lặp; số lượng không âm và không ghi nhận trùng.

Giao diện

Responsive 375/768/1440; có trạng thái trống/loading/lỗi; biểu mẫu có thông báo rõ.

Tests

pytest và Django checks chạy thật không có lỗi chặn; lint đạt; test cho logic rủi ro.

Tài liệu

README, .env.example, migrations, seed demo, kế hoạch, báo cáo tiến độ và bước demo có thật.

An toàn

Không lộ secret, không dùng dữ liệu thật; không chạy production/deploy/push khi chưa được phép.

12. Runbook Codex: tự làm, tự kiểm thử, tự sửa

Dùng Codex trong thư mục repository có SPEC.md và AGENTS.md. Tài liệu Word giúp người đọc; SPEC.md là bản văn bản thuận tiện cho Codex tra cứu.

Tạo PLAN.md (milestone và tiêu chí pass), DECISIONS.md (giả định chính), IMPLEMENTATION_STATUS.md (lệnh thực sự đã chạy, kết quả, blocker). Sau mỗi milestone chạy test và chỉ tiếp tục khi đạt.

Bảo đảm có tài liệu setup máy sạch; không dừng ở mức “đã viết mã” nếu môi trường cho phép chạy dự án. Không được báo hoàn thành khi test còn đỏ hoặc chức năng vẫn chỉ là UI giả.

Tính năng tự tiếp tục trong Codex có giới hạn phiên, ngân sách, quyền truy cập và các điều kiện phải xin duyệt. Mọi yêu cầu xóa dữ liệu, dịch vụ trả phí, secrets, push hoặc production deployment cần người dùng phê duyệt.

Tài liệu tham khảo: OpenAI Codex CLI; OpenAI Cookbook “Iterating Development Workflows with Codex”; “Using Goals in Codex”.


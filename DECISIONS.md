# Quyết định triển khai

- Django monolith ở thư mục gốc để lệnh `manage.py` dễ chạy trên Windows/Linux.
- PostgreSQL là database duy nhất; không dùng SQLite để thay bằng chứng row lock.
- Mỗi SKU có một đơn vị; lượng Decimal(18,3), tiền Decimal(18,2).
- Giá trị tồn = lượng hiện tại × giá vốn tham khảo; là ước tính, chưa phải FIFO
  hoặc định giá kế toán. Số nhập/xuất là lượng trong kỳ, không cộng tiền với lượng.
- Xác nhận phiếu khóa chứng từ và kho. Khóa hàng Warehouse hiện hữu serialize
  cập nhật cùng kho, bảo vệ cả trường hợp chưa có StockBalance; đổi lại throughput
  mỗi kho thấp hơn khóa theo SKU. Mọi biến động đi qua cùng service.
- Viewer chỉ đọc; Staff tạo/sửa/hủy phiếu nháp của mình; Manager/Admin duyệt và
  quản lý danh mục; chỉ Admin quản lý tài khoản. Không xóa dữ liệu nghiệp vụ.
- Phiếu đã xác nhận không sửa/hủy; không làm UI giả cho điều chỉnh/P2 chưa hỗ trợ.
- Dữ liệu seed là dữ liệu demo có nhãn, được ghi DB qua service giống giao dịch.
- Ngưỡng tồn thấp áp dụng cho các cặp SKU/kho đã phát sinh số dư (StockBalance).
  SKU mới chưa được nhập vào kho chưa có dòng tồn tại kho đó. Không tự gán mọi
  sản phẩm vào mọi kho hoặc giả lập số dư từ giao diện.
- Bộ lọc nhà cung cấp của báo cáo chọn các SKU từng nhận từ NCC đó rồi tính mọi
  biến động của chúng, để không bỏ sót phiếu xuất và làm sai số tồn cuối kỳ.
- Local-only theo SPEC; không đăng ký hosting, push Git hoặc khởi tạo dịch vụ phí.
- Cập nhật khi bàn giao: Windows Application Control chặn psycopg_binary native.
  Windows launcher mặc định chạy Docker local, không sửa policy. Native vẫn giữ
  nguyên ở .runtime/pgdata (55433); Docker dùng volume riêng và không tự sao chép
  dữ liệu. seed_demo --if-empty chỉ bootstrap khi DEMO_MODE bật và chưa có tài
  khoản hoặc dữ liệu nghiệp vụ.
- Demo công khai mới dùng alias `demo`, search_path chỉ có schema riêng
  `warehouse_public_demo`, không có fallback sang public. Kết nối mặc định read-only;
  chỉ lệnh prepare_public_demo được bật ghi khi chuẩn bị dữ liệu giả lập có marker.
- Phiên demo là principal Viewer không lưu User, không chứa auth user ID; quyền
  admin trước đó bị bỏ khi vào demo. Chỉ session/CSRF được thay đổi, dữ liệu nghiệp
  vụ bị chặn ghi. Mọi request demo có Cache-Control no-store và Vary Cookie.
- Render được người dùng yêu cầu ngày 11/11/2026, chỉ Free trong My Workspace;
  dùng Blueprint cho web và PostgreSQL cùng Singapore. Không nâng gói hoặc tự
  tái sử dụng/xóa dịch vụ khác. PostgreSQL Free có giới hạn 30 ngày.

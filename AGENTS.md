# Smart Warehouse — quy tắc làm việc

Đọc SPEC.md, PLAN.md, DECISIONS.md và IMPLEMENTATION_STATUS.md trước khi sửa.
Phạm vi hiện tại là MVP Smart Warehouse, không triển khai Smart Sales/P2 ngầm.

- Dùng Python 3.13, Django 5.2 LTS và PostgreSQL thật. Không đổi database sang
  SQLite để bỏ qua bài kiểm tra cạnh tranh; không hardcode số liệu giao diện.
- Mọi thay đổi tồn kho đi qua inventory/services.py, giữ transaction và thứ tự
  khóa. Phiếu đã xác nhận và lịch sử không được sửa/xóa qua giao diện.
- Kiểm tra quyền ở backend; không dựa vào việc ẩn nút. Mỗi SKU một đơn vị,
  Decimal cho số lượng/tiền. Không gọi giá vốn tham khảo là định giá kế toán.
- Chạy checks, migrations --check, ruff và pytest cho thay đổi logic; dùng
  PostgreSQL test database. Khi đổi UI, kiểm tra desktop/tablet/mobile và các
  thao tác thật. Ghi kết quả lệnh đã chạy, không tự ghi PASS chưa kiểm chứng.
- Không xóa dữ liệu, reset database/volume hoặc ghi đè .env. Không in mật khẩu,
  token, URL chứa thông tin đăng nhập. Giữ secrets và runtime ngoài source.
- Chỉ chạy local. Không push Git, deploy production, tạo dịch vụ tính phí hoặc
  dùng dữ liệu nhạy cảm thật khi chưa có yêu cầu rõ ràng của người dùng.
- Tôn trọng ứng dụng khác trên máy: cổng 8000 và 55432 đang được dùng khi nghiệm
  thu; phiên Warehouse dùng 8010 và PostgreSQL 55433. Chỉ dừng process do mình tạo.

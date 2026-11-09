# Smart Warehouse — kế hoạch triển khai

Phạm vi: MVP trong SPEC.md; chỉ chạy local, không push hoặc deploy. P2 (chuyển kho,
kiểm kê, barcode/lô) được giữ riêng, chỉ thực hiện sau khi MVP được kiểm chứng.

1. **Nền tảng:** Python 3.13, Django 5.2, PostgreSQL, custom user/4 vai trò,
   migrations, cấu hình môi trường. Pass: migrate DB trống, đăng nhập và checks.
2. **Danh mục:** sản phẩm, danh mục, nhà cung cấp, kho; form, tìm/lọc/phân trang,
   lưu trữ thay xóa; nhập CSV. Pass: validation và quyền backend được test.
3. **Giao dịch:** phiếu nhiều dòng nháp → xác nhận/hủy, dịch vụ nghiệp vụ atomic,
   khóa dữ liệu, lịch sử/audit. Pass: nhập/xuất, rollback, chống lặp và cạnh tranh
   thật trên PostgreSQL.
4. **Báo cáo và giao diện:** dashboard, biểu đồ DB, tồn thấp, NXT theo kỳ,
   Excel/CSV, in phiếu. Pass: dữ liệu báo cáo khớp movement, filter được giữ.
5. **Nghiệm thu:** pytest/ruff/checks, smoke HTTP, browser 375/768/1440, ảnh chụp,
   README, ERD, Docker Compose, hướng dẫn demo/backup. Chỉ ghi ĐẠT khi đã chạy.

Kết quả thực tế và giới hạn môi trường được ghi trong IMPLEMENTATION_STATUS.md.

Nghiệm thu hiện tại: milestone 1–5 đạt trên bản Docker local; 113 test PostgreSQL,
51 HTTP checks và bộ bằng chứng giao diện 55/47 checks đã lưu. Native Windows
hiện bị policy chặn driver; Docker launcher đã chạy thành công và là cách mở
bản bàn giao. P2 chưa triển khai. Chi tiết lịch sử/giới hạn trong báo cáo tiến độ.

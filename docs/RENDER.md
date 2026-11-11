# Smart Warehouse trên Render Free

Blueprint: `render.yaml`, nhánh `main`, region Singapore. Người dùng đã duyệt
kế hoạch tạo mới một Web Service Free và một PostgreSQL Free ngày 11/11/2026.
Không thay đổi các dịch vụ khác trong workspace.

- Website: https://smart-warehouse-0sh0.onrender.com
- [Web Service Dashboard](https://dashboard.render.com/web/srv-dbpugirrjlhs73b5als0)
- [Blueprint Dashboard](https://dashboard.render.com/blueprint/exs-dbpuajgae00c73cnk7t0)
- [PostgreSQL Dashboard](https://dashboard.render.com/d/dpg-dbpufqbrjlhs73b58ik0-a)

Chọn **Xem Demo** tại trang đăng nhập để xem dữ liệu giả với quyền Viewer.
Demo dùng schema riêng `warehouse_public_demo`, không hiển thị dữ liệu nghiệp vụ.
Nút **Thoát Demo** hoặc **Đăng nhập quản trị** xóa phiên demo và quay lại đăng nhập.

Các tài khoản `demo_admin`, `demo_manager`, `demo_staff`, `demo_viewer` trong môi
trường cloud có mật khẩu do Render sinh riêng ở biến `DEMO_PASSWORD`. Chủ dự án
xem tại mục Environment của Web Service; không chia sẻ mật khẩu này lên CV,
GitHub hoặc ảnh chụp. Mật khẩu local trong `.env` không được đưa lên Render.

Khi khởi động, container chạy migrations, seed dữ liệu giả vào database trống,
chuẩn bị schema demo rồi chạy Gunicorn trên `$PORT`. Không reset hay xóa dữ liệu.
`/health/` kiểm tra kết nối database. Secret và kết nối database được Render
sinh/liên kết bằng Blueprint, không ghi trong source.

Blueprint bật auto-sync và Web Service bật tự triển khai nhánh `main`. Sau mỗi
lần push, kiểm tra Deploys để xác nhận commit mới đạt **Live**, rồi mở website
kiểm tra. Trạng thái Blueprint đồng bộ không thay thế kiểm tra website.

Theo [giới hạn Free của Render](https://render.com/docs/free), Web Service có thể
ngủ sau thời gian không có truy cập nên lần mở đầu sẽ chậm. PostgreSQL Free này
hết hạn **11/12/2026** (Render ghi `expiresAt: 2026-12-11T03:58:34Z`). Đây không
phải link demo được bảo đảm hoạt động vĩnh viễn. Trước ngày hết hạn cần tự chọn
phương án duy trì phù hợp; không tự nâng gói hoặc phát sinh chi phí.

Không tải dữ liệu nhạy cảm thật lên môi trường trình diễn. Bằng chứng chạy thực
tế và commit đã nghiệm thu được ghi trong `IMPLEMENTATION_STATUS.md`.

# Hướng dẫn sao lưu và phục hồi

## Sao lưu

1. Mở mục Cài đặt.
2. Chọn `Kiểm tra cơ sở dữ liệu`.
3. Chọn `Sao lưu cơ sở dữ liệu`.
4. Ghi lại đường dẫn bản sao.
5. Chép bản sao sang thiết bị an toàn.

## Vị trí dữ liệu

- Cơ sở dữ liệu: `%LOCALAPPDATA%\TCMExpert\data`.
- Bản sao mặc định: thư mục `backups` bên cạnh.
- Nhật ký: `%LOCALAPPDATA%\TCMExpert\logs`.

## Phục hồi

1. Thoát hoàn toàn ứng dụng.
2. Sao lưu tệp hiện tại lần cuối.
3. Đổi tên bản sao thành `tcm_expert.db`.
4. Chép vào thư mục `data`.
5. Mở lại ứng dụng.
6. Chạy kiểm tra cơ sở dữ liệu.

Không phục hồi khi ứng dụng đang chạy.
# Sao lưu và phục hồi — Epic 28

- Đăng nhập bằng tài khoản quản trị.
- Mở `Sao lưu và phục hồi`.
- Chọn `Tạo bản sao lưu`.
- Chọn vị trí lưu tệp `.db`.
- Dùng `Phục hồi từ tệp` khi cần.
- Kiểm tra thông tin trước xác nhận.
- Ứng dụng tự sao lưu dữ liệu hiện tại.
- Khởi động lại sau khi phục hồi.

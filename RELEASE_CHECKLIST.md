# Stable Release 2.0

## Kiểm tra tự động

- Chạy `scripts\\check.ps1`.
- Không có lỗi Ruff.
- Toàn bộ kiểm thử Pytest đạt.
- Kiểm thử cấu hình hỏng đạt.
- Kiểm thử hiệu năng SQLite đạt.
- Kiểm thử suy luận minh bạch đạt.

## Kiểm tra thủ công

- Mở đủ chín mục menu.
- Chuyển menu chỉ sáng một mục.
- Tạo và cập nhật bệnh nhân.
- Tạo một lần khám mới.
- Nhập đủ dữ liệu Tứ chẩn.
- Phân tích ảnh và âm thanh mẫu.
- Lưu bài thuốc kinh nghiệm.
- Tạo và phê duyệt đơn thuốc.
- Tạo báo cáo hỗ trợ quyết định.
- Kiểm tra và sao lưu SQLite.
- Phục hồi thử một bản sao lưu.
- Kiểm tra cảnh báo dữ liệu thiếu.
- Kiểm tra bắt buộc bác sĩ duyệt.
- Kiểm tra trên Windows x64 sạch.

## Phát hành

- Chạy `scripts\build.ps1`.
- Build trên Python 3.13 x64.
- Kiểm tra bản portable.
- Kiểm tra bộ cài Inno Setup.
- Không đóng gói dữ liệu bệnh nhân.
- Commit với nội dung Epic 16.
- Tag `v2.0-stable` sau nghiệm thu.

# Release Candidate 1

## Kiểm tra tự động

- Chạy `scripts\\check.ps1`.
- Không có lỗi Ruff.
- Toàn bộ kiểm thử Pytest đạt.

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

## Phát hành

- Build trên Python 3.13 x64.
- Không đóng gói dữ liệu bệnh nhân.
- Commit với nội dung Epic 15.
- Tag `v1.0.0-rc1` sau build đạt.

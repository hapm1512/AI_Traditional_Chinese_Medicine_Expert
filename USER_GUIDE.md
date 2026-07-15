# Hướng dẫn sử dụng 2.0

## Khởi động

1. Mở `TCMExpert.exe`.
2. Chờ dữ liệu tham chiếu khởi tạo.
3. Kiểm tra trạng thái trong Cài đặt.

## Quy trình khám

1. Tạo hoặc chọn bệnh nhân.
2. Tạo lần khám mới.
3. Nhập Vọng, Văn, Vấn, Thiết.
4. Kiểm tra dữ liệu còn thiếu.
5. Xem gợi ý biện chứng.
6. Xem bài thuốc tham khảo.
7. Bác sĩ kiểm tra cảnh báo.
8. Bác sĩ phê duyệt kết quả.
9. Tạo đơn thuốc khi phù hợp.

## Nguyên tắc an toàn

- Phần mềm không thay thế bác sĩ.
- AI không tự chẩn đoán.
- AI không tự kê đơn.
- Luôn kiểm tra dị ứng, thai kỳ.
- Luôn kiểm tra gan, thận.
- Chuyển khám khi có cảnh báo đỏ.

## Dữ liệu minh họa

Chạy lệnh sau từ môi trường phát triển:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\create_demo_database.py
```

Không dùng dữ liệu minh họa điều trị thật.

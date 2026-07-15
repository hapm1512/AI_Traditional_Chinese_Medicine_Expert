# AI Traditional Chinese Medicine Expert

Phần mềm hỗ trợ nhân viên phòng khám Đông y. Mọi chẩn đoán, bài thuốc và quyết định điều trị phải được bác sĩ có chuyên môn kiểm tra, phê duyệt.

## Epic 1 — Project Foundation

- Python 3.13 x64 và PySide6.
- Cấu trúc phân lớp, dễ mở rộng.
- SQLite với migration và dữ liệu nền.
- Cấu hình, logging, xử lý lỗi.
- Giao diện desktop nền tảng.
- Kiểm thử tự động và script Windows.

## Chạy trên Windows

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements-dev.txt
.\scripts\run.ps1
```

## Kiểm tra chất lượng

```powershell
.\scripts\check.ps1
```

SQLite được tạo tại `%LOCALAPPDATA%\TCMExpert\data\tcm_expert.db`.

## Nguyên tắc an toàn

- Đây là công cụ hỗ trợ, không tự điều trị.
- Bài thuốc chỉ mang tính tham khảo.
- Bác sĩ chịu trách nhiệm phê duyệt cuối cùng.
- Dữ liệu bệnh nhân cần được bảo vệ.


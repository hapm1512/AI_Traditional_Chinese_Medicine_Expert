# AI Traditional Chinese Medicine Expert

## Phiên bản 0.3.0

- Quản lý danh sách bệnh nhân.
- Thêm, sửa, ẩn và tìm kiếm.
- Quản lý lịch sử hồ sơ khám.
- Kiểm tra dữ liệu và ghi audit.

Phần mềm hỗ trợ nhân viên phòng khám Đông y. Mọi chẩn đoán, bài thuốc và quyết định điều trị phải được bác sĩ có chuyên môn kiểm tra, phê duyệt.

## Epic 2 — Database & Data Foundation

- SQLite schema phiên bản 2.
- Bệnh nhân và hồ sơ khám.
- Dữ liệu Vọng, Văn, Vấn, Thiết.
- Chứng trạng, hội chứng và bệnh danh.
- Tạng phủ, kinh lạc, khí huyết, âm dương.
- Dược liệu, phương thuốc và thành phần.
- Liều lượng, gia giảm và cách dùng.
- Chống chỉ định và tương tác.
- Repository CRUD và validation.
- Migration, seed và kiểm thử tự động.

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

Không commit file cơ sở dữ liệu bệnh nhân lên GitHub.

## Nguyên tắc an toàn

- Đây là công cụ hỗ trợ, không tự điều trị.
- Bài thuốc chỉ mang tính tham khảo.
- Bác sĩ chịu trách nhiệm phê duyệt cuối cùng.
- Dữ liệu bệnh nhân cần được bảo vệ.

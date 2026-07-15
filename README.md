# AI Traditional Chinese Medicine Expert

## Epic 15 — Release Candidate 2

- Khóa phiên bản `1.0.0 RC2`.
- Luôn hiển thị lựa chọn khi thiếu dữ liệu.
- Tự tải lại bệnh nhân khi mở trang đơn.
- Thu gọn biểu mẫu Văn chẩn, Vấn chẩn.
- Hoàn thiện toàn bộ chín mục điều hướng.
- Bổ sung trang cài đặt và bảo trì.
- Kiểm tra tính toàn vẹn cơ sở dữ liệu.
- Sao lưu SQLite an toàn ngay trong ứng dụng.
- Chuẩn hóa kiểm thử trước phát hành.
- Loại bỏ tệp cache và metadata phát sinh.

## Epic 14 — Clinical Decision Support

- Tổng hợp Tứ chẩn theo từng lần khám.
- Chấm độ đầy đủ và chỉ rõ dữ liệu thiếu.
- Hiển thị chứng, căn cứ và độ tin cậy.
- Tổng hợp pháp trị và bài thuốc tham khảo.
- Kiểm tra dị ứng, tương tác và nguy cơ.
- Cảnh báo dấu hiệu cần chuyển khám khẩn.
- Lưu phiên bản báo cáo cùng audit log.
- Bác sĩ bắt buộc phê duyệt kết quả.
- Không tự chẩn đoán hoặc kê đơn.

## Bài thuốc kinh nghiệm bác sĩ

- Tách riêng nguồn hệ thống và bác sĩ.
- Bác sĩ nhập thành phần bằng văn bản.
- Lưu pháp trị, chủ trị và cách dùng.
- Lưu gia giảm, chống chỉ định, tương tác.
- Ghi tên bác sĩ và nguồn kinh nghiệm.
- Cho phép sửa hoặc ẩn bài thuốc.
- Chỉ đưa vào AI sau khi phê duyệt.

Phiên bản 1.4 bổ sung hỗ trợ quyết định lâm sàng minh bạch.

Phiên bản 1.3 bổ sung hỗ trợ phân tích offline WAV cho giọng nói, tiếng ho,
tiếng thở; kiểm tra chất lượng, trích xuất đặc trưng, nhập tay và bác sĩ xác nhận.

## Epic 12 — Tongue Vision AI

- Nhập ảnh lưỡi từ tệp cục bộ.
- Kiểm tra sáng, nét, độ phân giải.
- Khoanh vùng lưỡi bằng thị giác offline.
- Mô tả màu lưỡi và rêu lưỡi.
- Gợi ý dấu răng và vết nứt.
- Lưu ảnh gốc cùng mã SHA-256.
- Hiển thị độ tin cậy từng lần phân tích.
- Bác sĩ chỉnh sửa và duyệt kết quả.
- Không đưa ra chẩn đoán độc lập.

## Phiên bản 1.2.0

## Epic 11 — Đơn thuốc bác sĩ

- Chỉ tạo đơn từ bài thuốc đã phê duyệt.
- Sao chép thành phần vào đơn độc lập.
- Lưu chẩn đoán, pháp trị và cách dùng.
- Lưu gia giảm và ghi chú an toàn.
- Quản lý bản nháp và trạng thái duyệt.
- Ghi tên bác sĩ và thời gian phê duyệt.
- Hiển thị bản xem trước đơn thuốc.
- Ghi audit khi tạo và phê duyệt.
- Không cho AI tự động kê đơn.

## Epic 10 — Formula Recommendation

- Xác định pháp trị từ hồ sơ biện chứng.
- Xếp hạng tối đa ba bài thuốc.
- Hiển thị thành phần, công năng, chủ trị, nguồn.
- Gợi ý huyệt vị để bác sĩ tham khảo.
- Kiểm tra dị ứng, thai kỳ, gan, thận, độc tính.
- Kiểm tra thuốc Tây và chống chỉ định.
- Không tự động kê toa hoặc đặt liều.
- Mọi kết quả bắt buộc bác sĩ phê duyệt.

- Quản lý danh sách bệnh nhân.
- Thêm, sửa, ẩn và tìm kiếm.
- Quản lý lịch sử hồ sơ khám.
- Kiểm tra dữ liệu và ghi audit.
- Nhập liệu Vọng, Văn, Vấn, Thiết.
- Phân loại và chấm mức độ phát hiện.
- Lưu nhận định sơ bộ và trạng thái duyệt.
- Nhập liệu Văn chẩn thủ công chuẩn hóa.
- Lưu người ghi nhận và thời gian.

## Epic 8 — Biện chứng luận trị

- Tổng hợp dữ liệu đầy đủ từ Tứ chẩn.
- Gợi ý hội chứng bằng luật minh bạch.
- Hiển thị Bát cương, bệnh cơ, phép trị.
- Lưu độ phù hợp và căn cứ lâm sàng.
- Chọn một chứng chính cho lần khám.
- Bác sĩ xác nhận trước quyết định điều trị.

## Epic 7 — Thiết chẩn

- Nhập mạch trái, phải theo Thốn–Quan–Xích.
- Ghi độ sâu, tốc độ, lực và nhịp.
- Ghi mạch tượng và số nhịp mỗi phút.
- Nhập xúc chẩn theo vùng cơ thể.
- Ghi nhiệt độ, đau, khối, da và bụng.
- Lưu người ghi nhận và thời điểm.
- Chưa kết nối thiết bị đo mạch ngoại vi.

## Epic 6 — Vấn chẩn

- Biểu mẫu Vấn chẩn theo Thập vấn.
- Ghi hàn nhiệt, mồ hôi và đau.
- Ghi ăn uống, khát và giấc ngủ.
- Ghi đại tiện, tiểu tiện, tai mắt.
- Ghi kinh đới và thai sản.
- Ghi khởi phát và điều trị hiện tại.
- Ghi riêng các dấu hiệu cảnh báo.
- Lưu người hỏi và thời gian cập nhật.

## Epic 5 — Văn chẩn thủ công

- Y tá nhập giọng nói và hơi thở.
- Ghi nhận ho, đờm, nấc và âm bệnh lý.
- Ghi nhận mùi và đặc điểm liên quan.
- Chuẩn hóa loại, tần suất, thời gian, mức độ.
- Chưa thu âm hoặc kết nối micro.
- Kiến trúc sẵn sàng tích hợp ngoại vi sau RC.

## Epic 4 — Hồ sơ khám và Tứ chẩn

- Chọn bệnh nhân và lần khám.
- Ghi nhận bốn phương pháp Tứ chẩn.
- Thêm, xem và xóa từng phát hiện.
- Cập nhật tiền sử, nhận định, bác sĩ.
- Quy trình bản nháp, duyệt và đóng.

Phần mềm hỗ trợ nhân viên phòng khám Đông y. Mọi chẩn đoán, bài thuốc và quyết định điều trị phải được bác sĩ có chuyên môn kiểm tra, phê duyệt.

## Epic 2 — Database & Data Foundation

- SQLite schema phiên bản 2.
- Bệnh nhân và hồ sơ khám.
- Dữ liệu Vọng, Văn, Vấn, Thiết.
- Chứng trạng, hội chứng và bệnh danh.
- Tạng phủ, kinh lạc, khí huyết, âm dương.
- Dược liệu, phương thuốc và thành phần.

## Epic 9 — Bài thuốc tham khảo

- Tra cứu theo tên, mã, nhóm, chỉ định, pháp trị.
- Hiển thị thành phần, vai trò, liều tham chiếu.
- Hiển thị chống chỉ định, tương tác và nguồn.
- Gắn bài thuốc tham khảo vào lần khám.
- Gia giảm và cách dùng do bác sĩ quyết định.
- Phê duyệt bắt buộc có ghi chú an toàn.
- Không tự động kê đơn hoặc thay thế bác sĩ.
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

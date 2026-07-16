# AI Traditional Chinese Medicine Expert

## Epic 28 — Sao lưu và phục hồi dữ liệu

- Chỉ quản trị viên được truy cập.
- Sao lưu SQLite bằng API an toàn.
- Kiểm tra toàn vẹn trước và sau sao lưu.
- Xác nhận trước khi phục hồi dữ liệu.
- Tự tạo bản sao an toàn trước phục hồi.
- Kiểm tra bảng dữ liệu bắt buộc.
- Ghi nhật ký sao lưu và phục hồi.
- Yêu cầu khởi động lại sau phục hồi.
- Phiên bản Epic 28: `3.3.0`.

## Epic 27 — Nhật ký hệ thống và truy vết

- Chỉ quản trị viên được xem nhật ký.
- Theo dõi đăng nhập và đăng xuất.
- Theo dõi thao tác lưu, khóa và xóa.
- Lọc theo người dùng, thao tác và thời gian.
- Xem chi tiết từng bản ghi chỉ đọc.
- Không cho sửa hoặc xóa nhật ký.
- Xuất báo cáo CSV mã hóa UTF-8.
- Phiên bản Epic 27: `3.2.0`.

## Epic 26 — Quản lý người dùng và phân quyền

- Đăng nhập bằng tài khoản quản trị, bác sĩ hoặc y tá.
- Khóa tài khoản 15 phút sau năm lần sai.
- Tự khóa phiên sau 15 phút không hoạt động.
- Chỉ bác sĩ được phê duyệt lâm sàng.
- Quản trị viên tạo, sửa và khóa tài khoản.
- Quản trị viên xóa tài khoản nhân sự đã nghỉ việc.
- Không thể xóa tài khoản đang đăng nhập.
- Nhật ký lưu tài khoản thực hiện thao tác.
- Tài khoản đầu tiên: `admin` / `Admin@123`.
- Bắt buộc đổi mật khẩu ngay lần đăng nhập đầu.

## Epic 25 — Clinic Operations Dashboard 3.0

- Cho phép bác sĩ xóa thông báo trễ quá ba giờ.
- Bắt buộc bác sĩ xác nhận trước khi xóa.
- Đóng thông báo nhưng giữ toàn bộ lịch sử.
- Hiển thị quyết định duyệt là `Đã được duyệt`.
- Nâng cấp trang Tổng quan thành dashboard vận hành.
- Hiển thị lịch hẹn hôm nay và lịch quá giờ.
- Thống kê lịch chưa nhắc trong bảy ngày.
- Thống kê hồ sơ điều trị và theo dõi.
- Hiển thị tổng số bệnh nhân đang quản lý.
- Ưu tiên lịch quá giờ trước lịch trong ngày.
- Mở nhanh trang bệnh nhân và lịch tái khám.
- Tự làm mới dashboard mỗi lần mở.
- Cho phép bác sĩ làm mới thủ công.
- Dashboard chỉ hỗ trợ vận hành phòng khám.
- Không tự đưa ra quyết định chuyên môn.
- Phiên bản Epic 25: `3.0.2`.

## Epic 24 — Appointment Reminders 2.9

- Tách riêng ngày hẹn và giờ hẹn.
- Chọn riêng giờ `00–23` và phút `00–59`.
- Không tự lấy giờ hiện tại khi tạo lịch.
- Bắt buộc chọn đủ giờ và phút.
- Hiển thị đầy đủ ngày và giờ trong danh sách.
- Tự hiển thị cảnh báo khi lịch đến giờ.
- Mỗi lịch hẹn chỉ cảnh báo một lần.
- Bỏ thanh cảnh báo lịch hẹn thường trực.
- Hiển thị cửa sổ cảnh báo nhỏ luôn nổi.
- Tiêu đề cảnh báo chớp màu mỗi 500 ms.
- Bác sĩ chủ động tắt sau khi đã xem.
- Chỉ ghi nhận đã xem khi đóng cảnh báo.
- Nút đã xem dừng chớp và ẩn ngay lập tức.
- Bác sĩ bắt buộc ghi lý do xử lý quá hạn.
- Quá 30 ngày được lưu làm lịch sử tham khảo.
- Quá 90 ngày tự đóng hồ sơ tái khám.
- Không xóa dữ liệu sức khỏe đã lưu.
- Trong 90 ngày có thể mở lại lịch tái khám.
- Sau 90 ngày phải tạo hồ sơ khám mới.
- Có thể lưu hồ sơ thành bệnh án tham khảo.
- Hiển thị danh sách lịch hẹn trong ngày.
- Theo dõi lịch sắp đến trong bảy ngày.
- Cảnh báo lịch đã qua nhưng chưa xác nhận.
- Lọc lịch chưa nhắc và đã nhắc.
- Ghi người nhắc và thời gian thực hiện.
- Lưu toàn bộ lịch sử nhắc độc lập.
- Lưu audit log cho mỗi lần nhắc.
- Không tự gửi SMS, Zalo hoặc thông báo ngoài.
- Nhắc lịch không thay thế chỉ định bác sĩ.
- Phiên bản `2.9.9`.

## Epic 23 — Follow-up Appointment Scheduling 2.8

- Quản lý lịch hẹn tái khám theo hồ sơ.
- Ghi ngày giờ, lý do và chuẩn bị.
- Theo dõi xác nhận, hoàn tất và hủy.
- Ghi nhận trường hợp bệnh nhân không đến.
- Lọc lịch hẹn theo từng trạng thái.
- Ngăn tạo trùng lịch cho cùng hồ sơ.
- Lưu người phụ trách mọi cập nhật.
- Lưu audit log khi tạo và đổi trạng thái.
- Lịch hẹn không thay thế chỉ định bác sĩ.
- Sửa duyệt báo cáo cũ còn quyết định chờ.
- Phiên bản `2.8.1`.

## Epic 22 — Treatment Outcome Reports 2.7

- Tổng hợp kết quả điều trị theo khoảng thời gian.
- Thống kê bệnh nhân và số lần theo dõi.
- Thống kê cải thiện, ổn định và nặng hơn.
- Tính thay đổi điểm triệu chứng trung bình.
- Ghi nhận số trường hợp phản ứng bất lợi.
- Hiển thị chi tiết từng lần tái khám.
- Lưu báo cáo dưới dạng ảnh chụp dữ liệu.
- Bắt buộc bác sĩ nhập kết luận chuyên môn.
- Lưu audit log khi xác nhận báo cáo.
- AI không tự kết luận hiệu quả điều trị.
- Phiên bản `2.7.0`.

## Epic 21 — Treatment Follow-up & Outcomes 2.6

- Theo dõi điều trị theo từng hồ sơ khám.
- Ghi ngày tái khám và trạng thái thực tế.
- So sánh điểm triệu chứng trước và sau.
- Ghi hiệu quả và mức tuân thủ điều trị.
- Ghi nhận phản ứng bất lợi riêng biệt.
- Đồng bộ trạng thái theo dõi bệnh nhân.
- Bắt buộc bác sĩ ghi nhận kết quả.
- Lưu audit log cho mọi lần theo dõi.
- AI không tự đánh giá hiệu quả điều trị.
- Phiên bản `2.6.0`.

## Epic 20 — AI Safety & Validation 2.5

- Kiểm định độ đầy đủ dữ liệu trước khi gọi AI.
- Chặn đề xuất khi Tứ chẩn dưới ngưỡng an toàn.
- Phát hiện nội dung chẩn đoán, kê đơn hoặc liều dùng.
- Chuẩn hóa và loại trùng nguồn tham khảo.
- Kiểm tra kết nối từng mô-đun trong Cài đặt.
- Hiển thị trạng thái và thời gian phản hồi.
- Lưu lỗi, fallback và kết quả kiểm định.
- AI không tạo hoặc tự phê duyệt đơn thuốc.
- Bác sĩ luôn quyết định và chịu trách nhiệm.
- Phiên bản `2.5.0`.


## Epic 19 — AI Clinical Workflow 2.4

- Tích hợp đề xuất AI theo từng hồ sơ khám.
- Lưu lịch sử đề xuất độc lập theo thời gian.
- Hiển thị nguồn mô-đun và độ tin cậy.
- Hiển thị căn cứ và cảnh báo an toàn.
- Bác sĩ chấp nhận hoặc từ chối rõ ràng.
- Từ chối bắt buộc ghi nhận lý do.
- Mọi quyết định được lưu audit log.
- Đề xuất AI không trở thành đơn thuốc.
- Phiên bản `2.4.0`.

## Epic 18 — Connected AI Providers 2.3

- Kết nối TCMChat qua API tương thích OpenAI.
- Dịch Việt–Trung hai chiều qua mô-đun cấu hình.
- Kết nối OpenTCM GraphRAG, TCMBank và SymMap.
- Cho phép máy chủ HTTPS hoặc máy cục bộ.
- Không lưu khóa API trong cơ sở dữ liệu.
- Đọc khóa TCMChat từ biến môi trường.
- Giới hạn thời gian chờ từ 3–120 giây.
- Tự quay về Rule Engine khi mô-đun lỗi.
- AI vẫn chỉ tạo đề xuất tham khảo.
- Bác sĩ bắt buộc kiểm tra và quyết định.
- Phiên bản `2.3.0`.

## Epic 17 — AI Integration Foundation 2.2

- Tách lớp AI khỏi giao diện và dữ liệu.
- Mặc định tắt toàn bộ luồng AI.
- Bổ sung công tắc AI trong Cài đặt.
- Chuẩn bị bộ dịch Việt–Trung hai chiều.
- Chuẩn bị adapter TCMChat.
- Chuẩn bị OpenTCM GraphRAG, TCMBank, SymMap.
- Luôn chạy Rule Engine minh bạch.
- Luồng cố định: AI đề xuất → bác sĩ kiểm tra → bác sĩ quyết định.
- AI không chẩn đoán, đặt liều, kê đơn hoặc phê duyệt.
- Mọi đề xuất hiển thị trạng thái chưa được bác sĩ duyệt.
- Bắt buộc bác sĩ phê duyệt trước khi sử dụng.
- Lưu đề xuất tham khảo thành báo cáo bản nháp.
- Chỉ phê duyệt báo cáo đã chọn trong bảng.
- Bắt buộc hồ sơ và giấy phép bác sĩ.
- Nút bác sĩ phê duyệt tự lưu đơn mới.
- Không bắt buộc tạo đơn nháp trước.
- Đổi nút thành `Tạo đơn thuốc`.
- Ẩn thanh cuộn tại ô có nút soạn thảo.
- Phiên bản `2.2.4`.

## Epic 17A — Clinical Workflow 2.1

- Quản lý quy ước mã nhóm bệnh.
- Tự tạo mã bệnh nhân và lần khám.
- Hiển thị ngày sinh chuẩn Việt Nam.
- Kiểm soát điện thoại và CCCD.
- Bắt buộc định danh bác sĩ sử dụng.
- Đồng bộ lịch sử khám trên mọi trang.
- Kết hợp nhận xét AI và bác sĩ.
- Chuẩn hóa bài thuốc và đơn thuốc.
- Bổ sung trang Tra cứu dược.

## Epic 16 — Testing & Stable Release

- Khóa phiên bản ổn định `2.0.0`.
- Kiểm thử dữ liệu lỗi và thiếu.
- Bắt buộc bác sĩ phê duyệt.
- Kiểm thử luật suy luận minh bạch.
- Kiểm tra hiệu năng khởi tạo SQLite.
- Xác minh toàn vẹn mọi bản sao lưu.
- Tự phục hồi cấu hình JSON hỏng.
- Đóng gói Windows bằng PyInstaller.
- Hỗ trợ bộ cài bằng Inno Setup.
- Bổ sung dữ liệu minh họa an toàn.
- Bổ sung hướng dẫn dùng và sao lưu.

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

## Build Windows 2.0

```powershell
.\scripts\build.ps1
```

- Bản portable nằm trong `release`.
- Bộ cài được tạo khi có Inno Setup.
- Không đóng gói dữ liệu bệnh nhân.

SQLite được tạo tại `%LOCALAPPDATA%\TCMExpert\data\tcm_expert.db`.

Không commit file cơ sở dữ liệu bệnh nhân lên GitHub.

## Nguyên tắc an toàn

- Đây là công cụ hỗ trợ, không tự điều trị.
- Bài thuốc chỉ mang tính tham khảo.
- Bác sĩ chịu trách nhiệm phê duyệt cuối cùng.
- Dữ liệu bệnh nhân cần được bảo vệ.

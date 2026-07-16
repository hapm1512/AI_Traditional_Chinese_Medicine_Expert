# Kiểm thử Ollama + Qwen

## Cài đặt

```powershell
winget install Ollama.Ollama
ollama pull qwen2.5:7b
ollama serve
```

## Kiểm thử trong ứng dụng

1. Mở `Bài thuốc tham khảo`.
2. Chọn tab `Tra cứu bài thuốc`.
3. Chọn một cổ phương Trung văn.
4. Nhấn `Dịch thử bằng Qwen`.
5. Kiểm tra bản dịch nháp.

## Dịch toàn bộ qua đêm

1. Nhấn `Dịch toàn bộ qua đêm`.
2. Xác nhận bắt đầu.
3. Giữ Ollama và ứng dụng đang chạy.
4. Có thể dừng sau bài hiện tại.
5. Chạy lại để tiếp tục phần còn thiếu.

Không đóng cửa sổ `ollama serve` khi kiểm thử.

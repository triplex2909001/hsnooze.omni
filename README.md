# hsnooze.omni

Cỗ máy sinh giọng đọc Voiceover phân đoạn bằng ma trận đám mây (15 Parallel Matrix Jobs, 0% VPS) cho kênh **HistorySnooze**.

## 🚀 Tính Năng Cốt Lõi
1. **Ma Trận 15 Tiến Trình Song Song (GHA Matrix):** Khởi chạy 15 jobs độc lập trên GitHub Actions runner cho 15 Parts cùng một lúc, rút ngắn thời gian sinh 90 phút audio xuống dưới 10 phút.
2. **Chia Nhỏ Sentence Chunks (15–30 Từ):** Mỗi Part được chia thành các câu ngắn tự nhiên, tránh nghẽn timeout mạng.
3. **Đồng Bộ Tức Thì Lên Google Drive (Immediate Sync):** Mỗi file chunk audio sau khi sinh xong được upload ngay lập tức lên Google Drive (`02. Media Generation/chunks/`), triệt tiêu rủi ro mất mát dữ liệu giữa chừng.
4. **Khoảng Lặng ASMR 3 Cấp Độ (Multi-Tier Silence Pacing):**
   - 1.0 giây giữa các câu (*intra-sentence*)
   - 2.0 giây giữa các đoạn (*inter-paragraph*)
   - 5.0 giây giữa các phần (*inter-part*)
5. **Kiểm Toán Âm Học GK4 (Acoustic Audit):** Kiểm tra dung lượng >= 10 KB, năng lượng RMS >= 0.003, chống file rỗng/im lặng.
6. **Smart Delta Restart:** Tự động bỏ qua các chunks/parts hợp lệ đã tồn tại trên Drive, chỉ chạy bù các file thiếu hoặc hư hỏng.

## 🔐 GitHub Secrets Cần Cấu Hình
- `TTS_API_KEY`: API Key cho dịch vụ TTS (OmniVoice / ElevenLabs / Google Cloud TTS).
- `GDRIVE_SERVICE_ACCOUNT_KEY`: Khóa Service Account JSON để upload file lên Google Drive và cập nhật Google Sheet.

## 🕹️ Cách Kích Hoạt
Truy cập tab **Actions** -> Chọn workflow **Omni Voiceover Matrix** -> Bấm **Run workflow**:
- `project_folder_id`: ID thư mục dự án trên Google Drive
- `character_name`: Tên nhân vật lịch sử
- `row_index`: Số hàng trên Google Sheet (để cập nhật Status = `Voiceover`, Voiceover = `Done`)

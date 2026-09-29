# Kế hoạch xây lại bộ công cụ tự động (Bạn chốt 30/9/2026)

Bối cảnh: đêm 29/9/2026, sau 11 ngày bot Data360X không chạy (máy bàn cơ quan im từ 18/9), việc đưa bot
lên laptop thất bại 3 lần liên tiếp vì lỗi trong bộ cài chưa từng được chạy thử ngoài máy bàn cơ quan; lượt
quét online trên máy chủ GitHub bị cổng Data360X từ chối (timeout 90 giây). Bạn kết luận: "nhiều sai lầm và
kém ở khâu tự động hóa", yêu cầu xây lại để bộ công cụ thành cánh tay của Claude, tự động hóa công việc
hằng ngày, không tốn dung lượng máy.

## Chẩn đoán

1. Cả dây chuyền treo trên một máy Windows có Chrome đã đăng nhập; GitHub và Claude ở nước ngoài bị cổng chặn.
2. Ba cơ chế chạy bot chồng nhau (Task Scheduler 18h, GitHub runner, lượt online), 17 workflow, 16 file .bat.
3. Bộ cài chưa từng được chạy thử ở đâu ngoài máy bàn cơ quan; Claude không có Windows nên sửa mù.
4. Không giám sát đầu-cuối: claude.ai ngừng đồng bộ 18 ngày, bot ngừng 11 ngày, CI vẫn xanh.
5. Nhiều tầng trung gian (Gemini, Mistral, giữ phiên mỗi giờ) so với việc cốt lõi: lấy văn bản về cho Claude đọc.
6. Dung lượng phình: skill-sct 600 MB PDF gốc; laptop gánh Python, Chromium riêng, runner, log không xoay vòng.

## Nguyên tắc

- Máy ở Lào Cai chỉ là **"tay"**: chép văn bản từ Data360X/vOffice lên GitHub. Không phân loại, không đọc hiểu.
- Claude trên mây là **"não"**: Routine đọc, xếp lĩnh vực, cập nhật plugin, soạn dự thảo, báo cáo.
- Tay **tự kéo việc** từ GitHub (hỏi mỗi 10 phút), không đăng ký runner, không có gì để "already configured".
- Mọi thứ đưa cho Bạn **đã chạy thử trên máy ảo Windows** (workflow `thu-bo-cai-windows.yml`). Chỉ bước đăng nhập có captcha là của Bạn.
- Thất bại phải kêu: Routine "Kiểm tra sức khỏe" mỗi sáng 07:41 gửi Bạn tối đa 10 dòng ✅/⚠️/❌.
- Không tự đăng nhập, không giải captcha; kho công khai không chứa hồ sơ nội bộ.

## Mặc định đã lấy (Bạn nói "đồng ý với bạn, bắt đầu đi" mà chưa chốt riêng)

| Điểm | Mặc định | Đổi thì ghi ở đây |
|---|---|---|
| Máy làm "tay" | cả laptop và máy bàn, máy nào bật thì làm | |
| Gemini đọc PDF | bỏ ở Giai đoạn 2, Claude đọc trực tiếp | |
| Kênh báo động | Telegram (đã có trong config.json) | |
| PDF gốc trong skill-sct | chuyển sang kho lưu trữ riêng ở Giai đoạn 2 | |

## Lộ trình và trạng thái

### Giai đoạn 0 — cầm máu (tuần 30/9)
- [x] Dừng thử runner trên laptop. Khi cần văn bản: nháy đúp `quet-lai-ngay.bat` (bot chạy thẳng).
- [x] Máy ảo Windows trên GitHub Actions chạy `cai-runner.ps1 -ChayThu` (bước 1–4) trước khi merge.
- [x] Routine "Kiểm tra sức khỏe dây chuyền" mỗi sáng 07:41 thứ Hai–Bảy.
- [x] Routine "Nâng cấp bộ plugin từ bản tin Data360X" 14:52 thứ Tư.
- [ ] Rà 17 workflow của vlncn-laocai: đánh dấu cái nào sẽ tắt ở Giai đoạn 1.

### Giai đoạn 1 — "tay" mới (2 tuần)
- [ ] `tay/tay.py` dưới 500 dòng: đăng nhập 1 lần (Chrome sẵn có của máy, không tải Chromium), giữ phiên,
      kéo yêu cầu từ `vlncn-laocai/yeu-cau/*.json`, đẩy kết quả, nhịp tim, tự cập nhật từ main, log xoay vòng 14 ngày.
- [ ] Một bộ cài duy nhất `cai-tay.bat`, đã qua máy ảo Windows; tổng dung lượng trên máy dưới 100 MB.
- [ ] Chạy song song bot cũ 1 tuần, so kết quả; rồi tắt bot cũ, runner, lượt online và các workflow thừa.

### Giai đoạn 2 — "não" đọc trực tiếp (2 tuần)
- [ ] Routine sáng thứ Hai–Sáu: việc chờ xử lý trên vOffice + soạn dự thảo.
- [ ] Bỏ Gemini: Routine Claude đọc PDF trong kho riêng tư.
- [ ] PDF gốc của skill-sct sang kho lưu trữ riêng; bỏ export-ignore tạm; skill-sct dưới 150 MB.

### Giai đoạn 3 — nghiên cứu công việc (tháng thứ hai)
- [ ] Nhật ký 4 tuần: văn bản đến/đi theo loại, việc được giao, thời gian phản hồi, dự thảo bị sửa ở đâu.
- [ ] Bản đồ công việc; chọn 3 việc lặp nhiều nhất để tự động trước.

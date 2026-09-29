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
- [x] Rà 17 workflow của vlncn-laocai (bảng dưới), đánh dấu số phận từng cái.

### Giai đoạn 1 — "tay" mới (2 tuần)
- [x] `tay/tay.py` v0.1.1 (~380 dòng, 30/9/2026): Chrome sẵn có của máy, giữ phiên mỗi giờ, quét thứ Tư hoặc khi quá
      7 ngày, kéo yêu cầu từ `vlncn-laocai/yeu-cau/*.json` (nhận bằng sha, hai máy không tranh), đẩy kết quả qua
      Contents API (không git clone), nhịp tim `trang-thai/tay.json`, tự cập nhật từ main, log xoay 14 ngày.
      Chưa làm: việc vOffice (`viec-cho-xu-ly`) — giữ workflow cũ tới v0.2.
- [x] Bộ cài `bot/cai-tay.bat` + `cai-tay.ps1`: Python, `pip install playwright` (không tải Chromium), tải mã, token,
      2 lịch Task Scheduler không cần Administrator. **Đã xanh trên máy ảo Windows** (workflow *Thu bo cai tren Windows*,
      lượt 55f9503 ngày 29/9/2026); máy ảo cũng bắt được 1 lỗi thật (in tiếng Việt ra console cp1252) trước khi Bạn gặp.
- [x] Hàng đợi `vlncn-laocai/yeu-cau/` + workflow `yeu-cau.yml` (ghi yêu cầu từ điện thoại); plugin `data360x-sct-vn` 1.1.0
      biết ghi yêu cầu cho TAY (ref 05, `goi_bot.py --qua-tay`).
- [ ] Cài TAY lên laptop (Bạn bấm `cai-tay.bat` một lần, xem HUONG-DAN-CAI-BOT.md mục đầu) và máy bàn cơ quan.
- [ ] Chạy song song bot cũ 1 tuần, so kết quả; rồi tắt bot cũ, runner, lượt online và các workflow thừa.
- [ ] TAY v0.2: việc vOffice (danh sách chờ xử lý + tải văn bản đến) để thay `viec-cho-xu-ly.yml`.

### Giai đoạn 2 — "não" đọc trực tiếp (2 tuần)
- [ ] Routine sáng thứ Hai–Sáu: việc chờ xử lý trên vOffice + soạn dự thảo.
- [ ] Bỏ Gemini: Routine Claude đọc PDF trong kho riêng tư.
- [ ] PDF gốc của skill-sct sang kho lưu trữ riêng; bỏ export-ignore tạm; skill-sct dưới 150 MB.

### Giai đoạn 3 — nghiên cứu công việc (tháng thứ hai)
- [ ] Nhật ký 4 tuần: văn bản đến/đi theo loại, việc được giao, thời gian phản hồi, dự thảo bị sửa ở đâu.
- [ ] Bản đồ công việc; chọn 3 việc lặp nhiều nhất để tự động trước.

## Rà 17 workflow của `vlncn-laocai` (30/9/2026)

| Workflow | Chạy ở | Việc | Số phận |
|---|---|---|---|
| Quet Data360X (may co quan) | máy Lào Cai | quét 30 ngày thứ Tư 11:30 | **gộp vào tay v2** (yêu cầu `quet`) |
| Giu phien Data360X (may co quan) | máy Lào Cai | mở trang chủ mỗi giờ | **tay v2 tự làm**, tắt sau khi tay v2 chạy |
| Lay van ban theo yeu cau (may co quan) | máy Lào Cai | Claude sai bot lấy văn bản | **gộp vào tay v2** (yêu cầu `lay`) |
| Tim van ban vien dan (may co quan) | máy Lào Cai | tìm văn bản dự thảo viện dẫn | **gộp vào tay v2** (yêu cầu `tim`) |
| Viec cho xu ly (vOffice + Data360X) | máy Lào Cai | 07:30 T2–T6, danh sách việc + toàn văn | **gộp vào tay v2** (yêu cầu `voffice`) |
| Viec tren vOffice (may co quan) | máy Lào Cai | 07:30 T2–T6, bản cũ của cái trên | **tắt ngay** (trùng, hai lượt cùng giờ tranh máy) |
| Zalo (may co quan) | máy Lào Cai | đọc/gửi Zalo, bấm tay | giữ tạm, xem 4 tuần có dùng không |
| Quet Data360X (online) | GitHub | quét bằng phiên xuất lên | **tắt ngay** (cổng timeout 29/9, chết hẳn) |
| Doc inbox (Gemini) | GitHub | Gemini đọc PDF giấy phép | Giai đoạn 2 thay bằng Routine Claude |
| Doc GP van chuyen HHNH | GitHub | Gemini đọc GP HHNH | Giai đoạn 2 thay bằng Routine Claude |
| Thi diem doc GP VLNCN | GitHub | thí điểm | **tắt ngay** |
| Thu Mistral OCR | GitHub | thí điểm | **tắt ngay** |
| Dong bo tri thuc sang plugin | GitHub | sinh 2 reference từ CSDL web | giữ (cơ học, ổn) |
| De xuat VBPL tu Data360X | GitHub | lọc VBPL công khai ra CSV | giữ (Routine thứ Tư dùng) |
| Ban tin Telegram 18h30 | GitHub | bản tin Telegram thứ Tư | giữ; xem gộp vào Routine sức khỏe |
| Soat du thao van ban | GitHub | soát .docx thả vào du-thao/ | giữ; Giai đoạn 2 xem chuyển sang Routine |

Kết quả: 5 workflow trên máy Lào Cai gộp thành **một** tiến trình `tay`; 4 workflow tắt ngay; 4 chuyển sang Routine
Claude ở Giai đoạn 2; 4 giữ. Từ 17 còn khoảng 6.

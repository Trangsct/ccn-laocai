# Báo cáo rà soát chất lượng dữ liệu — Cổng thông tin KCN/CCN tỉnh Lào Cai

**Ngày rà soát:** 11/6/2026
**Phạm vi:** `ccn-data.json`, `unit-details.json`, `ccn-polygons.json`, `data.js`, `index.html`, `app.js`, `api/chatbot-context.js`, `units/*.html`
**Tính chất:** Tài liệu nội bộ trong repo — KHÔNG xuất bản lên trang công khai, KHÔNG đưa vào nav. Báo cáo này CHỈ NÊU hiện trạng và đề xuất, không kèm bất kỳ chỉnh sửa dữ liệu nào.

---

## 1. Mâu thuẫn số liệu nội bộ ngay trong trang

### 1.1. Số lượng CCN quy hoạch: 32 / 33 / 35 — ba con số cùng tồn tại

| Nơi ghi | Con số | Vị trí |
|---|---|---|
| Meta description + OpenGraph + Twitter card | **32 CCN quy hoạch** | `index.html` dòng 9, 23, 34, 71 |
| Dữ liệu thật (`CCN_CHUA_DAU_TU`) | **33 đơn vị** | `ccn-data.json` (đếm thực tế) |
| Nút/tiêu đề trong trang | **35 CCN quy hoạch** | `index.html` dòng 553, 563, 1162, 1267, 1288, 1309, 1607 |

Ghi chú: "35 CCN chưa thành lập" là con số theo Quy hoạch tỉnh (QĐ 525/QĐ-UBND); 33 là số đơn vị hiện có hồ sơ trong dữ liệu; 32 là con số cũ chưa cập nhật sau khi thêm CCN Yên Hợp 2. Ba con số dùng lẫn lộn không chú thích khiến người đọc hiểu là mâu thuẫn.

### 1.2. Tổng số CCN: 54 vs 56

- `data.js` dòng 224: hardcode `tongCCN: 54` (comment ghi "23 hiện hữu + 31 quy hoạch mới" — không khớp dữ liệu hiện tại).
- `app.js` dòng 166 (sau khi fetch `ccn-data.json`): tính lại `tongCCN = 23 + 33 = 56`.
- Thẻ thống kê dashboard (markup trong `app.js` ~dòng 431) hiển thị con số này dưới nhãn **"Tổng Cụm công nghiệp theo Quy hoạch"** → người xem thấy **56**, trong khi Quy hoạch chính thức là **54** (19 CCN đã thành lập giữ lại + 35 chưa thành lập — `index.html` dòng 553). Nhãn và số không cùng hệ quy chiếu.

### 1.3. Tổng diện tích 23 CCN đã thành lập: 903,78 / 970,46 / 843,78 ha — ba tổng khác nhau

| Nguồn | Tổng diện tích |
|---|---|
| `index.html` (dòng 383, 524, 570, 1607, 1794) + `bao-cao-tong-hop-kcn-ccn-laocai.md` | **903,78 ha** |
| Cộng trường `dienTich` của 23 CCN trong `ccn-data.json` | **970,46 ha** |
| `api/chatbot-context.js` dòng 3 (tiêu đề mục A) | **843,78 ha** |

Chatbot sẽ trả lời 843,78 ha trong khi trang hiển thị 903,78 ha và số liệu chi tiết cộng lại ra 970,46 ha.

### 1.4. Tổng số dự án: "461+ (228 KCN + 233 CCN)" vs dữ liệu cộng được 204

- `index.html` dòng ~1040–1044 (thẻ thống kê tĩnh): **461+ dự án = 228 KCN + 233 CCN**.
- Cộng `soDoanhNghiep` của 23 CCN trong `ccn-data.json`: **204** — lệch 29 so với "233 CCN".
- Trường `soDoanhNghiep` của 21 KCN trong `ccn-data.json` **không có dữ liệu** (= 0), nên "228 dự án KCN" chỉ tồn tại trong văn bản tĩnh, không kiểm chứng được bằng dữ liệu.

### 1.5. Số KCN: 20 vs 21 vs "07 đã thành lập"

- Meta: "21 Khu công nghiệp" (`index.html` dòng 9); `KHU_CONG_NGHIEP` trong dữ liệu: **21 entry**, tổng diện tích cộng được **5.814 ha**.
- Phần giới thiệu: quy hoạch đến 2030 là **20 KCN / 5.797 ha** (dòng 540) và hiện trạng "**07 KCN đã thành lập** / 2.138,89 ha" (dòng 570).
- 21 entry dữ liệu = 20 KCN quy hoạch + KCN Đông Phố Mới (đã đưa ra khỏi quy hoạch nhưng vẫn trong danh sách). Cách trình bày hiện tại không nói rõ điều này; tổng 5.814 ≠ 5.797 cũng do chênh này.

### 1.6. Dead code thống kê header

`app.js` dòng 216–221 (`updateHeaderStats`) ghi vào `#header-total-ccn`, `#header-total-dn`, `#header-total-dt` — **các id này không tồn tại trong `index.html`** (đã bị xóa markup ở lần sửa giao diện nào đó). Hàm chạy vô hại nhưng là code chết, dễ gây hiểu nhầm khi bảo trì.

### 1.7. Fallback `data.js` lệch xa nguồn chính

So khớp tên CCN giữa `data.js` (fallback) và `ccn-data.json` (nguồn thật):

- **Thiếu trong fallback (6):** CCN An Thịnh, CCN Bảo Hưng 2, CCN Bảo Thắng (Thị trấn Phố Lu), CCN Hợp Minh, CCN Quang Kim số 1, CCN Xuân Ái (mở rộng).
- **Tên cũ còn trong fallback:** "CCN Quang Kim 1" (nay "Quang Kim số 1"), "CCN Xuân Ái" (nay "Xuân Ái (mở rộng)"), "CCN Bảo Thắng (Phố Lu)" (nay "(Thị trấn Phố Lu)"), "CCN Châu Quế Thượng" (không còn trong nguồn chính).

Hệ quả: khi fetch JSON lỗi (mạng yếu/offline), người dùng thấy bộ dữ liệu cũ và **slug sinh từ tên cũ sẽ không khớp** key `unit-details.json` → trang chi tiết rơi về "Thông tin chi tiết đang được cập nhật".

---

## 2. Thông tin có dấu hiệu lỗi thời

1. **Tin tức dừng ở 17/4/2026** (trước phiên này): tin mới nhất trên trang là 17/4, trong khi sự kiện khởi công CCN Thống Nhất 1 ngày 7/5/2026 chưa được đăng. → Đã bổ sung tin này trong cùng PR (Việc 1). Lưu ý thêm: **card tin số 4 thiếu dòng ngày đăng** (các tin khác đều có).
2. **`api/chatbot-context.js` lỗi thời nặng:**
   - Header ghi "Tự sinh từ `build_chatbot_context.py` — DO NOT EDIT" nhưng **script này không có trong repo** → không ai tái sinh được context.
   - Nội dung ghi "76 đơn vị" (hiện 77), "23 CCN đã thành lập (843,78 ha)" (lệch cả hai tổng còn lại), và comment cũ còn nhắc `gemini-1.5-flash` (hiện dùng 2.5). File chưa được build lại sau các đợt enrich dữ liệu lớn (các commit batch T11/2025–T5/2026 và `d219521`).
3. **Mốc thời gian đã qua hạn còn treo trong nội dung hiển thị** (so với 11/6/2026):
   - `ccn-data.json` (Yên Hợp 2, trường `ghiChu`): "kết thúc tiếp nhận hồ sơ ngày **3/5/2026**. Đến…" — đã quá hơn 1 tháng, cần cập nhật kết quả tiếp nhận (chỉ cập nhật khi có thông tin chính thức, không suy đoán).
   - `unit-details.json`: "hoàn thành giải phóng mặt bằng toàn bộ 75 ha trong **Quý I/2026**" — đã qua Quý I; tin khởi công 7/5 xác nhận GPMB đã xong, nên câu "trong Quý I/2026" giờ nên chuyển thì quá khứ.
   - `unit-details.json`: mốc "trước **30/6/2026**" — sắp đến hạn, cần theo dõi để cập nhật sau 30/6.
4. **Nguồn trích dẫn dashboard** ghi "Báo cáo … tháng 4 năm 2026" (`index.html` cuối phần giới thiệu) — sẽ cũ dần; nên có quy ước cập nhật theo quý.
5. **Service worker trên `main` đang ở v35**; PR #1 (bump v36 + cập nhật CLAUDE.md) đang chờ duyệt. Chừng nào chưa merge, người dùng cũ còn kẹt cache `app.js`.
6. `sitemap.xml`: 79 URL có `lastmod 2026-05-23` — chấp nhận được, nhưng có vài URL lastmod 2022/2024 (file PDF cũ) nên rà lại một lượt khi đổi domain.

---

## 3. VẤN ĐỀ CẦN QUYẾT: chuẩn hóa "Yên Hợp" / "Yên Hợp 1" / "giai đoạn I/II"

**KHÔNG tự sửa trong phiên này — chỉ tổng hợp hiện trạng để anh/chị quyết.**

Hiện trong dữ liệu tồn tại **3 thực thể** cùng địa bàn xã Xuân Ái:

| Thực thể | Nhóm | Diện tích | Hiện trạng theo dữ liệu |
|---|---|---|---|
| CCN Yên Hợp | `CUM_CONG_NGHIEP` (đã thành lập) | 12 ha | hoạt động, thành lập 2024 (QĐ 2201/QĐ-UBND ngày 6/11/2024); mô tả ghi "giai đoạn I, 12 ha" |
| CCN Yên Hợp 1 | `CCN_CHUA_DAU_TU` | 63 ha | `ghiChu`: "Giai đoạn II mở rộng CCN Yên Hợp sau 2030" |
| CCN Yên Hợp 2 | `CCN_CHUA_DAU_TU` | 75 ha | `huongPhatTrien`/`ghiChu` dòng 763–768: "Mở rộng CCN Yên Hợp **Giai đoạn II** (tăng lên 75 ha theo QĐ 525/2026)" |

**Các điểm mâu thuẫn cụ thể:**

1. **Cả "Yên Hợp 1" lẫn "Yên Hợp 2" đều tự nhận là "Giai đoạn II mở rộng CCN Yên Hợp"** (`ccn-data.json` dòng 750/755 vs 763/768) — không thể cùng đúng.
2. **`unit-details.json` key `ccn-yen-hop-1`** (dòng 1215–1220): trường `dienTich` = 63 ha (đúng theo ccn-data) nhưng `gioiThieu` lại mô tả "**CCN Yên Hợp giai đoạn I** … diện tích giai đoạn 1 **12 ha**, QĐ 2201/QĐ-UBND ngày 6/11/2024" — tức là đang mô tả **chính CCN Yên Hợp (12 ha) đang hoạt động**, trùng nội dung với key `ccn-yen-hop`. Trang chi tiết "Yên Hợp 1" hiện hiển thị nội dung của cụm khác.
3. **Cụm từ "Yên Hợp giai đoạn I" xuất hiện trên trang công khai** tại: `unit-details.json` dòng 1211 (`ccn-yen-hop`, hợp lý) và dòng 1220 (`ccn-yen-hop-1`, sai chỗ); `ccn-data.json` dòng 841 (trường `baoCao` của Yên Hợp 2: "Cùng địa bàn… với CCN Yên Hợp giai đoạn I (12 ha) đang hoạt động"); tin tức `index.html` dòng 1804 và 1830 dùng cách gọi "**Yên Hợp GĐ II**".
4. **`ccn-polygons.json`** có polygon "CCN Yên Hợp 1" (dòng 1217) và "CCN Yên Hợp 2" (dòng 1313) nhưng **không có polygon cho "CCN Yên Hợp"** (cụm 12 ha đang hoạt động) — cụm duy nhất đang hoạt động lại không có ranh giới trên bản đồ.
5. Hệ quả ba trang tĩnh cùng tồn tại: `units/ccn-yen-hop.html`, `ccn-yen-hop-1.html`, `ccn-yen-hop-2.html` (đều trong sitemap) — nếu chuẩn hóa lại tên, cần xử lý cả redirect/sitemap.

**Hai phương án để anh/chị chọn (chưa thực hiện):**
- **Phương án A — "dự án độc lập":** giữ 3 thực thể Yên Hợp / Yên Hợp 1 / Yên Hợp 2; xóa mọi chữ "giai đoạn I/II" trong mô tả; viết lại `gioiThieu` của `ccn-yen-hop-1` cho đúng cụm 63 ha.
- **Phương án B — "giai đoạn":** coi Yên Hợp là 1 dự án nhiều giai đoạn; gộp/đổi tên các entry theo "Yên Hợp (GĐ I/II)"; ảnh hưởng: slug, key `unit-details`, polygon name, 3 trang tĩnh, sitemap, chatbot context.

---

## 4. Chưa thống nhất giữa hai hệ trang chi tiết (SPA vs `units/*.html`)

**Điểm tốt:** kiểm tra tự động 77/77 trang tĩnh — đoạn `gioiThieu` trong `unit-details.json` **khớp** nội dung trang tĩnh tương ứng (hai hệ được sinh cùng đợt, commit `d219521`). Trang tĩnh có link ngược về SPA (`/#unit/<slug>`).

**Điểm lệch / rủi ro:**

1. **Một chiều:** SPA không có bất kỳ link nào sang `units/*.html` (0 tham chiếu trong `index.html`/`app.js`). Người dùng SPA không bao giờ tới trang tĩnh; hai hệ chỉ "gặp nhau" qua Google.
2. **Không có script sinh trang tĩnh trong repo** (chỉ có `.claude/sync-polygons-from-kml.py`). 77 trang tĩnh được sinh/sửa "thủ công theo đợt". Nghĩa là: **lần tới ai đó sửa `unit-details.json` qua CMS, trang tĩnh sẽ lệch ngay** và không có công cụ nào để đồng bộ lại. Sự "khớp 77/77" hiện tại là trạng thái may mắn tại một thời điểm, không phải cơ chế.
3. Trang tĩnh nhúng số liệu (diện tích, quyết định) tại thời điểm sinh — không tự cập nhật khi `ccn-data.json` đổi (khác SPA luôn fetch JSON mới). Đặc biệt vụ Yên Hợp (mục 3): nếu chuẩn hóa tên, 3 trang tĩnh phải sinh lại tay.
4. Nội dung mục 3.2 (gioiThieu của `ccn-yen-hop-1` sai cụm) **đã lan sang trang tĩnh** `units/ccn-yen-hop-1.html` — minh chứng cho rủi ro nhân đôi lỗi giữa hai hệ.

---

## 5. Đề xuất việc nên làm tiếp (theo thứ tự ưu tiên)

| # | Việc | Lý do ưu tiên | Độ phức tạp |
|---|---|---|---|
| 1 | **Merge PR #1** (bump SW v36) để gỡ kẹt cache `app.js` trên production | Đang ảnh hưởng trực tiếp người dùng; thay đổi 1 dòng đã sẵn | Rất thấp |
| 2 | **Quyết phương án Yên Hợp** (mục 3) rồi sửa đồng bộ ccn-data + unit-details + polygons + 3 trang tĩnh + tin tức + chatbot | Sai nội dung đang hiển thị công khai (trang Yên Hợp 1 mô tả cụm khác) | Trung bình |
| 3 | **Thống nhất bộ số liệu tổng** (mục 1): chọn 1 nguồn sự thật cho {số CCN QH, tổng CCN, tổng diện tích, tổng dự án}, sửa meta/dashboard/giới thiệu về cùng một bộ, chú thích rõ "theo quy hoạch" vs "hiện có hồ sơ" | Uy tín cổng thông tin nhà nước; hiện 3 con số diện tích khác nhau | Trung bình |
| 4 | **Viết lại script `build_chatbot_context.py`** (đã thất lạc) sinh `chatbot-context.js` từ `ccn-data.json` + `unit-details.json`, chạy lại để chatbot hết trả lời số cũ | Chatbot đang trả lời lệch trang; script gốc mất nên càng để lâu càng khó | Trung bình |
| 5 | **Viết script sinh `units/*.html` từ `unit-details.json`** (tương tự script polygon) để hai hệ trang chi tiết không lệch nhau nữa | Loại bỏ rủi ro hệ thống ở mục 4; làm 1 lần dùng mãi | Trung bình–Cao |
| 6 | **Đồng bộ fallback `data.js`** với `ccn-data.json` (hoặc thu nhỏ fallback chỉ còn khung rỗng + thông báo lỗi mạng) | Offline/lỗi mạng đang hiện dữ liệu cũ, sai tên | Thấp |
| 7 | **Cập nhật các mốc quá hạn** (mục 2.3) khi có thông tin chính thức từ Phòng QLCN; đặt lịch rà mốc 30/6/2026 | Tránh nội dung "treo" trên trang công khai | Thấp (cần dữ liệu) |
| 8 | **Đưa tin tức vào dữ liệu/CMS** (hiện hardcode trong `index.html`, mỗi tin mới phải sửa code) + bổ sung dòng ngày cho card tin 4 | Giảm phụ thuộc người biết code; quy trình đăng tin nhanh hơn | Trung bình |
| 9 | Dọn dead code `updateHeaderStats` (mục 1.6) | Vệ sinh code, tránh hiểu nhầm | Rất thấp |
| 10 | Cân nhắc domain chính thức thay `congnghieplaocai.vn` (ảnh hưởng canonical, sitemap, OG của 78 trang) | Hình ảnh cơ quan nhà nước; nên làm trước khi SEO "bám rễ" domain tạm | Trung bình (ngoài code là chính) |

---

*Báo cáo lập tự động bằng đối soát chéo các file dữ liệu trong repo tại commit gốc `9e45262`. Mọi con số "đếm/cộng được" đều tính trực tiếp từ JSON, có thể tái lập.*

# CLAUDE.md

File hướng dẫn cho Claude Code khi làm việc với dự án này.

## Dự án là gì

Cổng thông tin **Khu, Cụm công nghiệp tỉnh Lào Cai** — một website tĩnh do Sở Công Thương tỉnh Lào Cai duy trì, dùng để:

- Tra cứu, hiển thị trên bản đồ 23 CCN đã thành lập + 35 CCN quy hoạch + 20 KCN quy hoạch 2030.
- Hiển thị thống kê (Chart.js), tin tức, văn bản pháp luật (PDF), chi tiết từng CCN.
- Cho cán bộ Sở chỉnh sửa dữ liệu qua **Netlify CMS** mà không cần biết code.

Production deploy: **https://deploy-teal-ten-71.vercel.app** (host kép Netlify + Vercel; Netlify để chạy git-gateway + Identity cho CMS, Vercel cho tốc độ tải public).

Người sở hữu / vận hành: **trangsct@gmail.com** (giao tiếp bằng tiếng Việt). Source code lưu tại `C:\Users\USER\OneDrive\Web KCN CCN` (OneDrive sync — cẩn thận xung đột file khi đang sync).

## Cấu trúc file chính

```
.
├── index.html              # SPA 1 trang ~233KB, chứa toàn bộ markup + section dạng tab
├── app.js                  # Logic ~110KB: map, charts, filter, popup, sidebar, PDF iframes
├── style.css               # CSS ~40KB
├── data.js                 # Dữ liệu fallback (TINH_INFO, HUYEN_LIST, biến global khởi tạo)
├── ccn-data.json           # Nguồn dữ liệu CHÍNH (CMS ghi vào) — CUM_CONG_NGHIEP, CCN_CHUA_DAU_TU, KHU_CONG_NGHIEP
├── ccn-polygons.json       # Polygon ranh giới CCN trên bản đồ
├── unit-details.json       # Chi tiết mở rộng từng CCN (mốc tọa độ, hộ ảnh hưởng, BC…)
├── map-layers.json         # Cấu hình tile layer Leaflet
├── manifest.json + service-worker.js   # PWA
├── admin/
│   ├── index.html          # Netlify CMS entrypoint
│   └── config.yml          # Schema CMS (collections: ccn_hien_huu, …)
├── unit-files/             # Tài liệu riêng từng CCN (ccn-phu-thinh-4, ccn-bat-xat, …)
├── *.pdf                   # 6 file văn bản pháp luật (NĐ 32/2024, NĐ 35/2022, NQ 34, QĐ quy chế CCN…)
├── netlify.toml            # Build config Netlify (publish = ".")
└── vercel.json             # Header config cho service worker + manifest trên Vercel
```

## Công nghệ

- **Static site** thuần (HTML + CSS + JS), **không bundler**, không npm, không build step. Mở trực tiếp `index.html` là chạy được.
- **Leaflet 1.9.4** (CDN unpkg) cho bản đồ + popup tự né nav sticky.
- **Chart.js** (CDN) cho biểu đồ thống kê.
- **Netlify CMS + git-gateway + Netlify Identity** cho editorial workflow — biên tập sửa `ccn-data.json` rồi merge PR.
- **PWA** với service worker tự cache (đang ở **v8** — bump khi đổi asset).
- Host: **Netlify** (CMS, Identity) + **Vercel** (public domain chính).

## Quy ước

- **Không có bundler**: thêm script bằng thẻ `<script>` trong `index.html`, không import/export.
- **Mọi state ở biến global**: `CUM_CONG_NGHIEP`, `CCN_CHUA_DAU_TU`, `KHU_CONG_NGHIEP`, `THONG_KE`, `map`, `markers`, `charts` đều là biến toàn cục trong `app.js` / `data.js`. Khi thêm tính năng, theo pattern này — đừng đột ngột chuyển sang module ES.
- **2 nguồn dữ liệu**:
  - `data.js` nạp đồng bộ trước (giá trị mặc định / fallback nếu fetch fail).
  - `ccn-data.json` được fetch trong `DOMContentLoaded` rồi **ghi đè** lên biến global. Nguồn này là sự thật — CMS chỉ sửa file JSON.
  - Khi thêm trường mới: cập nhật cả `data.js` (fallback) + `ccn-data.json` (thật) + `admin/config.yml` (schema CMS) + chỗ render trong `app.js`.
- **PDF iframe**: dùng thuộc tính `data-pdf-src` thay vì `src` (browser sẽ không tự tải lúc parse HTML). JS xử lý sau DOMContentLoaded: desktop copy sang `src`, mobile thay bằng nút "Mở file PDF".
- **Service worker cache version**: bump số version trong `service-worker.js` mỗi khi thay đổi asset chính, nếu không user sẽ thấy bản cũ.
- **Popup Leaflet**:
  - `autoPanPaddingTopLeft` được tính ĐỘNG từ `#header.offsetHeight + #main-nav.offsetHeight + 20` (xem `updatePopupAutoPanPadding` trong app.js đầu file). Khi mở popup, page tự cuộn xuống để map full viewport (xử lý trong `map.on('popupopen')` của initMap).
  - z-index popup 950 > main-nav 900 > header 100.
  - `.leaflet-popup-content` có `max-height: 60vh; overflow-y: auto` (tránh clip ở viewport thấp).
- **XSS — luôn escape data từ CMS** (xem mục "Pattern bảo mật" bên dưới).
- **Ngôn ngữ**: toàn bộ UI, comment, commit message bằng **tiếng Việt**. Giữ phong cách này.
- **Commit message**: theo style hiện tại — câu mô tả ngắn gọn tiếng Việt, có lý do thay đổi. Xem `git log` để theo.

## Pattern bảo mật (đã áp dụng từ commit `108cc2c`)

- **`escapeHtml()`** ([app.js dòng cuối](app.js)) escape 5 ký tự `& < > " '` — dùng cho MỌI text từ `ccn-data.json` / `unit-details.json` render qua `innerHTML`.
- **Pattern click → trang chi tiết**: KHÔNG dùng `onclick="openUnitDetail('${slug}','${ten}')"` (rủi ro break attribute nếu `ten` có ký tự đặc biệt). Thay bằng:
  ```js
  // Markup
  `<div data-slug="${escapeHtml(slug)}" data-ten="${escapeHtml(ten)}">…</div>`
  // Handler — gắn 1 lần trên parent (event delegation), onclick = function (không nhân đôi khi re-render)
  container.onclick = function(e) {
      var target = e.target.closest('[data-slug]');
      if (target) openUnitDetail(target.dataset.slug, target.dataset.ten);
  };
  ```
- **Leaflet popup**: dùng `map.on('popupopen', ...)` + `e.popup.getElement().querySelector('[data-action="open-detail"]')` để gắn handler động cho mỗi popup.
- **URL trong attribute** (`href`, `src` từ CMS như `details.kml`, `vb.file`): bọc `escapeHtml()`.
- **`mailto:?subject=...`**: dùng `encodeURIComponent(...)` cho subject.
- **Demo "đúng chuẩn"**: 2 trường rủi ro cao nhất trong `openDetailModal` (ten header + moTa) set qua `textContent` thay vì `innerHTML`.
- **`details.gioiThieu` (unit-intro)** là TRƯỜNG HTML CÓ Ý ĐỒ — admin viết HTML markup. KHÔNG escape (sẽ phá format). Rủi ro thấp vì chỉ admin được sửa.

## Điểm yếu / việc đang treo

1. **Monolith file lớn**: `index.html` ~233KB và `app.js` ~110KB chứa tất cả section/tab/logic. Tìm/sửa khó. Đừng refactor toàn bộ — chỉ tách khi user yêu cầu rõ.
2. **2 nguồn dữ liệu trùng lặp**: `data.js` (fallback) và `ccn-data.json` (CMS) dễ lệch nhau. Khi sửa, nhớ đồng bộ cả hai.
3. **PDF nặng**: tổng ~32 MB PDF trong repo (NĐ 35/2022 ~8.6MB, bản đồ ~8MB, TT 14/2024 ~5.9MB…). Mỗi commit `git push` khá lâu trên mạng yếu. Không tự ý xóa — đây là văn bản pháp luật bắt buộc public.
4. **OneDrive sync**: làm việc trực tiếp trong thư mục OneDrive đang đồng bộ. Tránh đổi tên file lớn liên tục hoặc viết hàng loạt — dễ gây race với OneDrive client.
5. **Service worker cache**: nếu quên bump version, user sẽ giữ bản cũ rất lâu — đặc biệt trên mobile. Khi user phàn nàn "tôi không thấy thay đổi", hỏi họ DevTools → Application → Service Workers → Unregister → reload.
6. **🎯 ĐỘ CHÍNH XÁC TỌA ĐỘ KHU/CỤM TRÊN BẢN ĐỒ** — vấn đề lớn đang treo, xem mục "Việc dài hạn" bên dưới.

## Việc dài hạn

### A. Tăng độ chính xác tọa độ KCN/CCN trên bản đồ

**Hiện trạng**: tọa độ `lat`/`lng` trong `ccn-data.json` (cho `CUM_CONG_NGHIEP`, `CCN_CHUA_DAU_TU`, `KHU_CONG_NGHIEP`) được nhập thủ công, có thể lệch — chỉ marker điểm, chưa có polygon ranh giới chuẩn cho nhiều CCN.

**Mục tiêu**: mỗi KCN/CCN có (1) tọa độ trung tâm chính xác, (2) ranh giới polygon đúng theo quyết định thành lập.

**Nguồn dữ liệu CẦN bổ sung** (đề xuất user cung cấp):

1. **Tọa độ pháp lý từ quyết định thành lập từng CCN** — thường là bản đồ kèm theo QĐ với danh sách mốc giới (point N1, N2, …) có tọa độ VN-2000 hoặc WGS-84. Hiện đã có vài CCN trong `unit-files/ccn-*/` (vd. `ccn-bat-xat`, `ccn-phu-thinh-4`). Cần bổ sung phần còn lại.
2. **File KML / SHP / GeoJSON** của Sở Tài nguyên & Môi trường (nếu có) — ranh giới quy hoạch sử dụng đất.
3. **Bản đồ quy hoạch chính thức** (`ban-do-khu-cum-cn-2025.pdf` đã có 8MB trong repo) — có thể trích xuất tọa độ nếu PDF là layer vector.
4. **Cổng dữ liệu mở tỉnh Lào Cai** — `bando.laocai.gov.vn` (đã có link trong layer control); kiểm tra xem có WMS / WFS endpoint để overlay trực tiếp không.
5. **Cross-check Google Earth / Google Maps**: dùng để verify hợp lý cho từng CCN đã có (đối chiếu địa danh, đường, sông).

**Cách triển khai khi có dữ liệu**:
- Cập nhật `lat`/`lng` cho từng CCN trong `ccn-data.json` (qua CMS).
- Polygon ranh giới: bổ sung vào `ccn-polygons.json` (đã có cấu trúc sẵn, format GeoJSON-like). Mỗi CCN polygon là 1 array `[[lat,lng], …]`.
- KCN polygon: hiện chưa có file riêng. Cân nhắc tạo `kcn-polygons.json` cùng cấu trúc.

**Câu hỏi cần trả lời từ user khi triển khai**:
- Anh đã có file QĐ thành lập + bản đồ kèm theo cho cả 23 CCN hiện hữu chưa? Bao nhiêu CCN còn thiếu?
- Tọa độ trong QĐ là hệ VN-2000 hay WGS-84? (Nếu VN-2000 phải chuyển hệ trước khi đưa lên Leaflet, vì Leaflet dùng WGS-84/EPSG:4326).
- Có file KML / SHP / GeoJSON gốc nào không? Nếu có, chuyển GeoJSON là nhanh nhất.
- 35 CCN chưa thành lập đã có bản đồ chỉ giới nghiên cứu chưa, hay mới chỉ có địa danh xã/phường? Nếu chỉ có địa danh, tọa độ tạm thời sẽ là tâm xã.

### B. Refactor monolith (low priority)
Khi muốn maintainability lâu dài: tách `app.js` thành các module nhỏ (map.js, render.js, modal.js, charts.js…). Cần build step. Hiện không cần.

## Khi user yêu cầu thay đổi dữ liệu CCN

- Thường họ sẽ sửa thẳng `ccn-data.json` hoặc `unit-details.json`.
- Nếu thêm CCN mới: cập nhật cả `ccn-data.json` + `ccn-polygons.json` (nếu có ranh giới) + có thể tạo folder `unit-files/ccn-<slug>/`.
- Nếu chỉ chỉnh con số, mô tả: chỉ cần sửa `ccn-data.json`.
- Nếu chỉnh tọa độ: xem mục "Việc dài hạn A" để hỏi nguồn dữ liệu chuẩn trước.

## Lịch sử commit gần đây (để hiểu context)

```
e6a8143  fix: trang chi tiết KCN hiển thị tên đẹp + badge đúng (findUnitByName tra KHU_CONG_NGHIEP)
108cc2c  fix(security): vá lỗ hổng XSS qua innerHTML — escape toàn bộ dữ liệu CMS
7ce7481  feat: nút chuyển lớp Vệ tinh / Địa hình cho bản đồ KCN + CCN QH
f6b9624  feat: tắt banner gợi ý cài đặt PWA
d0ed26b  fix: popup bản đồ bị clip khi viewport thấp — tự cuộn + max-height 60vh
87fce98  chore: viết đầy đủ các chữ viết tắt KCN/CCN trên UI
bbc3707  fix: popup bản đồ bị che — autoPanPadding tính động theo header+nav
118064d  docs: thêm CLAUDE.md hướng dẫn cho AI agent
```

# CLAUDE.md

File hướng dẫn cho Claude Code khi làm việc với dự án này.

## Dự án là gì

Cổng thông tin **Khu, Cụm công nghiệp tỉnh Lào Cai** — một website tĩnh do Sở Công Thương tỉnh Lào Cai duy trì, dùng để:

- Tra cứu, hiển thị trên bản đồ 23 CCN đã thành lập + 35 CCN quy hoạch + 20 KCN quy hoạch 2030.
- Hiển thị thống kê (Chart.js), tin tức, văn bản pháp luật (PDF), chi tiết từng CCN.
- Cho cán bộ Sở chỉnh sửa dữ liệu qua **Netlify CMS** mà không cần biết code.

Production deploy: **https://www.congnghieplaocai.vn** (host kép Netlify + Vercel; Netlify để chạy git-gateway + Identity cho CMS, Vercel cho tốc độ tải public).

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
├── unit-details.json       # Chi tiết mở rộng từng CCN/KCN (mốc tọa độ, hộ ảnh hưởng, BC…) — nguồn cho trang chi tiết động trong SPA, key = slug
├── map-layers.json         # Cấu hình tile layer Leaflet
├── manifest.json + service-worker.js   # PWA (SW đang ở v36)
├── admin/
│   ├── index.html          # Netlify CMS entrypoint
│   └── config.yml          # Schema CMS (collections: ccn_hien_huu, …)
├── api/                    # Serverless trên Vercel (KHÔNG phải static)
│   ├── chat.js             # Vercel Edge Function: proxy gọi Google Gemini (free tier) cho chatbot. Endpoint POST /api/chat. Giữ GEMINI_API_KEY ở server.
│   └── chatbot-context.js  # Export CHATBOT_CONTEXT (~72KB) — cơ sở dữ liệu nhồi vào system prompt của Gemini
├── units/                  # 77 trang HTML TĨNH độc lập từng đơn vị (ccn-*.html, kcn-*.html) — bản SEO-friendly (meta/OG/canonical), nằm trong sitemap.xml; KHÔNG link từ nav SPA, tồn tại song song với trang chi tiết động
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
- **PWA** với service worker tự cache (đang ở **v36** — bump `CACHE_VERSION` mỗi khi đổi asset lõi).
- **Chatbot AI**: `api/chat.js` (Vercel Edge Function) proxy gọi **Google Gemini** — free tier. Danh sách `MODELS` thử lần lượt từ bản Flash cao nhất xuống (`gemini-3.8-flash` → 3.7 → 2.5-flash → 2.5-flash-lite làm lưới an toàn); bản chưa mở cho khóa API trả 404 thì tự bỏ qua, nên ra bản mới chỉ cần thêm một dòng vào đầu danh sách. Bạn chốt 03/9/2026: luôn ưu tiên bản Flash cao nhất, không dùng Pro. Context từ `api/chatbot-context.js`. Đây là phần serverless duy nhất, chỉ chạy trên Vercel.
- Host: **Netlify** (CMS, Identity) + **Vercel** (public domain chính + serverless `api/`).

## Quy ước

- **Không có bundler**: thêm script bằng thẻ `<script>` trong `index.html`, không import/export.
- **Mọi state ở biến global**: `CUM_CONG_NGHIEP`, `CCN_CHUA_DAU_TU`, `KHU_CONG_NGHIEP`, `THONG_KE`, `map`, `markers`, `charts` đều là biến toàn cục trong `app.js` / `data.js`. Khi thêm tính năng, theo pattern này — đừng đột ngột chuyển sang module ES.
- **2 nguồn dữ liệu**:
  - `data.js` nạp đồng bộ trước (giá trị mặc định / fallback nếu fetch fail).
  - `ccn-data.json` được fetch trong `DOMContentLoaded` rồi **ghi đè** lên biến global. Nguồn này là sự thật — CMS chỉ sửa file JSON.
  - Khi thêm trường mới: cập nhật cả `data.js` (fallback) + `ccn-data.json` (thật) + `admin/config.yml` (schema CMS) + chỗ render trong `app.js`.
- **PDF iframe**: dùng thuộc tính `data-pdf-src` thay vì `src` (browser sẽ không tự tải lúc parse HTML). JS xử lý sau DOMContentLoaded: desktop copy sang `src`, mobile thay bằng nút "Mở file PDF".
- **Service worker cache version**: bump `CACHE_VERSION` trong `service-worker.js` mỗi khi thay đổi asset chính, nếu không user sẽ thấy bản cũ. Chiến lược: **network-first cho HTML + JSON** (`index.html`, `ccn-data.json`, `unit-details.json`… luôn lấy bản mới), **cache-first cho asset tĩnh** (`app.js`, `data.js`, `style.css`, ảnh, font, PDF — chỉ thay khi đổi version). ⚠️ Vì logic render nằm trong `app.js` (cache-first), nếu sửa `app.js` mà QUÊN bump version thì user kẹt bản cũ dù JSON đã mới — đây là nguyên nhân điển hình của lỗi "Thông tin chi tiết đang được cập nhật" còn hiện trên production dù `unit-details.json` đã đủ dữ liệu. Khi bump version: SW mới activate → xóa cache cũ → `clients.claim()` → postMessage `sw-updated` → `index.html` tự `location.reload()`.
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

### A. Độ chính xác tọa độ KCN/CCN — workflow KML chuẩn

**Hiện trạng (cập nhật 7/2026)**: `ccn-polygons.json` được sinh từ bộ ranh giới TỔNG HỢP `unit-files/_tong-hop/ranh-gioi-kcn-ccn.kml` (giải nén từ `Ranh_gioi_KCN_CCN_Lao_Cai.kmz` — Sở tổng hợp từ QĐ thành lập, hồ sơ quy hoạch và báo cáo xã/phường, kèm bảng tọa độ VN-2000 `Toa_do_KCN_CCN_Lao_Cai_sapxep.xlsx`). Tổng **57 ranh giới** (16 KCN + 41 CCN), trong đó 27 là ranh TẠM (`is_approx: true` — trích KMZ/CAD 2025 hoặc báo cáo chờ hồ sơ gốc, vẽ NÉT ĐỨT trên bản đồ chung). Chưa có ranh giới (hiển thị chấm cam): KCN Bắc Duyên Hải, Cốc Mỳ - Trịnh Tường, Bát Xát, Cam Đường, Thống Nhất, Đông Phố Mới + ~19 CCN. **Script sinh file: `python .claude/import-polygons-from-kmz.py`** (hỗ trợ `--dry-run`; META mapping ở đầu script; KHÔNG chạy script cũ `sync-polygons-from-kml.py` nữa — các KML lẻ trong `unit-files/` có thể lỗi thời so với bộ tổng hợp). Tên polygon trong `ccn-polygons.json` là tên ĐẦY ĐỦ trùng `ten` trong `ccn-data.json` (để bản đồ chung merge được mô tả và slugify ra trang chi tiết). Tab **"🗺️ Bản đồ chung KCN–CCN"** (`data-tab="ccnranhgioi"`) đã khôi phục trên nav từ 7/2026: polygon chuẩn = nét liền, ranh tạm = nét đứt, chưa có tọa độ = chấm cam.

**Workflow chuẩn của Sở** (đã thiết lập từ CCN Thống Nhất 1):
1. Cán bộ nhận "Bảng tọa độ ranh giới CCN.docx" từ QĐ thành lập (hệ **VN-2000 / TM-3** — kinh tuyến trục 104°45' cho phía Tây tỉnh, 105°00' cho phía Đông).
2. Mở Google Earth Pro → tạo placemark từng mốc + Polygon → File > Save Place As → KML.
3. Đặt vào `unit-files/ccn-<slug>/ranh-gioi.kml` (đây là chuẩn vàng).
4. Đặt thêm `ranh-gioi.kmz` (Google Earth tự tạo) + bản scan QĐ (`qd-XXX.pdf`) cùng folder để truy vết.
5. Chạy `python .claude/sync-polygons-from-kml.py` để tự ghi polygon vào `ccn-polygons.json` với `is_approx: false` + field `source` trỏ về KML.
6. Bump SW version → commit → push.

**Script `.claude/sync-polygons-from-kml.py`**:
- Đọc tất cả `unit-files/*/ranh-gioi.kml` theo MAPPING slug→name (định nghĩa trong script).
- Convert KML lng,lat → JSON [lat, lng] (Leaflet dùng [lat, lng]).
- Hỗ trợ `--dry-run` để xem diff trước khi ghi.
- Khi thêm CCN mới có KML, chỉ cần thêm 1 dòng vào `MAPPING` ở đầu script.

**Nguồn dữ liệu để mở rộng**:
1. QĐ thành lập + bản đồ kèm theo cho 19 CCN đã thành lập còn lại + 32 CCN QH.
2. KCN: hiện chưa có folder nào trong `unit-files/`. Cần tạo `unit-files/kcn-<slug>/ranh-gioi.kml` theo cùng workflow.
3. Cổng `bando.laocai.gov.vn` (link đã có trong map) — kiểm tra WMS/WFS endpoint để overlay trực tiếp (xa hơn).
4. Cross-check Google Earth cho các CCN đang hoạt động (dễ thấy nhà xưởng trên ảnh vệ tinh) — tạo KML "tạm OK" với note `is_approx: true` nếu chưa có QĐ chính thức.

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

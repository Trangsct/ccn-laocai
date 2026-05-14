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
├── app.js                  # Logic ~107KB: map, charts, filter, popup, sidebar, PDF iframes
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
- **PWA** với service worker tự cache (đang ở version v2 — bump khi đổi asset).
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
- **Popup Leaflet**: đã cấu hình `autoPanPaddingTopLeft: [20, 140]` để né header + main-nav (z-index popup 950 > nav 900).
- **Ngôn ngữ**: toàn bộ UI, comment, commit message bằng **tiếng Việt**. Giữ phong cách này.
- **Commit message**: theo style hiện tại — câu mô tả ngắn gọn tiếng Việt, có lý do thay đổi. Xem `git log` để theo.

## Điểm yếu đã biết (cần để ý khi sửa)

1. **XSS qua `innerHTML`**: app.js có ~16 chỗ dùng `innerHTML` với dữ liệu từ `ccn-data.json`. Vì CMS có editorial workflow + chỉ admin được duyệt nên rủi ro thấp, nhưng nếu thêm field text mới hiển thị qua `innerHTML` cần cân nhắc escape hoặc đổi sang `textContent`.
2. **Monolith file lớn**: `index.html` ~233KB và `app.js` ~107KB chứa tất cả section/tab/logic. Tìm/sửa khó. Đừng refactor toàn bộ — chỉ tách khi user yêu cầu rõ.
3. **2 nguồn dữ liệu trùng lặp**: `data.js` (fallback) và `ccn-data.json` (CMS) dễ lệch nhau. Khi sửa, nhớ đồng bộ cả hai.
4. **PDF nặng**: tổng ~32 MB PDF trong repo (NĐ 35/2022 ~8.6MB, bản đồ ~8MB, TT 14/2024 ~5.9MB…). Mỗi commit `git push` khá lâu trên mạng yếu. Không tự ý xóa — đây là văn bản pháp luật bắt buộc public.
5. **OneDrive sync**: làm việc trực tiếp trong thư mục OneDrive đang đồng bộ. Tránh đổi tên file lớn liên tục hoặc viết hàng loạt — dễ gây race với OneDrive client.
6. **Service worker cache**: nếu quên bump version, user sẽ giữ bản cũ rất lâu — đặc biệt trên mobile.

## Khi user yêu cầu thay đổi dữ liệu CCN

- Thường họ sẽ sửa thẳng `ccn-data.json` hoặc `unit-details.json`.
- Nếu thêm CCN mới: cập nhật cả `ccn-data.json` + `ccn-polygons.json` (nếu có ranh giới) + có thể tạo folder `unit-files/ccn-<slug>/`.
- Nếu chỉ chỉnh con số, mô tả: chỉ cần sửa `ccn-data.json`.

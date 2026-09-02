# Đồng bộ văn bản mới từ QLVB lên 2 trang web (userscript Tampermonkey)

Cổng đăng nhập tập trung `login.yenbai.gov.vn` có captcha bắt buộc nên bot không tự đăng nhập được
từ GitHub Actions (đã thử ngày 02/9/2026). Phương án thay thế: cán bộ đăng nhập QLVB như thường,
script `tools/qlvb-sync.user.js` chạy trong Chrome đọc bảng Văn bản đến / Văn bản đi rồi gửi lên GitHub.

## Cài đặt (3 việc, chỉ bấm chuột)

1. **Cài Tampermonkey**: mở Chrome, vào chrome.google.com/webstore, gõ Tampermonkey, bấm "Thêm vào Chrome".
   Bấm biểu tượng mảnh ghép (góc phải thanh địa chỉ) → bấm ghim cạnh Tampermonkey để nó hiện ra ngoài.
2. **Tạo token**: mở github.com/settings/personal-access-tokens/new. Tên "qlvb-sync", Expiration 1 năm.
   Repository access → "Only select repositories" → tích `ccn-laocai` và `vlncn-laocai`.
   Repository permissions → dòng **Contents** → "Read and write". Bấm Generate token, copy chuỗi `github_pat_...` (chỉ hiện 1 lần).
3. **Cài script**: dán link sau vào thanh địa chỉ Chrome, Tampermonkey hiện trang cài, bấm **Install**:

   https://raw.githubusercontent.com/Trangsct/ccn-laocai/main/tools/qlvb-sync.user.js

   Mở QLVB, đăng nhập, vào Văn bản đến. Khi có văn bản cần gửi, hộp thoại hiện lên hỏi token: dán chuỗi ở bước 2, bấm OK.
   Token lưu trong Tampermonkey trên máy, các lần sau tự dùng.

Từ đó chỉ mở QLVB như mọi ngày. Góc dưới phải hiện thông báo số văn bản đã gửi.

## Menu Tampermonkey (bấm biểu tượng Tampermonkey khi đang ở trang QLVB)

- **Đổi token GitHub (QLVB sync)**: nhập lại token khi hết hạn hoặc đổi.
- **Xóa token GitHub (QLVB sync)**.
- **Quên danh sách đã gửi (gửi lại từ đầu)**: xóa bộ nhớ số ký hiệu đã gửi (GitHub vẫn tự loại trùng).

Token sai hoặc hết hạn: script tự hỏi lại ngay khi GitHub trả lỗi 401/403.

## Script làm gì

- Mỗi 4 giây quét trang; khi thấy bảng văn bản (tự nhận diện cột theo tiêu đề: Số/Ký hiệu, Ngày, Cơ quan, Trích yếu, Độ mật) thì đọc từng dòng.
- Chỉ lấy văn bản độ mật **Thường**, ngày trong 7 ngày gần đây, trích yếu có từ khóa KCN/CCN hoặc VLNCN (bộ từ khóa `TU_KHOA` chép từ `scripts/qlvb_bot.py`).
- Đọc `van-ban-moi.json` hiện có trên GitHub, chỉ gửi văn bản chưa có (so theo số ký hiệu), giữ tối đa 200 văn bản, ghi bằng GitHub Contents API vào:
  - `Trangsct/ccn-laocai` → `van-ban-moi.json` (nhóm KCCN)
  - `Trangsct/vlncn-laocai` → `van-ban-moi.json` (nhóm VLNCN)
- Ghi nhớ số ký hiệu đã gửi trong Tampermonkey để không gửi lại.
- Tự cập nhật phiên bản mới khi file trên nhánh `main` đổi (`@updateURL`), Tampermonkey kiểm tra định kỳ.
- Vercel tự deploy khi có commit.

## Khi bảng không được nhận diện

Script tự dò cột theo chữ trên tiêu đề. Nếu không thấy thông báo nào dù bảng đã hiện, lưu trang
(Ctrl+S → "Trang web, hoàn chỉnh") gửi cho Claude Code để khóa cứng chỉ số cột tại dòng `const COT`.

## Hiển thị trên website

Bước sau: thêm mục "Văn bản mới" trên congnghieplaocai.vn và vlncn-laocai.vercel.app đọc từ
`van-ban-moi.json`, làm qua PR để xem preview trước khi merge.

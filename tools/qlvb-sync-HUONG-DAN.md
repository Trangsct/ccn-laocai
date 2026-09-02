# Đồng bộ văn bản mới từ QLVB lên 2 trang web (userscript Tampermonkey)

Cổng đăng nhập tập trung `login.yenbai.gov.vn` có captcha bắt buộc nên bot không tự đăng nhập được
từ GitHub Actions (đã thử ngày 02/9/2026). Phương án thay thế: cán bộ đăng nhập QLVB như thường,
script `tools/qlvb-sync.user.js` chạy trong Chrome đọc bảng Văn bản đến / Văn bản đi rồi gửi lên GitHub.

## Cài đặt (5 bước)

1. Chrome → Chrome Web Store → tìm **Tampermonkey** → Thêm vào Chrome.
2. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token: chọn 2 repo `ccn-laocai` và `vlncn-laocai`, Repository permissions → **Contents: Read and write**. Copy token (không dán vào chat).
3. Bấm biểu tượng Tampermonkey → **Create a new script** → xóa hết, dán toàn bộ nội dung file `tools/qlvb-sync.user.js`.
4. Sửa dòng `const GITHUB_TOKEN = 'DAN_TOKEN_VAO_DAY';` → dán token vào giữa 2 dấu nháy. Ctrl+S.
5. Mở QLVB, đăng nhập (nhập captcha như thường), vào Văn bản đến / Văn bản đi. Góc dưới phải hiện thông báo số văn bản đã gửi.

## Script làm gì

- Mỗi 4 giây quét trang; khi thấy bảng văn bản (tự nhận diện cột theo tiêu đề: Số/Ký hiệu, Ngày, Cơ quan, Trích yếu, Độ mật) thì đọc từng dòng.
- Chỉ lấy văn bản độ mật **Thường**, ngày trong 7 ngày gần đây, trích yếu có từ khóa KCN/CCN hoặc VLNCN (bộ từ khóa `TU_KHOA` chép từ `scripts/qlvb_bot.py`).
- Đọc `van-ban-moi.json` hiện có trên GitHub, chỉ gửi văn bản chưa có (so theo số ký hiệu), giữ tối đa 200 văn bản, ghi bằng GitHub Contents API vào:
  - `Trangsct/ccn-laocai` → `van-ban-moi.json` (nhóm KCCN)
  - `Trangsct/vlncn-laocai` → `van-ban-moi.json` (nhóm VLNCN)
- Ghi nhớ số ký hiệu đã gửi trong Tampermonkey để không gửi lại.
- Vercel tự deploy khi có commit.

## Khi bảng không được nhận diện

Script tự dò cột theo chữ trên tiêu đề. Nếu không thấy thông báo nào dù bảng đã hiện, lưu trang
(Ctrl+S → "Trang web, hoàn chỉnh") gửi cho Claude Code để khóa cứng chỉ số cột tại dòng `const COT`.

## Hiển thị trên website

Bước sau: thêm mục "Văn bản mới" trên congnghieplaocai.vn và vlncn-laocai.vercel.app đọc từ
`van-ban-moi.json`, làm qua PR để xem preview trước khi merge.

# Hướng dẫn cài Bot Data360X trên máy cơ quan (Windows)

Bot đọc Văn bản đến / Văn bản đi trên Data360X (csdlvb.laocai.gov.vn) lúc 18h hằng ngày, tải PDF của
văn bản thuộc lĩnh vực theo dõi và đẩy vào thư mục `inbox/` của repo đích trên GitHub. Từ đó GitHub
Actions đọc PDF bằng Gemini và cập nhật website. Bạn chỉ đăng nhập Data360X khi bot báo phiên hết hạn.

Giai đoạn hiện tại chỉ nối **loại 1: Giấy phép sử dụng VLNCN** (số ký hiệu có GP-SCT ở Văn bản đi
do Phòng Công nghiệp soạn, hoặc GP-UBND ở Văn bản đến có "vật liệu nổ" trong trích yếu) → repo `vlncn-laocai`.

## A. Chuẩn bị (5 phút, làm 1 lần)

1. **Token GitHub**: mở github.com/settings/personal-access-tokens/new. Tên `bot-data360x`, Expiration 1 năm.
   Repository access → Only select repositories → tích 4 repo `ccn-laocai`, `vlncn-laocai`,
   `vlncn-laocai-files`, `skill-sct`. Repository permissions → **Contents: Read and write**.
   Bấm Generate token, copy chuỗi `github_pat_...` (chỉ hiện 1 lần, để sẵn trong Notepad).
2. Bot tự đặt vào `D:\du-an` nếu máy có ổ D, không thì `C:\du-an` (laptop thường chỉ có ổ C). Trong hướng dẫn, chỗ nào ghi `D:\du-an` thì trên máy chỉ có ổ C đọc là `C:\du-an`.

## B. Cài đặt (mỗi bước chỉ bấm)

1. Mở **PowerShell** (Start → gõ PowerShell → Enter), dán lệnh sau rồi Enter để tải file cài:

   ```
   $r = if (Test-Path D:\) {'D:\du-an'} else {'C:\du-an'}; mkdir "$r\bot" -Force | Out-Null; curl.exe -sSL -o "$r\bot\cai-dat.bat" https://raw.githubusercontent.com/Trangsct/ccn-laocai/main/bot/cai-dat.bat; explorer "$r\bot"
   ```

   Cửa sổ thư mục `du-an\bot` (ổ D hoặc C) mở ra, trong đó có `cai-dat.bat`.
2. Nháy đúp **cai-dat.bat**. Nó tự cài Python (nếu chưa có), Playwright, Chromium, tải các file bot,
   rồi hỏi token: dán chuỗi `github_pat_...`, Enter. Nếu nó báo "Da cai Python, hay dong cua so nay"
   thì đóng rồi nháy đúp cai-dat.bat lần nữa.
3. Nháy đúp **dang-nhap-lan-dau.bat**. Chrome (hồ sơ riêng của bot) mở trang Data360X: đăng nhập như
   thường, nhập captcha. Khi thấy trang chủ Data360X, quay lại cửa sổ đen bấm Enter. Phiên được lưu.
4. Nháy đúp **chay-thu.bat**. Bot chạy 1 lần ở chế độ soi: đọc 2 danh sách, mở thử trang chi tiết, tải
   PDF, lưu tất cả vào `D:\du-an\bot-profile\logs\soi\` và KHÔNG đẩy gì lên GitHub. Xong, nén thư mục
   `logs\soi` (chuột phải → Send to → Compressed folder) gửi cho Claude Code để khóa selector trang chi tiết.
5. Khi Claude Code báo bot đã chạy thật được: chuột phải **dat-lich.bat** → **Run as administrator**.
   Nó đăng ký 4 lịch: 18:00 chạy chính; 07:00, 12:00, 15:00 giữ phiên. Chạy cả T7, CN, kể cả khi khóa
   màn hình, đánh thức máy nếu đang ngủ. Máy phải bật (không tắt nguồn).

## C. Bot chạy thế nào, kiểm tra ở đâu

- **Bot tự cập nhật**: mỗi lần chạy (tự động 18h hay Bạn bấm `cap-nhat-ngay.bat`, `quet-lai-120-ngay.bat`, `chay-thu.bat`),
  file `tai-ban-moi.bat` tải bản mới nhất của script Python và TẤT CẢ file .bat từ GitHub về `D:\du-an\bot`.
  Vì vậy khi tôi sửa bot, Bạn không phải tải lại gì; máy thứ hai cũng tự lấy bản mới.
- Log: `D:\du-an\bot-profile\logs\<ngày>.log`. Mở bằng Notepad, dòng cuối là tóm tắt: quét bao nhiêu
  văn bản, đẩy bao nhiêu file, lỗi gì.
- Kiểm tra bot đã chạy chưa: mở Task Scheduler (Start → gõ Task Scheduler), mục Task Scheduler Library,
  4 dòng "Bot Data360X - ...", cột Last Run Time / Last Run Result (0x0 là thành công).
- Kết quả trên GitHub: repo `vlncn-laocai` → thư mục `inbox/` có file `<số>_GP-UBND.pdf` + `.json`,
  và `inbox/_da-xu-ly.json` là danh sách đã tải (bot không tải trùng).

## D. Khi bot báo "cần bạn đăng nhập lại"

Bot hiện thông báo Windows (và Telegram nếu đã cấu hình) rồi để nguyên cửa sổ Chrome ở trang đăng nhập.
Bạn đăng nhập trong cửa sổ đó, bot tự nhận ra và chạy tiếp (chờ tối đa 6 lần × 15 phút). Nếu lỡ mất,
nháy đúp `dang-nhap-lan-dau.bat`, đăng nhập, rồi nháy đúp `chay-thu.bat` hoặc chờ 18h hôm sau.

## E. Telegram (làm ở Bước 3, 3 phút)

Mở Telegram → tìm **BotFather** → gửi `/newbot` → đặt tên → nhận token. Tìm **userinfobot** → gửi
`/start` → nhận chat id. Mở `D:\du-an\bot-profile\config.json` bằng Notepad, dán vào 2 dòng
`telegram_token` và `telegram_chat_id`, lưu. Từ đó mỗi lần chạy bot nhắn 1 tin tóm tắt.

## F. Đổi token, đổi máy

- Đổi token GitHub: nháy đúp `cai-dat.bat`, dán token mới (các bước khác tự bỏ qua vì đã cài).
- Cài sang máy khác: làm lại mục B. Hồ sơ Chrome nằm ở `D:\du-an\bot-profile\chrome-profile`, không
  chép sang máy khác, đăng nhập lại là xong.

## GitHub ra lệnh cho máy này chạy (cách đang dùng từ 04/9/2026)

Cổng Data360X không cho máy chủ nước ngoài đọc dữ liệu, nên bot vẫn phải chạy trên máy đã đăng nhập. Cách
làm hiện nay: GitHub giữ lịch và ra lệnh, máy cơ quan thi hành.

**Cài một lần**: bấm CHUỘT PHẢI vào `cai-runner.bat` → **Run as administrator**. Làm theo hai bước hiện trên
màn hình: mở trang GitHub nó chỉ, copy chuỗi token ở mục Configure, dán vào rồi Enter. Xong là máy nhận lệnh
được, chạy nền như một dịch vụ, không cần mở cửa sổ nào.

**Từ đó về sau**:

- Tự động **11h30 thứ Tư hằng tuần**.
- Muốn chạy ngay: vào https://github.com/Trangsct/vlncn-laocai/actions → chọn **Quet Data360X (may co quan)**
  → **Run workflow**. Không cần ngồi trước máy cơ quan, bấm từ điện thoại cũng được.
- Máy tắt thì lệnh nằm chờ, bật máy lên là chạy tiếp.
- Kiểm tra máy còn nhận lệnh không: https://github.com/Trangsct/vlncn-laocai/settings/actions/runners,
  phải thấy dòng xanh **Idle**.

## Chủ động cập nhật khi Bạn thấy cần (không chờ 18h)

Có hai cách, dùng cách nào cũng được:

**Cách 1 - bấm trên máy tính (lấy văn bản mới nhất từ Data360X):**
mở thư mục `D:\du-an\bot`, bấm đúp vào **`cap-nhat-ngay.bat`**. Bot quét văn bản mới, tải PDF và đẩy lên GitHub;
phần đọc nội dung tự chạy tiếp. Muốn tiện hơn: bấm chuột phải vào file → *Gửi tới* → *Desktop (tạo lối tắt)*,
sau này chỉ cần bấm đúp biểu tượng ngoài màn hình.

**Cách 2 - bấm trên trang web (xử lý văn bản bot đã tải về):**
vào https://vlncn-laocai.vercel.app/cap-nhat, nhập mã bảo vệ rồi bấm *Chạy ngay*. Trang đó cũng hiện
trạng thái các lượt chạy gần đây. Lần đầu cần cấu hình hai biến trên Vercel, hướng dẫn ngay trên trang.

## Quét bù văn bản cũ (khi cần lấy lại giấy phép đã ký trước đây)

Bình thường bot chỉ quét 3 ngày gần nhất cho nhanh. Khi cần lấy lại văn bản cũ (ví dụ giấy phép vận chuyển
hàng hóa nguy hiểm tháng 6, 7/2026 chưa có trên trang), bấm đúp **`quet-lai-120-ngay.bat`** trong `D:\du-an\bot`.
Bot quét 120 ngày gần nhất, bỏ qua văn bản đã xử lý, chỉ tải cái còn thiếu. Mất khoảng 10 đến 25 phút.

## Chạy bot trên máy thứ hai (ví dụ máy để bàn ở cơ quan)

Bot chạy được trên nhiều máy. Danh sách văn bản đã xử lý (`inbox/_da-xu-ly.json`) nằm trên GitHub chứ không nằm
trên máy, nên **hai máy không tải trùng nhau**: máy nào chạy trước lấy văn bản mới, máy chạy sau tự bỏ qua.

**KHÔNG cần chép thư mục `du-an` sang.** Chép hồ sơ Chrome (`bot-profile\chrome-profile`) giữa hai máy thường mất
phiên đăng nhập, lại nặng. Cài mới sạch sẽ hơn và chỉ mất khoảng 10 phút:

1. Trên máy mới, tải file cài đặt: mở https://raw.githubusercontent.com/Trangsct/ccn-laocai/main/bot/cai-dat.bat
   → bấm chuột phải → *Lưu thành* → lưu vào thư mục `D:\du-an\bot` (chưa có thì tạo mới; máy không có ổ D thì dùng `C:\du-an\bot`).
2. Bấm đúp `cai-dat.bat`. File tự cài Python, Playwright, Chromium, tải toàn bộ script và các file .bat.
3. Khi máy hỏi token, dán chuỗi `github_pat_...` — mở `config.json` trên máy cũ (`D:\du-an\bot-profile\config.json`)
   bằng Notepad để chép, hoặc tạo token mới trên GitHub. Chạy xong phải thấy dòng **TOKEN DUNG DUOC**.
4. Bấm đúp `dang-nhap-lan-dau.bat`, đăng nhập Data360X trên máy mới (có captcha, Bạn tự nhập).
5. Bấm đúp `chay-thu.bat` để kiểm tra bot đọc được văn bản.

**Chọn MỘT máy giữ lịch tự chạy 18h**, tránh hai máy cùng chạy một lúc:
- Máy giữ lịch: bấm chuột phải `dat-lich.bat` → *Run as administrator*.
- Máy còn lại: bấm đúp `bo-lich.bat` để gỡ lịch; vẫn chạy tay bằng `cap-nhat-ngay.bat` bất cứ lúc nào.

Nên để lịch ở máy **hay bật và hay đăng nhập Data360X nhất**. Máy kia dùng khi cần chạy gấp.

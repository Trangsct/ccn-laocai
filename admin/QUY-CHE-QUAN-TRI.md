# Quy chế Quản trị Tài khoản và An toàn dữ liệu

**Cổng thông tin Khu, Cụm công nghiệp tỉnh Lào Cai**
**Sở Công Thương tỉnh Lào Cai**

> Áp dụng cho toàn bộ tài khoản có quyền chỉnh sửa dữ liệu trên cổng thông tin
> `https://www.congnghieplaocai.vn` (sau đây gọi là "Cổng").
>
> Ban hành: 2026-05-21 · Phiên bản: 1.0

---

## I. Phạm vi và đối tượng áp dụng

1. Quy chế áp dụng cho mọi tài khoản truy cập trang quản trị nội dung (Netlify CMS) của Cổng tại địa chỉ `/admin/`.

2. Đối tượng:
   - **Quản trị viên Sở Công Thương** — Phòng Quản lý Công nghiệp; có quyền cao nhất.
   - **Biên tập viên Sở** — Cán bộ Phòng Quản lý Công nghiệp được giao nhiệm vụ rà soát dữ liệu.
   - **Cán bộ địa phương** — Cán bộ Ủy ban nhân dân cấp xã/phường được phân công theo dõi cụm công nghiệp trên địa bàn.
   - **Chủ đầu tư hạ tầng** (đặc biệt, khi cần) — Đại diện doanh nghiệp/hợp tác xã làm chủ đầu tư hạ tầng Cụm công nghiệp do doanh nghiệp quản lý.

---

## II. Phân quyền (Role-Based Access)

### A. Quản trị viên Sở (Super Admin)

- **Số lượng tối đa: 2 người** (1 chính + 1 dự phòng).
- Bao gồm: Trưởng/Phó phòng Quản lý Công nghiệp.
- Quyền hạn:
  - Phê duyệt (merge) thay đổi dữ liệu do biên tập viên/cán bộ địa phương đề xuất.
  - Mời, khóa, xóa tài khoản người dùng.
  - Cấu hình hệ thống, môi trường biến (environment variables), khóa API.
  - Khôi phục dữ liệu khi có sự cố.

### B. Biên tập viên Sở (Editor)

- **Số lượng đề xuất: 3-5 người** thuộc Phòng Quản lý Công nghiệp.
- Quyền hạn:
  - Chỉnh sửa toàn bộ dữ liệu (ccn-data.json, unit-details.json).
  - Đề xuất thay đổi (tạo Pull Request qua Editorial Workflow).
  - Rà soát, góp ý đề xuất từ cán bộ địa phương.
  - **Không** có quyền merge — phải qua Quản trị viên.

### C. Cán bộ địa phương (Local Editor)

- **Mỗi xã/phường có cụm công nghiệp được cấp 1 tài khoản.**
- Quyền hạn (theo nguyên tắc tự giác + hậu kiểm):
  - Chỉ chỉnh sửa thông tin Cụm công nghiệp/Khu công nghiệp **trên địa bàn quản lý**.
  - Đề xuất thay đổi qua Editorial Workflow — không được tự ý merge.
  - **Không** chỉnh sửa Quyết định pháp lý do tỉnh ban hành (chỉ Sở Công Thương cập nhật).
  - **Không** chỉnh sửa dữ liệu của địa bàn khác. Vi phạm sẽ bị xử lý theo Mục VIII.

### D. Chủ đầu tư hạ tầng (Investor — tùy chọn)

- Chỉ cấp khi doanh nghiệp/HTX là chủ đầu tư hạ tầng và yêu cầu cập nhật tiến độ.
- Tài khoản tạm thời, có thời hạn (12 tháng), gia hạn theo nhu cầu.
- Quyền tương đương Cán bộ địa phương + thêm: chỉ sửa được cụm công nghiệp do mình làm chủ đầu tư.

---

## III. Quản lý tài khoản

### A. Mở tài khoản

1. **Email công vụ ưu tiên**: ưu tiên email `@laocai.gov.vn`, `@congthuong.gov.vn`, hoặc email của UBND xã/phường. Email cá nhân (gmail, yahoo) chỉ được dùng khi đơn vị chưa có email công vụ.

2. **Một người = một tài khoản**: nghiêm cấm dùng email tập thể (vd: `vanphong@xaABC.gov.vn`) hoặc chia sẻ tài khoản giữa nhiều người.

3. **Quy trình mời**:
   - Đơn vị/cán bộ gửi văn bản đề nghị cấp tài khoản (qua email công vụ hoặc văn bản giấy) tới Phòng Quản lý Công nghiệp - Sở Công Thương.
   - Văn bản nêu rõ: họ tên, chức vụ, đơn vị công tác, email, số điện thoại liên hệ, phạm vi cụm/khu công nghiệp được giao quản lý.
   - Quản trị viên gửi email mời (Netlify Identity → Invite User) trong vòng 03 ngày làm việc.
   - Người được mời thiết lập mật khẩu lần đầu trong vòng 07 ngày, sau đó link hết hạn.

### B. Mật khẩu

- **Độ dài tối thiểu: 12 ký tự**.
- **Bắt buộc đủ 4 nhóm**: chữ hoa, chữ thường, số, ký tự đặc biệt.
- **Cấm**: dùng tên đơn vị, năm sinh, số điện thoại, từ điển phổ thông (vd `123456`, `password`, `laocai2026`).
- **Định kỳ**: Quản trị viên đổi mật khẩu mỗi 90 ngày; Biên tập viên/Cán bộ địa phương 180 ngày.
- **Không lưu mật khẩu** dưới dạng văn bản (file Word/Excel/note) trên máy chung hoặc thiết bị di động.

### C. Xác thực đa yếu tố (MFA)

- **Bắt buộc** đối với Quản trị viên Sở.
- **Khuyến nghị** đối với Biên tập viên Sở và Cán bộ địa phương.
- Sử dụng ứng dụng Authenticator (Google Authenticator, Microsoft Authenticator, Authy) hoặc khóa cứng FIDO2 (đối với Quản trị viên).

### D. Khóa và xóa tài khoản

- Tài khoản bị khóa tự động sau **05 lần đăng nhập sai liên tiếp**.
- Tài khoản không hoạt động (no login) **liên tục 180 ngày** sẽ được rà soát và khóa tạm thời.
- Khi cán bộ chuyển công tác hoặc nghỉ hưu, đơn vị chủ quản phải có văn bản thông báo trong vòng 07 ngày để Quản trị viên khóa/xóa tài khoản.

---

## IV. Quy trình chỉnh sửa dữ liệu (Editorial Workflow)

### A. Sơ đồ chung

```
Cán bộ địa phương / Biên tập viên           Quản trị viên Sở
  ┌──────────────────┐                       ┌──────────────────┐
  │ 1. Đăng nhập     │                       │ 4. Nhận thông    │
  │    /admin/       │                       │    báo PR        │
  └────────┬─────────┘                       └────────┬─────────┘
           │                                          │
  ┌────────▼─────────┐                       ┌────────▼─────────┐
  │ 2. Chỉnh sửa     │   PR (Pull Request)   │ 5. Rà soát,      │
  │    cụm của mình  │ ────────────────────► │    đối chiếu     │
  │                  │                       │    QĐ pháp lý    │
  └────────┬─────────┘                       └────────┬─────────┘
           │                                          │
  ┌────────▼─────────┐                       ┌────────▼─────────┐
  │ 3. Save + Mark   │                       │ 6. Phê duyệt     │
  │    'Ready'       │                       │    (Merge) hoặc  │
  └──────────────────┘                       │    yêu cầu sửa   │
                                             └────────┬─────────┘
                                                      │
                                             ┌────────▼─────────┐
                                             │ 7. Tự động deploy │
                                             │    qua Vercel     │
                                             └──────────────────┘
```

### B. Trách nhiệm rà soát của Quản trị viên

Trước khi phê duyệt (merge), Quản trị viên phải đối chiếu:

1. **Tính chính xác**: số liệu khớp với Quyết định / Báo cáo chính thức của UBND tỉnh hoặc UBND cấp xã.
2. **Phạm vi**: cán bộ địa phương chỉ chỉnh sửa cụm/khu của địa bàn mình.
3. **Văn phong**: tuân thủ quy tắc của Cổng — không viết tắt CCN/KCN, dùng văn phong hành chính.
4. **Bảo mật**: nội dung không chứa thông tin nhạy cảm, mã độc, liên kết quảng cáo.
5. **Định dạng**: JSON hợp lệ, không phá vỡ cấu trúc.

Thời hạn rà soát: **05 ngày làm việc** kể từ khi PR được tạo. Quá hạn, Quản trị viên có nghĩa vụ phản hồi (đồng ý/yêu cầu sửa).

### C. Trường hợp khẩn cấp

Đối với thông tin có thời hạn (vd. cập nhật quyết định mới ban hành, sửa số liệu sai gây hiểu lầm), Quản trị viên có thể merge ngay sau khi xác minh qua điện thoại với người đề xuất và đối chiếu văn bản gốc, không cần đợi 05 ngày.

---

## V. Bảo mật kỹ thuật

### A. Hạn chế nội dung nhập

1. **Không upload file > 10 MB** (qua CMS).
2. **Không chèn thẻ HTML nguy hiểm** (`<script>`, `<iframe>` ngoài, `<embed>`). Toàn bộ trường `gioiThieu` đã được kiểm soát XSS qua `escapeHtml()` ở phía render — tuy nhiên việc chèn JavaScript trong nội dung vẫn bị cấm.
3. **Không chèn liên kết tới site không thuộc `.gov.vn`, `.vercel.app`, `.netlify.app`** trừ khi có lý do nghiệp vụ rõ ràng và Quản trị viên xác nhận.

### B. Phiên đăng nhập

- Tự động đăng xuất sau **08 giờ không hoạt động**.
- Tránh đăng nhập trên máy công cộng (quán cà phê, máy tính dùng chung).
- Đăng xuất ngay khi rời khỏi máy tính.

### C. Khóa API và biến môi trường

- `GEMINI_API_KEY` và các khóa API khác **chỉ lưu trên Vercel Environment Variables**, không được commit vào git, không gửi qua email/chat.
- Khóa bị rò rỉ phải báo Quản trị viên trong vòng 02 giờ. Quản trị viên rotate (đổi mới) khóa ngay.

### D. Backup

- Toàn bộ dữ liệu được backup **tự động** qua Git (mỗi commit là một bản sao đầy đủ lịch sử).
- Backup phụ trợ: Quản trị viên export toàn bộ repo về máy nội bộ Sở **mỗi tuần**.

---

## VI. Kiểm toán và giám sát (Audit)

### A. Lịch sử thay đổi

Mọi thay đổi đều được ghi nhận tự động qua Git:
- **Ai** đã thay đổi (email tài khoản Netlify)
- **Khi nào** (timestamp)
- **Cái gì** (diff chi tiết từng dòng)
- **Tại sao** (commit message do người chỉnh sửa nhập)

Xem lịch sử tại: `https://github.com/Trangsct/ccn-laocai/commits/main`

### B. Báo cáo định kỳ

Phòng Quản lý Công nghiệp thực hiện rà soát định kỳ:
- **Hằng tuần**: kiểm tra PR mới, log đăng nhập bất thường.
- **Hằng tháng**: thống kê số lượng thay đổi theo cán bộ, theo cụm/khu.
- **Hằng quý**: rà soát danh sách tài khoản, khóa tài khoản không hoạt động.

### C. Báo cáo bất thường

Ngay khi phát hiện một trong các dấu hiệu sau, Quản trị viên phải báo cáo Lãnh đạo Sở và xử lý trong vòng 24 giờ:
- Đăng nhập từ địa lý/thiết bị lạ.
- Thay đổi số liệu trái thẩm quyền (cán bộ địa phương sửa cụm của địa bàn khác).
- Nội dung có dấu hiệu spam, quảng cáo, kích động.
- Khóa API bị rò rỉ.

---

## VII. Xử lý sự cố

### A. Phục hồi dữ liệu

Khi dữ liệu bị xóa/sửa sai:
1. Quản trị viên truy cập lịch sử Git tại GitHub.
2. Tìm commit trước khi xảy ra sự cố.
3. Tạo Pull Request "revert" hoặc khôi phục thủ công.
4. Merge ngay → Vercel tự động deploy bản sạch trong 1-2 phút.

### B. Mất quyền truy cập

- Mất mật khẩu: dùng tính năng "Forgot password" trên trang đăng nhập `/admin/`. Email khôi phục được gửi tới email đăng ký.
- Mất quyền truy cập email: liên hệ Quản trị viên qua điện thoại để xác minh và reset.
- Quản trị viên duy nhất mất quyền truy cập: tài khoản dự phòng (Phó phòng Quản lý Công nghiệp) được ủy quyền khôi phục.

### C. Tấn công mạng (vd. tài khoản bị hack)

1. Quản trị viên khóa ngay tài khoản bị nghi ngờ.
2. Đổi mật khẩu Vercel/Netlify Identity master.
3. Rotate toàn bộ khóa API.
4. Rà soát Git log 30 ngày trước, revert thay đổi đáng ngờ.
5. Báo cáo Lãnh đạo Sở + Đội ứng cứu khẩn cấp an toàn thông tin tỉnh (nếu nghiêm trọng).

---

## VIII. Vi phạm và chế tài

Vi phạm Quy chế này sẽ bị xử lý tương xứng:

| Vi phạm | Lần 1 | Lần 2 | Lần 3 |
|---|---|---|---|
| Chia sẻ tài khoản | Cảnh báo bằng văn bản | Khóa tài khoản 30 ngày | Khóa vĩnh viễn + báo cáo Lãnh đạo |
| Chỉnh sửa trái thẩm quyền (cán bộ địa phương sửa địa bàn khác) | Cảnh báo + revert | Khóa 90 ngày | Khóa vĩnh viễn |
| Chèn nội dung độc hại (XSS, mã độc, quảng cáo) | Khóa ngay 90 ngày + báo cáo | Khóa vĩnh viễn + báo công an | — |
| Để lộ khóa API | Cảnh báo + rotate khóa | Khóa 60 ngày + tham gia đào tạo lại | Khóa vĩnh viễn |
| Không tuân thủ MFA (Quản trị viên) | Nhắc nhở | Khóa cho tới khi bật MFA | — |

Mức xử lý có thể nâng cao tùy mức độ thiệt hại, theo Quy chế cán bộ công chức của Sở.

---

## IX. Đào tạo và truyền thông

1. **Khi mở tài khoản mới**: Quản trị viên gửi kèm bộ tài liệu (Quy chế này + Hướng dẫn sử dụng CMS) và yêu cầu xác nhận đã đọc trong vòng 07 ngày.

2. **Mỗi 06 tháng**: tổ chức buổi hướng dẫn trực tuyến/trực tiếp về:
   - Cập nhật quy trình mới (nếu có).
   - Nhắc lại các sai sót thường gặp.
   - Thay đổi về luật, nghị định ảnh hưởng đến nội dung cần cập nhật trên Cổng.

3. **Khi có sự cố lớn**: Quản trị viên gửi thông báo tới toàn bộ tài khoản qua email + đính kèm hướng dẫn xử lý.

---

## X. Tuân thủ pháp luật

Quy chế này tuân thủ:

- **Luật An toàn thông tin mạng** số 86/2015/QH13 ngày 19/11/2015.
- **Luật An ninh mạng** số 24/2018/QH14 ngày 12/6/2018.
- **Nghị định số 85/2016/NĐ-CP** ngày 01/7/2016 về bảo đảm an toàn hệ thống thông tin theo cấp độ.
- **Nghị định số 53/2022/NĐ-CP** ngày 15/8/2022 quy định chi tiết một số điều của Luật An ninh mạng.
- **Nghị định số 13/2023/NĐ-CP** ngày 17/4/2023 về bảo vệ dữ liệu cá nhân.

Khi pháp luật về an toàn thông tin có thay đổi, Quy chế này phải được rà soát và điều chỉnh tương ứng trong vòng 30 ngày.

---

## Phụ lục A — Danh sách tài khoản (cập nhật bởi Quản trị viên)

| Email | Họ tên | Vai trò | Phạm vi quản lý | Ngày cấp | Ngày khóa (nếu có) |
|---|---|---|---|---|---|
| trangsct@laocai.gov.vn | Tr*** Hồng Trang | Quản trị viên Sở | Toàn cổng | 2026-04-01 | — |
| _(chờ bổ sung)_ | | | | | |

> Lưu ý: Danh sách này lưu trong nội bộ Phòng Quản lý Công nghiệp, không công khai trên web.

---

## Phụ lục B — Liên hệ

**Phòng Quản lý Công nghiệp - Sở Công Thương tỉnh Lào Cai**
- Địa chỉ: Số 165 đường Lý Thường Kiệt, phường Yên Bái, tỉnh Lào Cai
- Điện thoại: 02163.857.863
- Email: contact-sct@laocai.gov.vn

---

*Quy chế này có hiệu lực kể từ ngày ký ban hành. Mọi ý kiến đóng góp, đề xuất sửa đổi vui lòng gửi về Phòng Quản lý Công nghiệp.*

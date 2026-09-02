BẢN GIAO VIỆC CHO CLAUDE CODE
Dự án: TỰ ĐỘNG ĐỌC VĂN BẢN TỪ DATA360X, CẬP NHẬT 2 TRANG WEB VÀ CÁC SKILL
Ngày giao: 02/9/2026. Người giao: Trần Trọng Trang, Phó Trưởng phòng Quản lý Công nghiệp, Sở Công Thương Lào Cai.
Bản sửa lần 1 (02/9/2026, chiều): khâu 2 đọc PDF chuyển từ Claude API sang Gemini API gói miễn phí (8 điểm sửa, đánh dấu [SỬA]).

Cách dùng: mở claude.ai/code, phiên có đủ 4 repo (ccn-laocai, vlncn-laocai, vlncn-laocai-files, skill-sct), kéo 2 file HTML Data360X vào ô chat, dán toàn bộ nội dung từ mục I đến mục VIII bên dưới, bấm Enter.

===================================================================

I. MỤC TIÊU

Xây dựng dây chuyền tự động hoàn toàn: mỗi ngày lúc 18h00 (giờ Việt Nam), máy tự đọc các văn bản mới trên hệ thống Data360X của tỉnh (https://csdlvb.laocai.gov.vn, hai mục Văn bản đến và Văn bản đi), tải file PDF của những văn bản thuộc lĩnh vực tôi quản lý, đọc nội dung từng văn bản bằng Gemini API (gói miễn phí) [SỬA], rồi tự cập nhật vào đúng mục dữ liệu trên 2 trang web và vào file dữ liệu tham chiếu của các plugin trong repo skill-sct. Tôi không phải thao tác gì hằng ngày. Tôi chỉ can thiệp khi máy không chắc chắn (thiếu trường, trùng số, cấp lại, điều chỉnh) hoặc khi phiên đăng nhập hết hạn.

Hai trang web:
- congnghieplaocai.vn, repo ccn-laocai: quản lý KCN, CCN (thẻ từng CCN, tin tức, văn bản pháp lý, thu hút đầu tư).
- vlncn-laocai.vercel.app, repo vlncn-laocai, file PDF lưu ở repo vlncn-laocai-files: quản lý VLNCN gồm doanh nghiệp, nhân sự, công trình, GP sử dụng VLNCN, dịch vụ nổ mìn, GP tiền chất thuốc nổ, GCN huấn luyện, báo cáo định kỳ, báo cáo doanh nghiệp, cảnh báo.

Không làm mục "Văn bản mới" dạng danh sách tin. Nếu còn PR nào về giao diện "Văn bản mới" thì đóng.

II. RÀNG BUỘC CỨNG

1. Không dùng dịch vụ giải captcha dưới bất kỳ hình thức nào. Không cố đăng nhập tự động vào cổng login.yenbai.gov.vn. Việc đăng nhập là của tôi; máy chỉ dùng lại phiên đã đăng nhập.
2. Không bịa số, ngày, tên, giá trị. Chỉ ghi những gì đọc được trong PDF. Không đọc được thì để trống và ghi chú "không có trong văn bản". [SỬA 02/9/2026] Trích yếu trên Data360X rất hay sai (ghi "Dự thảo" dù đã phát hành, tên tổ chức cụt, ngày ghi lẫn vào trích yếu): trích yếu chỉ dùng để lọc sơ bộ ở khâu 1; phân loại cuối cùng và mọi dữ liệu lên web phải căn cứ nội dung PDF ở khâu 2. Bot gom rộng mọi GP-SCT của Phòng Công nghiệp, không loại vì chữ "Dự thảo".
3. Mật khẩu, token, khóa API không được xuất hiện trong code, trong log, trong PR. Chúng nằm ở GitHub Secrets hoặc file cấu hình trên máy tôi (đã đưa vào .gitignore). [SỬA] Khóa Gemini dùng secret tên GEMINI_API_KEY; không còn tham chiếu ANTHROPIC_API_KEY hay api.anthropic.com ở bất kỳ workflow, script nào.
4. Dữ liệu chỉ lấy từ Data360X. Trang vOffice cũ (qlvb.yenbai.gov.vn) bỏ hẳn.
5. CCN Yên Hợp (12 ha, đã thành lập) và CCN Yên Hợp 1 (63 ha, chưa thành lập) là 2 dự án độc lập tại xã Xuân Ái, không gọi giai đoạn I, II. CCN Bản Phung nhà đầu tư đã rút, không hiển thị.
6. Tôi không rành kỹ thuật. Việc gì bạn có quyền làm thì tự làm. Việc bắt buộc tôi làm thì viết hướng dẫn từng bước bấm ở đâu, gõ gì, có lệnh sẵn để copy.

III. NHỮNG GÌ ĐÃ CÓ (PR #29 đến #34 trong ccn-laocai)

- Máy chủ GitHub Actions gọi được hệ thống của tỉnh, nhưng cổng SSO có captcha, nên khâu thu thập không chạy trên GitHub mà chạy trên máy tôi.
- File HTML mẫu đã lưu tại ccn-laocai/tools/samples/ (PR #35). Khâu 2 thí điểm: vlncn-laocai/scripts/doc_gp_vlncn.py + workflow thi-diem-doc-gp.yml (PR #16, sửa Gemini ở PR #17).
- Userscript Tampermonkey tools/qlvb-sync.user.js đang chạy trong Chrome của tôi, đã có cơ chế lưu token bằng GM_setValue, GM_xmlhttpRequest, tự cập nhật qua @updateURL. Giữ lại làm phương án phụ.
- Nguồn dữ liệu Data360X: ứng dụng Next.js, bảng PrimeReact table.p-datatable-table, chuyển tab không tải lại trang. Hai trang: /van-ban-den/ và /van-ban-di/. Mỗi văn bản có trang chi tiết dạng /van-ban-di/detail/?id=... có file PDF đính kèm. Tôi đính kèm 2 file HTML mẫu, lưu vào tools/samples/ để tham chiếu.
- Cột trang Văn bản đến: STT, Số/ký hiệu VB, Số đến, Ngày đến, Ngày ban hành, Trích yếu, Đơn vị ban hành, Loại văn bản, Người nhận văn bản, Thao tác.
- Cột trang Văn bản đi: STT, Ngày ban hành, Số/ký hiệu VB, Trích yếu, Người ký, Đơn vị soạn thảo, Nơi nhận, Loại văn bản, Nguồn dữ liệu, Thao tác.

IV. KIẾN TRÚC 3 KHÂU

KHÂU 1. THU THẬP, chạy trên máy tính Windows ở cơ quan tôi
- scripts/bot-data360x.py dùng Playwright, Chrome persistent context, hồ sơ lưu tại D:\du-an\bot-profile để giữ phiên đăng nhập SSO giữa các lần chạy.
- Lịch: chạy chính 18h00 hằng ngày, kể cả thứ Bảy, Chủ nhật. Chạy giữ phiên (chỉ mở trang chủ Data360X rồi đóng) lúc 07h00, 12h00, 15h00 để phiên SSO không hết hạn do không hoạt động.
- Mỗi lần chạy chính: đọc toàn bộ văn bản có ngày ban hành trong 3 ngày gần nhất ở cả 2 trang (dự phòng ngày máy tắt), duyệt hết các trang phân trang, lọc theo bộ nhận diện ở mục V, so trùng với danh sách đã xử lý (file trong repo), mở trang chi tiết, tải PDF, đẩy lên repo đích tại inbox/<so-ky-hieu-lam-sach>.pdf kèm inbox/<so-ky-hieu-lam-sach>.json ghi số ký hiệu, ngày ban hành, trích yếu, cơ quan ban hành hoặc người ký, loại văn bản, nguồn (đến/đi), id Data360X. Đẩy bằng git push với token đọc từ D:\du-an\bot-profile\config.json.
- Repo đích: văn bản VLNCN, tiền chất, hóa chất, PANM, huấn luyện đi vào vlncn-laocai; văn bản KCN, CCN đi vào ccn-laocai.
- Khi phát hiện bị đưa về trang đăng nhập: không cố đăng nhập; mở cửa sổ Chrome nhìn thấy được tại trang đó; hiện thông báo Windows "Bot cần bạn đăng nhập lại Data360X"; gửi Telegram nếu đã cấu hình; thử lại mỗi 15 phút, tối đa 6 lần; ghi log tại D:\du-an\bot-profile\logs\.
- Khi tôi đăng nhập xong trong cửa sổ đó, bot tự nhận ra và chạy tiếp, không cần tôi bấm gì thêm.
- Tạo bộ công cụ cho người không rành kỹ thuật, đặt trong thư mục bot/ của repo ccn-laocai:
  cai-dat.bat: cài Python (nếu chưa có), Playwright, Chromium, tạo thư mục hồ sơ, hỏi token và dán vào config.json.
  dang-nhap-lan-dau.bat: mở Chrome hồ sơ riêng tại Data360X để tôi đăng nhập.
  chay-thu.bat: chạy bot một lần, in kết quả ra màn hình.
  dat-lich.bat: đăng ký Windows Task Scheduler cho 4 mốc giờ nêu trên, chạy kể cả khi máy khóa màn hình, đánh thức máy nếu đang ngủ.
  HUONG-DAN-CAI-BOT.md: từng bước, có ảnh mô tả bằng lời, có cách kiểm tra bot đã chạy chưa.
- Userscript Tampermonkey giữ lại: dùng chung danh sách đã xử lý để không tải trùng.

KHÂU 2. ĐỌC VÀ BÓC DỮ LIỆU, chạy trên GitHub Actions trong từng repo đích
- Workflow .github/workflows/doc-van-ban.yml chạy khi có file mới trong inbox/.
- [SỬA] Script Python gọi Gemini API qua thư viện google-genai, secret GEMINI_API_KEY, model gemini-2.5-flash. Nếu model này không còn thì script liệt kê tên các model Flash hiện hành và dừng để tôi chọn; không tự chọn model Pro. (Kết quả chạy 02/9/2026: gemini-2.5-flash đã đóng với người dùng mới, Google khuyến nghị gemini-3.6-flash; các model Flash hiện có: gemini-3.7-flash, gemini-3.6-flash, gemini-3.5-flash, gemini-3.5-flash-lite, gemini-3.1-flash-lite, gemini-flash-latest, gemini-flash-lite-latest. Đang dùng gemini-3.6-flash.)
- [SỬA] Gửi PDF trực tiếp dưới dạng file đính kèm (inline data; File API khi file lớn), không chỉ gửi text. PDF ảnh quét Gemini đọc được, không cần OCR riêng.
- [SỬA] Giới hạn gói miễn phí (khoảng 10-15 yêu cầu/phút, vài trăm yêu cầu/ngày): xử lý tuần tự từng PDF, nghỉ 6 giây giữa hai lần gọi; lỗi 429 thì chờ 30, 60, 120 giây thử lại tối đa 3 lần; vẫn lỗi thì để PDF lại inbox cho ngày mai và ghi vào báo cáo Telegram.
- Quy tắc bóc trường giữ nguyên: chỉ ghi giá trị đọc được trong PDF, trường không có để trống và mở PR chờ tôi; không bịa, không suy đoán. [SỬA] Prompt gửi Gemini phải chứa schema dữ liệu hiện có của trang (đọc từ file dữ liệu / models.py đang dùng, không tự đặt schema mới) và ví dụ mẫu từ file tham chiếu trong skill-sct (sd-vlncn-sct-vn/mau-van-ban).
- [SỬA] Yêu cầu Gemini trả JSON thuần theo schema: response_mime_type application/json + response_schema; kiểm tra JSON hợp lệ (parse được, đủ trường, đúng kiểu, ngày đúng dạng) trước khi ghi.
- Mỗi trường trả về kèm mức tin cậy cao/thấp và vị trí trang tìm thấy.
- Sau khi đọc: chuyển PDF từ inbox/ sang uploads/ của vlncn-laocai-files (hoặc thư mục file tương ứng của ccn-laocai), gắn link vào bản ghi; cập nhật danh sách đã xử lý; xóa file trong inbox/.
- Ghi bản ghi vào file dữ liệu tham chiếu của plugin tương ứng trong repo skill-sct (xem mục V), tăng version trong plugin.json, commit và push thẳng vào skill-sct.

KHÂU 3. DUYỆT VÀ XUẤT BẢN
- Mức tự động cao nhất: nếu tất cả trường bắt buộc của loại văn bản đó đều đọc được với tin cậy cao, số ký hiệu chưa tồn tại, không phải cấp lại/điều chỉnh/thu hồi, thì bot tự commit thẳng vào main, Vercel tự deploy. Không mở PR.
- Chỉ mở PR chờ tôi khi: thiếu trường bắt buộc, có trường tin cậy thấp, số ký hiệu đã tồn tại, văn bản là cấp lại/điều chỉnh/thu hồi/gia hạn, hoặc văn bản không khớp loại nào rõ ràng. Mô tả PR gồm bảng các trường đã đọc, dòng dữ liệu sẽ thêm/sửa, ảnh trang 1 PDF.
- 18h30 hằng ngày gửi Telegram cho tôi 1 tin: bot chạy được không, quét bao nhiêu văn bản, cập nhật tự động bao nhiêu, PR nào đang chờ (kèm link). Nếu chưa có Telegram thì ghi vào file bao-cao/YYYY-MM-DD.md trong repo.

V. LOẠI VĂN BẢN THEO DÕI VÀ NƠI CẬP NHẬT

Trang VLNCN (repo vlncn-laocai), plugin trong skill-sct:
1. Giấy phép sử dụng VLNCN: số ký hiệu chứa GP-SCT (Văn bản đi, đơn vị soạn thảo Phòng Công nghiệp) hoặc GP-UBND (Văn bản đến, UBND tỉnh, trích yếu có "vật liệu nổ"). Cập nhật mục GP sử dụng VLNCN, đồng thời tạo/cập nhật doanh nghiệp và công trình liên quan. Plugin: sd-vlncn-sct-vn.
2. Quyết định phê duyệt hoặc chấp thuận phương án nổ mìn: trích yếu có "phương án nổ mìn". Cập nhật vào công trình tương ứng. Plugin: sd-vlncn-sct-vn.
3. Quyết định công nhận kết quả kiểm tra và cấp GCN huấn luyện KTAT VLNCN, TCTN: trích yếu có "huấn luyện" hoặc "giấy chứng nhận huấn luyện"; đọc cả danh sách kèm theo, mỗi người một dòng. Cập nhật mục GCN huấn luyện và Nhân sự. Plugin: hl-vlncn-sct-vn.
4. Giấy phép kinh doanh tiền chất thuốc nổ, giấy chứng nhận đủ điều kiện hóa chất: trích yếu có "tiền chất" hoặc "hóa chất". Cập nhật mục GP tiền chất. Plugin: hc-sct-vn.
5. Thông báo sử dụng VLNCN của đơn vị dịch vụ nổ mìn: trích yếu có "thông báo sử dụng vật liệu nổ" hoặc "dịch vụ nổ mìn". Cập nhật mục Dịch vụ nổ mìn.
6. Báo cáo định kỳ của doanh nghiệp về VLNCN: trích yếu có "báo cáo" và "vật liệu nổ". Cập nhật mục Báo cáo của DN.

Trang KCN CCN (repo ccn-laocai):
7. Quyết định thành lập, mở rộng CCN; quyết định chấp thuận chủ trương đầu tư; quyết định lựa chọn chủ đầu tư hạ tầng; quyết định phê duyệt hoặc điều chỉnh quy hoạch chi tiết CCN; quyết định thành lập Hội đồng đánh giá: trích yếu có "cụm công nghiệp". Cập nhật thẻ CCN tương ứng (trạng thái, diện tích, chủ đầu tư, số và ngày quyết định), thêm bài tin ở mục tin tức, thêm văn bản vào mục văn bản pháp lý nếu là quyết định của UBND tỉnh. Plugin: kccn-sct-vn.
8. Văn bản về KCN của UBND tỉnh, Ban Quản lý Khu kinh tế: trích yếu có "khu công nghiệp". Cập nhật thẻ KCN tương ứng và tin tức. Plugin: kccn-sct-vn.

Văn bản không khớp loại nào: bỏ qua, không tải.

[BỔ SUNG 02/9/2026 sau khi chạy thật] Phòng Công nghiệp còn ký Giấy phép vận chuyển hàng hóa nguy hiểm (cùng ký hiệu GP-SCT, trích yếu "Giấy phép vận chuyển HHNH loại ..."), khoảng 10 giấy/tháng. Bạn chốt chiều 02/9/2026: đây là LOẠI 9, trang VLNCN mở thêm mục "Giấy phép vận chuyển hàng hóa nguy hiểm" (bảng hazmat_permits, đã lên web). Trích yếu Data360X hay sai (kể cả chữ "Dự thảo") nên bot khâu 1 gom MỌI GP-SCT của Phòng Công nghiệp, khâu 2 để Gemini phân loại theo NỘI DUNG PDF; bản dự thảo/chưa ký không đưa lên web.

[BỔ SUNG 02/9/2026] Trang lịch lãnh đạo Sở (lichlanhdaosocongthuong.com, công khai, không đăng nhập): làm ở Bước 3, bot đọc lịch ngày mai, lọc cuộc họp có Phòng Quản lý Công nghiệp hoặc từ khóa của Phòng, đưa vào tin Telegram 18h30. Không đưa lên website.
[BỔ SUNG chiều 02/9/2026 - KHÂU 2 + 3 ĐÃ TỰ ĐỘNG, GIAO CHO GEMINI] Bạn chốt: việc đọc ảnh/PDF giao hết cho Gemini để tiết kiệm token Claude, nhưng Gemini đọc số hay sai nên phải kiểm soát số liệu. Đã làm (repo vlncn-laocai, PR #24, #25):
- Workflow "Doc inbox (Gemini)" (.github/workflows/doc-inbox.yml, script scripts/doc_inbox.py) tự chạy khi bot đẩy file vào inbox/ và 18h20 hằng ngày: Gemini phân loại PDF theo nội dung (GP sử dụng VLNCN / GP vận chuyển HHNH / khác / dự thảo), trích xuất theo schema của trang, ghi CSDL, chuyển PDF sang vlncn-laocai-files/uploads.
- Kiểm soát số liệu (scripts/doc_gp_vlncn.py, hàm doc_pdf_kiem_soat): mỗi PDF đọc 2 LƯỢT bằng 2 model Flash khác nhau, so từng trường (số, ngày, mã số so tuyệt đối; danh sách khối lượng/hàng hóa so tập con số; chữ so gần đúng). Trường lệch thì KHÔNG ghi, hạ tin cậy, ghi "[CẦN ĐỐI CHIẾU]". Kiểm tra hợp lý: ngày hết hạn >= ngày cấp, ngày cấp không ở tương lai, số giấy phép khớp tên file, MST 10/12/13 chữ số, loại hàng 1-9, thời hạn GP HHNH <= 24 tháng, khối lượng VLNCN > 0; số/ngày còn đối chiếu với cột Số ký hiệu / Ngày ban hành của Data360X (cột có cấu trúc, không dùng trích yếu).
- Khâu 3: đợt nào MỌI giấy phép đạt chuẩn (không lệch 2 lượt, không cảnh báo, số/ngày tin cậy cao) thì commit thẳng main; có 1 giấy phép chưa chắc thì mở PR "Gemini đọc inbox ngày ... - chờ duyệt" kèm bảng đối chiếu để Bạn xem rồi bấm Merge.
- Workflow "Doc GP van chuyen HHNH" (scripts/doc_gp_hhnh.py) đọc lại 10 GP HHNH tháng 8/2026 đã nạp sơ bộ từ trích yếu, chế độ cap-nhat mở PR chờ duyệt.
- Việc Bạn cần làm 1 lần: thêm secret BOT_GITHUB_TOKEN vào repo vlncn-laocai (Settings > Secrets and variables > Actions > New repository secret; Name: BOT_GITHUB_TOKEN; Secret: dán chuỗi github_token trong D:\du-an\bot-profile\config.json). Thiếu secret này PDF ở lại inbox/, chưa chuyển sang vlncn-laocai-files.
- Còn lại của Bước 3: Telegram 18h30 + lịch lãnh đạo.

[BỔ SUNG chiều 02/9/2026 - BƯỚC 3 ĐÃ LÀM XONG PHẦN TỰ ĐỘNG]
- Bản tin Telegram 18h30: workflow "Ban tin Telegram 18h30" (vlncn-laocai/.github/workflows/bao-cao-telegram.yml, script scripts/bao_cao_telegram.py). Nội dung: (1) giấy phép dây chuyền đưa lên trang trong ngày, (2) việc cần Bạn xem (giấy phép còn dấu [CẦN ĐỐI CHIẾU], tệp chưa đọc được, tệp còn ở hộp thư), (3) lịch Lãnh đạo Sở ngày mai lấy từ lichlanhdaosocongthuong.com, Gemini lọc phần thuộc Phòng Quản lý Công nghiệp (cụm/khu công nghiệp, khuyến công, VLNCN, tiền chất, hóa chất, điện, năng lượng, thủy điện, khoáng sản, an toàn công nghiệp). Không tải được trang thì ghi rõ lý do, không bịa.
- Kết quả chạy thật khâu 2 ngày 02/9/2026: 6 Giấy phép sử dụng VLNCN (5234, 5235, 5236, 5315, 5323, 5347/GP-SCT) đã vào CSDL trang VLNCN; 5 giấy đạt chuẩn kiểm soát số liệu nên tự commit main, riêng 5236 hai lượt đọc lệch ở khối lượng VLNCN nên để trống và ghi [CẦN ĐỐI CHIẾU].
- Bài học vận hành: Vercel gói miễn phí chỉ cho 100 lượt triển khai/ngày tính chung cả tài khoản (cả 2 trang). Ngày 02/9/2026 chạm trần vì mỗi lần đẩy nhánh làm việc và mỗi PR đều sinh một bản xem trước, trang không cập nhật được dù dữ liệu đã lên main. Đã sửa vercel.json cả 2 repo: git.deploymentEnabled tắt triển khai cho nhánh claude/..., github.silent tắt bình luận bot. Chạm trần thì chờ 24 giờ hoặc vào Vercel > dự án > Deployments > dấu ba chấm > Redeploy.

VIỆC BẠN CẦN LÀM (3 việc, mỗi việc vài phút):
1. Thêm secret BOT_GITHUB_TOKEN vào repo vlncn-laocai: GitHub > repo vlncn-laocai > Settings > Secrets and variables > Actions > New repository secret; Name: BOT_GITHUB_TOKEN; Secret: dán chuỗi github_token trong D:\du-an\bot-profile\config.json. Thiếu secret này thì PDF ở lại inbox/, không chuyển sang kho vlncn-laocai-files.
2. Tạo bot Telegram: mở Telegram, tìm @BotFather, gõ /newbot, đặt tên bất kỳ, BotFather trả về một chuỗi dạng 1234567890:AAH... Nhắn một tin bất kỳ cho bot vừa tạo, rồi mở trình duyệt vào https://api.telegram.org/bot<CHUỖI_VỪA_NHẬN>/getUpdates để lấy số chat id trong mục "chat":{"id":...}. Thêm 2 secret vào repo vlncn-laocai như bước 1: TELEGRAM_TOKEN (chuỗi của BotFather) và TELEGRAM_CHAT_ID (số chat id).
3. Đặt lịch cho bot trên laptop: mở thư mục D:\du-an\bot, bấm chuột phải dat-lich.bat > Run as administrator.


VI. THỨ TỰ THỰC HIỆN

Mỗi bước xong báo cáo ngắn rồi mới sang bước sau. Báo cáo gồm: đã làm gì, kết quả thử, việc tôi cần làm (nếu có, kèm hướng dẫn), bước tiếp theo.

Bước 1. [SỬA] Khâu 2 thí điểm với loại 1 (GP sử dụng VLNCN). Lấy 2 giấy phép gần nhất đã có PDF trong vlncn-laocai-files, chạy script đọc bằng Gemini, in bảng các trường đọc được để tôi đối chiếu với dữ liệu trên vlncn-laocai.vercel.app, báo tỷ lệ trường khớp. Cần secret GEMINI_API_KEY trong vlncn-laocai (đã tạo 02/9/2026). Xong thì liệt kê file đã sửa và bước tôi cần bấm trên GitHub để kích hoạt workflow lần đầu.
Bước 2. Khâu 1: viết bot máy tôi và bộ file .bat, hướng dẫn cài. Tôi cài, chạy chay-thu.bat, gửi bạn kết quả. Chưa nối loại nào ngoài loại 1.
Bước 3. Khâu 3: cơ chế tự commit hoặc mở PR theo điều kiện, báo cáo 18h30, Telegram (hướng dẫn tôi tạo bot Telegram qua BotFather, 3 phút, tôi chỉ dán 2 chuỗi vào config.json).
Bước 4. Chạy thật loại 1 trong 3 ngày. Sửa lỗi phát sinh.
Bước 5. Mở rộng lần lượt loại 2, 3, 4, 5, 6 trên trang VLNCN, mỗi loại thử với văn bản có sẵn trước.
Bước 6. Mở rộng loại 7, 8 trên trang KCN CCN.
Bước 7. Rà soát: cập nhật CLAUDE.md của 2 repo mô tả dây chuyền; viết tài liệu VAN-HANH.md để tôi biết cách xem log, xử lý khi bot dừng, đổi token, gia hạn khóa API.

VII. TIÊU CHÍ HOÀN THÀNH

- Máy cơ quan bật, tôi không đụng vào, đúng 18h bot chạy, 18h30 tôi nhận tin Telegram, sáng hôm sau trang web và skill đã có dữ liệu mới.
- Mỗi tháng tôi phải đăng nhập lại Data360X không quá vài lần.
- Không có bản ghi nào trên trang web có số, ngày, tên không có trong PDF gốc.
- Mọi lỗi đều có trong log và trong tin Telegram, không có lỗi im lặng.

VIII. VIỆC BẮT BUỘC TÔI TỰ LÀM (bạn nhắc đúng lúc, kèm hướng dẫn)

1. [SỬA] Tạo khóa Gemini tại aistudio.google.com/apikey và đưa vào secret GEMINI_API_KEY của repo vlncn-laocai (đã làm 02/9/2026) và ccn-laocai (làm khi đến Bước 6).
2. Tạo 1 token GitHub fine-grained cho 4 repo (Contents: Read and write), dán vào config.json khi chạy cai-dat.bat.
3. Cài bot lên máy cơ quan một lần theo HUONG-DAN-CAI-BOT.md và đăng nhập Data360X lần đầu trong hồ sơ Chrome riêng.
4. Tạo bot Telegram qua BotFather, dán token và chat id vào config.json.
5. Đăng nhập lại khi bot báo phiên hết hạn.

Bắt đầu từ Bước 1.

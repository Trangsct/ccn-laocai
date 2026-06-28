# Dự án CCN Lào Cai

## Bối cảnh
Website quản lý nhà nước về Khu công nghiệp (KCN) và Cụm công nghiệp (CCN)
của Sở Công Thương tỉnh Lào Cai (tỉnh mới sau hợp nhất 01/7/2025, gồm cả
địa bàn Yên Bái cũ). Người dùng cuối là Lãnh đạo Sở, chuyên viên Phòng
QLCN, Lãnh đạo UBND tỉnh. Deploy tại congnghieplaocai.vn.

## Ràng buộc
- Toàn bộ giao diện và dữ liệu bằng tiếng Việt.
- Mọi địa danh thuộc Yên Bái cũ nay phải ghi là "tỉnh Lào Cai".
- Không tạo nhiều thay đổi trong một lần — mỗi tính năng tách thành commit
  riêng để dễ review và rollback.
- Không bịa số/ngày văn bản pháp luật. Khi viện dẫn pháp luật, chỉ dùng
  văn bản có trong repo hoặc do người dùng cung cấp.
- Không đẩy lên GitHub: thông tin cá nhân doanh nghiệp, số liệu vốn cụ
  thể từng dự án, sơ đồ điện chi tiết, phương án giá xăng dầu/điện đang
  xin ý kiến (thuộc danh mục bí mật theo QĐ 476/QĐ-TTg ngày 25/3/2026).

## Stack mong muốn
- Next.js + React + TypeScript (nếu repo đang dùng JS thuần, ưu tiên giữ
  nguyên, không refactor sang TS trừ khi tôi yêu cầu).
- Tailwind CSS cho styling.
- Leaflet cho bản đồ.
- Vercel cho deploy (đã thiết lập, không sửa cấu hình deploy).

## Quy ước commit
- Tiếng Việt, gọn, dạng "Thêm trang X" / "Sửa lỗi Y" / "Cập nhật dữ liệu Z".
- Mỗi PR một việc.

## Khi gặp việc liên quan đến văn bản hành chính
- Trích yếu, số ký hiệu, ngày tháng phải lấy chính xác từ tệp tin gốc,
  không tự suy đoán.
- Tham chiếu Nghị định 32/2024/NĐ-CP cho CCN, Nghị định 35/2022/NĐ-CP cho KCN.

## Trang chi tiết KCN/CCN (`unit-details.json` + `unit-files/<slug>/`)
Upload và nội dung chia theo 3 mức trạng thái pháp lý:

### Mức A — CCN/KCN đã có Quyết định thành lập chính thức
- Upload: **QĐ chủ trương đầu tư** + **QĐ thành lập**.
- Nội dung: **đầy đủ thông tin** trong 2 QĐ — gồm tên doanh nghiệp chủ
  đầu tư, mã số doanh nghiệp, địa chỉ, tổng mức đầu tư, vốn cụ thể, hiện
  trạng đất, cơ cấu sử dụng đất, ngành nghề, tiến độ, thời gian dự án.

### Mức B — CCN/KCN đang trình thành lập (mới có chủ trương đầu tư)
- Upload: **chỉ QĐ chủ trương đầu tư**.
- Nội dung: chỉ vị trí, diện tích, ngành nghề định hướng, tình trạng
  pháp lý. **KHÔNG nêu tên doanh nghiệp đề xuất, không nêu số vốn cụ thể**
  (doanh nghiệp trong báo cáo đề xuất CHƯA phải chủ đầu tư chính thức).

### Mức C — CCN/KCN chưa có chủ trương (mới trong QH tỉnh)
- Upload: không có file pháp lý nào (chỉ KML/sơ đồ nếu có).
- Nội dung: chỉ thông tin quy hoạch chung (vị trí, diện tích, ngành nghề
  định hướng).

### Nguyên tắc chung
- KHÔNG upload: báo cáo đề xuất của doanh nghiệp, tờ trình Sở Công Thương,
  ý kiến sở ngành, sơ đồ chi tiết, bảng phân tích pháp lý — trừ khi
  người dùng yêu cầu cụ thể.
- Số/ngày văn bản: lấy chính xác từ PDF gốc, không tự suy đoán. Nếu PDF
  mẫu để trống số → ghi "Quyết định ngày DD/MM/YYYY" không có số.

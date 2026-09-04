# Thư mục dự thảo cần soát

Bỏ tệp `.docx` dự thảo vào ngay thư mục này là máy tự soát.

## Cách bỏ tệp vào (không cần cài gì)

1. Mở https://github.com/Trangsct/ccn-laocai/tree/main/du-thao
2. Bấm **Add file** → **Upload files**, kéo tệp `.docx` vào, rồi bấm **Commit changes**.
3. Chờ khoảng một phút. Máy sẽ tạo thư mục cùng tên tệp, bên trong có:
   - `bao-cao-soat.md` — những gì máy soát được;
   - `trich-dan.json` — danh sách văn bản mà dự thảo viện dẫn, dùng cho bước tải văn bản kèm theo.
4. Máy mở một issue tại https://github.com/Trangsct/ccn-laocai/issues để Claude vào soát tiếp nội dung.

## Máy soát được những gì

- Liệt kê mọi văn bản được viện dẫn kèm số, ký hiệu, ngày.
- Đối chiếu sổ đăng ký văn bản của bộ plugin: văn bản nào **đã bị sửa đổi, thay thế**, hoặc **chưa tới ngày
  hiệu lực**. Đây là chỗ hay làm hỏng lập luận nhất.
- Cùng một văn bản mà trong tệp ghi hai ngày khác nhau.
- Câu ở Tờ trình và câu tương ứng ở dự thảo Quyết định nói khác nhau.
- Thể thức cơ bản theo Nghị định 30/2020/NĐ-CP: phông chữ, cỡ chữ, dấu `./.`, mục Nơi nhận.

## Máy KHÔNG làm gì

Máy không sửa văn bản. Việc đọc hiểu, đối chiếu bản gốc từng văn bản, xét mốc chuyển tiếp và chốt câu chữ
do Claude làm, rồi trả lại bản đã sửa có bôi đỏ kèm bảng giải trình từng chỗ.

## Chạy tay trên máy

```
python scripts/soat_du_thao.py du-thao/<tên tệp>.docx
```

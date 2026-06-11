#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinh api/chatbot-context.js từ nguồn sự thật ccn-data.json.

NGUỒN SỰ THẬT cho mục A/B/C là ccn-data.json. Phần intro (tổng quan tỉnh) và
footer (mục D Lưu ý + E Hướng dẫn hồ sơ) là nội dung TĨNH biên tập tay, đặt tại
  tools/chatbot-context-intro.md
  tools/chatbot-context-footer.md
— sửa hai file đó nếu muốn đổi phần tĩnh, rồi chạy lại script.

  python3 tools/build_chatbot_context.py            # ghi đè api/chatbot-context.js
  python3 tools/build_chatbot_context.py --check     # chỉ so sánh, không ghi (exit 1 nếu lệch)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def vn_num(x):
    """Định dạng số kiểu Việt Nam: ngăn nghìn bằng '.', thập phân bằng ','."""
    if x == int(x):
        s = f"{int(x):,}".replace(",", ".")
    else:
        s = f"{x:,.2f}".replace(",", "\0").replace(".", ",").replace("\0", ".")
    return s


def raw(x):
    """Giữ nguyên giá trị số như JSON (thập phân dấu chấm), bỏ .0 thừa của số nguyên."""
    if isinstance(x, float) and x == int(x):
        # KCN lưu diện tích dạng float (vd 100.0) -> giữ '100.0' như bản gốc
        return str(x)
    return str(x)


def line(label, value):
    return f"- {label}: {value}\n"


def build_section_a(units):
    total = round(sum(u.get("dienTich", 0) or 0 for u in units), 2)
    out = [f"## A. {len(units)} Cụm công nghiệp đã thành lập ({vn_num(total)} ha)\n"]
    for u in units:
        out.append(f"### {u['ten']}\n")
        out.append(line("Vị trí", u.get("xa", "")))
        out.append(
            f"- Diện tích: {raw(u.get('dienTich',0))} ha; "
            f"đã cho thuê {raw(u.get('dienTichDaChoThue',0))} ha; "
            f"tỷ lệ lấp đầy {raw(u.get('tyLeLapDay',0))}%\n"
        )
        out.append(line("Trạng thái", u.get("trangThai", "")))
        out.append(line("Năm thành lập", u.get("namThanhLap", "")))
        out.append(line("Số doanh nghiệp", u.get("soDoanhNghiep", "")))
        out.append(line("Ngành nghề", u.get("nganhNghe", "")))
        out.append(line("Quyết định", u.get("quyetDinh", "")))
        out.append(line("Hạ tầng", u.get("haTang", "")))
        out.append(line("Mô tả", u.get("moTa", "")))
        out.append("\n")
    return "".join(out)


def build_section_b(units):
    out = [f"## B. {len(units)} Cụm công nghiệp quy hoạch\n"]
    for u in units:
        out.append(f"### {u['ten']}\n")
        out.append(line("Vị trí", u.get("xa", "")))
        out.append(line("Diện tích quy hoạch", f"{raw(u.get('dienTich',0))} ha"))
        if u.get("huongPhatTrien"):
            out.append(line("Định hướng", u["huongPhatTrien"]))
        if u.get("baoCao"):
            out.append(line("Báo cáo", u["baoCao"]))
        if u.get("ghiChu"):
            out.append(line("Ghi chú", u["ghiChu"]))
        out.append("\n")
    return "".join(out)


def build_section_c(units):
    out = [f"## C. {len(units)} Khu công nghiệp\n"]
    for u in units:
        out.append(f"### {u['ten']}\n")
        out.append(line("Vị trí", u.get("viTri", "")))
        out.append(line("Diện tích", f"{raw(u.get('dienTich',0))} ha"))
        out.append(line("Trạng thái", u.get("trangThai", "")))
        out.append(line("Mô tả", u.get("moTa", "")))
        out.append("\n")
    return "".join(out)


def build_body():
    data = json.load(open(os.path.join(ROOT, "ccn-data.json"), encoding="utf-8"))
    intro = open(os.path.join(ROOT, "tools/chatbot-context-intro.md"), encoding="utf-8").read()
    footer = open(os.path.join(ROOT, "tools/chatbot-context-footer.md"), encoding="utf-8").read()
    body = (
        intro
        + build_section_a(data["CUM_CONG_NGHIEP"])
        + build_section_b(data["CCN_CHUA_DAU_TU"])
        + build_section_c(data["KHU_CONG_NGHIEP"])
        + footer
    )
    n = len(data["CUM_CONG_NGHIEP"]) + len(data["CCN_CHUA_DAU_TU"]) + len(data["KHU_CONG_NGHIEP"])
    header = (
        "// Tự sinh từ tools/build_chatbot_context.py — DO NOT EDIT THỦ CÔNG\n"
        f"// Nội dung tóm tắt {n} đơn vị KCN/CCN tỉnh Lào Cai cho Trợ lý AI\n"
    )
    return header + "export const CHATBOT_CONTEXT = " + json.dumps(body, ensure_ascii=False) + ";\n"


def main():
    out_path = os.path.join(ROOT, "api/chatbot-context.js")
    new = build_body()
    if "--check" in sys.argv:
        cur = open(out_path, encoding="utf-8").read() if os.path.exists(out_path) else ""
        if cur != new:
            print("LỆCH: api/chatbot-context.js chưa khớp nguồn. Chạy lại không có --check.")
            sys.exit(1)
        print("OK: api/chatbot-context.js đã khớp nguồn.")
        return
    open(out_path, "w", encoding="utf-8").write(new)
    print(f"Đã ghi {out_path} ({len(new)} ký tự).")


if __name__ == "__main__":
    main()

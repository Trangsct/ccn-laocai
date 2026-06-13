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
import re
import sys
import unicodedata
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mã huyện -> tên (đồng bộ HUYEN_LIST trong data.js)
HUYEN_TEN = {
    "tp-lao-cai": "TP. Lào Cai", "bao-thang": "Bảo Thắng", "bao-yen": "Bảo Yên",
    "bat-xat": "Bát Xát", "bac-ha": "Bắc Hà", "muong-khuong": "Mường Khương",
    "sa-pa": "TX. Sa Pa", "si-ma-cai": "Si Ma Cai", "van-ban": "Văn Bàn",
    "yen-binh": "Yên Bình", "van-chan": "Văn Chấn", "luc-yen": "Lục Yên",
    "tran-yen": "Trấn Yên", "van-yen": "Văn Yên", "khu-vuc-moi": "Khu vực Sáp nhập",
}


def slugify(s):
    """Tạo slug giống app.js để khớp khóa trong unit-details.json."""
    s = re.sub(r'^Cụm công nghiệp\s+', 'CCN ', s, flags=re.I)
    s = re.sub(r'^Khu công nghiệp\s+', 'KCN ', s, flags=re.I)
    s = s.lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('đ', 'd')
    s = re.sub(r'[^a-z0-9\s-]', '', s).strip()
    return re.sub(r'-+', '-', re.sub(r'\s+', '-', s))


def strip_html(s):
    """Bỏ thẻ HTML, gộp khoảng trắng -> text thuần cho chatbot."""
    t = re.sub(r'<[^>]+>', ' ', s or '')
    t = (t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
           .replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' '))
    return re.sub(r'\s+', ' ', t).strip()


def load_unit_details():
    """slug -> phần giới thiệu chi tiết (text thuần) từ unit-details.json."""
    d = json.load(open(os.path.join(ROOT, "unit-details.json"), encoding="utf-8"))
    out = {}
    for k, v in d.items():
        if isinstance(v, dict) and v.get("gioiThieu"):
            out[k] = strip_html(v["gioiThieu"])
    return out


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


def append_detail(out, ten, det):
    """Nhồi phần giới thiệu chi tiết (text thuần) từ unit-details.json nếu có."""
    txt = det.get(slugify(ten))
    if txt:
        out.append(f"- Chi tiết: {txt}\n")


def build_stats(data):
    """Mục thống kê tổng hợp tính trực tiếp từ dữ liệu danh mục."""
    tl = data["CUM_CONG_NGHIEP"]
    qh = data["CCN_CHUA_DAU_TU"]
    kcn = data["KHU_CONG_NGHIEP"]
    tt = Counter(u.get("trangThai") for u in tl)
    dn = sum(u.get("soDoanhNghiep", 0) or 0 for u in tl)
    hd = [u for u in tl if u.get("trangThai") == "hoat-dong"]
    lapday = round(sum(u.get("tyLeLapDay", 0) or 0 for u in hd) / len(hd), 1) if hd else 0
    dx = [u for u in qh if u.get("deXuatBoSung")]
    huyen = Counter(HUYEN_TEN.get(u.get("huyen"), u.get("huyen")) for u in tl)
    top = sorted(tl, key=lambda u: u.get("dienTich", 0) or 0, reverse=True)[:5]

    o = ["## Thống kê tổng hợp (tính từ dữ liệu danh mục, cập nhật theo QĐ 525/QĐ-UBND)\n"]
    o.append("- Định hướng đến 2030: 56 Cụm công nghiệp / 3.052,81 ha (54 cụm theo Quyết định 525/QĐ-UBND = 2.927,81 ha + 02 cụm huy động bổ sung trước năm 2030 là Gia Hội ~50 ha và Phong Hải ~75 ha) và 20 Khu công nghiệp / 5.797 ha.\n")
    o.append(f"- Cụm công nghiệp đã thành lập: {len(tl)} cụm (903,78 ha theo báo cáo Sở Công Thương) — {tt.get('hoat-dong',0)} đang hoạt động, {tt.get('xay-dung',0)} đang xây dựng hạ tầng. Tổng {dn} doanh nghiệp/dự án đăng ký; tỷ lệ lấp đầy bình quân của các cụm đang hoạt động ~{raw(lapday)}%.\n")
    o.append(f"- Cụm công nghiệp chưa thành lập (mục B): {len(qh)} cụm, trong đó {len(dx)} cụm là huy động bổ sung trước năm 2030 (Gia Hội, Phong Hải — huy động khi có nhà đầu tư đề xuất). Theo Quyết định 525/QĐ-UBND, nhóm chưa thành lập định hướng 35 cụm với tổng 1.914,40 ha (Danh mục thu hút đầu tư hạ tầng giai đoạn 2026-2030, suất vốn 7,611 tỷ đồng/ha).\n")
    kcn_tt = Counter(u.get("trangThai") for u in kcn)
    o.append(f"- Khu công nghiệp: {len(kcn)} đơn vị trong danh mục — 07 đã thành lập (2.138,89 ha), 14 chưa thành lập (3.558 ha theo Quy hoạch); trạng thái: {kcn_tt.get('hoat-dong',0)} hoạt động, {kcn_tt.get('xay-dung',0)} đang xây dựng, {kcn_tt.get('quy-hoach',0)} quy hoạch, {kcn_tt.get('rut-qh',0)} rút khỏi quy hoạch.\n")
    dist = "; ".join(f"{k}: {v}" for k, v in sorted(huyen.items(), key=lambda x: -x[1]))
    o.append(f"- Phân bố Cụm công nghiệp đã thành lập theo khu vực: {dist}.\n")
    tops = "; ".join(f"{u['ten']} ({raw(u.get('dienTich',0))} ha)" for u in top)
    o.append(f"- Một số Cụm công nghiệp đã thành lập có diện tích lớn nhất: {tops}.\n")
    o.append("- 04 Cụm công nghiệp đã thành lập sẽ rút khỏi quy hoạch đến 2030 (di dời phục vụ đường sắt tốc độ cao và chuyển đổi mục đích sử dụng đất): Đầm Hồng, Tây Cầu Mậu A, Đông Phố Mới, Sơn Mãn.\n")
    o.append("\n")
    return "".join(o)


def build_section_a(units, det):
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
        append_detail(out, u["ten"], det)
        out.append("\n")
    return "".join(out)


def build_section_b(units, det):
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
        append_detail(out, u["ten"], det)
        out.append("\n")
    return "".join(out)


def build_section_c(units, det):
    out = [f"## C. {len(units)} Khu công nghiệp\n"]
    for u in units:
        out.append(f"### {u['ten']}\n")
        out.append(line("Vị trí", u.get("viTri", "")))
        out.append(line("Diện tích", f"{raw(u.get('dienTich',0))} ha"))
        out.append(line("Trạng thái", u.get("trangThai", "")))
        out.append(line("Mô tả", u.get("moTa", "")))
        append_detail(out, u["ten"], det)
        out.append("\n")
    return "".join(out)


def build_body():
    data = json.load(open(os.path.join(ROOT, "ccn-data.json"), encoding="utf-8"))
    intro = open(os.path.join(ROOT, "tools/chatbot-context-intro.md"), encoding="utf-8").read()
    footer = open(os.path.join(ROOT, "tools/chatbot-context-footer.md"), encoding="utf-8").read()
    det = load_unit_details()
    body = (
        intro
        + build_stats(data)
        + build_section_a(data["CUM_CONG_NGHIEP"], det)
        + build_section_b(data["CCN_CHUA_DAU_TU"], det)
        + build_section_c(data["KHU_CONG_NGHIEP"], det)
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

# -*- coding: utf-8 -*-
"""
KHÂU 1 - Bot thu thập văn bản từ Data360X (https://csdlvb.laocai.gov.vn), chạy trên máy Windows ở cơ quan.

Cách chạy (các file .bat trong thư mục bot/ gọi sẵn):
  python bot-data360x.py --dang-nhap    mở Chrome hồ sơ riêng tại Data360X để cán bộ đăng nhập lần đầu
  python bot-data360x.py --giu-phien    chỉ mở trang chủ rồi đóng, giữ phiên SSO (07h, 12h, 15h)
  python bot-data360x.py                chạy chính (18h): quét Văn bản đến + Văn bản đi 3 ngày gần nhất,
                                        lọc văn bản theo dõi, tải PDF, đẩy lên inbox/ của repo đích
  python bot-data360x.py --soi          như chạy chính nhưng KHÔNG đẩy lên GitHub; lưu HTML/ảnh vào logs/soi/
                                        để hoàn thiện selector (dùng khi trang đổi giao diện)

Hồ sơ Chrome + cấu hình + log: D:\\du-an\\bot-profile  (đổi bằng biến môi trường BOT_HOME)
  config.json: {"github_token": "...", "telegram_token": "", "telegram_chat_id": ""}
  logs\\YYYY-MM-DD.log

Nguyên tắc: không đăng nhập hộ, không giải captcha. Bị đưa về trang đăng nhập thì mở cửa sổ Chrome cho
cán bộ tự đăng nhập, thông báo Windows + Telegram, thử lại mỗi 15 phút tối đa 6 lần.

Đang nối: loại 1 (GP sử dụng VLNCN) và loại 9 (GP vận chuyển hàng hóa nguy hiểm) -> repo vlncn-laocai.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.request
import urllib.error
from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from pathlib import Path

BOT_HOME = Path(os.environ.get("BOT_HOME") or (r"D:\du-an\bot-profile" if Path("D:\\").exists() else r"C:\du-an\bot-profile"))
PROFILE = BOT_HOME / "chrome-profile"
LOG_DIR = BOT_HOME / "logs"
CONFIG = BOT_HOME / "config.json"
GOC_WEB = "https://csdlvb.laocai.gov.vn"
TRANG_CHU = GOC_WEB + "/trang-chu/"
TRANG = {"den": "https://csdlvb.laocai.gov.vn/van-ban-den/", "di": "https://csdlvb.laocai.gov.vn/van-ban-di/"}
SO_NGAY_QUET = 3
SO_NGAY_QUET_SOI = 30      # chế độ soi quét rộng hơn để chắc chắn gặp giấy phép mà thử tải PDF
CHO_DANG_NHAP_PHUT = 15
SO_LAN_CHO_DANG_NHAP = 6
GITHUB_OWNER = "Trangsct"

# Loại văn bản theo dõi (mục V bản giao việc). Bước 2: loại 1 (GP sử dụng VLNCN) và loại 9 (GP vận chuyển HHNH).
# NGUYÊN TẮC (Bạn chốt 02/9/2026): trích yếu trên Data360X hay sai/thiếu (ghi "Dự thảo" dù đã phát hành, tên tổ chức
# cụt...), nên trích yếu CHỈ dùng để lọc sơ bộ; phân loại cuối cùng và mọi dữ liệu ghi lên web căn cứ NỘI DUNG PDF
# (khâu 2 đọc bằng Gemini). Vì vậy bot gom RỘNG: mọi GP-SCT của Phòng Công nghiệp đều tải; không loại vì chữ "Dự thảo".
def _ty(vb):
    return " " + bo_dau(vb["trich_yeu"]) + " "


def _gp_phong_cong_nghiep(vb):
    return ("GP-SCT" in vb["so_ky_hieu"].upper() and vb["nguon"] == "di"
            and "cong nghiep" in bo_dau(vb.get("don_vi", "")))


LOAI_VAN_BAN = [
    {
        "ma": "gp_su_dung_vlncn",
        "ten": "Giấy phép sử dụng VLNCN",
        "repo": "vlncn-laocai",
        "khop": lambda vb: (
            (_gp_phong_cong_nghiep(vb)
             and ("vat lieu no" in _ty(vb) or "no min" in _ty(vb) or " no tai " in _ty(vb) or " de no " in _ty(vb)))
            or ("GP-UBND" in vb["so_ky_hieu"].upper() and vb["nguon"] == "den" and "vat lieu no" in _ty(vb))
        ),
    },
    {
        "ma": "gp_van_chuyen_hhnh",
        "ten": "Giấy phép vận chuyển hàng hóa nguy hiểm",
        "repo": "vlncn-laocai",
        "khop": lambda vb: (
            _gp_phong_cong_nghiep(vb) and "van chuyen" in _ty(vb)
            and ("hang hoa nguy hiem" in _ty(vb) or "hhnh" in _ty(vb))
        ),
    },
    {
        # Giấy phép khác của Phòng Công nghiệp mà trích yếu không đủ để xếp loại -> vẫn tải, khâu 2 phân loại theo nội dung
        "ma": "gp_cong_nghiep_chua_ro",
        "ten": "Giấy phép Phòng Công nghiệp (chưa rõ loại, phân loại theo PDF)",
        "repo": "vlncn-laocai",
        "khop": _gp_phong_cong_nghiep,
    },
]


# ---------------------------------------------------------------- GOM TRI THỨC CHO CÁC PLUGIN
# Bạn chốt 12/9/2026: "cập nhật thông tin cả công văn đi và đến cho tất cả các plugin, để phục vụ công
# việc một cách tốt và chính xác hơn".
#
# Hai luồng tách bạch:
#   1. GIẤY PHÉP cá biệt (LOAI_VAN_BAN ở trên) -> inbox/ -> máy đọc PDF -> cơ sở dữ liệu giấy phép.
#   2. TRI THỨC: mọi văn bản đi + đến còn lại được xếp theo lĩnh vực của từng plugin trong kho skill-sct;
#      văn bản quy phạm / chỉ đạo / hướng dẫn thì tải PDF về kho RIÊNG TƯ vlncn-laocai/theo-doi/ kèm một
#      bản tin theo ngày, để Claude đọc rồi cập nhật plugin (Bạn chốt: việc đọc hiểu và cập nhật plugin
#      là của Claude bản cao nhất, máy chỉ làm phần cơ học).
#
# TUYỆT ĐỐI không đẩy văn bản nội bộ sang skill-sct hay ccn-laocai: hai kho đó CÔNG KHAI ra Internet.
REPO_TRI_THUC = "vlncn-laocai"
THU_MUC_TRI_THUC = "theo-doi"
TOI_DA_PDF_MOI_LUOT = 30       # chặn trần để một lượt quét bù 120 ngày không phình kho
PDF_TOI_DA_MB = 12

# Từ khóa viết KHÔNG DẤU, khớp trong trích yếu + loại văn bản. Một văn bản có thể thuộc nhiều lĩnh vực.
LINH_VUC = [
    {"ma": "kccn-sct-vn", "ten": "Khu công nghiệp, cụm công nghiệp",
     "tu_khoa": ["khu cong nghiep", "cum cong nghiep", " kcn", " ccn", "ha tang ky thuat cum",
                 "chu dau tu ha tang"]},
    {"ma": "sd-vlncn-sct-vn", "ten": "Sử dụng vật liệu nổ công nghiệp, phương án nổ mìn",
     "tu_khoa": ["vat lieu no cong nghiep", " vlncn", "no min", "phuong an no", "tien chat thuoc no"]},
    {"ma": "kho-vlncn-sct-vn", "ten": "Kho vật liệu nổ công nghiệp",
     "tu_khoa": ["kho vat lieu no", "kho vlncn", "kho chua vat lieu no", "bai chua vat lieu no"]},
    {"ma": "hl-vlncn-sct-vn", "ten": "Huấn luyện kỹ thuật an toàn VLNCN",
     "tu_khoa": ["huan luyen ky thuat an toan", "huan luyen vat lieu no", "giay chung nhan huan luyen",
                 "sat hach", "boi duong nghiep vu chi huy no min"]},
    {"ma": "hnh-sct-vn", "ten": "Vận chuyển hàng hóa nguy hiểm",
     "tu_khoa": ["hang hoa nguy hiem", " hhnh", "van chuyen hang nguy hiem"]},
    {"ma": "hc-sct-vn", "ten": "Hóa chất, tiền chất công nghiệp",
     "tu_khoa": ["hoa chat", "tien chat", "khai bao hoa chat", "su co hoa chat", "phieu kiem soat"]},
    {"ma": "attp-sct-vn", "ten": "An toàn thực phẩm ngành Công Thương",
     "tu_khoa": ["an toan thuc pham", " attp", "thuc pham", "ruou", "bia", "nuoc giai khat",
                 "banh keo", "dau thuc vat", "tu cong bo san pham", "co so du dieu kien"]},
    {"ma": "atvsld-sct-vn", "ten": "An toàn, vệ sinh lao động",
     "tu_khoa": ["an toan ve sinh lao dong", "atvsld", "an toan lao dong", "tai nan lao dong",
                 "kiem dinh may", "kiem dinh thiet bi"]},
    {"ma": "pccc-sct-vn", "ten": "Phòng cháy, chữa cháy và cứu nạn cứu hộ",
     "tu_khoa": ["phong chay", "chua chay", " pccc", "cuu nan cuu ho", "phuong an chua chay"]},
    {"ma": "bvmt-sct-vn", "ten": "Bảo vệ môi trường ngành Công Thương",
     "tu_khoa": ["bao ve moi truong", "danh gia tac dong moi truong", " dtm", "giay phep moi truong",
                 "chat thai", "khi thai", "quan trac moi truong", "kinh te tuan hoan"]},
    {"ma": "qlks-sct-vn", "ten": "Quản lý khoáng sản",
     "tu_khoa": ["khoang san", "khai thac mo", "giay phep khai thac", "tan thu khoang san",
                 "dong cua mo", "bai thai", "apatit", "quang ", "quan ly mo", "tru luong"]},
    {"ma": "tkm-sct-vn", "ten": "Thẩm định thiết kế mỏ",
     "tu_khoa": ["thiet ke mo", "thiet ke co so", "thiet ke ky thuat thi cong mo", "tham dinh thiet ke"]},
    {"ma": "xd-sct-vn", "ten": "Xây dựng chuyên ngành Công Thương",
     "tu_khoa": ["giay phep xay dung", "bao cao nghien cuu kha thi", "nghiem thu cong trinh",
                 "tham dinh du an", "cong trinh dien", "cum cong trinh", "kiem tra cong tac nghiem thu"]},
    {"ma": "dacn-sct-vn", "ten": "Dự án công nghiệp, chỉ tiêu tăng trưởng",
     "tu_khoa": ["san xuat cong nghiep", "chi so san xuat", " iip", "gia tri san xuat cong nghiep",
                 "tang truong", "danh muc du an", "tien do du an", "kich ban tang truong",
                 "chu truong dau tu", "khuyen cong", "cum lien ket nganh"]},
    {"ma": "quy-hoach-ct-vn", "ten": "Quy hoạch ngành Công Thương",
     "tu_khoa": ["quy hoach", "phuong an phat trien", "dieu chinh quy hoach", "ke hoach su dung dat",
                 "luoi dien", "nang luong", "thuy dien", "dien luc", "dien mat troi", "dien gio",
                 "phat dien", "nha may dien", "tram bien ap", "duong day", "gia dien", "phu tai"]},
    {"ma": "xp-sct-vn", "ten": "Xử phạt vi phạm hành chính, kiểm tra chuyên ngành",
     "tu_khoa": ["vi pham hanh chinh", "xu phat", "thanh tra", "kiem tra chuyen nganh", "kiem tra lien nganh",
                 "cuong che", "khac phuc hau qua", "don thu", "khieu nai", "to cao"]},
    {"ma": "vbhc-vn", "ten": "Soạn thảo, thể thức văn bản hành chính",
     "tu_khoa": ["the thuc van ban", "cong tac van thu", "luu tru", "nghi dinh 30/2020", "ky so",
                 "chung thuc dien tu"]},
    {"ma": "sct-laocai-org-vn", "ten": "Tổ chức bộ máy, phân công nhiệm vụ của Sở",
     "tu_khoa": ["co cau to chuc", "phan cong nhiem vu", "quy che lam viec", "kien toan", "bo nhiem",
                 "dieu dong", "thanh lap to cong tac", "phan cong cong tac", "vi tri viec lam"]},
    {"ma": "bpb-sct-vn", "ten": "Bài phát biểu, tham luận của lãnh đạo Sở",
     "tu_khoa": ["bai phat bieu", "tham luan", "dien van", "de cuong phat bieu", "tra loi phong van"]},
]


def xep_linh_vuc(vb):
    """Văn bản này liên quan tới plugin nào? Trả danh sách mã (có thể nhiều, có thể rỗng)."""
    chu = " " + bo_dau(f"{vb.get('trich_yeu', '')} {vb.get('loai', '')}") + " "
    return [lv["ma"] for lv in LINH_VUC if any(tk in chu for tk in lv["tu_khoa"])]


def la_giay_phep_ca_biet(vb):
    """Giấy phép/giấy chứng nhận cấp cho một doanh nghiệp cụ thể. Không dùng để cập nhật plugin vì
    không chứa quy định mới - đã có dây chuyền riêng đọc vào cơ sở dữ liệu giấy phép."""
    sk = (vb.get("so_ky_hieu") or "").upper()
    return any(x in sk for x in ("/GP-", "/GCN-", "/GXN-", "/CC-"))


# Loại văn bản MANG QUY ĐỊNH - đọc là có thể phải sửa plugin. Nhận qua số ký hiệu.
KY_HIEU_QUY_PHAM = ("/NĐ-CP", "/TT-", "/QĐ-TTG", "/QĐ-UBND", "/QĐ-BCT", "/CT-", "/NQ-",
                    "/KH-", "/HD-", "/QC-", "/TB-")
# Công văn thường nhưng nội dung là quy định đang hình thành -> vẫn đáng đọc.
TU_KHOA_QUY_PHAM = ("du thao", "quy dinh", "huong dan", "tieu chi", "quy che", "de an",
                    "chuong trinh", "tong ket", "so ket", "ke hoach", "sua doi", "thay the")
# Không bao giờ tải: giấy mời, hồ sơ mời thầu, lịch họp - không có quy định nào trong đó.
TU_KHOA_BO_QUA = ("giay moi", "moi hop", "moi du", "goi thau", "ho so moi thau", "e-hsmt",
                  "lich cong tac", "lich tiep cong dan")


def dang_gom(vb):
    """Có tải PDF về để Claude đọc và cập nhật plugin không?

    Bạn chốt 12/9/2026 sau lượt chạy đầu: tải mọi văn bản khớp từ khóa thì một lượt 30 ngày kéo về
    101 MB / 40 tệp, phần lớn là công văn trao đổi từng dự án và cả giấy mời họp - đọc không sửa được
    plugin nào. Nay chỉ tải văn bản MANG QUY ĐỊNH; văn bản còn lại vẫn vào mục lục đầy đủ (có số, ngày,
    trích yếu, đường dẫn trang chi tiết) nên cần bản gốc nào thì gọi bot tải riêng văn bản đó.
    """
    if not xep_linh_vuc(vb) or la_giay_phep_ca_biet(vb):
        return False
    sk = (vb.get("so_ky_hieu") or "").upper()
    ty = " " + bo_dau(vb.get("trich_yeu", "")) + " "
    if "/GM-" in sk or any(t in ty for t in TU_KHOA_BO_QUA):
        return False
    return any(k in sk for k in KY_HIEU_QUY_PHAM) or any(t in ty for t in TU_KHOA_QUY_PHAM)


def trich_chu_pdf(pdf_bytes):
    """Lấy lớp chữ trong PDF. Không có pypdf hoặc PDF là bản scan (không có lớp chữ) thì trả chuỗi rỗng.

    Vì sao cần (12/9/2026): lượt gom đầu tiên tải 40 PDF hết 101 MB, mỗi tuần như vậy là kho phình vài GB
    một năm. Trong khi thứ Claude cần để cập nhật plugin là NỘI DUNG chữ - nặng vài chục KB. Nên văn bản
    nào đọc được chữ thì chỉ lưu chữ; bản scan không có lớp chữ mới giữ nguyên PDF.
    """
    # pymupdf đọc tiếng Việt tốt hơn; pypdf là đường lui. Máy chưa có thì cài một lần, lần sau sẵn rồi.
    for goi, cach in (("pymupdf", "pymupdf"), ("pypdf", "pypdf")):
        for lan in (1, 2):
            try:
                if cach == "pymupdf":
                    import pymupdf
                    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
                        return "\n\n".join(t.get_text().strip() for t in doc).strip()
                from pypdf import PdfReader
                import io
                return "\n\n".join((t.extract_text() or "").strip()
                                    for t in PdfReader(io.BytesIO(pdf_bytes)).pages).strip()
            except ImportError:
                if lan == 2:
                    break
                log(f"  [tri thức] chưa có {goi}, đang cài...")
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install", "-q", goi], timeout=300)
                except Exception:
                    break
            except Exception as e:
                log(f"  [tri thức] {goi} không đọc được:", repr(e))
                break
    return ""


def _json_gh(repo, duong, token, mac_dinh):
    raw, sha = gh_doc(repo, duong, token)
    try:
        return (json.loads(raw) if raw else mac_dinh), sha
    except Exception:
        return mac_dinh, sha


def gom_tri_thuc(ctx, page, van_ban, token, tu_ngay, toi_da=TOI_DA_PDF_MOI_LUOT):
    """Xếp mọi văn bản đi + đến theo lĩnh vực plugin, tải PDF văn bản quy phạm/chỉ đạo, ghi bản tin.

    Ghi lên kho riêng tư vlncn-laocai:
      theo-doi/danh-muc-<năm>.json  mục lục MỌI văn bản quét được (kể cả loại chưa xếp được lĩnh vực)
      theo-doi/<năm>/<số>.pdf       bản gốc văn bản đáng đọc
      theo-doi/bao-cao/<ngày>.md    bản tin để Claude đọc đầu phiên rồi cập nhật plugin
      theo-doi/_da-gom.json         đã ghi nhận rồi thì lượt sau bỏ qua
    """
    nam = date.today().year
    danh_muc, sha_muc = _json_gh(REPO_TRI_THUC, f"{THU_MUC_TRI_THUC}/danh-muc-{nam}.json", token, [])
    da_gom, sha_gom = _json_gh(REPO_TRI_THUC, f"{THU_MUC_TRI_THUC}/_da-gom.json", token, {})

    moi, da_tai, loi = [], 0, []
    for vb in sorted(van_ban, key=lambda v: (parse_ngay(v["ngay_ban_hanh"]) or date.min), reverse=True):
        khoa = f"{vb['so_ky_hieu']}|{vb['ngay_ban_hanh']}"
        if khoa in da_gom:
            continue
        ghi = {k: vb.get(k, "") for k in ("so_ky_hieu", "ngay_ban_hanh", "trich_yeu", "don_vi",
                                          "nguoi_ky", "loai", "nguon", "url_chi_tiet")}
        ghi["linh_vuc"] = xep_linh_vuc(vb)
        ghi["gom_luc"] = date.today().isoformat()
        if dang_gom(vb):
            if da_tai >= toi_da:
                loi.append(f"{vb['so_ky_hieu']}: đã chạm trần {toi_da} tệp/lượt, để lượt sau")
            else:
                # Data360X có văn bản để trống số ký hiệu (bản cam kết, phụ lục doanh nghiệp gửi lên):
                # lấy tên theo mã văn bản trên cổng, nếu không sẽ ra tệp rỗng tên ".md" (vụ 12/9/2026).
                ten_tep = lam_sach_vn(vb["so_ky_hieu"]) or f"vb-{vb.get('id_data360x') or 'khong-so'}"
                goc = f"{THU_MUC_TRI_THUC}/{nam}/{ten_tep}"
                try:
                    pdf = tai_pdf(ctx, page, vb)
                except Exception as e:
                    log(f"  [tri thức] lỗi tải {vb['so_ky_hieu']}: {e!r}")
                    pdf = None
                if not pdf:
                    loi.append(f"{vb['so_ky_hieu']}: không tìm thấy PDF")
                else:
                    chu = trich_chu_pdf(pdf)
                    msg_vb = f"Theo dõi văn bản: {vb['so_ky_hieu']}"
                    if len(chu) >= 800:          # đọc được chữ -> lưu chữ, nhẹ hơn PDF vài chục lần
                        dau = [f"# {vb['so_ky_hieu']} - {vb['trich_yeu']}", "",
                               f"- Ngày ban hành: {vb['ngay_ban_hanh']}",
                               f"- Nguồn: văn bản {'đến' if vb['nguon'] == 'den' else 'đi'}"
                               f" | Đơn vị: {vb.get('don_vi', '')} | Người ký: {vb.get('nguoi_ky', '')}",
                               f"- Lĩnh vực: {', '.join(ghi['linh_vuc'])}",
                               f"- Bản gốc trên Data360X: {vb.get('url_chi_tiet', '')}",
                               "",
                               "> Chữ dưới đây lấy từ lớp text của PDF. Số và ngày ở trường ký số có thể "
                               "không nằm trong lớp text - lấy theo hai dòng trên, hoặc mở bản gốc.",
                               "", "---", "", chu]
                        duong = goc + ".md"
                        gh_ghi(REPO_TRI_THUC, duong, "\n".join(dau).encode(), msg_vb, token)
                    elif len(pdf) <= PDF_TOI_DA_MB * 1024 * 1024:
                        duong = goc + ".pdf"     # bản scan, không có lớp chữ -> giữ nguyên PDF
                        gh_ghi(REPO_TRI_THUC, duong, pdf, msg_vb + " (bản scan)", token)
                    else:
                        loi.append(f"{vb['so_ky_hieu']}: bản scan {len(pdf) // 1024 // 1024} MB, "
                                   f"quá lớn - chỉ ghi mục lục")
                        duong = ""
                    if duong:
                        ghi["tep"] = duong
                        da_tai += 1
                        log(f"  [tri thức] {vb['so_ky_hieu']} ({', '.join(ghi['linh_vuc'])}) -> {duong}")
        danh_muc.append(ghi)
        da_gom[khoa] = ghi["gom_luc"]
        moi.append(ghi)

    if not moi:
        log("  [tri thức] không có văn bản nào mới so với lần trước")
        return 0

    # --- bản tin cho Claude đọc đầu phiên
    ten_lv = {lv["ma"]: lv["ten"] for lv in LINH_VUC}
    huong = {"den": "đến", "di": "đi"}
    dong = [f"# Văn bản mới trên Data360X - {date.today().strftime('%d/%m/%Y')}", "",
            f"Quét từ ngày {tu_ngay.strftime('%d/%m/%Y')}: {len(van_ban)} văn bản đi + đến, "
            f"trong đó {len(moi)} văn bản lần đầu ghi nhận, tải về {da_tai} tệp.", "",
            "Cách dùng: Claude đọc mục nào thì mở tệp PDF tương ứng trong `theo-doi/`, đối chiếu plugin "
            "cùng tên trong kho `skill-sct`, sửa nếu có quy định/số liệu mới rồi nâng phiên bản plugin.",
            "",
            "Văn bản không có đường dẫn PDF là loại không mang quy định (công văn trao đổi từng việc, "
            "giấy mời, hồ sơ mời thầu) nên chỉ ghi mục lục. Cần bản gốc của một văn bản trong đó thì mở "
            "`url_chi_tiet` của nó trong `danh-muc-<năm>.json`, hoặc chạy workflow *Tim van ban vien dan "
            "(may co quan)*.", ""]
    for ma, ten in ten_lv.items():
        nhom = [r for r in moi if ma in r["linh_vuc"]]
        if not nhom:
            continue
        dong.append(f"## {ma} - {ten} ({len(nhom)} văn bản)")
        if len(nhom) > 40:
            dong.append(f"*Liệt kê 40 văn bản mới nhất; đủ {len(nhom)} văn bản xem `danh-muc-{nam}.json`.*")
            dong.append("")
        for r in nhom[:40]:
            tep = f" -> `{r['tep']}`" if r.get("tep") else (
                " *(giấy phép cá biệt, đã vào cơ sở dữ liệu giấy phép)*" if la_giay_phep_ca_biet(r)
                else " *(chưa tải được PDF)*")
            dong.append(f"- [{huong.get(r['nguon'], r['nguon'])}] **{r['so_ky_hieu']}** "
                        f"ngày {r['ngay_ban_hanh']} - {r['trich_yeu']}{tep}")
        dong.append("")
    khac = [r for r in moi if not r["linh_vuc"]]
    if khac:
        dong += [f"## Chưa xếp được vào plugin nào ({len(khac)} văn bản, chỉ ghi mục lục)", "",
                 "Nếu một chủ đề lặp lại nhiều lần ở mục này thì nên cân nhắc lập plugin mới, "
                 "hoặc bổ sung từ khóa vào bảng LINH_VUC. "
                 f"Liệt kê 25 văn bản mới nhất; đủ danh sách xem `danh-muc-{nam}.json`.", ""]
        for r in khac[:25]:
            dong.append(f"- [{huong.get(r['nguon'], r['nguon'])}] {r['so_ky_hieu']} "
                        f"ngày {r['ngay_ban_hanh']} - {r['trich_yeu']}")
        dong.append("")
    if loi:
        dong += ["## Chỗ máy chưa lấy được", ""] + [f"- {x}" for x in loi] + [""]

    duong_bt = f"{THU_MUC_TRI_THUC}/bao-cao/{date.today().isoformat()}.md"
    _, sha_bt = gh_doc(REPO_TRI_THUC, duong_bt, token)
    msg = f"Theo dõi văn bản {date.today().strftime('%d/%m/%Y')}: {len(moi)} văn bản mới, tải {da_tai} tệp"
    gh_ghi(REPO_TRI_THUC, duong_bt, "\n".join(dong).encode(), msg, token, sha_bt)
    gh_ghi(REPO_TRI_THUC, f"{THU_MUC_TRI_THUC}/danh-muc-{nam}.json",
           json.dumps(danh_muc, ensure_ascii=False, indent=1).encode(), msg, token, sha_muc)
    gh_ghi(REPO_TRI_THUC, f"{THU_MUC_TRI_THUC}/_da-gom.json",
           json.dumps(da_gom, ensure_ascii=False, indent=1).encode(), msg, token, sha_gom)
    log(f"  [tri thức] {len(moi)} văn bản mới, tải {da_tai} tệp, bản tin: {duong_bt}")
    return len(moi)


_log_f = None


def log(*a):
    global _log_f
    s = datetime.now().strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    if _log_f is None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _log_f = open(LOG_DIR / f"{date.today().isoformat()}.log", "a", encoding="utf-8")
    _log_f.write(s + "\n")
    _log_f.flush()


def bo_dau(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.replace("đ", "d").replace("Đ", "D")).strip().lower()


def lam_sach(so_ky_hieu):
    """2743/GP-UBND -> 2743_GP-UBND (theo quy ước đặt tên file trong vlncn-laocai-files)."""
    return re.sub(r"[^A-Za-z0-9_.\-]+", "_", so_ky_hieu.strip()).strip("_")


def lam_sach_vn(so_ky_hieu):
    """Như lam_sach nhưng bỏ dấu trước, để 5962/SXD-PTĐT ra 5962_SXD-PTDT chứ không phải 5962_SXD-PT_T
    (vụ 12/9/2026: dấu tiếng Việt bị thay bằng gạch dưới, nhìn tên tệp không biết là văn bản nào)."""
    s = unicodedata.normalize("NFD", str(so_ky_hieu or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^A-Za-z0-9_.\-]+", "_", s.strip()).strip("_")


def parse_ngay(s):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def doc_config():
    """Đọc config.json. Tệp bị thừa nội dung (dán đè, chạy cài đặt 2 lần...) thì lấy khối JSON ĐẦU TIÊN
    rồi ghi lại cho sạch, thay vì bỏ trắng token như trước (vụ 04/9/2026: 'Extra data: line 5 column 3')."""
    if not CONFIG.exists():
        return {}
    chu = CONFIG.read_text(encoding="utf-8-sig").strip()
    try:
        return json.loads(chu)
    except json.JSONDecodeError:
        pass
    try:
        cfg, _ = json.JSONDecoder().raw_decode(chu)      # bỏ phần thừa phía sau
        if isinstance(cfg, dict):
            log("config.json có phần thừa - đã lấy phần hợp lệ và ghi lại cho sạch.")
            try:
                CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                log("  (không ghi lại được:", repr(e), ")")
            return cfg
    except Exception as e:
        log("config.json lỗi:", e)
    # cứu vớt lần cuối: nhặt từng khóa bằng biểu thức
    cfg = {k: m.group(1) for k in ("github_token", "telegram_token", "telegram_chat_id")
           for m in [re.search(rf'"{k}"\s*:\s*"([^"]*)"', chu)] if m}
    if cfg.get("github_token"):
        log("config.json hỏng nặng - đã nhặt được token, ghi lại tệp mới.")
        try:
            CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    else:
        log("config.json không đọc được token nào.")
    return cfg


# ---------------------------------------------------------------- thông báo
def thong_bao_windows(tieu_de, noi_dung):
    if os.name != "nt":
        return
    ps = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $n = $t.GetElementsByTagName('text'); $n.Item(0).AppendChild($t.CreateTextNode('{tieu_de}')) | Out-Null
    $n.Item(1).AppendChild($t.CreateTextNode('{noi_dung}')) | Out-Null
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Bot Data360X').Show([Windows.UI.Notifications.ToastNotification]::new($t))
    """
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=20, capture_output=True)
    except Exception as e:
        log("Không hiện được thông báo Windows:", e)


def telegram(noi_dung):
    cfg = doc_config()
    tok, chat = cfg.get("telegram_token"), cfg.get("telegram_chat_id")
    if not tok or not chat:
        return
    try:
        data = json.dumps({"chat_id": chat, "text": noi_dung[:4000]}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        log("Telegram lỗi:", e)


# ---------------------------------------------------------------- GitHub Contents API
def gh(method, url, body=None, token=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code == 404 and method == "GET":
            return None
        raise RuntimeError(f"GitHub {e.code}: {e.read()[:200]!r}")


def gh_doc(repo, path, token):
    r = gh("GET", f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/contents/{path}?ref=main", token=token)
    if not r:
        return None, None
    return base64.b64decode(r["content"]), r["sha"]


def gh_ghi(repo, path, noi_dung: bytes, msg, token, sha=None):
    body = {"message": msg, "content": base64.b64encode(noi_dung).decode(), "branch": "main"}
    if sha:
        body["sha"] = sha
    return gh("PUT", f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/contents/{path}", body, token)


def ghi_nhip_tim(token, tong_quet, da_day, loi):
    """Ghi 'nhịp tim' mỗi lần bot chạy, kể cả khi không có văn bản mới.

    GitHub căn vào tệp này để biết máy đã nghỉ bao lâu: quá 7 ngày thì tự mở một phiên chạy online
    (Bạn chốt 04/9/2026). Để ngoài thư mục inbox/ để không kích hoạt workflow đọc Gemini mỗi lần ghi.
    """
    import socket

    noi_dung = {
        "lan_cuoi": datetime.now().isoformat(timespec="minutes"),
        "may": socket.gethostname(),
        "quet": tong_quet,
        "day": len(da_day),
        "loi": loi[:5],
    }
    try:
        _, sha = gh_doc("vlncn-laocai", "trang-thai/bot-chay.json", token)
        gh_ghi("vlncn-laocai", "trang-thai/bot-chay.json",
               json.dumps(noi_dung, ensure_ascii=False, indent=2).encode(),
               f"Bot Data360X: nhịp tim {noi_dung['lan_cuoi']} ({socket.gethostname()})", token, sha)
        log("  đã ghi nhịp tim lên GitHub")
    except Exception as e:
        log("  không ghi được nhịp tim:", repr(e))


def da_xu_ly_doc(repo, token):
    raw, sha = gh_doc(repo, "inbox/_da-xu-ly.json", token)
    try:
        return (json.loads(raw) if raw else {}), sha
    except Exception:
        return {}, sha


# ---------------------------------------------------------------- trình duyệt
def mo_trinh_duyet(p, headless=False):
    PROFILE.mkdir(parents=True, exist_ok=True)
    return p.chromium.launch_persistent_context(
        str(PROFILE), headless=headless, channel="chrome" if os.name == "nt" else None,
        viewport={"width": 1400, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh",
        accept_downloads=True, args=["--disable-blink-features=AutomationControlled"],
    )


def mo_trinh_duyet_online(p, phien_json):
    """Chạy trên GitHub: KHÔNG đăng nhập, chỉ dùng lại phiên Bạn đã đăng nhập tay rồi xuất lên
    (đúng ràng buộc 1: không giải captcha, không tự đăng nhập)."""
    b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    # Cổng Data360X không gửi kèm chứng thư trung gian. Chrome trên Windows tự đi tải nên vào được, còn
    # Chromium trên máy chủ Linux thì không, dẫn tới treo 90 giây rồi lỗi (vụ 04/9/2026). Workflow cài sẵn
    # chứng thư trung gian; BO_QUA_TLS=1 chỉ dùng khi cách đó không xong.
    ctx = b.new_context(storage_state=json.loads(phien_json), viewport={"width": 1400, "height": 900},
                        locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh", accept_downloads=True,
                        ignore_https_errors=os.environ.get("BO_QUA_TLS") == "1")
    return ctx


def cap_nhat_secret(repo, ten, gia_tri: str, token):
    """Ghi phiên vào GitHub Secret (mã hoá bằng khoá công khai của repo trước khi gửi)."""
    from base64 import b64encode

    from nacl import encoding, public      # pip install pynacl

    kc = gh("GET", f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/actions/secrets/public-key", token=token)
    hop = public.SealedBox(public.PublicKey(kc["key"].encode(), encoding.Base64Encoder()))
    gh("PUT", f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/actions/secrets/{ten}",
       {"encrypted_value": b64encode(hop.encrypt(gia_tri.encode())).decode(), "key_id": kc["key_id"]}, token)


def xuat_phien():
    """Chạy trên máy Bạn: lấy phiên Data360X đang đăng nhập rồi cất vào GitHub Secret DATA360X_PHIEN."""
    from playwright.sync_api import sync_playwright

    cfg = doc_config()
    token = cfg.get("github_token", "")      # thiếu token vẫn chạy được: cuối cùng sẽ đi đường dán tay
    with sync_playwright() as p:
        ctx = mo_trinh_duyet(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(4000)
            if can_dang_nhap(page):
                print("\nPhiên đã hết. Hãy đăng nhập Data360X trong cửa sổ vừa mở (nhập captcha như thường),")
                print("thấy trang chủ hiện ra thì quay lại đây và bấm Enter.")
                try:
                    input()
                except EOFError:
                    page.wait_for_timeout(120000)
                page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(3000)
            if can_dang_nhap(page):
                log("Vẫn chưa đăng nhập được, chưa xuất phiên.")
                return 1
            phien = json.dumps(ctx.storage_state(), ensure_ascii=False)
        finally:
            ctx.close()
    if not token:
        log("Chưa có github_token trong config.json - chuyển sang cách dán tay.")
        return dan_tay(phien)
    try:
        cap_nhat_secret("vlncn-laocai", "DATA360X_PHIEN", phien, token)
    except Exception as e:
        # Token không có quyền ghi Secret (403) -> chép sẵn vào clipboard, Bạn dán tay 1 lần.
        log("Không tự ghi được khóa lên GitHub:", repr(e))
        return dan_tay(phien)
    log(f"Đã đưa phiên lên GitHub ({len(phien)} ký tự). Từ giờ GitHub tự quét, không cần máy này.")
    thong_bao_windows("Bot Data360X", "Đã đưa phiên đăng nhập lên GitHub. GitHub sẽ tự quét hằng ngày.")
    return 0


def dan_tay(phien):
    """Đường lui khi token không được phép ghi Secret: lưu ra file, chép vào clipboard, mở sẵn trang GitHub."""
    tep = BOT_HOME / "phien-data360x.txt"
    tep.write_text(phien, encoding="utf-8")
    da_chep = False
    if os.name == "nt":
        try:
            subprocess.run("clip", input=phien.encode("utf-16-le"), check=True)
            da_chep = True
        except Exception as e:
            log("  (không chép được vào clipboard:", repr(e), ")")
    trang = "https://github.com/Trangsct/vlncn-laocai/settings/secrets/actions/new"
    print()
    print("=" * 64)
    print("  CHỈ CÒN 1 BƯỚC DÁN TAY (khoảng 30 giây)")
    print("=" * 64)
    print(f"  Phiên đăng nhập đã lưu tại: {tep}")
    print("  Nội dung " + ("ĐÃ CHÉP SẴN vào clipboard (Ctrl+V là ra)." if da_chep
                           else "nằm trong file trên: mở bằng Notepad, Ctrl+A rồi Ctrl+C."))
    print()
    print("  1. Trang GitHub vừa mở (nếu chưa mở, vào địa chỉ dưới đây):")
    print(f"     {trang}")
    print("  2. Ô Name gõ:   DATA360X_PHIEN")
    print("  3. Ô Secret bấm Ctrl+V để dán, rồi bấm nút Add secret.")
    print("  4. Xong. Đóng cửa sổ này. GitHub sẽ tự quét Data360X 18h hằng ngày.")
    print()
    print("  (Nếu GitHub báo khóa đã tồn tại: bấm vào tên DATA360X_PHIEN trong danh sách,")
    print("   dán chuỗi mới rồi bấm Update secret.)")
    print("=" * 64)
    try:
        import webbrowser

        webbrowser.open(trang)
    except Exception:
        pass
    thong_bao_windows("Bot Data360X", "Phiên đã chép vào clipboard - dán vào GitHub Secret DATA360X_PHIEN")
    return 0


def can_dang_nhap(page):
    u = page.url.lower()
    if "login.yenbai.gov.vn" in u or "/login" in u or "dang-nhap" in u:
        return True
    try:
        return page.locator("#usernameUserInput, input[name='username']").count() > 0
    except Exception:
        return False


def cho_dang_nhap(ctx, page, p=None):
    """Mở cửa sổ nhìn thấy được, báo cán bộ đăng nhập, chờ tối đa 6 x 15 phút.

    Trả (ok, ctx, page): Chrome bị đóng giữa chừng (vụ 16/9/2026 - lượt quét thứ Tư chết sau 17 giây vì
    TargetClosedError) thì mở lại cửa sổ và chờ tiếp thay vì đổ cả lượt chạy; vì thế ctx/page có thể là mới.
    """
    thong_bao_windows("Bot cần bạn đăng nhập lại Data360X", "Đăng nhập trong cửa sổ Chrome vừa mở, bot sẽ tự chạy tiếp.")
    telegram("Bot Data360X: phiên đăng nhập hết hạn. Hãy đăng nhập lại trong cửa sổ Chrome trên máy cơ quan.")
    for lan in range(SO_LAN_CHO_DANG_NHAP):
        log(f"Chờ đăng nhập, lần {lan + 1}/{SO_LAN_CHO_DANG_NHAP} (tối đa {CHO_DANG_NHAP_PHUT} phút)")
        het = time.time() + CHO_DANG_NHAP_PHUT * 60
        while time.time() < het:
            try:
                page.wait_for_timeout(10000)
                if not can_dang_nhap(page) and "csdlvb.laocai.gov.vn" in page.url:
                    log("Đã đăng nhập, chạy tiếp.")
                    return True, ctx, page
            except Exception as e:
                if p is None:
                    raise
                log("Cửa sổ Chrome bị đóng khi đang chờ đăng nhập - mở lại:", repr(e))
                time.sleep(5)
                try:
                    ctx.close()
                except Exception:
                    pass
                ctx = mo_trinh_duyet(p, headless=False)
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
                page.bring_to_front()
    log("Hết thời gian chờ đăng nhập.")
    return False, ctx, page


def cho_bang(page):
    page.wait_for_selector("table.p-datatable-table", timeout=60000)
    page.wait_for_timeout(2000)   # Next.js vẽ xong dữ liệu


def doc_bang(page, nguon):
    """Đọc mọi dòng trên trang hiện tại. Cột nhận diện theo tiêu đề."""
    heads = [bo_dau(h.inner_text()) for h in page.locator("table.p-datatable-table thead th").all()]
    idx = {}
    for i, h in enumerate(heads):
        if "so/ky hieu" in h or "so ky hieu" in h:
            idx["so"] = i
        elif h.startswith("ngay ban hanh"):
            idx["ngay"] = i
        elif "trich yeu" in h:
            idx["trich_yeu"] = i
        elif "don vi ban hanh" in h or "don vi soan thao" in h:
            idx["don_vi"] = i
        elif "nguoi ky" in h:
            idx["nguoi_ky"] = i
        elif "loai van ban" in h:
            idx["loai"] = i
    if "so" not in idx or "trich_yeu" not in idx:
        raise RuntimeError(f"Không nhận ra cột bảng ({nguon}): {heads}")
    ket = []
    for tr in page.locator("table.p-datatable-table tbody tr").all():
        cells = tr.locator("td").all()
        if len(cells) <= idx["trich_yeu"]:
            continue
        lay = lambda k: cells[idx[k]].inner_text().strip() if k in idx else ""
        link = tr.locator("a[href*='/detail/']").first
        href = link.get_attribute("href") if link.count() else ""
        href = urljoin(GOC_WEB, href) if href else ""      # Data360X trả đường dẫn tương đối /van-ban-di/detail/?id=...
        m = re.search(r"[?&]id=(\d+)", href or "")
        ket.append({
            "so_ky_hieu": lay("so"), "ngay_ban_hanh": lay("ngay"), "trich_yeu": lay("trich_yeu"),
            "don_vi": lay("don_vi"), "nguoi_ky": lay("nguoi_ky"), "loai": lay("loai"),
            "nguon": nguon, "id_data360x": m.group(1) if m else "", "url_chi_tiet": href or "",
        })
    return ket


def quet_danh_sach(page, nguon, tu_ngay, soi_dir=None):
    """Duyệt các trang phân trang cho tới khi gặp văn bản cũ hơn tu_ngay (bảng sắp theo ngày giảm dần)."""
    page.goto(TRANG[nguon], wait_until="domcontentloaded", timeout=90000)
    if can_dang_nhap(page):
        return None
    cho_bang(page)
    if soi_dir:
        (soi_dir / f"danh-sach-{nguon}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(soi_dir / f"danh-sach-{nguon}.png"), full_page=True)
    tat_ca, trang_so = [], 1
    while True:
        rows = doc_bang(page, nguon)
        tat_ca.extend(rows)
        ngay_cu = [parse_ngay(r["ngay_ban_hanh"]) for r in rows if parse_ngay(r["ngay_ban_hanh"])]
        log(f"  {nguon}: trang {trang_so}, {len(rows)} dòng")
        if not rows and trang_so == 1:
            # 0 dòng ngay trang đầu: hoặc thật sự không có văn bản, hoặc phiên không được cổng chấp nhận.
            # In vài dấu hiệu để phân biệt (vụ 04/9/2026: chạy trên GitHub ra 0 dòng, trên máy ra 62 dòng).
            try:
                chu = re.sub(r"\s+", " ", page.locator("body").inner_text()[:400])
                log(f"  [chẩn đoán] URL: {page.url}")
                log(f"  [chẩn đoán] tiêu đề: {page.title()}")
                log(f"  [chẩn đoán] đầu trang: {chu}")
            except Exception as e:
                log("  [chẩn đoán] không đọc được nội dung trang:", repr(e))
        # Trần 80 trang (mỗi trang 25 dòng): quét 30 ngày cần khoảng 28 trang mỗi bảng. Trần cũ 20
        # trang làm lượt 12/9/2026 cụt mất các ngày 13-19/8. Bảng sắp theo ngày giảm dần nên
        # bình thường vòng lặp tự dừng sớm, trần chỉ là lưới an toàn.
        if not rows or (ngay_cu and min(ngay_cu) < tu_ngay) or trang_so >= 80:
            break
        nut = page.locator("button.p-paginator-next")
        if not nut.count() or nut.first.is_disabled():
            break
        nut.first.click()
        page.wait_for_timeout(2500)
        cho_bang(page)
        trang_so += 1
    return [r for r in tat_ca if parse_ngay(r["ngay_ban_hanh"]) and parse_ngay(r["ngay_ban_hanh"]) >= tu_ngay]


def _la_pdf(b):
    return isinstance(b, (bytes, bytearray)) and b[:5] == b"%PDF-"


def tai_qua_chrome(page, url):
    """Cho chính Chrome (đang đăng nhập) tải URL rồi trả bytes; tránh lỗi chứng chỉ của backend."""
    js = """async (u) => {
        const r = await fetch(u, {credentials: 'include'});
        if (!r.ok) return null;
        const a = new Uint8Array(await r.arrayBuffer());
        let s = '';
        for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode.apply(null, a.subarray(i, i + 0x8000));
        return btoa(s);
    }"""
    try:
        b64 = page.evaluate(js, url)
        return base64.b64decode(b64) if b64 else None
    except Exception as e:
        log("  Chrome fetch lỗi:", str(e)[:120])
        return None


def tai_pdf(ctx, page, vb, soi_dir=None):
    """Mở trang chi tiết, tìm và tải PDF đính kèm. Trả bytes hoặc None.
    Data360X hiển thị PDF trong iframe trỏ tới csdlvb-backend.laocai.gov.vn/api/documentpublic/get-attach-by-id?...
    (backend thiếu chứng chỉ trung gian nên không tải bằng request riêng được). Thứ tự thử:
      1) bắt đúng phản hồi PDF mà Chrome đã tải cho iframe;  2) nhờ Chrome fetch lại URL đó;
      3) link .pdf / nút Tải trên trang."""
    bat_duoc = []

    def _on_response(resp):
        try:
            u = resp.url
            if "get-attach-by-id" in u or u.lower().split("?")[0].endswith(".pdf") \
                    or resp.headers.get("content-type", "").lower().startswith("application/pdf"):
                bat_duoc.append(resp)
        except Exception:
            pass

    page.on("response", _on_response)
    try:
        page.goto(vb["url_chi_tiet"], wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)   # chờ iframe tải PDF
        if soi_dir:
            (soi_dir / f"chi-tiet-{lam_sach(vb['so_ky_hieu'])}.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(soi_dir / f"chi-tiet-{lam_sach(vb['so_ky_hieu'])}.png"), full_page=True)
        # 1) phản hồi PDF Chrome đã tải cho iframe
        for resp in bat_duoc:
            try:
                b = resp.body()
                if _la_pdf(b):
                    log(f"  PDF lấy từ phản hồi của Chrome ({len(b)} bytes)")
                    return bytes(b)
            except Exception as e:
                log("  không đọc được body phản hồi:", str(e)[:100])
        # 2) nhờ Chrome fetch lại URL trong iframe / embed / object / link
        urls = []
        for sel in ("iframe[src]", "embed[src]", "object[data]"):
            for el in page.locator(sel).all():
                src = el.get_attribute("src") or el.get_attribute("data") or ""
                src = re.sub(r"^.*?file=", "", src) if "file=" in src else src   # pdf.js viewer?file=...
                if src and not src.startswith("about:"):
                    urls.append(urljoin(GOC_WEB, src))
        for a in page.locator("a[href]").all():
            href = a.get_attribute("href") or ""
            if re.search(r"\.pdf(\?|$)", href, flags=re.I) or "get-attach" in href or "download" in href.lower():
                urls.append(urljoin(GOC_WEB, href))
        for u in urls:
            b = tai_qua_chrome(page, u)
            if _la_pdf(b):
                log(f"  PDF lấy bằng Chrome fetch ({len(b)} bytes)")
                return b
            b2 = None
            try:
                r = ctx.request.get(u, timeout=120000)
                b2 = r.body() if r.ok else None
            except Exception as e:
                log("  request lỗi:", str(e)[:100])
            if _la_pdf(b2):
                return b2
        # 3) nút tải xuống
        for sel in ("a:has-text('Tải'), button:has-text('Tải')", "[aria-label*='Tải'], [title*='Tải']"):
            nut = page.locator(sel)
            if nut.count():
                try:
                    with page.expect_download(timeout=60000) as dl:
                        nut.first.click()
                    data = Path(dl.value.path()).read_bytes()
                    if _la_pdf(data):
                        return data
                except Exception as e:
                    log("  nút tải lỗi:", str(e)[:100])
        if urls:
            log("  đã thấy URL PDF nhưng không tải được:", re.sub(r"token=[A-Za-z0-9]+", "token=…", urls[0])[:140])
        return None
    finally:
        page.remove_listener("response", _on_response)


def _khop_so(a, b):
    """So số ký hiệu bỏ khoảng trắng và chữ hoa thường: '340/TTr-UBND' == '340 /TTR - UBND'."""
    lam = lambda x: re.sub(r"[\s.]", "", str(x or "")).upper()
    return lam(a) == lam(b)


def tim_van_ban(can_tim, luu_vao, so_ngay_lui=3, online=False):
    """Tìm và tải các văn bản ĐƯỢC VIỆN DẪN trong một dự thảo (Bạn chốt 04/9/2026).

    can_tim: danh sách {"so_ky_hieu": "340/TTr-UBND", "ngay": "20/8/2026"} - ngày để biết quét từ đâu.
    Quét cả văn bản đến và văn bản đi từ ngày cũ nhất trong danh sách (lùi thêm vài ngày cho chắc), lấy đúng
    những dòng khớp số ký hiệu rồi tải PDF về thư mục luu_vao.
    """
    from playwright.sync_api import sync_playwright

    cfg = doc_config()
    token = cfg.get("github_token", "")
    phien = os.environ.get("DATA360X_PHIEN", "")
    luu_vao = Path(luu_vao)
    luu_vao.mkdir(parents=True, exist_ok=True)

    ngay = [parse_ngay(v.get("ngay") or "") for v in can_tim]
    ngay = [n for n in ngay if n]
    tu_ngay = (min(ngay) if ngay else date.today() - timedelta(days=30)) - timedelta(days=so_ngay_lui)
    can = {re.sub(r"[\s.]", "", v["so_ky_hieu"]).upper(): v for v in can_tim}
    log(f"Tìm {len(can)} văn bản, quét từ {tu_ngay.isoformat()}: {', '.join(v['so_ky_hieu'] for v in can_tim)}")

    thay, thieu = [], list(can.keys())
    with sync_playwright() as p:
        ctx = mo_trinh_duyet_online(p, phien) if online else mo_trinh_duyet(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
            if can_dang_nhap(page):
                if online:
                    log("PHIÊN HẾT HẠN: chạy xuat-phien.bat trên máy rồi thử lại.")
                    return 3
                page.bring_to_front()
                ok, ctx, page = cho_dang_nhap(ctx, page, p)
                if not ok:
                    return 3
            for nguon in ("den", "di"):
                rows = quet_danh_sach(page, nguon, tu_ngay)
                if rows is None:
                    log("Bị đưa về trang đăng nhập giữa chừng.")
                    return 3
                for vb in rows:
                    khoa = re.sub(r"[\s.]", "", vb["so_ky_hieu"]).upper()
                    if khoa not in can or khoa not in thieu:
                        continue
                    log(f"  thấy {vb['so_ky_hieu']} ({nguon}) - {vb['trich_yeu'][:60]}")
                    pdf = tai_pdf(ctx, page, vb)
                    ten = lam_sach(vb["so_ky_hieu"])
                    if pdf:
                        (luu_vao / f"{ten}.pdf").write_bytes(pdf)
                    else:
                        log("    không tải được PDF, chỉ ghi thông tin")
                    (luu_vao / f"{ten}.json").write_text(
                        json.dumps(vb, ensure_ascii=False, indent=2), encoding="utf-8")
                    thay.append(vb["so_ky_hieu"])
                    thieu.remove(khoa)
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    (luu_vao / "_ket-qua-tim.json").write_text(json.dumps(
        {"tim_luc": datetime.now().isoformat(timespec="minutes"), "tu_ngay": tu_ngay.isoformat(),
         "thay": thay, "khong_thay": [can[k]["so_ky_hieu"] for k in thieu]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Tìm xong: thấy {len(thay)}, không thấy {len(thieu)}"
        + (f" ({', '.join(can[k]['so_ky_hieu'] for k in thieu)})" if thieu else ""))
    if token:
        ghi_nhip_tim(token, len(thay) + len(thieu), thay, [])
    return 0


def _tach_yeu_cau(yeu_cau):
    """"5511/SCT-CN; 3226/QĐ-UBND; tiêu chí lựa chọn chủ đầu tư" -> ([số ký hiệu chuẩn hóa], [từ khóa không dấu]).
    Mục có dấu "/" là số ký hiệu (khớp đúng), còn lại là từ khóa (khớp trong trích yếu, không phân biệt dấu)."""
    so, tu_khoa = {}, []
    for muc in re.split(r"[;\n]+", yeu_cau or ""):
        muc = muc.strip().strip('"\'')
        if not muc:
            continue
        if "/" in muc:
            so[re.sub(r"[\s.]", "", muc).upper()] = muc
        else:
            tu_khoa.append(bo_dau(muc))
    return so, tu_khoa


def lay_theo_yeu_cau(yeu_cau, luu_vao, so_ngay=60, online=False):
    """CÁNH TAY CỦA CLAUDE (Bạn chốt 17/9/2026): Claude đang làm việc cần văn bản nào thì ra lệnh cho bot vào
    Data360X lấy đúng văn bản đó, không phải chờ lượt quét tuần.

    yeu_cau: chuỗi các mục cách nhau bằng ";": số ký hiệu (có "/") hoặc từ khóa trong trích yếu.
    Quét cả văn bản đến và đi trong so_ngay ngày gần nhất, tải mọi dòng khớp, lưu vào luu_vao:
      <số>.md   chữ trong văn bản (kèm số, ngày, đơn vị, đường dẫn bản gốc ở đầu) - bản scan thì .pdf
      _ket-qua.json + README.md   thấy gì, thiếu gì, để Claude đọc ngay
    """
    from playwright.sync_api import sync_playwright

    cfg = doc_config()
    token = cfg.get("github_token", "")
    phien = os.environ.get("DATA360X_PHIEN", "")
    luu_vao = Path(luu_vao)
    luu_vao.mkdir(parents=True, exist_ok=True)
    so, tu_khoa = _tach_yeu_cau(yeu_cau)
    if not so and not tu_khoa:
        log("Yêu cầu rỗng: cần ít nhất một số ký hiệu hoặc từ khóa.")
        return 2
    tu_ngay = date.today() - timedelta(days=so_ngay)
    log(f"Lấy theo yêu cầu, quét từ {tu_ngay.isoformat()}: số ký hiệu {list(so.values())}, từ khóa {tu_khoa}")

    thay, thieu_so = [], set(so.keys())
    with sync_playwright() as p:
        ctx = mo_trinh_duyet_online(p, phien) if online else mo_trinh_duyet(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
            if can_dang_nhap(page):
                if online:
                    log("PHIÊN HẾT HẠN: chạy xuat-phien.bat trên máy rồi thử lại.")
                    return 3
                page.bring_to_front()
                ok, ctx, page = cho_dang_nhap(ctx, page, p)
                if not ok:
                    return 3
            for nguon in ("den", "di"):
                rows = quet_danh_sach(page, nguon, tu_ngay)
                if rows is None:
                    log("Bị đưa về trang đăng nhập giữa chừng.")
                    return 3
                for vb in rows:
                    khoa = re.sub(r"[\s.]", "", vb["so_ky_hieu"]).upper()
                    ty = " " + bo_dau(vb["trich_yeu"]) + " "
                    ly_do = ("số " + so[khoa]) if khoa in so else next((f"từ khóa \"{t}\"" for t in tu_khoa if t in ty), None)
                    if not ly_do:
                        continue
                    log(f"  thấy {vb['so_ky_hieu']} ({nguon}, {ly_do}) - {vb['trich_yeu'][:60]}")
                    ten = lam_sach_vn(vb["so_ky_hieu"]) or f"vb-{vb.get('id_data360x') or 'khong-so'}"
                    if (luu_vao / f"{ten}.md").exists() or (luu_vao / f"{ten}.pdf").exists():
                        ten += "-" + (vb.get("id_data360x") or nguon)      # hai văn bản trùng số
                    try:
                        pdf = tai_pdf(ctx, page, vb)
                    except Exception as e:
                        log("    lỗi tải:", repr(e))
                        pdf = None
                    tep = ""
                    if pdf:
                        chu = trich_chu_pdf(pdf)
                        if len(chu) >= 800:
                            dau = [f"# {vb['so_ky_hieu']} - {vb['trich_yeu']}", "",
                                   f"- Ngày ban hành: {vb['ngay_ban_hanh']}",
                                   f"- Nguồn: văn bản {'đến' if nguon == 'den' else 'đi'}"
                                   f" | Đơn vị: {vb.get('don_vi', '')} | Người ký: {vb.get('nguoi_ky', '')}",
                                   f"- Lý do lấy: {ly_do}",
                                   f"- Bản gốc trên Data360X: {vb.get('url_chi_tiet', '')}", "",
                                   "> Chữ dưới đây lấy từ lớp text của PDF. Số và ngày ở trường ký số có thể "
                                   "không nằm trong lớp text - lấy theo hai dòng trên, hoặc mở bản gốc.",
                                   "", "---", "", chu]
                            tep = f"{ten}.md"
                            (luu_vao / tep).write_text("\n".join(dau), encoding="utf-8")
                        else:
                            tep = f"{ten}.pdf"
                            (luu_vao / tep).write_bytes(pdf)
                    else:
                        log("    không tải được PDF, chỉ ghi thông tin")
                    (luu_vao / f"{ten}.json").write_text(
                        json.dumps({**vb, "ly_do": ly_do, "tep": tep}, ensure_ascii=False, indent=2), encoding="utf-8")
                    thay.append({**vb, "ly_do": ly_do, "tep": tep})
                    thieu_so.discard(khoa)
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    kq = {"lay_luc": datetime.now().isoformat(timespec="minutes"), "yeu_cau": yeu_cau,
          "tu_ngay": tu_ngay.isoformat(), "thay": thay, "khong_thay_so": [so[k] for k in thieu_so]}
    (luu_vao / "_ket-qua.json").write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8")
    dong = [f"# Kết quả lấy văn bản theo yêu cầu - {datetime.now().strftime('%d/%m/%Y %H:%M')}", "",
            f"Yêu cầu: `{yeu_cau}`  |  quét từ {tu_ngay.strftime('%d/%m/%Y')}  |  thấy {len(thay)}", ""]
    for v in thay:
        dong.append(f"- [{'đến' if v['nguon'] == 'den' else 'đi'}] **{v['so_ky_hieu']}** ngày {v['ngay_ban_hanh']} "
                    f"- {v['trich_yeu']} ({v['ly_do']})" + (f" -> `{v['tep']}`" if v['tep'] else " *(không tải được PDF)*"))
    if thieu_so:
        dong += ["", "## Không thấy trong khoảng quét", ""] + [f"- {so[k]}" for k in thieu_so] + \
                ["", "Có thể văn bản cũ hơn khoảng quét (tăng --ngay) hoặc số ký hiệu ghi khác trên Data360X."]
    (luu_vao / "README.md").write_text("\n".join(dong) + "\n", encoding="utf-8")
    log(f"Lấy xong: thấy {len(thay)}, không thấy {len(thieu_so)} số ký hiệu")
    if token:
        ghi_nhip_tim(token, len(thay), [v["so_ky_hieu"] for v in thay], [])
    return 0


# ---------------------------------------------------------------- luồng chính
def chay_chinh(soi=False, so_ngay=None, online=False, gom=True, gom_toi_da=TOI_DA_PDF_MOI_LUOT):
    from playwright.sync_api import sync_playwright

    cfg = doc_config()
    token = cfg.get("github_token", "")
    phien = os.environ.get("DATA360X_PHIEN", "")
    if online:
        token = os.environ.get("BOT_GITHUB_TOKEN", "") or token
        if not phien:
            log("Chưa có phiên Data360X (secret DATA360X_PHIEN). Trên máy Bạn chạy xuat-phien.bat một lần.")
            return 4
    if not soi and not token:
        log("Chưa có github_token trong config.json. Chạy cai-dat.bat để nhập.")
        thong_bao_windows("Bot Data360X", "Chưa có token GitHub trong config.json")
        return 2
    soi_dir = None
    if soi:
        soi_dir = LOG_DIR / "soi" / datetime.now().strftime("%Y-%m-%d_%H%M")
        soi_dir.mkdir(parents=True, exist_ok=True)
    tu_ngay = date.today() - timedelta(days=so_ngay or (SO_NGAY_QUET_SOI if soi else SO_NGAY_QUET))
    tong_quet, da_day, loi, phien_moi, tri_thuc_moi = 0, [], [], None, 0

    with sync_playwright() as p:
        ctx = mo_trinh_duyet_online(p, phien) if online else mo_trinh_duyet(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
            if can_dang_nhap(page):
                if online:      # trên GitHub không có ai nhập captcha -> dừng, báo Bạn xuất lại phiên
                    log("PHIÊN HẾT HẠN: trên máy Bạn chạy xuat-phien.bat rồi để GitHub chạy tiếp.")
                    return 3
                page.bring_to_front()
                ok, ctx, page = cho_dang_nhap(ctx, page, p)
                if not ok:
                    telegram("Bot Data360X: không đăng nhập được sau 90 phút, bỏ lượt chạy hôm nay.")
                    return 3
            van_ban = []
            for nguon in ("den", "di"):
                rows = quet_danh_sach(page, nguon, tu_ngay, soi_dir)
                if rows is None:
                    log("Bị đưa về trang đăng nhập giữa chừng.")
                    return 3
                van_ban.extend(rows)
            tong_quet = len(van_ban)
            log(f"Quét được {tong_quet} văn bản từ {tu_ngay.isoformat()}")
            if soi:
                for vb in van_ban:
                    log(f"    [{vb['nguon']}] {vb['ngay_ban_hanh']} | {vb['so_ky_hieu']} | {vb.get('don_vi','')[:30]} | {vb['trich_yeu'][:80]}")

            # Lọc theo loại theo dõi
            chon = []
            for vb in van_ban:
                for loai in LOAI_VAN_BAN:
                    try:
                        if loai["khop"](vb):
                            chon.append((loai, vb))
                            break
                    except Exception:
                        pass
            log(f"Thuộc loại theo dõi: {len(chon)}")
            if soi:
                # Soi: chỉ mở 1 giấy phép (ưu tiên loại theo dõi), không có thì 1 văn bản bất kỳ
                chon = chon[:1] if chon else ([(LOAI_VAN_BAN[0], van_ban[0])] if van_ban else [])
                log("Chế độ soi: mở thử trang chi tiết của " + (chon[0][1]["so_ky_hieu"] if chon else "không có văn bản nào"))

            cache_da_xu_ly = {}
            for loai, vb in chon:
                repo = loai["repo"]
                ten = lam_sach(vb["so_ky_hieu"])
                if repo not in cache_da_xu_ly:
                    cache_da_xu_ly[repo] = da_xu_ly_doc(repo, token) if not soi else ({}, None)
                da, sha_da = cache_da_xu_ly[repo]
                if vb["so_ky_hieu"] in da:
                    log(f"  bỏ qua (đã xử lý): {vb['so_ky_hieu']}")
                    continue
                log(f"  tải PDF: {vb['so_ky_hieu']} - {vb['trich_yeu'][:70]}")
                pdf = tai_pdf(ctx, page, vb, soi_dir)
                if not pdf:
                    loi.append(f"{vb['so_ky_hieu']}: không tìm thấy PDF trên trang chi tiết")
                    log("  KHÔNG tìm thấy PDF")
                    continue
                if soi:
                    (soi_dir / f"{ten}.pdf").write_bytes(pdf)
                    log(f"  (soi) đã lưu {ten}.pdf, {len(pdf)} bytes")
                    continue
                meta = {**vb, "loai_theo_doi": loai["ma"], "tai_luc": datetime.now().isoformat(timespec="minutes")}
                msg = f"Bot Data360X: {vb['so_ky_hieu']} ({loai['ten']})"
                gh_ghi(repo, f"inbox/{ten}.pdf", pdf, msg, token)
                gh_ghi(repo, f"inbox/{ten}.json", json.dumps(meta, ensure_ascii=False, indent=2).encode(), msg, token)
                da[vb["so_ky_hieu"]] = date.today().isoformat()
                r = gh_ghi(repo, "inbox/_da-xu-ly.json", json.dumps(da, ensure_ascii=False, indent=2).encode(),
                           "Bot Data360X: cập nhật danh sách đã xử lý", token, sha_da)
                cache_da_xu_ly[repo] = (da, r["content"]["sha"])
                da_day.append(f"{vb['so_ky_hieu']} -> {repo}")
                log(f"  đã đẩy lên {repo}/inbox/{ten}.pdf")

            # Gom tri thức cho các plugin: xếp MỌI văn bản đi + đến theo lĩnh vực, tải văn bản quy phạm /
            # chỉ đạo về kho riêng tư rồi ghi bản tin (Bạn chốt 12/9/2026).
            if gom and not soi:
                log("Gom tri thức cho các plugin...")
                try:
                    tri_thuc_moi = gom_tri_thuc(ctx, page, van_ban, token, tu_ngay, gom_toi_da)
                except Exception as e:
                    log("  [tri thức] lỗi:", repr(e))
                    loi.append(f"gom tri thức: {e!r}")
        finally:
            try:
                if online:
                    phien_moi = json.dumps(ctx.storage_state(), ensure_ascii=False)
            except Exception as e:
                log("Không đọc lại được phiên:", repr(e))
            try:
                ctx.close()
            except Exception:
                pass

    tom_tat = (f"Bot Data360X {date.today().isoformat()}: quét {tong_quet} văn bản, "
               f"đẩy {len(da_day)} file"
               + (f", theo dõi thêm {tri_thuc_moi} văn bản cho plugin" if tri_thuc_moi else "")
               + (": " + "; ".join(da_day) if da_day else "")
               + (f". Lỗi {len(loi)}: " + "; ".join(loi) if loi else ""))
    log(tom_tat)
    if not soi:
        ghi_nhip_tim(token, tong_quet, da_day, loi)
        telegram(tom_tat)
    if online and phien_moi:
        try:
            cap_nhat_secret("vlncn-laocai", "DATA360X_PHIEN", phien_moi, token)
            log("Đã lưu lại phiên vừa làm mới (kéo dài hạn dùng).")
        except Exception as e:
            log("Không lưu lại được phiên:", repr(e))
    return 0


def giu_phien():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = mo_trinh_duyet(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(5000)
            if can_dang_nhap(page):
                log("Giữ phiên: phiên đã hết, cần đăng nhập lại.")
                thong_bao_windows("Bot Data360X", "Phiên Data360X đã hết hạn. Mở dang-nhap-lan-dau.bat để đăng nhập lại.")
                telegram("Bot Data360X: phiên đăng nhập đã hết hạn (phát hiện lúc giữ phiên). Hãy đăng nhập lại trên máy cơ quan.")
                return 3
            log("Giữ phiên: OK")
        finally:
            ctx.close()
    return 0


def dang_nhap_lan_dau():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = mo_trinh_duyet(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
        print("\nHãy đăng nhập Data360X trong cửa sổ Chrome vừa mở (nhập captcha như thường).")
        print("Khi thấy trang chủ Data360X hiện ra, quay lại cửa sổ này và bấm Enter để lưu phiên.")
        try:
            input()
        except EOFError:
            page.wait_for_timeout(120000)
        ok = not can_dang_nhap(page)
        log("Đăng nhập lần đầu:", "OK, đã lưu hồ sơ Chrome" if ok else "chưa thấy đăng nhập")
        ctx.close()
    return 0 if ok else 1


def kiem_tra_token():
    """Kiểm tra token GitHub trong config.json: đọc 4 repo, ghi rồi xóa 1 file thử trong 2 repo đích."""
    token = doc_config().get("github_token", "")
    if not token:
        print("CHUA CO token trong", CONFIG)
        return 1
    ok = True
    try:
        u = gh("GET", "https://api.github.com/user", token=token)
        print(f"Token hop le, tai khoan: {u.get('login')}")
    except Exception as e:
        print("Token KHONG hop le:", e)
        return 1
    for repo in ("ccn-laocai", "vlncn-laocai", "vlncn-laocai-files", "skill-sct"):
        r = gh("GET", f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}", token=token)
        print(f"  doc {repo:22s}: {'OK' if r else 'KHONG THAY (chua tich repo nay khi tao token)'}")
        ok = ok and bool(r)
    for repo in ("vlncn-laocai", "ccn-laocai"):
        path = "inbox/.thu-token.txt"
        try:
            r = gh_ghi(repo, path, b"kiem tra quyen ghi, tu xoa", "kiểm tra quyền ghi token bot (tự xóa)", token)
            gh("DELETE", f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/contents/{path}",
               {"message": "xóa file kiểm tra quyền ghi", "sha": r["content"]["sha"], "branch": "main"}, token)
            print(f"  ghi {repo:22s}: OK (da ghi va xoa file thu)")
        except Exception as e:
            print(f"  ghi {repo:22s}: KHONG ({e}) -> token thieu quyen Contents: Read and write")
            ok = False
    print("\nKET QUA:", "TOKEN DUNG DUOC, sang buoc dang-nhap-lan-dau.bat" if ok else "TOKEN CHUA DUNG DUOC, tao lai token theo huong dan")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dang-nhap", action="store_true")
    ap.add_argument("--giu-phien", action="store_true")
    ap.add_argument("--soi", action="store_true")
    ap.add_argument("--ngay", type=int, help="quét N ngày gần nhất (mặc định 3; chạy bù lần đầu dùng 30)")
    ap.add_argument("--kiem-tra-token", action="store_true")
    ap.add_argument("--xuat-phien", action="store_true", help="đưa phiên đăng nhập hiện tại lên GitHub Secret")
    ap.add_argument("--online", action="store_true", help="chạy trên GitHub bằng phiên đã xuất (không đăng nhập)")
    ap.add_argument("--tim", metavar="TRICH_DAN_JSON",
                    help="tìm và tải các văn bản viện dẫn liệt kê trong tệp trich-dan.json")
    ap.add_argument("--luu", default="kem-theo", help="thư mục lưu văn bản tìm được (mặc định: kem-theo)")
    ap.add_argument("--lay", metavar="YEU_CAU",
                    help='lấy văn bản theo yêu cầu của Claude: "5511/SCT-CN; 3226/QĐ-UBND; tiêu chí lựa chọn chủ đầu tư" '
                         '(mục có "/" là số ký hiệu, còn lại là từ khóa trong trích yếu; quét --ngay ngày, mặc định 60)')
    ap.add_argument("--khong-gom", action="store_true",
                    help="chỉ lấy giấy phép, bỏ bước gom tri thức cho các plugin")
    ap.add_argument("--gom-toi-da", type=int, default=TOI_DA_PDF_MOI_LUOT,
                    help=f"tối đa bao nhiêu tệp tri thức tải về mỗi lượt (mặc định {TOI_DA_PDF_MOI_LUOT})")
    a = ap.parse_args()
    try:
        if a.kiem_tra_token:
            return kiem_tra_token()
        if a.dang_nhap:
            return dang_nhap_lan_dau()
        if a.giu_phien:
            return giu_phien()
        if a.xuat_phien:
            return xuat_phien()
        if a.lay:
            return lay_theo_yeu_cau(a.lay, a.luu, so_ngay=a.ngay or 60, online=a.online)
        if a.tim:
            d = json.loads(Path(a.tim).read_text(encoding="utf-8"))
            can = [{"so_ky_hieu": v["so_ky_hieu"], "ngay": (v.get("ngay") or [""])[0]}
                   for v in d.get("vien_dan", d if isinstance(d, list) else [])]
            return tim_van_ban(can, a.luu, online=a.online)
        return chay_chinh(soi=a.soi, so_ngay=a.ngay, online=a.online,
                          gom=not a.khong_gom, gom_toi_da=a.gom_toi_da)
    except Exception as e:
        log("LỖI:", repr(e))
        telegram(f"Bot Data360X lỗi: {e!r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

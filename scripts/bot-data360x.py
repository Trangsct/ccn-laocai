# -*- coding: utf-8 -*-
"""
KHÂU 1 - Bot thu thập văn bản, chạy trên máy Windows ở Lào Cai.
Từ 29/10/2026 cổng mặc định là egov1 (https://egov1.laocai.gov.vn - trang quản lý văn bản mới Bạn chuyển sang);
Data360X (https://csdlvb.laocai.gov.vn) vẫn dùng được bằng config.json "he_thong": "data360x" hoặc --he-thong data360x.

Cách chạy (các file .bat trong thư mục bot/ gọi sẵn):
  python bot-data360x.py --dang-nhap    mở Chrome hồ sơ riêng tại cổng (egov1/Data360X) để cán bộ đăng nhập lần đầu
  python bot-data360x.py --giu-phien    chỉ mở trang chủ rồi đóng, giữ phiên SSO (07h, 12h, 15h)
  python bot-data360x.py                chạy chính (18h): quét Văn bản đến + Văn bản đi 3 ngày gần nhất,
                                        lọc văn bản theo dõi, tải PDF, đẩy lên inbox/ của repo đích
  python bot-data360x.py --soi          như chạy chính nhưng KHÔNG đẩy lên GitHub; lưu HTML/ảnh vào logs/soi/
                                        để hoàn thiện selector (dùng khi trang đổi giao diện)
  python bot-data360x.py --khao-sat     (egov1) đi một vòng cổng, ghi HTML/ảnh/API lên vlncn-laocai/theo-doi/egov/soi/
  python bot-data360x.py --viec         (egov1) việc Chưa/Chờ/Đang xử lý trong Văn bản đến: tải toàn văn, đẩy lên
                                        vlncn-laocai/theo-doi/viec-cho-xu-ly/<ngày>/ (thay vOffice)

Hồ sơ Chrome + cấu hình + log: <ổ>:\\du-an\\bot-profile với thư mục du-an đã có sẵn trên ổ D/E/F/G, không thì C:\\du-an\\bot-profile (đổi bằng biến môi trường BOT_HOME)
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
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.request
import urllib.error
from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlparse
from datetime import date, datetime, timedelta
from pathlib import Path

def _goc_du_an() -> Path:
    r"""Thư mục du-an ĐÃ CÓ sẵn trên ổ D/E/F/G (tạo trước khi cài), không thì C:\du-an (máy cơ quan: ổ D cấm ghi, ổ D bé)."""
    goc = Path(r"C:\du-an")
    for o in "DEFG":
        if Path(f"{o}:\\du-an").is_dir():
            goc = Path(f"{o}:\\du-an")
    return goc

BOT_HOME = Path(os.environ.get("BOT_HOME") or (_goc_du_an() / "bot-profile"))
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
TOI_DA_PDF_MOI_LUOT = 60       # chặn trần để một lượt quét bù 120 ngày không phình kho (30 -> 60 từ 10/10/2026: một tuần ~90 tệp)
LAY_TOI_DA_MOI_TU_KHOA = 12    # --lay: một từ khóa rộng ("quy chuẩn kỹ thuật quốc gia") không được kéo về hàng chục hồ sơ
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


def _cung_van_ban_gh(duong, vb, danh_muc, token):
    """True nếu chưa có tệp ở `duong` trên GitHub, hoặc tệp đó là của CHÍNH văn bản này (ghi đè được)."""
    raw, _ = gh_doc(REPO_TRI_THUC, duong, token)
    if raw is None:
        return True
    if any(m.get("tep") == duong and m.get("so_ky_hieu") == vb["so_ky_hieu"] for m in danh_muc):
        return True
    return raw[:400].decode("utf-8", "ignore").startswith(f"# {vb['so_ky_hieu']} -")


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
    cho_ghi = {}                                   # đường dẫn -> bytes, đẩy MỘT commit cuối lượt
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
                # Vụ 10/10/2026: trước đây vẫn ghi vào da_gom nên "để lượt sau" không bao giờ tới (96 văn bản
                # của ba lượt 12/9, 30/9, 10/10 bị kẹt, trong đó QĐ 3628/QĐ-UBND, QĐ 6320/QĐ-SCT). Nay bỏ qua
                # hẳn - không vào mục lục, không đánh dấu - để lượt sau quét lại từ đầu.
                loi.append(f"{vb['so_ky_hieu']}: đã chạm trần {toi_da} tệp/lượt, để lượt sau")
                continue
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
                dinh_kem = tai_dinh_kem(ctx, page, vb)            # hồ sơ nhiều tệp (17/9/2026)
                luong = doc_luong_xu_ly(page)
                vai, nguoi_xl, han_xl = suy_vai_tro(luong)
                dinh_kem += lay_theo_qr(ctx, vb, pdf, dinh_kem)   # tài liệu sau mã QR (17/9/2026)
                if not pdf and not any(d.get("bytes") for d in dinh_kem):
                    loi.append(f"{vb['so_ky_hieu']}: không tìm thấy PDF")
                elif pdf and len(pdf) > PDF_TOI_DA_MB * 1024 * 1024 and len(trich_chu_pdf(pdf)) < 800:
                    loi.append(f"{vb['so_ky_hieu']}: bản scan {len(pdf) // 1024 // 1024} MB, quá lớn - chỉ ghi mục lục")
                else:
                    dau = [f"# {vb['so_ky_hieu']} - {vb['trich_yeu']}", "",
                           f"- Ngày ban hành: {vb['ngay_ban_hanh']}",
                           f"- Nguồn: văn bản {'đến' if vb['nguon'] == 'den' else 'đi'}"
                           f" | Đơn vị: {vb.get('don_vi', '')} | Người ký: {vb.get('nguoi_ky', '')}",
                           f"- Lĩnh vực: {', '.join(ghi['linh_vuc'])}",
                           f"- Bản gốc trên {TEN_HE_THONG}: {vb.get('url_chi_tiet', '')}"] + dong_luong_md(luong, vai, nguoi_xl, han_xl) + [
                           "",
                           "> Chữ dưới đây lấy từ lớp text của PDF. Số và ngày ở trường ký số có thể "
                           "không nằm trong lớp text - lấy theo hai dòng trên, hoặc mở bản gốc."]
                    ghi["vai_tro_phong"], ghi["nguoi_xu_ly_chinh"], ghi["han_xu_ly"] = vai, nguoi_xl, han_xl
                    ten_goc = goc.rsplit("/", 1)[1]
                    thu_muc = goc.rsplit("/", 1)[0]
                    goi, ten_chinh = dong_goi_ho_so(vb, ten_goc, pdf, dinh_kem, dau)
                    # Vụ 10/10/2026: tệp cùng tên đã có trên GitHub -> GitHub 422 "sha wasn't supplied", cả bước
                    # gom dừng, không ra bản tin. Cùng văn bản (gom lại sau lượt hỏng) thì ghi đè; văn bản KHÁC
                    # trùng tên thì thêm hậu tố mã Data360X/ngày để không đè mất.
                    if ten_chinh and not _cung_van_ban_gh(f"{thu_muc}/{ten_chinh}", vb, danh_muc, token):
                        ten_goc += "_" + (str(vb.get("id_data360x") or "") or lam_sach_vn(vb["ngay_ban_hanh"]))
                        goi, ten_chinh = dong_goi_ho_so(vb, ten_goc, pdf, dinh_kem, dau)
                    for ten_t, du_lieu in goi:          # ghi một lần cuối lượt (gh_mot_commit)
                        cho_ghi[f"{thu_muc}/{ten_t}"] = du_lieu
                    duong = f"{thu_muc}/{ten_chinh}"
                    ghi["tep"] = duong
                    ghi["dinh_kem"] = [{"ten": d["ten"], "tai_duoc": bool(d.get("bytes"))} for d in dinh_kem]
                    da_tai += 1
                    log(f"  [tri thức] {vb['so_ky_hieu']} ({', '.join(ghi['linh_vuc'])}) -> {duong}"
                        + (f" + {sum(1 for d in dinh_kem if d.get('bytes'))} đính kèm" if dinh_kem else ""))
        danh_muc.append(ghi)
        da_gom[khoa] = ghi["gom_luc"]
        moi.append(ghi)

    if not moi:
        log("  [tri thức] không có văn bản nào mới so với lần trước")
        return 0

    # --- bản tin cho Claude đọc đầu phiên
    ten_lv = {lv["ma"]: lv["ten"] for lv in LINH_VUC}
    huong = {"den": "đến", "di": "đi"}
    dong = [f"# Văn bản mới trên {TEN_HE_THONG} - {date.today().strftime('%d/%m/%Y')}", "",
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
            # Nhãn đúng với lý do (vụ 29/10/2026: mọi công văn trao đổi đều bị ghi "chưa tải được PDF" dù bot không hề thử)
            tep = f" -> `{r['tep']}`" if r.get("tep") else (
                " *(giấy phép cá biệt, đã vào cơ sở dữ liệu giấy phép)*" if la_giay_phep_ca_biet(r)
                else " *(chưa tải được PDF)*" if dang_gom(r)
                else " *(công văn trao đổi, chỉ ghi mục lục - cần bản gốc thì sai bot lấy)*")
            dau_tl = "" if not isinstance(r, dict) else ("" if r.get("da_tra_loi") else "⚠️ CHƯA trả lời - ")
            dong.append(f"- {dau_tl}[{huong.get(r['nguon'], r['nguon'])}] **{r['so_ky_hieu']}** "
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
    msg = f"Theo dõi văn bản {date.today().strftime('%d/%m/%Y')}: {len(moi)} văn bản mới, tải {da_tai} tệp"
    cho_ghi[duong_bt] = "\n".join(dong).encode()
    cho_ghi[f"{THU_MUC_TRI_THUC}/danh-muc-{nam}.json"] = json.dumps(danh_muc, ensure_ascii=False, indent=1).encode()
    cho_ghi[f"{THU_MUC_TRI_THUC}/_da-gom.json"] = json.dumps(da_gom, ensure_ascii=False, indent=1).encode()
    try:
        gh_mot_commit(REPO_TRI_THUC, cho_ghi, msg, token)
    except Exception as e:
        log("  [tri thức] một commit không được, ghi từng tệp:", str(e)[:120])
        for duong, nd in cho_ghi.items():
            try:
                gh_ghi_de(REPO_TRI_THUC, duong, nd, msg, token)
            except Exception as e2:
                log(f"  [tri thức] lỗi ghi {duong}: {e2!r}"[:200])
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
    if r.get("encoding") == "none" or (not r.get("content") and r.get("size")):
        # Tệp > 1 MB: Contents API trả content rỗng. Không tải bản thô thì danh-muc-<năm>.json (992 KB ngày
        # 10/10/2026) bị đọc thành rỗng rồi ghi đè mất mục lục -> tải bản thô.
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/contents/{path}?ref=main",
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github.raw",
                     "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(req, timeout=300) as rr:
            return rr.read(), r["sha"]
    return base64.b64decode(r["content"]), r["sha"]


def gh_ghi(repo, path, noi_dung: bytes, msg, token, sha=None):
    body = {"message": msg, "content": base64.b64encode(noi_dung).decode(), "branch": "main"}
    if sha:
        body["sha"] = sha
    return gh("PUT", f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/contents/{path}", body, token)


def gh_ghi_de(repo, path, noi_dung: bytes, msg, token):
    """Ghi tệp; đã có tệp cùng đường dẫn (GitHub 422 vì thiếu sha) thì lấy sha rồi ghi đè."""
    try:
        return gh_ghi(repo, path, noi_dung, msg, token)
    except RuntimeError as e:
        if "422" not in str(e):
            raise
        _, sha = gh_doc(repo, path, token)
        if not sha:
            raise
        return gh_ghi(repo, path, noi_dung, msg, token, sha)


def thong_tin_may() -> dict:
    """Máy nào đang chạy và nối mạng kiểu gì (Bạn chốt 20/9/2026: laptop dùng wifi, máy bàn dùng LAN).

    Dùng để bản tin ghi rõ việc chạy ở máy nào, hai máy nối tiếp nhau khi Bạn di chuyển nhà - cơ quan.
    """
    import socket
    ra = {"may": socket.gethostname(), "loai": "", "mang": ""}
    if os.name != "nt":
        return ra
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "$p=(Get-NetConnectionProfile | Select-Object -First 1);"
                            "$b=(Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue);"
                            "\"$($p.InterfaceAlias)|$(if($b){'laptop'}else{'may-ban'})\""],
                           capture_output=True, timeout=25, text=True)
        chu = (r.stdout or "").strip()
        if "|" in chu:
            giao_dien, loai = chu.split("|", 1)
            ra["loai"] = loai.strip()
            g = giao_dien.lower()
            ra["mang"] = "wifi" if ("wi-fi" in g or "wireless" in g or "wlan" in g) else (
                "lan" if "ethernet" in g else giao_dien.strip())
    except Exception:
        pass
    return ra


def ghi_nhip_tim(token, tong_quet, da_day, loi):
    """Ghi 'nhịp tim' mỗi lần bot chạy, kể cả khi không có văn bản mới.

    GitHub căn vào tệp này để biết máy đã nghỉ bao lâu: quá 7 ngày thì tự mở một phiên chạy online
    (Bạn chốt 04/9/2026). Để ngoài thư mục inbox/ để không kích hoạt workflow đọc Gemini mỗi lần ghi.
    """
    import socket

    may = thong_tin_may()
    noi_dung = {
        "lan_cuoi": datetime.now().isoformat(timespec="minutes"),
        "may": socket.gethostname(),
        "loai_may": may.get("loai", ""),
        "mang": may.get("mang", ""),
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
REQ = None     # request context bỏ qua lỗi chứng thư của csdlvb-backend (thiếu chứng thư trung gian); tạo trong mo_trinh_duyet
HDR_BACKEND = {}   # Authorization (JWT) mà Chrome gửi tới csdlvb-backend - SPA giữ token ở localStorage, không ở cookie,
                   # nên request riêng chỉ mang cookie bị 401 (lượt 17/9/2026: 48 lần get-attach đều trượt trong 1 giây)
URL_BACKEND_DA_THAY = []   # đường dẫn backend đã thấy khi mở trang chi tiết (ghi log để soi API)
URL_ATTACH_DA_THAY = []    # URL đầy đủ (cả query) mà Chrome dùng để tải tệp đính kèm - làm khuôn cho các tệp còn lại
DS_TRA_LOI_JSON = []       # phản hồi JSON của API get-danh-sach-van-ban-tra-loi (biết việc đã xử lý chưa)


def _bat_header_backend(req):
    """page.on("request"): nhặt Authorization + header tùy biến Chrome gửi tới backend, dùng lại cho REQ."""
    try:
        u = req.url
        if "csdlvb-backend" not in u:
            return
        duong = u.split("?")[0].split("/api/")[-1]
        if duong not in URL_BACKEND_DA_THAY:
            URL_BACKEND_DA_THAY.append(duong)
        if "get-attach-by-id" in u and u not in URL_ATTACH_DA_THAY:
            URL_ATTACH_DA_THAY.append(u)
        h = req.headers
        for k, v in h.items():
            kl = k.lower()
            if kl in ("authorization", "token", "x-token", "x-access-token") or kl.startswith("x-auth"):
                if HDR_BACKEND.get(k) != v:
                    HDR_BACKEND[k] = v
                    log(f"  đã bắt header {k} của backend ({len(v)} ký tự)")
    except Exception:
        pass


def _gom_json_tra_loi(resp):
    """page.on("response"): gom danh sách VĂN BẢN TRẢ LỜI của một văn bản đến.

    Bạn chốt 20/9/2026: việc ở mục "Chờ xử lý" mà CHƯA có văn bản đi trả lời thì mới phải soạn.
    Cổng có sẵn API get-danh-sach-van-ban-tra-loi — dùng chính nó, không suy đoán theo trích yếu.
    """
    try:
        if "van-ban-tra-loi" in resp.url or "vanbantraloi" in resp.url.lower():
            DS_TRA_LOI_JSON.append(json.loads(resp.text()))
    except Exception:
        pass


def _gom_json_attach(resp):
    """page.on("response"): gom phản hồi JSON của backend có nhắc tới attach (danh sách đính kèm)."""
    try:
        u = resp.url
        ct = resp.headers.get("content-type", "").lower()
        if ("attach" in u.lower() and "get-attach-by-id" not in u) or ("json" in ct and "document" in u.lower()):
            chu = resp.text()
            if "attach" in chu.lower() or "get-attachs" in u:
                DS_DINH_KEM_JSON.append(json.loads(chu))
    except Exception:
        pass


def _tao_req(p, ctx):
    """Playwright APIRequestContext với ignore_https_errors, mang cookie của phiên Chrome đang đăng nhập.
    Vụ 17/9/2026: ctx.request báo 'unable to verify the first certificate', fetch trong trang bị CORS chặn."""
    global REQ
    try:
        REQ = p.request.new_context(ignore_https_errors=True, storage_state=ctx.storage_state(), timeout=120000)
    except Exception as e:
        log("  không tạo được request context riêng:", repr(e))
        REQ = None
    return REQ


def tai_bang_req(ctx, url):
    """Tải URL bằng REQ (bỏ qua chứng thư) rồi mới tới ctx.request. Trả (bytes|None, tên tệp theo content-disposition|'')."""
    for r_ctx in (REQ, ctx.request):
        if r_ctx is None:
            continue
        try:
            r = r_ctx.get(url, timeout=120000, headers=HDR_BACKEND or None)
            if r.ok:
                b = r.body()
                if b and len(b) > 200:
                    return b, _ten_tu_phan_hoi(r, url, "")
            else:
                log(f"    tải URL: HTTP {r.status} ({url[-60:]})")
        except Exception as e:
            log("    tải URL lỗi:", str(e)[:90])
    return None, ""


def mo_trinh_duyet(p, headless=False, thu_nho=False):
    """thu_nho=True: mở Chrome ở dạng thu nhỏ dưới thanh tác vụ (lượt giữ phiên mỗi giờ, không làm phiền)."""
    PROFILE.mkdir(parents=True, exist_ok=True)
    args = ["--disable-blink-features=AutomationControlled"]
    if thu_nho:
        args.append("--start-minimized")
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE), headless=headless, channel="chrome" if os.name == "nt" else None,
        viewport={"width": 1400, "height": 900}, locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh",
        accept_downloads=True, args=args,
    )
    _tao_req(p, ctx)
    return ctx


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
    _tao_req(p, ctx)
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
    thong_bao_windows(f"Bot cần bạn đăng nhập lại {TEN_HE_THONG}", "Đăng nhập trong cửa sổ Chrome vừa mở, bot sẽ tự chạy tiếp.")
    telegram(f"Bot {TEN_HE_THONG}: phiên đăng nhập hết hạn. Hãy đăng nhập lại trong cửa sổ Chrome trên máy cơ quan.")
    for lan in range(SO_LAN_CHO_DANG_NHAP):
        log(f"Chờ đăng nhập, lần {lan + 1}/{SO_LAN_CHO_DANG_NHAP} (tối đa {CHO_DANG_NHAP_PHUT} phút)")
        het = time.time() + CHO_DANG_NHAP_PHUT * 60
        while time.time() < het:
            try:
                page.wait_for_timeout(10000)
                if not can_dang_nhap(page) and GOC_WEB.split("//")[1] in page.url:
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

    DS_DINH_KEM_JSON.clear()
    DS_TRA_LOI_JSON.clear()

    def _on_response(resp):
        try:
            u = resp.url
            if "get-attach-by-id" in u or u.lower().split("?")[0].endswith(".pdf") \
                    or resp.headers.get("content-type", "").lower().startswith("application/pdf"):
                bat_duoc.append(resp)
            else:
                _gom_json_attach(resp)
                _gom_json_tra_loi(resp)
        except Exception:
            pass

    page.on("response", _on_response)
    page.on("request", _bat_header_backend)
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


# ---------------------------------------------------------------- LUỒNG XỬ LÝ (Bạn chốt 17/9/2026)
# "Đọc kỹ phần Thông tin gửi, nhận thì biết Trưởng phòng nào chủ trì (phải soạn văn bản của Sở), Trưởng phòng
# nào phối hợp (chuyên viên phòng đó soạn văn bản của phòng gửi phòng chủ trì)."
PHONG_TOI = "công nghiệp"      # phòng của người dùng, để bot suy ra vai trò chủ trì / phối hợp / nhận để biết


def doc_luong_xu_ly(page):
    """Đang ở trang chi tiết: mở tab "Thông tin gửi, nhận", đọc bảng luồng xử lý (mọi trang phân trang).
    Trả danh sách dict theo tiêu đề cột đã bỏ dấu: nguoi gui, don vi gui, thoi gian, nguoi nhan, don vi nhan,
    hanh dong, ngay qua han, trang thai."""
    ket = []
    try:
        tab = page.locator("text=/Thông tin gửi, nhận|Thông tin gửi nhận|Luồng xử lý/i")
        if not tab.count():
            return ket
        tab.first.click(timeout=5000)
        page.wait_for_timeout(1500)
        bang = None
        for t in page.locator("table").all():
            try:
                h = bo_dau(t.locator("thead").inner_text())
            except Exception:
                continue
            if "nguoi nhan" in h and ("hanh dong" in h or "trang thai" in h):
                bang = t
                break
        if bang is None:
            return ket
        heads = [bo_dau(x.inner_text()) for x in bang.locator("thead th").all()]
        # Bảng này thường NHIỀU TRANG (Bạn nhắc 17/9/2026: 16 bước / 4 trang) -> lật tới khi nút "sau" mờ đi.
        # Nút phân trang của CHÍNH bảng này: cùng khối p-datatable, không lấy nhầm nút của bảng đính kèm.
        nut = bang.locator("xpath=ancestor::div[contains(@class,'p-datatable')][1]//button[contains(@class,'p-paginator-next')]")
        if not nut.count():
            nut = bang.locator("xpath=following::button[contains(@class,'p-paginator-next')][1]")
        da_thay = set()
        for trang in range(20):
            moi_them = 0
            for tr in bang.locator("tbody tr").all():
                o = [c.inner_text().strip() for c in tr.locator("td").all()]
                if len(o) < 4:
                    continue
                khoa = "|".join(o)
                if khoa in da_thay:
                    continue
                da_thay.add(khoa)
                moi_them += 1
                ket.append({heads[i] if i < len(heads) else f"cot{i}": v for i, v in enumerate(o)})
            if not nut.count() or nut.first.is_disabled() or moi_them == 0:
                break
            nut.first.click()
            page.wait_for_timeout(1200)
        log(f"  luồng xử lý: {len(ket)} bước")
    except Exception as e:
        log("  luồng xử lý lỗi:", repr(e))
    return ket


def suy_vai_tro(luong, phong=PHONG_TOI):
    """Từ luồng xử lý suy ra vai trò của phòng: chủ trì / phối hợp / nhận để biết / không có; ai xử lý chính; hạn."""
    vai, nguoi, han = "không có", "", ""
    phong = bo_dau(phong)
    for b in luong:
        dv = bo_dau(b.get("don vi nhan", ""))
        hd = bo_dau(b.get("hanh dong", ""))
        if phong in dv:
            if "xu ly chinh" in hd or "chu tri" in hd:
                vai, nguoi = "chủ trì", b.get("nguoi nhan", "")
            elif "phoi hop" in hd and vai != "chủ trì":
                vai = "phối hợp"
            elif vai == "không có":
                vai = "nhận để biết"
        if not han:
            han = b.get("ngay qua han", "") or b.get("han xu ly", "")
    return vai, nguoi, han


def dong_luong_md(luong, vai, nguoi, han):
    """Các dòng ghi vào đầu tệp .md."""
    if not luong:
        return []
    ra = [f"- Luồng xử lý: Phòng {PHONG_TOI.title()} **{vai.upper()}**"
          + (f" — xử lý chính: {nguoi}" if nguoi else "") + (f" — hạn xử lý: {han}" if han else ""),
          "  - " + ("Phòng chủ trì → soạn văn bản của SỞ (công văn/tờ trình Sở ký)." if vai == "chủ trì" else
                    "Phòng phối hợp → chuyên viên soạn công văn NỘI BỘ của Phòng gửi phòng chủ trì." if vai == "phối hợp" else
                    "Nhận để biết → không phải soạn văn bản, chỉ theo dõi." if vai == "nhận để biết" else
                    "Phòng không có trong luồng — hỏi lại người dùng trước khi soạn."),
          "", "| Người gửi | Người nhận | Đơn vị nhận | Hành động | Trạng thái |", "|---|---|---|---|---|"]
    for b in luong:
        ra.append(f"| {b.get('nguoi gui', '')} | {b.get('nguoi nhan', '')} | {b.get('don vi nhan', '')} | "
                  f"{b.get('hanh dong', '')} | {b.get('trang thai', '')} |")
    return ra


# ---------------------------------------------------------------- HỒ SƠ NHIỀU TỆP (Bạn chốt 17/9/2026)
# "Trong 1 hồ sơ thì có nhiều file, hãy nghĩ cách tải đủ file": ngoài PDF chính hiện trong khung xem, trang chi
# tiết còn tab "File đính kèm" liệt kê dự thảo .docx, bảng so sánh, báo cáo... Bot tải tất cả, trích chữ .docx
# bằng zipfile (không cần thư viện ngoài) để Claude đọc được ngay.
DINH_KEM_TOI_DA = 15
DINH_KEM_TOI_DA_MB = 25
DUOI_TEP = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".jpg", ".png", ".txt")


def trich_chu_docx(b):
    """Chữ trong .docx: đọc word/document.xml, mỗi đoạn một dòng, ô bảng cách nhau bằng ' | '."""
    import io
    import zipfile
    import xml.etree.ElementTree as ET
    try:
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            xml = z.read("word/document.xml")
    except Exception:
        return ""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        goc = ET.fromstring(xml)
    except ET.ParseError:
        return ""
    dong = []
    body = goc.find("w:body", ns)
    if body is None:
        return ""

    def doan(p):
        return "".join(t.text or "" for t in p.iter("{%s}t" % ns["w"])).strip()

    for el in body:
        tag = el.tag.split("}")[1]
        if tag == "p":
            dong.append(doan(el))
        elif tag == "tbl":
            for tr in el.iter("{%s}tr" % ns["w"]):
                o = [" ".join(doan(p) for p in tc.iter("{%s}p" % ns["w"])).strip()
                     for tc in tr.iter("{%s}tc" % ns["w"])]
                dong.append("| " + " | ".join(o) + " |")
            dong.append("")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(dong)).strip()


def trich_chu_tep(ten, b):
    """Trả chữ của tệp theo đuôi (pdf/docx), chuỗi rỗng nếu không trích được."""
    d = ten.lower()
    if d.endswith(".pdf") or _la_pdf(b):
        return trich_chu_pdf(b)
    if d.endswith(".docx") or b[:2] == b"PK":
        return trich_chu_docx(b)
    return ""


def _ten_tep_sach(ten):
    ten = unicodedata.normalize("NFD", str(ten or "")).strip()
    ten = "".join(c for c in ten if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
    ten = re.sub(r"[^A-Za-z0-9._()\-]+", "-", ten).strip("-.")
    return ten[:90] or "tep"


DS_DINH_KEM_JSON = []     # phản hồi JSON có chứa attachId mà Chrome nhận khi mở trang chi tiết (tai_pdf gom vào)


def _nhat_attach(obj, ra):
    """Đệ quy qua JSON tìm object có attachId (hoặc id) + tên tệp."""
    if isinstance(obj, dict):
        khoa = {k.lower(): k for k in obj}
        aid = next((obj[khoa[k]] for k in ("attachid", "attach_id", "idattach", "attachmentid", "fileid", "id") if k in khoa), None)
        ten = next((obj[khoa[k]] for k in ("filename", "file_name", "attachname", "name", "tenfile", "ten_file", "fileattachname", "tentep", "ten") if k in khoa), None)
        if ten is None:
            ten = next((v for v in obj.values() if isinstance(v, str) and any(v.lower().endswith(d) for d in DUOI_TEP)), None)
        if aid and ten and isinstance(ten, str) and any(str(ten).lower().endswith(d) for d in DUOI_TEP):
            ra.append({"attachId": str(aid), "ten": ten, "obj": obj})
        for v in obj.values():
            _nhat_attach(v, ra)
    elif isinstance(obj, list):
        for v in obj:
            _nhat_attach(v, ra)


def doc_van_ban_tra_loi() -> list[dict]:
    """Trả [{"so_ky_hieu", "ngay", "trich_yeu"}] các văn bản ĐI trả lời cho văn bản đang mở."""
    ra, da = [], set()

    def _nhat(obj):
        if isinstance(obj, dict):
            khoa = {k.lower(): k for k in obj}
            so = next((obj[khoa[k]] for k in ("documenT_CODE".lower(), "document_code", "socongvan",
                                              "so_ky_hieu", "sokyhieu", "code") if k in khoa), None)
            if so and isinstance(so, str) and "/" in so:
                ty = next((obj[khoa[k]] for k in ("abstract", "trichyeu", "trich_yeu", "noidung")
                           if k in khoa), "") or ""
                ngay = next((obj[khoa[k]] for k in ("publisH_DATE".lower(), "publish_date", "ngayky",
                                                    "ngay_ban_hanh", "datE_CREATE".lower()) if k in khoa), "") or ""
                if so not in da:
                    da.add(so)
                    ra.append({"so_ky_hieu": so, "ngay": str(ngay)[:10], "trich_yeu": str(ty)[:200]})
            for v in obj.values():
                _nhat(v)
        elif isinstance(obj, list):
            for v in obj:
                _nhat(v)

    for j in DS_TRA_LOI_JSON:
        _nhat(j)
    return ra


def tai_dinh_kem(ctx, page, vb):
    """Đang ở trang chi tiết: mở tab "File đính kèm", tải từng tệp. Trả [{"ten", "loai", "bytes"}].

    Không biết trước cổng phát tệp kiểu nào nên thử lần lượt: (1) link có href; (2) bấm vào tên tệp rồi bắt
    download; (3) bắt phản hồi get-attach-by-id hoặc tab mới mở ra. Không được cái nào thì ghi log để soi sau.
    """
    ket = []
    try:
        page.on("response", _gom_json_attach)
        page.on("request", _bat_header_backend)
        tab = page.locator("text=/File đính kèm|Tệp đính kèm|Tài liệu đính kèm/i")
        if tab.count():
            try:
                tab.first.click(timeout=5000)
                page.wait_for_timeout(2500)
            except Exception:
                pass
        if URL_BACKEND_DA_THAY:
            log("  API backend đã thấy: " + ", ".join(URL_BACKEND_DA_THAY[:12]))
        for u in URL_ATTACH_DA_THAY[:4]:
            log("  URL tải tệp Chrome đã dùng: " + re.sub(r"(token=)[^&]+", r"\1…", u)[:220])
        for j in DS_DINH_KEM_JSON[:3]:
            log("  JSON đính kèm (đầu): " + json.dumps(j, ensure_ascii=False)[:600])
        if not HDR_BACKEND:
            log("  chưa bắt được Authorization của backend - request riêng có thể bị 401")
        # hàng nào có tên tệp (đuôi quen thuộc) thì coi là một tệp đính kèm
        hang = []
        for tr in page.locator("table tbody tr").all():
            try:
                chu = tr.inner_text().strip()
            except Exception:
                continue
            if any(d in chu.lower() for d in DUOI_TEP) and len(chu) < 400:
                hang.append(tr)
        if not hang:
            for a in page.locator("a[href]").all():
                try:
                    chu = (a.inner_text() or "").strip()
                    if any(chu.lower().endswith(d) for d in DUOI_TEP):
                        hang.append(a)
                except Exception:
                    pass
        if not hang:
            return ket
        log(f"  đính kèm: thấy {len(hang)} tệp")
        # Đường tắt: trang chi tiết thường đã chứa sẵn URL get-attach-by-id của từng tệp (trong href, data-*,
        # script). Tải thẳng bằng ctx.request, KHÔNG bấm - bấm vào tệp PDF từng làm Chrome đóng (vụ 17/9/2026).
        try:
            html = page.content()
        except Exception:
            html = ""
        url_san = []
        for m in re.finditer(r"""(https?://[^\s"'<>]+get-attach[^\s"'<>]*|/api/[^\s"'<>]*get-attach[^\s"'<>]*)""", html):
            u = m.group(1).replace("&amp;", "&")
            u = u if u.startswith("http") else urljoin(GOC_WEB, u)
            if u not in url_san:
                url_san.append(u)
        log(f"  đính kèm: {len(url_san)} URL get-attach có sẵn trong trang" + (f", ví dụ {url_san[0][:90]}" if url_san else ""))
        ds_json = []
        for j in DS_DINH_KEM_JSON:
            _nhat_attach(j, ds_json)
        if ds_json:
            log(f"  đính kèm: JSON của cổng liệt kê {len(ds_json)} tệp: " + ", ".join(f"{d['attachId']}={d['ten'][:30]}" for d in ds_json[:6]))
        goc_attach, aid_goc = "", None
        for u in url_san:
            mm = re.match(r"(.*get-attach-by-id)\?.*?attachId=(\d+)", u)
            if mm:
                goc_attach, aid_goc = mm.group(1), int(mm.group(2))
                break
        da_thu, ten_thay = set(), {}
        try:
            mau_hang = hang[0].evaluate("e => e.outerHTML.slice(0, 400)")
            log(f"  đính kèm: HTML hàng đầu: {mau_hang!r}")
        except Exception:
            pass
        for i, tr in enumerate(hang[:DINH_KEM_TOI_DA], 1):
            try:
                chu = tr.inner_text().strip()
            except Exception:
                chu = f"tep-{i}"
            m = re.search(r"([^\n\t|]+\.(?:pdf|docx?|xlsx?|pptx?|zip|rar|jpe?g|png|txt))", chu, re.I)
            ten = (m.group(1).strip() if m else f"tep-{i}")
            ten = re.sub(r"^\d{1,2}\.\s+", "", ten)      # "2. Dự thảo Thông tư.docx" -> bỏ số thứ tự (giữ "15.9.2026-...")
            loai = ""
            m2 = re.search(r"(Tệp[^\n\t|]*|Văn bản[^\n\t|]*)$", chu)
            if m2:
                loai = m2.group(1).strip()
            b = None
            # (1) link có href
            try:
                a = tr.locator("a[href]").first if tr.locator("a[href]").count() else None
                href = (a.get_attribute("href") or "") if a else (tr.get_attribute("href") or "")
            except Exception:
                href = ""
            if href and not href.startswith(("javascript", "#")):
                b = tai_qua_chrome(page, urljoin(GOC_WEB, href))
            # (1b') theo KHUÔN URL mà Chrome đã dùng để tải tệp đầu (đường dẫn có tên tệp + query attachId):
            # thay tên tệp và attachId bằng của tệp đang cần.
            if not b and URL_ATTACH_DA_THAY:
                from urllib.parse import quote
                khuon = URL_ATTACH_DA_THAY[0]
                ung_vien = []
                for d in ds_json:
                    if _ten_tep_sach(d["ten"]).lower() == _ten_tep_sach(ten).lower() or d["ten"].strip().lower() == ten.strip().lower():
                        u2 = re.sub(r"(get-attach-by-id)/[^?]*", lambda m: m.group(1) + "/" + quote(d["ten"]), khuon)
                        u2 = re.sub(r"attachId=\d+", f"attachId={d['attachId']}", u2)
                        ung_vien.append(u2)
                        ung_vien.append(re.sub(r"(get-attach-by-id)/[^?]*", r"\1", u2))
                if not ung_vien:
                    # không có JSON: chỉ thay tên tệp trong đường dẫn, giữ query (thử xem cổng tra theo tên)
                    ung_vien.append(re.sub(r"(get-attach-by-id)/[^?]*", lambda m: m.group(1) + "/" + quote(ten), khuon))
                for u2 in ung_vien:
                    b, ten_r = tai_bang_req(ctx, u2)
                    if b and (_la_pdf(b) or not ten.lower().endswith(".pdf")):
                        log(f"    {ten}: tải theo khuôn URL của Chrome ({len(b)} bytes)")
                        break
                    b = None
            # (1b) attachId trong JSON, URL trần không token (cổng hiện trả 400 - giữ để phòng cổng đổi)
            if not b:
                for d in ds_json:
                    if _ten_tep_sach(d["ten"]).lower() == _ten_tep_sach(ten).lower() or d["ten"].strip().lower() == ten.strip().lower():
                        b, _ = tai_bang_req(ctx, f"{goc_attach}?attachId={d['attachId']}")
                        if b:
                            log(f"    {ten}: tải theo attachId {d['attachId']} từ JSON ({len(b)} bytes)")
                            break
            # (1c) URL get-attach có sẵn trong trang, theo thứ tự hàng
            if not b and len(url_san) >= len(hang):
                b, _ = tai_bang_req(ctx, url_san[i - 1])
                if b:
                    log(f"    {ten}: tải thẳng URL có sẵn ({len(b)} bytes)")
            # (1d) quét lân cận attachId của tệp đã biết: tên tệp trong content-disposition khớp thì lấy.
            # Data360X cấp attachId tăng dần khi văn thư đính tệp nên các tệp cùng hồ sơ nằm sát nhau.
            if not b and goc_attach and aid_goc and REQ is not None:
                for lech in list(range(1, 25)) + list(range(-1, -25, -1)):
                    aid = aid_goc + lech
                    if aid in da_thu:
                        continue
                    da_thu.add(aid)
                    try:
                        r = REQ.get(f"{goc_attach}?attachId={aid}", timeout=60000, headers=HDR_BACKEND or None)
                        if not r.ok:
                            if len(da_thu) <= 2:
                                log(f"    quét lân cận attachId={aid}: HTTP {r.status}")
                            continue
                        ten_r = _ten_tu_phan_hoi(r, "", "")
                        if ten_r:
                            ten_thay[aid] = (ten_r, r.body())
                        if ten_r and (_ten_tep_sach(ten_r).lower() == _ten_tep_sach(ten).lower() or ten_r.strip().lower() == ten.strip().lower()):
                            b = r.body()
                            log(f"    {ten}: tìm thấy ở attachId {aid} ({len(b)} bytes)")
                            break
                    except Exception as e:
                        if len(da_thu) <= 2:
                            log(f"    quét lân cận attachId={aid} lỗi: {str(e)[:80]}")
                        continue
                if not b:
                    for aid, (ten_r, bb) in ten_thay.items():
                        if _ten_tep_sach(ten_r).lower() == _ten_tep_sach(ten).lower():
                            b = bb
                            break
            if not b:
                log(f"    {ten}: KHÔNG tải được (hàng: {chu[:80]!r})")
                ket.append({"ten": ten, "loai": loai, "bytes": None})
                continue
            if len(b) > DINH_KEM_TOI_DA_MB * 1024 * 1024:
                log(f"    {ten}: {len(b) // 1024 // 1024} MB, quá lớn - bỏ qua")
                ket.append({"ten": ten, "loai": loai, "bytes": None})
                continue
            ket.append({"ten": ten, "loai": loai, "bytes": b})
    except Exception as e:
        log("  đính kèm lỗi:", repr(e))
    return ket


# ---------------------------------------------------------------- TÀI LIỆU SAU MÃ QR (Bạn chốt 17/9/2026)
# Nhiều công văn của Bộ chỉ in mã QR: "Đề nghị quét QR để tải tài liệu" - dự thảo nằm ở đường dẫn trong QR
# (Google Drive, cổng của Bộ...). Bot dựng ảnh trang PDF, đọc QR bằng OpenCV, tải tài liệu ở đường dẫn đó.
QR_TRANG_TOI_DA = 6
QR_TEP_TOI_DA = 12


def quet_qr_pdf(pdf_bytes):
    """Trả danh sách URL đọc được từ mã QR trong PDF (mọi trang, tối đa QR_TRANG_TOI_DA trang)."""
    try:
        import pymupdf
    except ImportError:
        return []
    try:
        import cv2
        import numpy as np
    except ImportError:
        log("  [QR] chưa có OpenCV, đang cài opencv-python-headless (một lần)...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opencv-python-headless", "numpy"], timeout=600)
            import cv2
            import numpy as np
        except Exception as e:
            log("  [QR] không cài được OpenCV:", repr(e))
            return []
    urls = []
    try:
        bo_doc = cv2.QRCodeDetector()
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            for i, trang in enumerate(doc):
                if i >= QR_TRANG_TOI_DA:
                    break
                for dpi in (200, 300):
                    pix = trang.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
                    anh = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
                    try:
                        ok, ds, _, _ = bo_doc.detectAndDecodeMulti(anh)
                        chuoi = [c for c in ds if c] if ok else []
                    except Exception:
                        chuoi = []
                    if not chuoi:
                        c, _, _ = bo_doc.detectAndDecode(anh)
                        chuoi = [c] if c else []
                    if chuoi:
                        for c in chuoi:
                            if c.startswith(("http://", "https://")) and c not in urls:
                                urls.append(c)
                                log(f"  [QR] trang {i + 1}: {c[:100]}")
                        break
    except Exception as e:
        log("  [QR] lỗi đọc:", repr(e))
    return urls


def _ten_tu_phan_hoi(r, url, mac_dinh):
    cd = r.headers.get("content-disposition", "") if hasattr(r, "headers") else ""
    m = re.search(r"filename\*=UTF-8\'\'([^;]+)", cd) or re.search(r'filename="?([^";]+)"?', cd)
    if m:
        from urllib.parse import unquote
        return unquote(m.group(1)).strip()
    duoi = url.split("?")[0].rsplit("/", 1)[-1]
    return duoi if "." in duoi and len(duoi) < 120 else mac_dinh


def tai_tu_url(ctx, url, mac_dinh="tai-lieu"):
    """Tải tài liệu ở một URL bằng phiên Chrome (ctx.request: có cookie, không vướng CORS).
    Nhận diện Google Drive (tệp, thư mục), trang web liệt kê tệp. Trả [{"ten","loai","bytes"}]."""
    ra = []
    try:
        u = url.strip()
        m = re.search(r"drive\.google\.com/file/d/([\w-]+)", u)
        if m:
            u = f"https://drive.google.com/uc?export=download&id={m.group(1)}&confirm=t"
        m2 = re.search(r"drive\.google\.com/drive/(?:u/\d+/)?folders/([\w-]+)", u)
        if m2:
            # Trang thư mục Drive dựng bằng JS, HTML ban đầu không có tên tệp. Trang "embeddedfolderview" là
            # HTML tĩnh: có link /file/d/<id>/view và tên tệp (vụ 9425/UBND-NC 17/9/2026: bản cũ thấy 0 tệp).
            r = (REQ or ctx.request).get(f"https://drive.google.com/embeddedfolderview?id={m2.group(1)}#list", timeout=120000)
            html = r.text() if r.ok else ""
            import html as _html
            ids = re.findall(r"https://drive\.google\.com/file/d/([\w-]+)/view", html)
            ten_tep = [_html.unescape(t) for t in re.findall(r'class="flip-entry-title">([^<]+)<', html)]
            thu_muc_con = [f for f in re.findall(r"https://drive\.google\.com/drive/folders/([\w-]+)", html) if f != m2.group(1)]
            ids_u = []
            for x in ids:
                if x not in ids_u:
                    ids_u.append(x)
            log(f"  [QR] thư mục Google Drive: {len(ids_u)} tệp, {len(set(thu_muc_con))} thư mục con")
            for i, fid in enumerate(ids_u[:QR_TEP_TOI_DA], 1):
                ten = ten_tep[i - 1] if i - 1 < len(ten_tep) else f"{mac_dinh}-{i}"
                kq = tai_tu_url(ctx, f"https://drive.google.com/uc?export=download&id={fid}&confirm=t", ten)
                for d in kq:
                    if d["ten"].startswith(mac_dinh) or "." not in d["ten"]:
                        d["ten"] = ten
                ra += kq
            for j, fid in enumerate(list(dict.fromkeys(thu_muc_con))[:3], 1):      # thư mục con: một cấp
                ra += tai_tu_url(ctx, f"https://drive.google.com/drive/folders/{fid}", f"{mac_dinh}-tm{j}")
            if not ids_u and not thu_muc_con:
                ra.append({"ten": f"{mac_dinh}-thu-muc-drive.txt", "loai": "QR", "bytes": (u + "\n").encode()})
            return ra
        r = (REQ or ctx.request).get(u, timeout=180000)
        if not r.ok:
            log(f"  [QR] {u[:80]}: HTTP {r.status}")
            return ra
        b = r.body()
        ct = (r.headers.get("content-type") or "").lower()
        ten = _ten_tu_phan_hoi(r, u, mac_dinh)
        if "text/html" in ct and not _la_pdf(b):
            html = b.decode("utf-8", errors="replace")
            # Google Drive hỏi xác nhận tải tệp lớn
            m3 = re.search(r'action="([^"]+)"', html)
            if m3 and "drive" in u and "confirm" in html:
                tham = dict(re.findall(r'name="(\w+)"\s+value="([^"]*)"', html))
                r2 = ctx.request.get(m3.group(1).replace("&amp;", "&"), params=tham or None, timeout=180000)
                if r2.ok and "text/html" not in (r2.headers.get("content-type") or ""):
                    ra.append({"ten": _ten_tu_phan_hoi(r2, u, mac_dinh), "loai": "QR", "bytes": r2.body()})
                    return ra
            # trang web liệt kê tài liệu: lấy các link tệp
            links = []
            for mm in re.finditer(r'href="([^"]+\.(?:pdf|docx?|xlsx?|zip|rar))"', html, re.I):
                l = urljoin(u, mm.group(1).replace("&amp;", "&"))
                if l not in links:
                    links.append(l)
            log(f"  [QR] trang web: {len(links)} tệp liên kết")
            ra.append({"ten": f"{mac_dinh}-trang.html", "loai": "QR", "bytes": b})
            for i, l in enumerate(links[:QR_TEP_TOI_DA], 1):
                r3 = ctx.request.get(l, timeout=180000)
                if r3.ok:
                    ra.append({"ten": _ten_tu_phan_hoi(r3, l, f"{mac_dinh}-{i}"), "loai": "QR", "bytes": r3.body()})
            return ra
        if "." not in ten:
            ten += ".pdf" if _la_pdf(b) else (".docx" if b[:2] == b"PK" else ".bin")
        ra.append({"ten": ten, "loai": "QR", "bytes": b})
    except Exception as e:
        log("  [QR] lỗi tải:", repr(e))
    return ra


def lay_theo_qr(ctx, vb, pdf_chinh, dinh_kem):
    """Quét QR trong PDF chính và mọi PDF đính kèm; tải tài liệu ở URL đọc được, gắn thêm vào dinh_kem."""
    nguon = [("văn bản chính", pdf_chinh)] + [(d["ten"], d["bytes"]) for d in dinh_kem if d.get("bytes") and _la_pdf(d["bytes"])]
    da = set()
    them = []
    for ten_goc, b in nguon:
        if not b:
            continue
        for url in quet_qr_pdf(b):
            if url in da:
                continue
            da.add(url)
            kq = tai_tu_url(ctx, url, "qr")
            if not kq:
                kq = [{"ten": "qr-khong-tai-duoc.txt", "loai": "QR", "bytes": (url + "\n").encode()}]
            for d in kq:
                d["qr_url"] = url
                d["tu_tep"] = ten_goc
            them += kq
            log(f"  [QR] từ {ten_goc}: {len(kq)} tệp ({url[:60]})")
    return them


def dong_goi_ho_so(vb, ten_goc, pdf_chinh, dinh_kem, dau_md):
    """Từ PDF chính + đính kèm -> danh sách (tên tệp, bytes) để ghi ra đĩa hoặc lên GitHub.
    Văn bản chính: .md nếu có chữ, .pdf nếu scan. Mỗi đính kèm: tệp gốc + .md chữ (nếu trích được).
    Trả (danh_sach, tên tệp chính)."""
    ra = []
    ten_chinh = ""
    muc_dk = []
    for i, dk in enumerate(dinh_kem, 1):
        nhan = "qr" if dk.get("loai") == "QR" else "dk"
        if not dk.get("bytes"):
            muc_dk.append(f"- {i}. {dk['ten']} ({dk.get('loai') or 'không rõ'}) - *không tải được*")
            continue
        ten_dk = f"{ten_goc}__{nhan}{i}-{_ten_tep_sach(dk['ten'])}"
        ra.append((ten_dk, dk["bytes"]))
        chu = trich_chu_tep(dk["ten"], dk["bytes"])
        dong = f"- {i}. {dk['ten']} ({dk.get('loai') or 'tệp'}) -> `{ten_dk}`"
        if dk.get("qr_url"):
            dong += f" — tải từ mã QR trong *{dk.get('tu_tep')}*: {dk['qr_url']}"
        if len(chu) >= 200:
            ten_md = ten_dk.rsplit(".", 1)[0] + ".md"
            ra.append((ten_md, f"# Đính kèm {i} của {vb['so_ky_hieu']}: {dk['ten']}\n\n{chu}".encode()))
            dong += f", chữ: `{ten_md}`"
        muc_dk.append(dong)
    if pdf_chinh:
        chu = trich_chu_pdf(pdf_chinh)
        if len(chu) >= 800:
            ten_chinh = ten_goc + ".md"
            than = list(dau_md)
            if muc_dk:
                than += ["", f"## Tệp đính kèm trên {TEN_HE_THONG}", ""] + muc_dk
            than += ["", "---", "", chu]
            ra.append((ten_chinh, "\n".join(than).encode()))
        else:
            ten_chinh = ten_goc + ".pdf"
            ra.append((ten_chinh, pdf_chinh))
            if muc_dk:
                ra.append((ten_goc + ".md", ("\n".join(dau_md) + "\n\n*(Văn bản chính là bản scan: xem "
                           + ten_chinh + f")*\n\n## Tệp đính kèm trên {TEN_HE_THONG}\n\n" + "\n".join(muc_dk)).encode()))
    elif muc_dk:
        ten_chinh = ten_goc + ".md"
        ra.append((ten_chinh, ("\n".join(dau_md) + f"\n\n*(Không tải được PDF chính)*\n\n## Tệp đính kèm trên {TEN_HE_THONG}\n\n"
                               + "\n".join(muc_dk)).encode()))
    return ra, ten_chinh


def _chuan_so(x) -> str:
    """Chuẩn hóa số ký hiệu để so khớp: bỏ mọi ký tự không phải chữ/số, hạ chữ hoa.

    '7273/STC-G&CS' -> '7273STCGCS'. Cổng Data360X có lúc ghi ký hiệu thiếu/khác dấu ngăn
    ('&', '-', khoảng trắng), vụ 18/9/2026: tìm thấy đúng dòng 7273 nhưng so khớp trượt nên
    báo "không thấy".
    """
    return re.sub(r"[^0-9A-Za-zÀ-ỹ]+", "", str(x or "")).upper()


def _khop_so(a, b):
    """So số ký hiệu bỏ khoảng trắng và chữ hoa thường: '340/TTr-UBND' == '340 /TTR - UBND'."""
    return _chuan_so(a) == _chuan_so(b)


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
    can = {_chuan_so(v["so_ky_hieu"]): v for v in can_tim}
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
                # Tìm từng số trong ô tìm kiếm của cổng (17/9/2026); không có ô tìm thì lật trang như cũ
                rows = []
                for k in list(thieu):
                    kq = tim_tren_cong(page, nguon, phan_so(can[k]["so_ky_hieu"]))
                    if kq is None:
                        if can_dang_nhap(page):
                            log("Bị đưa về trang đăng nhập giữa chừng.")
                            return 3
                        kq = quet_danh_sach(page, nguon, tu_ngay)
                        if kq is None:
                            return 3
                        rows = kq
                        break
                    rows.extend(kq)
                for vb in rows:
                    khoa = _chuan_so(vb["so_ky_hieu"])
                    if khoa not in can or khoa not in thieu:
                        continue
                    log(f"  thấy {vb['so_ky_hieu']} ({nguon}) - {vb['trich_yeu'][:60]}")
                    pdf = tai_pdf(ctx, page, vb)
                    ten = lam_sach(vb["so_ky_hieu"])
                    if pdf:
                        (luu_vao / f"{ten}.pdf").write_bytes(pdf)
                    else:
                        log("    không tải được PDF, chỉ ghi thông tin")
                    dk_all = tai_dinh_kem(ctx, page, vb)                          # hồ sơ nhiều tệp (17/9/2026)
                    dk_all += lay_theo_qr(ctx, vb, pdf, dk_all)
                    for i, dk in enumerate(dk_all, 1):
                        if dk.get("bytes"):
                            nhan = "qr" if dk.get("loai") == "QR" else "dk"
                            (luu_vao / f"{ten}__{nhan}{i}-{_ten_tep_sach(dk['ten'])}").write_bytes(dk["bytes"])
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


def tim_tren_cong(page, nguon, chuoi, toi_da_trang=10):
    """Gõ chuỗi vào ô "Nhập số/ký hiệu hoặc trích yếu văn bản" của Data360X rồi đọc bảng kết quả (Bạn chốt
    17/9/2026: "trang cơ sở dữ liệu có thanh tìm kiếm mà, nên tìm bằng từ khóa hơn là mở từng trang").
    Trả danh sách dòng; None nếu bị đưa về trang đăng nhập hoặc không thấy ô tìm (để nơi gọi lật trang như cũ)."""
    page.goto(TRANG[nguon], wait_until="domcontentloaded", timeout=90000)
    if can_dang_nhap(page):
        return None
    cho_bang(page)
    o = page.get_by_placeholder(re.compile(r"ký hiệu|trích yếu|ky hieu|trich yeu", re.I))
    if not o.count():
        o = page.locator("input[type='text']").first
        if not o.count():
            log(f"  ({nguon}) không thấy ô tìm kiếm - lật trang như cũ")
            return None
    o = o.first
    o.fill("")
    o.fill(chuoi)
    o.press("Enter")
    page.wait_for_timeout(2500)
    try:
        cho_bang(page)
    except Exception:
        return []
    rows, trang = [], 1
    while True:
        try:
            rows.extend(doc_bang(page, nguon))
        except RuntimeError as e:      # bảng không có dòng nào -> thiếu cột
            log(f"  ({nguon}) '{chuoi}': {e}")
            break
        nut = page.locator("button.p-paginator-next")
        if trang >= toi_da_trang or not nut.count() or nut.first.is_disabled():
            break
        nut.first.click()
        page.wait_for_timeout(2000)
        cho_bang(page)
        trang += 1
    log(f"  ({nguon}) tìm '{chuoi}': {len(rows)} dòng")
    return rows


def sua_vo_ma(chu):
    """'lá»±a chá»n' -> 'lựa chọn': chuỗi UTF-8 bị đọc nhầm thành Windows-1252 (vụ 17/9/2026, Windows PowerShell
    đọc script không BOM như ANSI rồi ghi lại thành UTF-8 hai lần). Chỉ sửa khi có dấu hiệu vỡ."""
    if not chu or not re.search(r"[ÃÂá»Æ]", chu):
        return chu
    # Windows đọc từng byte theo cp1252; byte cp1252 không định nghĩa (0x81, 0x8D...) thành U+0081... -> mã lại
    # từng ký tự: cp1252 trước, không được thì latin-1.
    goc = bytearray()
    try:
        for c in chu:
            try:
                goc += c.encode("cp1252")
            except UnicodeEncodeError:
                goc += c.encode("latin-1")
        thu = goc.decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return chu
    if re.search(r"[ÃÂ]", thu):
        return chu
    log(f"  đã sửa chuỗi vỡ mã: {thu[:60]!r}")
    return thu


# Bạn chốt 17/9/2026: "từ khóa nên ngắn gọn: chỉ số văn bản, không kèm mã phía sau; tra về một dự án thì chỉ
# tên riêng (Xuân Ái) vì nhiều cách viết (CCN Xuân Ái, Cụm CN Xuân Ái...) sẽ không tra được".
_CHU_CHUNG = re.compile(
    r"^(?:(?:cum|khu|dia diem)\s+(?:cong nghiep|cn)|ccn|kcn|cong ty|cty|doanh nghiep|dn|du an|mo|nha may|"
    r"co so|hop tac xa|htx|xa|phuong|thi tran|huyen|tinh|thanh pho|tp|ubnd|uy ban nhan dan|so|phong|ban)\s+", re.I)


def rut_gon_tu_khoa(tu_khoa):
    """'Cụm công nghiệp Xuân Ái' -> 'Xuân Ái'; 'Công ty CP PH Group' -> 'PH Group'. Bỏ dần các chữ chung ở đầu."""
    goc = tu_khoa.strip()
    khong_dau = bo_dau(goc)
    while True:
        m = _CHU_CHUNG.match(khong_dau)
        if not m:
            break
        # cắt cùng số CHỮ ở bản có dấu (bo_dau giữ nguyên số chữ)
        so_chu = len(m.group(0).split())
        goc = " ".join(goc.split()[so_chu:])
        khong_dau = bo_dau(goc)
        if not goc:
            return tu_khoa.strip()
    # "CP", "TNHH", "MTV" đứng đầu sau khi bỏ "công ty" cũng là chữ chung
    goc = re.sub(r"^(?:cp|tnhh|mtv|co phan|trach nhiem huu han|mot thanh vien)\s+", "", goc, flags=re.I) \
        if re.match(r"^(?:cp|tnhh|mtv|cổ phần|trách nhiệm hữu hạn|một thành viên)\s+", goc, re.I) else goc
    return goc.strip() or tu_khoa.strip()


def phan_so(so_ky_hieu):
    """'3226/QĐ-UBND' -> '3226' để gõ vào ô tìm (ô tìm khớp cả số ký hiệu lẫn trích yếu; lọc lại bằng số đầy đủ)."""
    m = re.match(r"\s*([0-9]+)", so_ky_hieu or "")
    return m.group(1) if m else so_ky_hieu


def _tach_yeu_cau(yeu_cau):
    """"5511/SCT-CN; 3226/QĐ-UBND; tiêu chí lựa chọn chủ đầu tư" -> ([số ký hiệu chuẩn hóa], [từ khóa không dấu]).
    Mục có dấu "/" là số ký hiệu (khớp đúng), còn lại là từ khóa (khớp trong trích yếu, không phân biệt dấu)."""
    so, tu_khoa = {}, []
    for muc in re.split(r"[;\n]+", yeu_cau or ""):
        muc = muc.strip().strip('"\'')
        if not muc:
            continue
        if "/" in muc:
            so[_chuan_so(muc)] = muc
        else:
            gon = rut_gon_tu_khoa(muc)
            if gon != muc:
                log(f"  từ khóa rút gọn: '{muc}' -> '{gon}'")
            tu_khoa.append(bo_dau(gon))
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
    yeu_cau = sua_vo_ma(yeu_cau)
    so, tu_khoa = _tach_yeu_cau(yeu_cau)
    tu_khoa_goc = [rut_gon_tu_khoa(m.strip().strip('"\'')) for m in re.split(r"[;\n]+", yeu_cau or "")
                   if m.strip().strip('"\'') and "/" not in m]
    if not so and not tu_khoa:
        log("Yêu cầu rỗng: cần ít nhất một số ký hiệu hoặc từ khóa.")
        return 2
    tu_ngay = date.today() - timedelta(days=so_ngay)
    log(f"Lấy theo yêu cầu, quét từ {tu_ngay.isoformat()}: số ký hiệu {list(so.values())}, từ khóa {tu_khoa}")

    thay, thieu_so, dem_tk, bo_qua_tk, loi_chung, ten_da_dung = [], set(so.keys()), {}, {}, "", set()
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
            chuoi_tim = sorted({phan_so(v) for v in so.values()}) + tu_khoa_goc
            da_co = set()      # khử trùng trên CẢ hai bảng (vụ 17/9: 5612/TTr-SCT bị ghi hai lần)
            for nguon in ("den", "di"):
                # Gõ từng mục vào ô tìm kiếm của cổng; ô tìm không có thì lật trang trong khoảng ngày như cũ
                rows = []
                for chuoi in chuoi_tim:
                    kq = tim_tren_cong(page, nguon, chuoi)
                    if kq is None:
                        if can_dang_nhap(page):
                            log("Bị đưa về trang đăng nhập giữa chừng.")
                            return 3
                        kq = quet_danh_sach(page, nguon, tu_ngay)
                        if kq is None:
                            return 3
                        rows.extend(kq)
                        break
                    rows.extend(kq)
                if so and rows and not any(_chuan_so(v["so_ky_hieu"]) in so for v in rows):
                    log(f"  ({nguon}) không dòng nào khớp số ký hiệu; cổng ghi: "
                        + ", ".join(dict.fromkeys(v["so_ky_hieu"] for v in rows[:8])))
                for vb in rows:
                    dau = vb.get("id_data360x") or (vb["so_ky_hieu"] + vb["ngay_ban_hanh"])
                    if dau in da_co:
                        continue
                    da_co.add(dau)
                    khoa = _chuan_so(vb["so_ky_hieu"])
                    ty = " " + bo_dau(vb["trich_yeu"]) + " "
                    ly_do = ("số " + so[khoa]) if khoa in so else next((f"từ khóa \"{t}\"" for t in tu_khoa if t in ty), None)
                    if not ly_do:
                        continue
                    if ly_do.startswith("từ khóa"):
                        dem_tk[ly_do] = dem_tk.get(ly_do, 0) + 1
                        if dem_tk[ly_do] > LAY_TOI_DA_MOI_TU_KHOA:
                            bo_qua_tk[ly_do] = bo_qua_tk.get(ly_do, 0) + 1
                            continue
                    log(f"  thấy {vb['so_ky_hieu']} ({nguon}, {ly_do}) - {vb['trich_yeu'][:60]}")
                    # Chrome bị đóng giữa chừng (vụ 17/9/2026: cả lượt đổ, mọi văn bản sau đều "Target closed")
                    # -> mở lại rồi làm tiếp, không bỏ cả lượt.
                    try:
                        page.evaluate("1")
                    except Exception:
                        log("  Chrome đã bị đóng - mở lại và làm tiếp")
                        try:
                            ctx.close()
                        except Exception:
                            pass
                        ctx = mo_trinh_duyet_online(p, phien) if online else mo_trinh_duyet(p, headless=False)
                        page = ctx.pages[0] if ctx.pages else ctx.new_page()
                        page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
                        page.wait_for_timeout(2000)
                    ten = lam_sach_vn(vb["so_ky_hieu"]) or f"vb-{vb.get('id_data360x') or 'khong-so'}"
                    if ten in ten_da_dung:                                  # hai văn bản trùng số trong CÙNG lượt
                        ten += "-" + (vb.get("id_data360x") or nguon)      # (gọi lại cùng thư mục thì ghi đè, không nhân bản)
                    ten_da_dung.add(ten)
                    try:
                        pdf = tai_pdf(ctx, page, vb)
                    except Exception as e:
                        log("    lỗi tải:", repr(e))
                        pdf = None
                    dinh_kem = tai_dinh_kem(ctx, page, vb)        # hồ sơ nhiều tệp (17/9/2026)
                    luong = doc_luong_xu_ly(page)                  # ai chủ trì, ai phối hợp (17/9/2026)
                    vai, nguoi_xl, han_xl = suy_vai_tro(luong)
                    tra_loi = doc_van_ban_tra_loi()                # đã có văn bản đi trả lời chưa (20/9/2026)
                    dinh_kem += lay_theo_qr(ctx, vb, pdf, dinh_kem)   # tài liệu sau mã QR (17/9/2026)
                    dong_tl = (["- **Đã có văn bản trả lời**: "
                                + "; ".join(f"{t['so_ky_hieu']} ngày {t['ngay']}" for t in tra_loi)]
                               if tra_loi else
                               ["- **CHƯA có văn bản đi trả lời** - việc còn phải xử lý."])
                    dau = [f"# {vb['so_ky_hieu']} - {vb['trich_yeu']}", ""] + dong_tl + [
                           f"- Ngày ban hành: {vb['ngay_ban_hanh']}",
                           f"- Nguồn: văn bản {'đến' if nguon == 'den' else 'đi'}"
                           f" | Đơn vị: {vb.get('don_vi', '')} | Người ký: {vb.get('nguoi_ky', '')}",
                           f"- Lý do lấy: {ly_do}",
                           f"- Bản gốc trên {TEN_HE_THONG}: {vb.get('url_chi_tiet', '')}"] + dong_luong_md(luong, vai, nguoi_xl, han_xl) + ["",
                           "> Chữ dưới đây lấy từ lớp text của PDF. Số và ngày ở trường ký số có thể "
                           "không nằm trong lớp text - lấy theo hai dòng trên, hoặc mở bản gốc."]
                    goi, tep = dong_goi_ho_so(vb, ten, pdf, dinh_kem, dau)
                    for ten_t, du_lieu in goi:
                        (luu_vao / ten_t).write_bytes(du_lieu)
                    if not pdf:
                        log("    không tải được PDF chính" + (f", có {sum(1 for d in dinh_kem if d.get('bytes'))} đính kèm" if dinh_kem else ""))
                    ghi_vb = {**vb, "ly_do": ly_do, "tep": tep, "luong_xu_ly": luong,
                              "vai_tro_phong": vai, "nguoi_xu_ly_chinh": nguoi_xl, "han_xu_ly": han_xl,
                              "van_ban_tra_loi": tra_loi, "da_tra_loi": bool(tra_loi),
                              "dinh_kem": [{"ten": d["ten"], "loai": d.get("loai", ""), "tai_duoc": bool(d.get("bytes"))} for d in dinh_kem]}
                    (luu_vao / f"{ten}.json").write_text(json.dumps(ghi_vb, ensure_ascii=False, indent=2), encoding="utf-8")
                    thay.append(ghi_vb)
                    thieu_so.discard(khoa)
        except Exception as e:
            loi_chung = repr(e)
            log("LỖI giữa chừng, vẫn ghi phần đã lấy được:", loi_chung)
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    kq = {"lay_luc": datetime.now().isoformat(timespec="minutes"), "yeu_cau": yeu_cau,
          "tu_ngay": tu_ngay.isoformat(), "thay": thay, "khong_thay_so": [so[k] for k in thieu_so],
          "bo_qua_vi_tu_khoa_rong": bo_qua_tk, "loi": loi_chung}
    (luu_vao / "_ket-qua.json").write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8")
    dong = [f"# Kết quả lấy văn bản theo yêu cầu - {datetime.now().strftime('%d/%m/%Y %H:%M')}", "",
            f"Yêu cầu: `{yeu_cau}`  |  quét từ {tu_ngay.strftime('%d/%m/%Y')}  |  thấy {len(thay)}", ""]
    for v in thay:
        dk = v.get("dinh_kem") or []
        dong.append(f"- [{'đến' if v['nguon'] == 'den' else 'đi'}] **{v['so_ky_hieu']}** ngày {v['ngay_ban_hanh']} "
                    f"- {v['trich_yeu']} ({v['ly_do']})" + (f" -> `{v['tep']}`" if v['tep'] else " *(không tải được PDF)*")
                    + (f" + {sum(1 for d in dk if d['tai_duoc'])}/{len(dk)} tệp đính kèm" if dk else "")
                    + (f" — Phòng {v['vai_tro_phong']}" + (f", xử lý chính: {v['nguoi_xu_ly_chinh']}" if v.get('nguoi_xu_ly_chinh') else "")
                       + (f", hạn {v['han_xu_ly']}" if v.get('han_xu_ly') else "") if v.get('vai_tro_phong') and v['vai_tro_phong'] != 'không có' else ""))
    if thieu_so:
        dong += ["", f"## Không thấy trên {TEN_HE_THONG}", ""] + [f"- {so[k]}" for k in thieu_so] + \
                ["", f"Có thể số ký hiệu ghi khác trên {TEN_HE_THONG} (thử chỉ phần số), hoặc văn bản chưa được cập nhật lên cổng."]
    if bo_qua_tk:
        dong += ["", "## Từ khóa quá rộng", ""] + \
                [f"- {k}: đã lấy {LAY_TOI_DA_MOI_TU_KHOA} văn bản mới nhất, bỏ qua {v} văn bản khác. "
                 f"Hãy tra `danh-muc-<năm>.json` hoặc dùng từ khóa hẹp hơn / số ký hiệu cụ thể." for k, v in bo_qua_tk.items()]
    if loi_chung:
        dong += ["", "## Lượt lấy bị lỗi giữa chừng", "", f"- {loi_chung}", "- Phần trên là những gì đã lấy được trước khi lỗi; gọi lại để lấy phần còn thiếu."]
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
    viec_tom = ""

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
                    telegram(f"Bot {TEN_HE_THONG}: không đăng nhập được sau 90 phút, bỏ lượt chạy hôm nay.")
                    return 3
            if HE_THONG == "egov" and not soi and token and not _egov_da_khao_sat_len_kho():
                # Lần đầu chạy trên cổng mới: ghi lại cấu trúc cổng lên kho riêng tư để Claude hoàn thiện bộ đọc
                log("Lần đầu chạy trên egov1: khảo sát cổng trước khi quét...")
                try:
                    _egov_khao_sat_va_day(ctx, page, token)
                except Exception as e:
                    log("  khảo sát lỗi (vẫn quét tiếp):", repr(e))
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

            # egov1: việc Chưa/Chờ/Đang xử lý trong Văn bản đến (thay vOffice, Bạn chuyển 29/10/2026).
            # Việc có thể nhận từ trước khoảng quét hằng ngày (3 ngày) nên đọc lại tối thiểu 30 ngày.
            if HE_THONG == "egov" and not soi and token:
                log("Việc chờ xử lý trên egov1...")
                try:
                    den = [v for v in van_ban if v["nguon"] == "den"]
                    den = _egov_quet_danh_sach(page, "den", date.today() - timedelta(days=max(30, (date.today() - tu_ngay).days)),
                                               tra_cuu=False) or den
                    tong_viec, moi_viec = _egov_lay_viec(
                        ctx, page, den, BOT_HOME / "ket-qua" / "viec" / date.today().isoformat(), token)
                    viec_tom = f"; {tong_viec} việc chờ xử lý (tải mới {moi_viec}) -> {THU_MUC_VIEC}/"
                except Exception as e:
                    log("  [việc] lỗi:", repr(e))
                    loi.append(f"việc chờ xử lý: {e!r}")
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

    tom_tat = (f"Bot {TEN_HE_THONG} {date.today().isoformat()}: quét {tong_quet} văn bản, "
               f"đẩy {len(da_day)} file"
               + (f", theo dõi thêm {tri_thuc_moi} văn bản cho plugin" if tri_thuc_moi else "")
               + (": " + "; ".join(da_day) if da_day else "")
               + viec_tom
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
    """Mở trang chủ cổng (egov1 hoặc Data360X) bằng phiên đã có rồi đóng (~20 giây), để cổng không cắt phiên.
    Bạn chốt 24/9/2026: chạy MỖI GIỜ trong giờ làm việc (trước đó chỉ thứ Tư -> phiên hết gần như mỗi ngày),
    cửa sổ Chrome thu nhỏ. Chỉ dùng lại phiên có sẵn; phiên hết thì báo để Bạn đăng nhập."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = mo_trinh_duyet(p, headless=False, thu_nho=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(5000)
            if can_dang_nhap(page):
                log("Giữ phiên: phiên đã hết, cần đăng nhập lại.")
                thong_bao_windows(f"Bot {TEN_HE_THONG}", f"Phiên {TEN_HE_THONG} đã hết hạn. Mở dang-nhap-lan-dau.bat để đăng nhập lại.")
                telegram(f"Bot {TEN_HE_THONG}: phiên đăng nhập đã hết hạn (phát hiện lúc giữ phiên). Hãy đăng nhập lại trên máy cơ quan.")
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
        print(f"\nHãy đăng nhập {TEN_HE_THONG} ({GOC_WEB}) trong cửa sổ Chrome vừa mở (nhập mã xác thực như thường).")
        print(f"Khi thấy danh sách văn bản / trang chủ {TEN_HE_THONG} hiện ra, quay lại cửa sổ này và bấm Enter để lưu phiên.")
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


def tat_quick_edit():
    """Tắt QuickEdit của cửa sổ cmd: lỡ bấm chuột vào cửa sổ đen là Windows dừng bot tới khi nhấn Esc
    (vụ 10/10/2026, Bạn bấm vào cửa sổ trong lúc quét lại 12 ngày). Không phải Windows hoặc lỗi thì bỏ qua."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.GetStdHandle(-10)                    # STD_INPUT_HANDLE
        mode = ctypes.c_uint32()
        if k32.GetConsoleMode(h, ctypes.byref(mode)):
            # bỏ ENABLE_QUICK_EDIT_MODE (0x40), bật ENABLE_EXTENDED_FLAGS (0x80) để thay đổi có hiệu lực
            k32.SetConsoleMode(h, (mode.value & ~0x40) | 0x80)
    except Exception:
        pass


# ---------------------------------------------------------------- HỆ THỐNG MỚI egov1.laocai.gov.vn (Bạn chuyển 29/10/2026)
# Từ 29/10/2026 Bạn làm việc trên "trang quản lý tài liệu mới" egov1.laocai.gov.vn (menu Trang chủ, Quản lý nhiệm vụ,
# Văn bản đến, Văn bản đi, Lịch đơn vị, Họp không giấy). Danh sách Văn bản đến (/document/xem-den-index?type=all) là
# bảng có tiêu đề cột: STT, Cấp độ, Trích yếu, Số ký hiệu, Ngày Ban Hành, Ngày Nhận, Trạng thái, Cơ quan ban hành,
# Người Ký, Độ mật, Nguồn văn bản - đọc từ ảnh chụp màn hình Bạn gửi, không đoán.
#
# Máy chủ Claude ở nước ngoài KHÔNG vào được cổng này, nên phần chưa thấy tận mắt (đường dẫn Văn bản đi, trang chi
# tiết, cách cổng phát tệp) bot tự dò: nhận cột theo TIÊU ĐỀ, tìm trang Văn bản đi bằng cách bấm menu như người dùng,
# thử mọi cách tải tệp. Lần chạy đầu tiên bot tự KHẢO SÁT (HTML, ảnh, danh sách API của cổng) rồi đẩy lên kho riêng
# tư vlncn-laocai/theo-doi/egov/soi/ để Claude hoàn thiện bộ đọc; lệnh tay: --khao-sat.
#
# Văn bản có Độ mật khác "Thường" KHÔNG bao giờ được tải hay ghi lên GitHub (chỉ đếm số lượng trong log).
# Data360X vẫn dùng được: config.json "he_thong": "data360x" hoặc biến môi trường BOT_HE_THONG=data360x.
EGOV_GOC = "https://egov1.laocai.gov.vn"
EGOV_DS_DEN = EGOV_GOC + "/document/xem-den-index?type=all"      # "Danh sách văn bản"; type=chuaxem là "Xem để biết"
EGOV_DS_DI = EGOV_GOC + "/document/xem-di-index?type=data360"     # ảnh Bạn gửi 29/10/2026: "Danh sách văn bản đi"
EGOV_NHIEM_VU = EGOV_GOC + "/work/unit/main/1"                    # Quản lý nhiệm vụ (11 ô đếm); /2 = Văn bản đi ở trang chủ
EGOV_TRANG_CHU = EGOV_GOC + "/home/default/1"                     # Tổng quan: bảng nhiệm vụ UBND tỉnh giao / nội bộ
EGOV_MENU = {"den": "Văn bản đến", "di": "Văn bản đi"}
EGOV_CHO_LAG_GIAY = 90          # cổng rất chậm (Bạn báo 29/10/2026): chờ "Đang tải dữ liệu..." tắt tới 90 giây
EGOV_TRANG_DA_DO = BOT_HOME / "egov-trang.json"      # đường dẫn danh sách đã dò được, lần sau vào thẳng
EGOV_DA_KHAO_SAT = BOT_HOME / "egov-khao-sat.json"   # có tệp này thì lần quét sau không khảo sát lại
EGOV_TRANG_TOI_DA = 150         # lưới an toàn: 150 trang (10 dòng/trang khi không đổi được số dòng = 1.500 văn bản)
EGOV_TAB_TRA_CUU = {"den": "Tra cứu văn bản đến", "di": "Tra cứu văn bản đi"}   # tab thấy TẤT CẢ văn bản của Sở (Bạn chỉ 29/10/2026)
EGOV_TAB_CUA_TOI = {"den": "Danh sách văn bản", "di": "Chờ xử lý"}            # tab chỉ văn bản giao cho Bạn
EGOV_SO_DONG = 100              # muốn bảng hiện bao nhiêu dòng mỗi trang (cổng mặc định 10)
EGOV_VIEC_TOI_DA = 30           # mỗi lượt tải toàn văn tối đa bao nhiêu việc chờ xử lý
THU_MUC_VIEC = "theo-doi/viec-cho-xu-ly"

# (khóa, các cụm mở đầu tiêu đề cột - viết không dấu). Thứ tự quan trọng: "ngay nhan" trước "ngay".
EGOV_COT = [
    ("so", ("so ky hieu", "so/ky hieu", "so hieu", "ky hieu", "so van ban", "so di", "so den")),
    ("ngay_nhan", ("ngay nhan", "ngay den")),
    ("ngay", ("ngay ban hanh", "ngay ky", "ngay van ban", "ngay phat hanh")),
    ("trich_yeu", ("trich yeu",)),
    ("don_vi", ("co quan ban hanh", "don vi ban hanh", "noi ban hanh", "noi gui", "don vi soan thao",
                "don vi soan", "phong soan thao", "phong ban soan thao", "don vi")),
    ("nguoi_ky", ("nguoi ky",)),
    ("nguoi_soan", ("nguoi soan",)),
    ("trang_thai", ("trang thai", "tinh trang")),
    ("do_mat", ("do mat",)),
    ("do_khan", ("cap do", "do khan")),
    ("loai", ("loai van ban", "the loai")),
    ("nguon_vb", ("nguon van ban",)),
    ("han", ("han xu ly", "thoi han")),
]

_EGOV_TEP = {"khoa": None, "chinh": None, "khac": []}   # tệp của trang chi tiết đang mở (tai_pdf -> tai_dinh_kem)

# Đọc bảng danh sách bằng một lượt JS (nhanh hơn đọc từng ô). Bảng DataTables có thể tách tiêu đề và thân ra hai
# <table> (scrollX) - khi đó lấy thân ở khối .dataTables_scrollBody cùng wrapper.
_JS_DOC_BANG = r"""() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const thay = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
  for (const t of document.querySelectorAll('table')) {
    if (!thay(t)) continue;
    let heads = null;
    for (const r of (t.tHead ? Array.from(t.tHead.rows) : [])) {
      const hs = Array.from(r.cells).map(c => norm(c.innerText));
      if (hs.some(h => /trích yếu/i.test(h))) { heads = hs; break; }
    }
    if (!heads) continue;
    let body = t.tBodies[0];
    if (!body || !body.rows.length) {
      const wrap = t.closest('.dataTables_wrapper, .dt-container');
      const kia = wrap && wrap.querySelector('.dataTables_scrollBody table tbody, .dt-scroll-body table tbody');
      if (kia) body = kia;
    }
    const rows = [];
    let trong = false;
    for (const tr of (body ? Array.from(body.rows) : [])) {
      const cells = Array.from(tr.cells);
      if (cells.length < 3) {
        if (/không có|không tìm thấy|no data|no matching|empty|trống/i.test(norm(tr.innerText))) trong = true;
        continue;
      }
      rows.push({
        o: cells.map(c => norm(c.innerText)),
        href: cells.map(c => Array.from(c.querySelectorAll('a[href]'))
          .filter(a => { const h = a.getAttribute('href') || ''; return h && h !== '#' && !/^(javascript|mailto):/i.test(h); })
          .map(a => a.href)),
        bam: cells.map(c => { const e = c.querySelector('[onclick]'); return e ? e.getAttribute('onclick') : ''; }),
        tr: Object.assign({onclick: tr.getAttribute('onclick') || '', id: tr.id || ''}, tr.dataset),
      });
    }
    return {heads, rows, trong, url: location.href};
  }
  return null;
}"""

_JS_DAT_SO_DONG = r"""(n) => {
  try {
    const $ = window.jQuery || window.$;
    if ($ && $.fn && $.fn.dataTable) {
      const api = $.fn.dataTable.tables({visible: true, api: true});
      if (api && api.context && api.context.length) {
        if (api.page.len() >= n) return 'da-du';
        api.page.len(n).draw(false);
        return 'datatables';
      }
    }
  } catch (e) {}
  const ds = Array.from(document.querySelectorAll('select'));
  for (let i = 0; i < ds.length; i++) {
    const so = Array.from(ds[i].options).map(o => parseInt(o.text, 10));
    if (!so.includes(10) || so.filter(x => !isNaN(x)).length < 2) continue;
    let tot = null;
    for (const o of ds[i].options) {
      const x = parseInt(o.text, 10);
      if (!isNaN(x) && x <= 200 && (tot === null || x > parseInt(tot.text, 10))) tot = o;
    }
    if (!tot) continue;
    if (ds[i].value === tot.value) return 'da-du';
    // select thường bị widget (select2/chosen) che, select_option của Playwright không bấm được -> gán thẳng
    ds[i].value = tot.value;
    ds[i].dispatchEvent(new Event('change', {bubbles: true}));
    try { const $ = window.jQuery || window.$; if ($) $(ds[i]).trigger('change'); } catch (e) {}
    return {chon: i, gia_tri: tot.value, chu: tot.text.trim()};
  }
  return null;
}"""

_JS_TRANG_SAU = r"""() => {
  const tat = el => el.classList.contains('disabled') || (el.closest('li') && el.closest('li').classList.contains('disabled'))
    || el.disabled || el.getAttribute('aria-disabled') === 'true';
  try {
    const $ = window.jQuery || window.$;
    if ($ && $.fn && $.fn.dataTable) {
      const api = $.fn.dataTable.tables({visible: true, api: true});
      if (api && api.context && api.context.length) {
        const i = api.page.info();
        if (i.page >= i.pages - 1) return 'het';
        api.page('next').draw('page');
        return 'datatables';
      }
    }
  } catch (e) {}
  const chon = ['.dataTables_paginate .next', '.dt-paging-button.next', 'li.next', 'li.page-item.next',
    '[aria-label="Next"]', '[aria-label="Trang sau"]', '[title="Trang sau"]', '[title="Next"]'];
  for (const s of chon) {
    for (const el of document.querySelectorAll(s)) {
      if (!el.offsetParent) continue;
      if (tat(el)) return 'het';
      (el.querySelector('a,button') || el).click();
      return 'bam';
    }
  }
  for (const el of document.querySelectorAll('.pagination a, .pagination button, [class*=paginat] a, [class*=paginat] button')) {
    const t = (el.innerText || '').trim();
    if (['›', '»', '>', 'Sau', 'Tiếp', 'Next', 'Trang sau'].includes(t)) {
      if (tat(el)) return 'het';
      el.click();
      return 'bam';
    }
  }
  return null;
}"""

# Ứng viên tệp trên trang chi tiết: link có đuôi tệp / từ khóa tải, khung xem PDF, tên tệp không có link (bấm mới tải)
_JS_TEP = r"""() => {
  const duoi = /\.(pdf|docx?|xlsx?|pptx?|zip|rar|jpe?g|png|txt)(\?|$|#)/i;
  const tk = /(download|tai-?xuong|taifile|getfile|get-file|viewfile|view-file|attach|dinh-?kem|\/files?\/|uploads?\/)/i;
  const ra = [], ten_le = [];
  const them = (url, ten, kieu) => { if (url && !ra.some(x => x.url === url)) ra.push({url, ten: (ten || '').replace(/\s+/g, ' ').trim().slice(0, 200), kieu}); };
  for (const a of document.querySelectorAll('a[href]')) {
    const h = a.getAttribute('href') || '';
    if (!h || h === '#' || /^(javascript|mailto):/i.test(h)) continue;
    const ten = a.innerText || a.getAttribute('title') || a.getAttribute('download') || '';
    if (duoi.test(h) || tk.test(h) || duoi.test(ten) || a.hasAttribute('download')) them(a.href, ten, 'lien-ket');
  }
  for (const el of document.querySelectorAll('iframe[src], embed[src], object[data]')) {
    let s = el.getAttribute('src') || el.getAttribute('data') || '';
    if (!s || s.startsWith('about:')) continue;
    const m = s.match(/[?&]file=([^&]+)/);
    if (m) s = decodeURIComponent(m[1]);
    try { them(new URL(s, location.href).href, el.getAttribute('title') || '', 'khung-xem'); } catch (e) {}
  }
  for (const el of document.querySelectorAll('a, span, td, div, li, button, p, label')) {
    if (el.children.length > 2) continue;
    const t = (el.innerText || '').trim();
    if (t.length < 200 && /\.(pdf|docx?|xlsx?)$/i.test(t) && !ten_le.includes(t)) ten_le.push(t);
  }
  return {lien_ket: ra, ten_le};
}"""

_JS_FETCH = r"""async (u) => {
  try {
    const r = await fetch(u, {credentials: 'include'});
    const ct = r.headers.get('content-type') || '', cd = r.headers.get('content-disposition') || '';
    if (!r.ok) return {status: r.status, ct, cd};
    const a = new Uint8Array(await r.arrayBuffer());
    let s = '';
    for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode.apply(null, a.subarray(i, i + 0x8000));
    return {status: r.status, ct, cd, b64: btoa(s)};
  } catch (e) { return {loi: String(e)}; }
}"""


def _egov_anh_xa_cot(heads):
    """Tiêu đề cột -> {khóa: chỉ số}. Hàm thuần (máy ảo Windows thử được, xem tay.py --chay-thu)."""
    idx = {}
    for i, h in enumerate(bo_dau(x) for x in heads):
        for khoa, cum in EGOV_COT:
            if khoa not in idx and any(h.startswith(c) for c in cum):
                idx[khoa] = i
                break
    return idx


def _egov_la_mat(vb):
    """Độ mật khác 'Thường' (Mật, Tối mật, Tuyệt mật...) -> không bao giờ tải, không ghi lên GitHub."""
    m = bo_dau(vb.get("do_mat", ""))
    return bool(m) and m not in ("thuong", "binh thuong", "khong mat", "khong", "-")


def _egov_ngay(vb):
    """Ngày dùng để cắt khoảng quét: văn bản đến lấy Ngày nhận, không có thì Ngày ban hành."""
    return parse_ngay(vb.get("ngay_nhan", "")) or parse_ngay(vb.get("ngay_ban_hanh", ""))


def _egov_dong_thanh_vb(hang, idx, nguon):
    o = hang["o"]
    lay = lambda k: o[idx[k]] if k in idx and idx[k] < len(o) else ""
    href = hang.get("href") or [[] for _ in o]
    url = ""
    for k in ("trich_yeu", "so"):
        if k in idx and idx[k] < len(href) and href[idx[k]]:
            url = href[idx[k]][0]
            break
    if not url:
        url = next((h[0] for h in href if h), "")
    if not url:      # dòng không có link: thử nhặt đường dẫn trong onclick của ô hoặc của dòng
        for s in list(hang.get("bam") or []) + [(hang.get("tr") or {}).get("onclick", "")]:
            m = re.search(r"""['"](/[^'"\s]+)['"]""", s or "")
            if m:
                url = urljoin(EGOV_GOC, m.group(1))
                break
    m = re.search(r"[?&](?:id|documentId|docId|vanBanId|idVanBan)=([\w-]+)", url or "", flags=re.I) \
        or re.search(r"/(\d{3,})(?:[/?#]|$)", url or "")
    ma = m.group(1) if m else str((hang.get("tr") or {}).get("id", "") or "")
    return {
        "so_ky_hieu": lay("so"), "ngay_ban_hanh": lay("ngay"), "ngay_nhan": lay("ngay_nhan"),
        "trich_yeu": lay("trich_yeu"), "don_vi": lay("don_vi"), "nguoi_ky": lay("nguoi_ky"), "loai": lay("loai"),
        "trang_thai": lay("trang_thai"), "do_mat": lay("do_mat"), "do_khan": lay("do_khan"), "han": lay("han"),
        "nguon": nguon, "id_data360x": ma, "url_chi_tiet": url, "he_thong": "egov",
    }


def _egov_doc_bang(page):
    try:
        return page.evaluate(_JS_DOC_BANG)
    except Exception:
        return None


_JS_DANG_TAI = r"""() => {
  const thay = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
  // chỉ hộp báo tải (div/span/p), KHÔNG xét ô bảng: cột Trạng thái có "Đang xử lý" (bắt được khi chạy thử 29/10/2026)
  for (const el of document.querySelectorAll('div, span, p')) {
    if (el.children.length > 3 || el.closest('table')) continue;
    const t = (el.innerText || '').trim();
    if (t.length < 60 && /đang tải|dang tai|loading\.\.\.|processing/i.test(t) && thay(el)) return true;
  }
  return false;
}"""


def _egov_dang_tai(page):
    try:
        return bool(page.evaluate(_JS_DANG_TAI))
    except Exception:
        return False


def _egov_tong_so(page):
    """'Tổng số: 54 bản ghi' hoặc 'Showing 1 to 10 of 54 entries' -> 54; không thấy -> None."""
    try:
        chu = page.locator("body").inner_text()
    except Exception:
        return None
    m = re.search(r"T[ổo]ng s[ốo]\s*:?\s*([\d.,]+)\s*b[ảa]n ghi", chu, flags=re.I) \
        or re.search(r"of\s+([\d.,]+)\s+entries", chu, flags=re.I) \
        or re.search(r"trong t[ổo]ng s[ốo]\s+([\d.,]+)", chu, flags=re.I)
    return int(re.sub(r"[.,]", "", m.group(1))) if m else None


def _egov_cho_bang(page, giay=EGOV_CHO_LAG_GIAY):
    """Chờ bảng có tiêu đề 'Trích yếu' và có dòng (hoặc báo trống), và hộp "Đang tải dữ liệu..." đã tắt.
    Cổng rất chậm: bảng có thể hiện tiêu đề ngay nhưng dòng tới sau vài chục giây. Trả kết quả _JS_DOC_BANG hoặc None."""
    bat_dau = time.time()
    kq = None
    while time.time() - bat_dau < giay:
        if _egov_dang_tai(page):
            page.wait_for_timeout(1500)
            continue
        kq = _egov_doc_bang(page)
        if kq and (kq["rows"] or kq.get("trong")):
            page.wait_for_timeout(700)
            return _egov_doc_bang(page) or kq
        if kq and time.time() - bat_dau > 40:      # có bảng nhưng 40 giây không tải gì mà vẫn không có dòng: coi như trống
            return kq
        page.wait_for_timeout(1000)
    return kq


def _egov_chu_ky(kq):
    """Dấu nhận biết trang bảng hiện tại để biết đã sang trang mới chưa."""
    if not kq:
        return ""
    return f"{len(kq['rows'])}|" + "|".join(" ".join(r["o"])[:80] for r in kq["rows"][:3])


def _egov_cho_doi(page, cu, giay=EGOV_CHO_LAG_GIAY):
    bat_dau = time.time()
    while time.time() - bat_dau < giay:
        page.wait_for_timeout(800)
        if _egov_dang_tai(page):
            continue
        kq = _egov_doc_bang(page)
        if kq and _egov_chu_ky(kq) != cu and (kq["rows"] or kq.get("trong")):
            page.wait_for_timeout(600)
            return _egov_doc_bang(page) or kq
    return None


def _egov_trang_da_do():
    try:
        return json.loads(EGOV_TRANG_DA_DO.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _egov_bam(page, nhan, cho_giay=0):
    """Bấm phần tử nhìn thấy được có chữ ĐÚNG bằng nhan (không bấm nhầm 'Tra cứu văn bản đến').
    cho_giay > 0: chờ phần tử hiện ra (trang Angular vẽ tab sau khi tải - vụ 29/10/2026: bấm ngay sau goto thì chưa có tab)."""
    het = time.time() + cho_giay

    def _bam(el):
        for i in range(min(el.count(), 6)):
            if el.nth(i).is_visible():
                el.nth(i).click(timeout=8000)
                page.wait_for_timeout(2500)
                return True
        return False

    try:
        # Ưu tiên tab thật (li.topbar-tab) và chờ nó hiện; chữ trùng ở chỗ khác (menu, liên kết) chỉ bấm khi hết giờ chờ
        while True:
            if _bam(page.locator(f"li.topbar-tab:has(span.topbar-tab__label:text-is('{nhan}'))")):
                return True
            if time.time() >= het:
                return _bam(page.get_by_text(nhan, exact=True))
            page.wait_for_timeout(1000)
    except Exception as e:
        log(f"  không bấm được '{nhan}':", str(e)[:100])
        return False


def _egov_bam_menu(page, nguon):
    """Vào danh sách văn bản như người dùng: menu 'Văn bản đến/đi' rồi tab 'Danh sách văn bản' (nếu có)."""
    if EGOV_GOC.split("//")[1] not in page.url:
        page.goto(EGOV_DS_DEN, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2500)
    if not _egov_bam(page, EGOV_MENU[nguon]):
        return False
    _egov_bam(page, "Danh sách văn bản")
    return True


# ---------------------------------------------------------------- API JSON của egov1 (khảo sát 29/10/2026 14:36)
# Giao diện chỉ là lớp vỏ: danh sách, chi tiết, nhiệm vụ đều lấy từ egov-gateway.laocai.gov.vn trả JSON, ví dụ
#   /ioffice/Ajax/IworkHandler.ashx?page=1&length=10&type=xemden&...      -> {"value": {"total", "data": [{sohieu, trichyeu,
#        ngaybanhanh, ngaynhan, tinhtrang, cqbh, nguoiky, domat, capdo, vaitro, nguoixulychinh, macongvan, files...}]}}
#   /ioffice/Ajax/IworkHandler.ashx?type=xemden_chitiet&documentId=<macongvan>&t=0 -> {"value": {ButPhe, LinhVuc, ...}}
#   /ioffice/Ajax/IworkHandler.ashx?type=get_quyen_nhac_viec             -> số đếm vb_den_chua_xu_ly, ...
#   /work/api/works/reminds/v1?workCreateType=0                            -> [{code: waiting|doing|..., count}]
#   /work/api/works/v1?page=1&length=10&type=waiting                       -> {"data": [nhiệm vụ]}
#   /work/api/works/report/works-sumary?isHighestCompany=false             -> nhiệm vụ UBND tỉnh giao / nội bộ của Sở
# Bot để Chrome tự gọi (nhận header xác thực), rồi gọi lại đúng URL đó với length lớn: một lượt thay vì lật 10 dòng/trang
# trên giao diện lag. API không trả thì quay về đọc bảng như cũ.
EGOV_GATEWAY = "https://egov-gateway.laocai.gov.vn"
EGOV_API_DONG = 200
EGOV_API_TRANG_TOI_DA = 400     # 400 trang x 200 dòng: đủ cả lượt quét 395 ngày (dừng sớm khi gặp ngày cũ hơn khoảng quét)
_EGOV_API = {"hdr": {}, "url": {}, "moi": None, "resp": []}   # resp: phản hồi JSON của gateway vừa bắt (tìm API danh sách)
NHAN_NHIEM_VU = {"waiting": "Chờ xử lý", "doing": "Đang thực hiện", "awaitApproval": "Chờ duyệt",
                 "awaitToApproval": "Chờ phê duyệt", "dueDate": "Đến hạn", "outOfDate": "Quá hạn", "refuse": "Trả lại",
                 "cooperate": "Phối hợp", "incharge": "Phụ trách", "view": "Để biết", "finish": "Đã hoàn thành",
                 "sendDraft": "Dự thảo đã gửi", "draftNotHasMission": "Dự thảo chưa tạo nhiệm vụ"}
NV_LAY_DANH_SACH = ("outOfDate", "dueDate", "waiting", "doing", "awaitApproval", "refuse")


def _egov_nghe_api(page):
    """Gắn một lần cho mỗi trang: nhặt header xác thực Chrome gửi tới gateway và URL API danh sách vừa gọi."""
    if getattr(page, "_egov_nghe", False):
        return
    page._egov_nghe = True

    def _req(r):
        try:
            u = r.url
            if EGOV_GATEWAY.split("//")[1] not in u:
                return
            for k, v in r.headers.items():
                if k.lower() in ("authorization", "token", "x-access-token", "x-auth-token", "userid", "x-user-id",
                                 "companyid", "x-company-id", "accesstoken"):
                    _EGOV_API["hdr"][k] = v
            if "length=" in u or "pagesize=" in u.lower():
                q = parse_qs(urlparse(u).query)
                loai = (q.get("type") or [""])[0]
                _EGOV_API["url"][loai] = u
                _EGOV_API["moi"] = (loai, u)
        except Exception:
            pass

    def _resp(r):
        try:
            if EGOV_GATEWAY.split("//")[1] in r.url and "json" in (r.headers.get("content-type") or "").lower():
                _EGOV_API["resp"].append(r)
                del _EGOV_API["resp"][:-80]
        except Exception:
            pass

    page.on("request", _req)
    page.on("response", _resp)


_KHOA_VB = ("sohieu", "trichyeu", "symbol", "abridgment", "sokyhieu", "kyhieu")


def _tim_ds_vb(j, sau=0):
    """Tìm trong JSON mảng các văn bản (phần tử có khóa số hiệu / trích yếu). Trả (mảng, tổng số) hoặc (None, 0)."""
    if sau > 4:
        return None, 0
    if isinstance(j, list):
        if j and isinstance(j[0], dict) and any(str(k).lower() in _KHOA_VB for k in j[0]):
            return j, 0
        return None, 0
    if isinstance(j, dict):
        for v in j.values():
            ds, tong_trong = _tim_ds_vb(v, sau + 1)
            if ds is not None:
                if tong_trong:
                    return ds, tong_trong
                tong = next((j[k] for k in j if str(k).lower() in ("total", "recordstotal", "totalcount", "totalrecords",
                                                                    "totalrecord", "recordsfiltered", "count")
                             and isinstance(j[k], int)), 0)
                return ds, tong
    return None, 0


def _egov_tim_api_ds():
    """Trong các phản hồi gateway vừa bắt (mới nhất trước), lời gọi nào trả danh sách văn bản -> mẫu để gọi lại
    {"url", "method", "body", "ct"}. Vụ 30/10/2026: tab Tra cứu không gọi API dạng GET ...length=..., bot đọc giao diện
    10 dòng/trang và dừng ở 1.500 văn bản; nay nhận ra API theo NỘI DUNG phản hồi, kể cả POST."""
    for r in reversed(_EGOV_API["resp"]):
        try:
            ds, _ = _tim_ds_vb(r.json())
        except Exception:
            continue
        if ds:
            q = r.request
            return {"url": r.url, "method": q.method, "body": q.post_data or "",
                    "ct": (q.headers.get("content-type") or "")}
    return None


def _doi_trang_body(body, ct, trang, dong):
    """Đổi tham số phân trang trong thân POST (JSON hoặc form). Khóa 0-gốc (giá trị ban đầu 0) giữ 0-gốc."""
    ten_trang = ("page", "pageindex", "pagenumber", "currentpage", "pageno")
    ten_dong = ("length", "pagesize", "limit", "size", "rows", "perpage", "recordsperpage", "take")
    ten_bo = ("skip", "start", "offset")

    def _gan(k, v0):
        kl = str(k).lower()
        if kl in ten_trang:
            return (trang - 1) if str(v0) == "0" else trang
        if kl in ten_dong:
            return dong
        if kl in ten_bo:
            return (trang - 1) * dong
        return None

    if "json" in ct.lower() or body.strip().startswith(("{", "[")):
        try:
            d = json.loads(body)
        except Exception:
            return body

        def _di(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    moi = _gan(k, v) if not isinstance(v, (dict, list)) else None
                    if moi is not None:
                        o[k] = moi
                    else:
                        _di(v)
            elif isinstance(o, list):
                for x in o:
                    _di(x)
        _di(d)
        return json.dumps(d, ensure_ascii=False)
    q = parse_qsl(body, keep_blank_values=True)
    return urlencode([(k, str(_gan(k, v)) if _gan(k, v) is not None else v) for k, v in q])


def _egov_ghi_chan_doan(nguon, ly_do):
    """Đẩy lên kho riêng tư danh sách lời gọi gateway của tab vừa mở (đã che mã) để Claude sửa bộ đọc."""
    try:
        token = doc_config().get("github_token", "")
        if not token:
            return
        ds = []
        for r in _EGOV_API["resp"][-40:]:
            try:
                hinh = _hinh_json(r.json())
            except Exception:
                hinh = None
            q = r.request
            ds.append({"method": q.method, "url": _che(r.url), "body": _che(q.post_data or "")[:1500],
                       "status": r.status, "hinh": hinh})
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        gh_mot_commit(REPO_TRI_THUC, {f"{THU_MUC_TRI_THUC}/egov/soi/{ts}-tra-cuu-{nguon}.json":
                                      json.dumps({"ly_do": ly_do, "goi": ds}, ensure_ascii=False, indent=1).encode()},
                      f"Chẩn đoán tab Tra cứu {nguon} egov1: {ly_do}"[:120], token)
        log(f"  ({nguon}) đã đẩy chẩn đoán lời gọi API lên theo-doi/egov/soi/{ts}-tra-cuu-{nguon}.json")
    except Exception as e:
        log("  không đẩy được chẩn đoán:", str(e)[:120])


def _egov_api(page, url, nhan=""):
    """GET qua request context của Chrome (cùng cookie) + header xác thực đã nhặt. Trả JSON hoặc None."""
    try:
        r = page.request.get(url, headers=_EGOV_API["hdr"] or None, timeout=EGOV_CHO_LAG_GIAY * 1000)
        if not r.ok:
            log(f"  API {nhan} HTTP {r.status}")
            return None
        return r.json()
    except Exception as e:
        log(f"  API {nhan} lỗi:", str(e)[:120])
        return None


def _doi_tham_so(url, **kv):
    q = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
    for k, v in kv.items():
        for k0 in list(q):
            if k0.lower() == k.lower():
                q[k0] = str(v)
    return url.split("?")[0] + "?" + urlencode(q)


def _lay(d, *khoa):
    """Giá trị đầu tiên có trong dict theo danh sách khóa (không phân biệt hoa thường)."""
    thuong = {str(k).lower(): v for k, v in d.items()}
    for k in khoa:
        v = thuong.get(k.lower())
        if v not in (None, ""):
            return v
    return ""


def _ngay_vn(x):
    """'2026-10-28T00:00:00' -> '28/10/2026'; giữ nguyên nếu đã dạng dd/mm/yyyy."""
    x = str(x or "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", x)
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else x[:10]


def _egov_json_vb(d, nguon):
    """Một phần tử JSON danh sách -> dict văn bản như bộ đọc bảng (tên khóa của cổng ghi ở đầu mục này)."""
    mcv = str(_lay(d, "macongvan", "documentId", "id", "guid"))
    ty = re.sub(r"\s+", " ", str(_lay(d, "trichyeu", "abridgment", "trich_yeu", "noidung"))).strip()
    url = (f"{EGOV_GOC}/document/xem-den-xem?documentId={mcv}&t=0&hxl=" if nguon == "den" and mcv
           else str(_lay(d, "url", "link")))
    return {
        "so_ky_hieu": str(_lay(d, "sohieu", "symbol", "sokyhieu", "so_ky_hieu", "kyhieu")).strip(),
        "ngay_ban_hanh": _ngay_vn(_lay(d, "ngaybanhanh", "publishTime", "ngayky")),
        "ngay_nhan": _ngay_vn(_lay(d, "ngaynhan", "ngayden")), "trich_yeu": ty,
        "don_vi": str(_lay(d, "cqbh", "coquanbanhanh", "documentSentCompany", "donvisoanthao", "phongban", "publishBy")),
        "nguoi_ky": str(_lay(d, "nguoiky", "signer")), "loai": str(_lay(d, "loaivanban", "tenloai")),
        "trang_thai": str(_lay(d, "tinhtrang", "trangthai")), "do_mat": str(_lay(d, "domat")),
        "do_khan": str(_lay(d, "capdo", "dokhan")), "han": str(_lay(d, "hxl", "hanxuly")),
        "vai_tro": str(_lay(d, "vaitro")), "nguoi_xu_ly_chinh": str(_lay(d, "nguoixulychinh")),
        "so_den": str(_lay(d, "soden", "number")), "da_xem": _lay(d, "xem"),
        "nguon": nguon, "id_data360x": mcv, "url_chi_tiet": url, "he_thong": "egov",
    }


def _egov_api_danh_sach(page, nguon, tu_ngay, mau_url):
    """Gọi lại API danh sách với EGOV_API_DONG dòng/lượt cho tới khi gặp ngày cũ hơn tu_ngay. None nếu API không dùng được."""
    ra, da, mat, trang = [], set(), 0, 1
    mau = mau_url if isinstance(mau_url, dict) else {"url": mau_url, "method": "GET", "body": "", "ct": ""}
    while trang <= EGOV_API_TRANG_TOI_DA:
        u = _doi_tham_so(mau["url"], length=EGOV_API_DONG, pageSize=EGOV_API_DONG, page=trang, pageIndex=trang,
                         skip=(trang - 1) * EGOV_API_DONG, start=(trang - 1) * EGOV_API_DONG)
        if mau["method"].upper() == "POST":
            hdr = dict(_EGOV_API["hdr"])
            if mau["ct"]:
                hdr["content-type"] = mau["ct"]
            try:
                r = page.request.post(u, headers=hdr or None, timeout=EGOV_CHO_LAG_GIAY * 1000,
                                      data=_doi_trang_body(mau["body"], mau["ct"], trang, EGOV_API_DONG))
                j = r.json() if r.ok else None
            except Exception as e:
                log(f"  API danh sách {nguon} (POST) lỗi:", str(e)[:120])
                j = None
        else:
            j = _egov_api(page, u, f"danh sách {nguon}")
        ds_vb, tong_vb = _tim_ds_vb(j) if j is not None else (None, 0)
        v = (j or {}).get("value", j) if isinstance(j, dict) else None
        if ds_vb is not None and not (isinstance(v, dict) and isinstance(v.get("data"), list)):
            v = {"data": ds_vb, "total": tong_vb}            # API trả dạng khác {value: {data, total}}
        if isinstance(v, dict) and v.get("success") is False:
            log(f"  ({nguon}) API cổng báo lỗi: {str(v.get('message'))[:120]}")
            return None if trang == 1 else ra
        data = (v or {}).get("data") if isinstance(v, dict) else None
        if not isinstance(data, list):
            return None if trang == 1 else ra
        tong = (v or {}).get("total") or (v or {}).get("recordsTotal") or 0
        moi = 0
        for d in data:
            if not isinstance(d, dict):
                continue
            vb = _egov_json_vb(d, nguon)
            if _egov_la_mat(vb):
                mat += 1
                continue
            khoa = vb["id_data360x"] or f"{vb['so_ky_hieu']}|{vb['ngay_ban_hanh']}"
            if khoa in da:
                continue
            da.add(khoa)
            ra.append(vb)
            moi += 1
        ngay = [n for n in (_egov_ngay(r) for r in ra[-moi:] if moi) if n] if moi else []
        log(f"  ({nguon}) API trang {trang}: {len(data)} dòng, đã đọc {len(ra)}/{tong}"
            + (f", tới ngày {min(ngay).strftime('%d/%m/%Y')}" if ngay else ""))
        if not data or moi == 0 or (tong and len(ra) + mat >= tong) or (ngay and max(ngay) < tu_ngay):
            break
        trang += 1
    if mat:
        log(f"  ({nguon}) bỏ {mat} văn bản có độ mật (không tải, không ghi)")
    return ra


def _egov_api_chi_tiet(page, vb):
    """Bút phê / chỉ đạo, lĩnh vực, loại văn bản của văn bản đến (API xemden_chitiet). {} nếu không lấy được."""
    if vb.get("nguon") != "den" or not vb.get("id_data360x"):
        return {}
    j = _egov_api(page, f"{EGOV_GATEWAY}/ioffice/Ajax/IworkHandler.ashx?type=xemden_chitiet"
                        f"&documentId={vb['id_data360x']}&t=0", "chi tiết")
    v = (j or {}).get("value") if isinstance(j, dict) else None
    if not isinstance(v, dict):
        return {}
    but_phe = re.sub(r"<br\s*/?>|</br>", "\n", str(v.get("ButPhe") or ""))
    but_phe = re.sub(r"<[^>]+>", "", but_phe).replace("&nbsp;", " ")
    but_phe = "\n".join(x.strip() for x in but_phe.splitlines() if x.strip())
    return {"but_phe": but_phe, "linh_vuc_cong": str(v.get("LinhVuc") or "").strip(),
            "loai": str(v.get("LoaiVanBan") or "").strip(), "ma_dinh_danh": str(v.get("MaDinhDanh") or "")}


def _egov_mo_danh_sach(page, nguon, tra_cuu=True):
    """Mở trang danh sách rồi bấm tab "Tra cứu văn bản …" (tất cả văn bản của Sở) hay "Danh sách văn bản" (phần giao cho
    Bạn). Trả kết quả đọc bảng; None nếu bị đưa về trang đăng nhập; False nếu không tìm thấy."""
    _egov_nghe_api(page)
    da_do = _egov_trang_da_do()
    ung_vien = []
    if da_do.get(nguon):
        ung_vien.append(("url", da_do[nguon]))
    if nguon == "den":
        ung_vien.append(("url", EGOV_DS_DEN))
    else:
        ung_vien += [("url", EGOV_DS_DI), ("url", EGOV_DS_DI.split("?")[0] + "?type=all")]
    ung_vien.append(("menu", None))
    for kieu, url in ung_vien:
        try:
            if kieu == "url":
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
            elif not _egov_bam_menu(page, nguon):
                continue
            if can_dang_nhap(page):
                return None
            tab = (EGOV_TAB_TRA_CUU if tra_cuu else EGOV_TAB_CUA_TOI)[nguon]
            _EGOV_API["moi"] = None; _EGOV_API["resp"] = []                     # URL API danh sách bắt được SAU lúc bấm tab
            if _egov_bam(page, tab, cho_giay=30):
                log(f"  ({nguon}) đã bấm tab '{tab}'")
            else:
                log(f"  ({nguon}) không thấy tab '{tab}' - đọc tab đang mở")
            kq = _egov_cho_bang(page)
            if kq and kq.get("heads"):
                if da_do.get(nguon) != page.url:
                    da_do[nguon] = page.url
                    try:
                        EGOV_TRANG_DA_DO.parent.mkdir(parents=True, exist_ok=True)
                        EGOV_TRANG_DA_DO.write_text(json.dumps(da_do, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                    log(f"  ({nguon}) danh sách ở {page.url}")
                return kq
            log(f"  ({nguon}) {kieu} {url or ''}: không thấy bảng có cột Trích yếu (URL {page.url})")
        except Exception as e:
            log(f"  ({nguon}) {kieu} {url or ''} lỗi:", str(e)[:150])
    return False


def _egov_dat_so_dong(page, kq):
    """Đặt bảng hiện EGOV_SO_DONG dòng/trang cho nhanh (mặc định 10). Trả kết quả đọc bảng sau khi đổi."""
    cu = _egov_chu_ky(kq)
    try:
        r = page.evaluate(_JS_DAT_SO_DONG, EGOV_SO_DONG)
        if r and r != "da-du":
            moi = _egov_cho_doi(page, cu, 30)
            if not moi and isinstance(r, dict):
                # gán bằng JS không ăn: bấm widget hiện ra rồi chọn mục có số lớn nhất
                try:
                    page.locator("select").nth(r["chon"]).select_option(r["gia_tri"], timeout=5000)
                except Exception:
                    o = page.locator(".select2-selection, .chosen-single, .dataTables_length, .dt-length").first
                    if o.count():
                        o.click(timeout=5000)
                        page.get_by_text(r["chu"], exact=True).last.click(timeout=5000)
                moi = _egov_cho_doi(page, cu, 30)
            kq = moi or _egov_doc_bang(page) or kq
            log(f"  số dòng mỗi trang: {len(kq['rows'])}")
            return kq
    except Exception as e:
        log("  không đổi được số dòng mỗi trang:", str(e)[:100])
    return kq


def _egov_doc_cac_trang(page, nguon, kq, dung=None, toi_da=EGOV_TRANG_TOI_DA):
    """Đọc bảng qua các trang. dung(rows_trang) trả True thì dừng sau trang đó. Bỏ văn bản mật."""
    idx = _egov_anh_xa_cot(kq["heads"])
    if "trich_yeu" not in idx or "so" not in idx:
        log(f"  ({nguon}) không nhận ra cột bảng: {kq['heads']}")
        return []
    tat_ca, da_thay, mat, trang = [], set(), 0, 1
    tong = _egov_tong_so(page)
    while True:
        rows = []
        for h in kq["rows"]:
            vb = _egov_dong_thanh_vb(h, idx, nguon)
            if _egov_la_mat(vb):
                mat += 1
                continue
            khoa = f"{vb['so_ky_hieu']}|{vb['ngay_ban_hanh']}|{vb['trich_yeu'][:60]}"
            if khoa in da_thay:
                continue
            da_thay.add(khoa)
            rows.append(vb)
        tat_ca.extend(rows)
        ngay_cuoi = next((r.get("ngay_nhan") or r.get("ngay_ban_hanh") for r in reversed(rows)), "")
        log(f"  {nguon}: trang {trang}, {len(kq['rows'])} dòng, đã đọc {len(tat_ca)}"
            + (f"/{tong}" if tong else "") + (f", tới ngày {ngay_cuoi}" if ngay_cuoi else "")
            + (" - dừng khi gặp ngày cũ hơn khoảng quét" if trang == 1 and dung else ""))
        if not kq["rows"] or trang >= toi_da or (dung and dung(rows)):
            break
        cu = _egov_chu_ky(kq)
        try:
            r = page.evaluate(_JS_TRANG_SAU)
        except Exception:
            r = None
        if r in (None, "het"):
            break
        moi = _egov_cho_doi(page, cu)
        if not moi:
            log(f"  {nguon}: bấm trang sau nhưng bảng không đổi - dừng")
            break
        kq, trang = moi, trang + 1
    if mat:
        log(f"  {nguon}: bỏ {mat} văn bản có độ mật (không tải, không ghi)")
    return tat_ca


def _doc_xlsx(b):
    """Trả (tiêu đề, các dòng) của sheet đầu. openpyxl chưa có thì cài một lần (như pymupdf)."""
    import io
    for lan in (1, 2):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
            ws = wb.worksheets[0]
            dong = [["" if c is None else str(c).strip() for c in r] for r in ws.iter_rows(values_only=True)]
            dong = [r for r in dong if any(r)]
            # hàng tiêu đề = hàng đầu tiên có chữ "Trích yếu"
            for i, r in enumerate(dong[:10]):
                if any("trich yeu" in bo_dau(x) for x in r):
                    return r, dong[i + 1:]
            return (dong[0], dong[1:]) if dong else ([], [])
        except ImportError:
            if lan == 2:
                break
            log("  chưa có openpyxl, đang cài...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-q", "openpyxl"], timeout=300)
            except Exception:
                break
        except Exception as e:
            log("  không đọc được Excel:", repr(e)[:120])
            break
    return [], []


def _egov_xuat_excel(page, nguon):
    """Bấm nút Xuất Excel của danh sách (ảnh 29/10/2026: nút xanh 'Xuất Excel' và biểu tượng Excel trên thanh công cụ),
    bắt tệp tải xuống, trả danh sách văn bản như _egov_doc_cac_trang. Không có nút / không tải được -> []."""
    for sel in ("button:has-text('Xuất Excel')", "a:has-text('Xuất Excel')", ".buttons-excel", "[title*='Excel']",
                "button:has-text('Excel')"):
        nut = page.locator(sel)
        if not nut.count() or not nut.first.is_visible():
            continue
        try:
            with page.expect_download(timeout=EGOV_CHO_LAG_GIAY * 1000) as dl:
                nut.first.click(timeout=8000)
            b = Path(dl.value.path()).read_bytes()
        except Exception as e:
            log(f"  ({nguon}) Xuất Excel: {str(e)[:100]}")
            continue
        heads, dong = _doc_xlsx(b)
        idx = _egov_anh_xa_cot(heads)
        if "so" not in idx or "trich_yeu" not in idx:
            log(f"  ({nguon}) Excel không nhận ra cột: {heads[:12]}")
            return []
        ra, mat = [], 0
        for r in dong:
            vb = _egov_dong_thanh_vb({"o": r, "href": [[] for _ in r]}, idx, nguon)
            if _egov_la_mat(vb):
                mat += 1
                continue
            ra.append(vb)
        log(f"  ({nguon}) Xuất Excel: {len(ra)} dòng" + (f", bỏ {mat} văn bản mật" if mat else ""))
        return ra
    return []


def _egov_quet_danh_sach(page, nguon, tu_ngay, soi_dir=None, tra_cuu=True):
    """Thay quet_danh_sach của Data360X. tra_cuu=True: tab Tra cứu (mọi văn bản của Sở, để gom tri thức);
    False: tab Danh sách văn bản (phần giao cho Bạn, để lấy việc chờ xử lý). Trả danh sách từ tu_ngay; None nếu phải đăng nhập."""
    kq = _egov_mo_danh_sach(page, nguon, tra_cuu)
    if kq is None:
        return None
    if kq is False:
        log(f"  KHÔNG tìm thấy danh sách văn bản {'đến' if nguon == 'den' else 'đi'} trên egov1 - "
            "cần khảo sát lại (python bot-data360x.py --khao-sat)")
        telegram(f"Bot egov1: không tìm thấy danh sách văn bản {'đến' if nguon == 'den' else 'đi'}. "
                 "Chạy khao-sat-egov.bat rồi báo Claude.")
        return []
    if soi_dir:
        (soi_dir / f"danh-sach-{nguon}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(soi_dir / f"danh-sach-{nguon}.png"), full_page=True)
    # Ưu tiên API JSON mà chính trang vừa gọi (nhanh, đủ trường, không lật trang trên giao diện lag).
    # Nhận theo nội dung phản hồi trước (bắt được cả POST của tab Tra cứu), rồi mới theo URL có length=.
    mau_nd = _egov_tim_api_ds()
    if mau_nd:
        log(f"  ({nguon}) API danh sách theo nội dung: {mau_nd['method']} {mau_nd['url'].split('?')[0]}")
        tu_api = _egov_api_danh_sach(page, nguon, tu_ngay, mau_nd)
        if tu_api:
            return [r for r in tu_api if _egov_ngay(r) and _egov_ngay(r) >= tu_ngay]
    moi = _EGOV_API.get("moi")
    if moi:
        log(f"  ({nguon}) API danh sách: type={moi[0]}")
        tu_api = _egov_api_danh_sach(page, nguon, tu_ngay, moi[1])
        if tu_api:
            return [r for r in tu_api if _egov_ngay(r) and _egov_ngay(r) >= tu_ngay]
        if tu_api is None and nguon == "di" and tra_cuu:
            # data360_outgoing_documents_list báo lỗi (29/10/2026) -> tab "Đã phát hành"
            _EGOV_API["moi"] = None; _EGOV_API["resp"] = []
            if _egov_bam(page, "Đã phát hành", cho_giay=15):
                log("  (di) Tra cứu không trả dữ liệu - đọc tab 'Đã phát hành'")
                kq = _egov_cho_bang(page) or kq
                moi = _EGOV_API.get("moi")
                if moi:
                    tu_api = _egov_api_danh_sach(page, nguon, tu_ngay, moi[1])
                    if tu_api:
                        return [r for r in tu_api if _egov_ngay(r) and _egov_ngay(r) >= tu_ngay]
    if tra_cuu and (date.today() - tu_ngay).days > 31:
        _egov_ghi_chan_doan(nguon, f"không dùng được API, đọc giao diện (quét từ {tu_ngay.strftime('%d/%m/%Y')})")
    kq = _egov_dat_so_dong(page, kq)
    tong = _egov_tong_so(page)
    if tong is not None:
        log(f"  ({nguon}) cổng báo tổng số {tong} bản ghi")
    # Cổng lag: thử Xuất Excel trước. Excel chỉ chứa trang hiện tại thì không đủ (ít hơn tổng số) -> lật trang như thường.
    # Excel không có đường dẫn trang chi tiết: ghép lại từ bảng trang đầu theo số ký hiệu, còn lại mở qua ô tìm kiếm.
    tu_excel = _egov_xuat_excel(page, nguon)
    if tu_excel and (tong is None or len(tu_excel) >= min(tong, EGOV_SO_DONG * EGOV_TRANG_TOI_DA)) \
            and len(tu_excel) > len(kq["rows"]):
        idx = _egov_anh_xa_cot(kq["heads"])
        url_theo_so = {}
        if "so" in idx and "trich_yeu" in idx:
            for h in kq["rows"]:
                v = _egov_dong_thanh_vb(h, idx, nguon)
                if v["url_chi_tiet"]:
                    url_theo_so[_chuan_so(v["so_ky_hieu"]) + "|" + v["ngay_ban_hanh"]] = v["url_chi_tiet"]
        for v in tu_excel:
            v["url_chi_tiet"] = url_theo_so.get(_chuan_so(v["so_ky_hieu"]) + "|" + v["ngay_ban_hanh"], "")
        return [r for r in tu_excel if _egov_ngay(r) and _egov_ngay(r) >= tu_ngay]

    def _du_cu(rows):
        ngay = [n for n in (_egov_ngay(r) for r in rows) if n]
        return bool(ngay) and max(ngay) < tu_ngay      # cả trang đã cũ hơn khoảng quét

    rows = _egov_doc_cac_trang(page, nguon, kq, dung=_du_cu)
    if not rows and kq.get("rows"):
        log(f"  [chẩn đoán] tiêu đề cột: {kq['heads']}")
    return [r for r in rows if _egov_ngay(r) and _egov_ngay(r) >= tu_ngay]


def _egov_go_tim(page, chuoi):
    """Gõ chuỗi vào ô tìm kiếm của bảng. Trả True nếu gõ được."""
    kq = _egov_doc_bang(page)
    cu = _egov_chu_ky(kq)
    o = None
    for sel in (".dataTables_filter input", ".dt-search input", "input[type='search']"):
        el = page.locator(sel)
        if el.count() and el.first.is_visible():
            o = el.first
            break
    if o is None:
        el = page.get_by_placeholder(re.compile(r"tìm|search|ký hiệu|trích yếu", re.I))
        if el.count():
            o = el.first
    if o is None and kq:      # ô lọc ngay dưới tiêu đề cột "Số ký hiệu"
        idx = _egov_anh_xa_cot(kq["heads"])
        if "so" in idx:
            el = page.locator(f"thead tr:nth-child(2) th:nth-child({idx['so'] + 1}) input")
            if el.count():
                o = el.first
    if o is None:
        return False
    o.fill("")
    o.fill(chuoi)
    o.press("Enter")
    _egov_cho_doi(page, cu, 10)
    return True


def _egov_tim_tren_cong(page, nguon, chuoi, toi_da_trang=10):
    """Thay tim_tren_cong của Data360X: gõ số ký hiệu / từ khóa vào ô tìm của bảng rồi đọc kết quả."""
    kq = _egov_mo_danh_sach(page, nguon, tra_cuu=True)
    if not kq:
        return None
    moi = _EGOV_API.get("moi")
    if moi and "term=" in moi[1]:          # API có tham số term: tìm thẳng, không gõ vào ô tìm trên giao diện lag
        rows = _egov_api_danh_sach(page, nguon, date(2000, 1, 1), _doi_tham_so(moi[1], term=chuoi))
        if rows is not None:
            log(f"  ({nguon}) API tìm '{chuoi}': {len(rows)} dòng")
            return rows
    if not _egov_go_tim(page, chuoi):
        log(f"  ({nguon}) không thấy ô tìm kiếm - lật trang như cũ")
        return None
    kq = _egov_doc_bang(page) or kq
    rows = _egov_doc_cac_trang(page, nguon, kq, toi_da=toi_da_trang)
    log(f"  ({nguon}) tìm '{chuoi}': {len(rows)} dòng")
    return rows


def _egov_can_dang_nhap(page):
    u = page.url.lower()
    if any(k in u for k in ("/login", "dang-nhap", "dangnhap", "signin", "/sso", "/auth/", "/account/")):
        return True
    if u.startswith("http") and EGOV_GOC.split("//")[1] not in u:     # bị chuyển sang cổng khác (SSO)
        return True
    try:
        return page.locator("input[type='password']:visible").count() > 0
    except Exception:
        return False


def _egov_khoa(vb):
    return f"{vb.get('nguon')}|{vb.get('so_ky_hieu')}|{vb.get('ngay_ban_hanh')}|{vb.get('url_chi_tiet')}"


def _egov_mo_chi_tiet(ctx, page, vb):
    """Mở trang chi tiết của văn bản. Không có đường dẫn thì tìm trên danh sách rồi bấm vào trích yếu."""
    if vb.get("url_chi_tiet"):
        page.goto(vb["url_chi_tiet"], wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(3500)
        return not can_dang_nhap(page)
    if not _egov_mo_danh_sach(page, vb["nguon"]):
        return False
    _egov_go_tim(page, vb["so_ky_hieu"] or vb["trich_yeu"][:40])
    hang = page.locator("table tbody tr", has_text=vb["so_ky_hieu"] or vb["trich_yeu"][:40]).first
    if not hang.count():
        log(f"  không thấy dòng {vb['so_ky_hieu']} trên danh sách để mở chi tiết")
        return False
    so_tab, cu = len(ctx.pages), page.url
    dich = hang.get_by_text(vb["trich_yeu"][:30]) if vb.get("trich_yeu") else hang.locator("td").nth(2)
    (dich.first if dich.count() else hang).click(timeout=10000)
    page.wait_for_timeout(3500)
    if len(ctx.pages) > so_tab:           # mở ra tab mới: lấy đường dẫn rồi mở ngay trong tab đang dùng
        moi = ctx.pages[-1]
        try:
            moi.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:
            pass
        u = moi.url
        moi.close()
        if u and not u.startswith("about:"):
            page.goto(u, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
    if page.url != cu:
        vb["url_chi_tiet"] = page.url
    return True


def _ten_tu_cd(cd, url, mac_dinh):
    m = re.search(r"filename\*=(?:UTF-8|utf-8)''([^;]+)", cd or "") or re.search(r'filename="?([^";]+)"?', cd or "")
    if m:
        from urllib.parse import unquote
        return unquote(m.group(1)).strip()
    duoi = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    return duoi if "." in duoi[-6:] else mac_dinh


def _egov_fetch(page, url):
    """Cho chính Chrome (đang đăng nhập) tải URL. Trả (bytes|None, tên tệp theo content-disposition|'')."""
    try:
        r = page.evaluate(_JS_FETCH, url)
    except Exception as e:
        log("    Chrome fetch lỗi:", str(e)[:100])
        return None, ""
    if not r or not r.get("b64"):
        return None, ""
    b = base64.b64decode(r["b64"])
    if (r.get("ct") or "").lower().startswith("text/html") or b[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
        return None, ""      # trang xem, không phải tệp
    return b, _ten_tu_cd(r.get("cd", ""), url, "")


def _egov_mo_va_tai_tep(ctx, page, vb, soi_dir=None):
    """Mở trang chi tiết, tải MỌI tệp (văn bản chính + đính kèm) một lần, cất vào _EGOV_TEP."""
    import hashlib
    _EGOV_TEP.update(khoa=_egov_khoa(vb), chinh=None, khac=[])
    bat = []

    def _on(resp):
        try:
            ct = (resp.headers.get("content-type") or "").lower()
            cd = resp.headers.get("content-disposition") or ""
            if "pdf" in ct or "octet-stream" in ct or "msword" in ct or "officedocument" in ct or "attachment" in cd.lower():
                bat.append(resp)
        except Exception:
            pass

    page.on("response", _on)
    tep, da = [], set()

    def _them(ten, b, nguon_tep):
        if not b or len(b) < 200:
            return
        if len(b) > DINH_KEM_TOI_DA_MB * 1024 * 1024:
            log(f"    {ten}: {len(b) // 1024 // 1024} MB, quá lớn - bỏ qua")
            return
        h = hashlib.sha1(b).hexdigest()
        if h in da:
            return
        da.add(h)
        if _la_pdf(b) and not ten.lower().endswith(".pdf"):
            ten = (ten or "van-ban") + ".pdf"
        tep.append({"ten": ten or f"tep-{len(tep) + 1}", "bytes": b, "nguon_tep": nguon_tep})

    def _them_zip(ten, b, nguon_tep):
        """Cổng gửi một .zip chứa mọi đính kèm (nút "Tải xuống tất cả các file đính kèm", ảnh 29/10/2026): bung từng tệp."""
        import io
        import zipfile
        try:
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                so = 0
                for m in z.infolist():
                    if m.is_dir() or m.file_size < 200 or m.file_size > DINH_KEM_TOI_DA_MB * 1024 * 1024:
                        continue
                    _them(Path(m.filename).name, z.read(m), nguon_tep)
                    so += 1
                log(f"  tải tất cả đính kèm: {ten} -> {so} tệp")
                return so
        except zipfile.BadZipFile:
            return 0

    try:
        if not _egov_mo_chi_tiet(ctx, page, vb):
            return
        for nhan in ("File đính kèm", "Tệp đính kèm", "Tài liệu đính kèm", "Văn bản đính kèm", "Đính kèm"):
            if _egov_bam(page, nhan):
                break
        # Ưu tiên nút "Tải xuống tất cả các file đính kèm" (một lần tải, cổng lag đỡ nhiều lượt)
        for sel in ("[title*='Tải xuống tất cả']", "[aria-label*='Tải xuống tất cả']", "[data-original-title*='Tải xuống tất cả']",
                    "button:has-text('Tải xuống tất cả')", "a:has-text('Tải xuống tất cả')", "[title*='tất cả các file']"):
            nut = page.locator(sel)
            if not nut.count() or not nut.first.is_visible():
                continue
            try:
                with page.expect_download(timeout=EGOV_CHO_LAG_GIAY * 1000) as dl:
                    nut.first.click(timeout=8000)
                b = Path(dl.value.path()).read_bytes()
                ten = dl.value.suggested_filename or "dinh-kem.zip"
                if b[:2] == b"PK" and (ten.lower().endswith(".zip") or not ten.lower().endswith((".docx", ".xlsx", ".pptx"))):
                    if _them_zip(ten, b, "tai-tat-ca"):
                        break
                _them(ten, b, "tai-tat-ca")
                break
            except Exception as e:
                log("  nút tải tất cả:", str(e)[:100])
        if soi_dir:
            ten_soi = lam_sach(vb["so_ky_hieu"] or "khong-so")
            (soi_dir / f"chi-tiet-{ten_soi}.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(soi_dir / f"chi-tiet-{ten_soi}.png"), full_page=True)
        for resp in bat:
            try:
                _them(_ten_tu_cd(resp.headers.get("content-disposition", ""), resp.url, ""), resp.body(), "khung-xem")
            except Exception:
                pass
        ds = page.evaluate(_JS_TEP) or {"lien_ket": [], "ten_le": []}
        for c in ds["lien_ket"][:DINH_KEM_TOI_DA]:
            b, ten_cd = _egov_fetch(page, c["url"])
            if not b:
                try:
                    r = ctx.request.get(c["url"], timeout=120000)
                    if r.ok and not (r.headers.get("content-type") or "").lower().startswith("text/html"):
                        b, ten_cd = r.body(), _ten_tu_cd(r.headers.get("content-disposition", ""), c["url"], "")
                except Exception:
                    pass
            ten = c["ten"] if re.search(r"\.\w{2,4}$", c["ten"] or "") else (ten_cd or c["ten"])
            _them(ten, b, c["kieu"])
        # tên tệp hiện trên trang mà chưa tải được: bấm vào, bắt tệp tải xuống hoặc tab xem mở ra
        co_ten = {bo_dau(t["ten"]) for t in tep}
        for ten in ds["ten_le"][:DINH_KEM_TOI_DA]:
            if bo_dau(ten) in co_ten:
                continue
            el = page.get_by_text(ten, exact=True)
            if not el.count():
                continue
            so_tab = len(ctx.pages)
            try:
                with page.expect_download(timeout=15000) as dl:
                    el.first.click(timeout=8000)
                _them(ten, Path(dl.value.path()).read_bytes(), "bam-tai")
            except Exception:
                if len(ctx.pages) > so_tab:
                    moi = ctx.pages[-1]
                    try:
                        moi.wait_for_load_state("domcontentloaded", timeout=20000)
                        b, _ = _egov_fetch(page, moi.url)
                        _them(ten, b, "bam-mo-tab")
                    except Exception:
                        pass
                    finally:
                        moi.close()
        if not tep:
            log(f"  {vb['so_ky_hieu']}: không thấy tệp nào trên trang chi tiết ({page.url})")
        pdf = [t for t in tep if _la_pdf(t["bytes"])]
        chinh = next((t for t in pdf if t["nguon_tep"] == "khung-xem"), None) or (pdf[0] if pdf else None)
        _EGOV_TEP["chinh"] = chinh["bytes"] if chinh else None
        _EGOV_TEP["khac"] = [{"ten": t["ten"], "loai": "đính kèm", "bytes": t["bytes"]} for t in tep if t is not chinh]
        log(f"  {vb['so_ky_hieu']}: {len(tep)} tệp" + (f", văn bản chính {chinh['ten']}" if chinh else ", không có PDF"))
    finally:
        page.remove_listener("response", _on)


def _egov_tai_pdf(ctx, page, vb, soi_dir=None):
    """Thay tai_pdf của Data360X: trả bytes PDF văn bản chính (hoặc None)."""
    _egov_mo_va_tai_tep(ctx, page, vb, soi_dir)
    return _EGOV_TEP["chinh"]


def _egov_tai_dinh_kem(ctx, page, vb):
    """Thay tai_dinh_kem của Data360X: các tệp còn lại của trang chi tiết vừa mở bằng tai_pdf."""
    if _EGOV_TEP["khoa"] != _egov_khoa(vb):
        _egov_mo_va_tai_tep(ctx, page, vb)
    return list(_EGOV_TEP["khac"])


# ---------------------------------------------------------------- KHẢO SÁT CỔNG (lần đầu, hoặc khi cổng đổi giao diện)
_KHOA_NHAY_CAM = re.compile(r"(token|password|passwd|matkhau|mat_khau|secret|authorization|cookie|captcha|otp)", re.I)


def _che(chu):
    """Che giá trị nhạy cảm trong query string / form / JSON trước khi ghi ra tệp."""
    chu = re.sub(r"((?:access_|refresh_)?token|password|passwd|matkhau|secret|captcha|otp|key)=([^&\s]+)",
                 r"\1=…", str(chu or ""), flags=re.I)
    chu = re.sub(r'("(?:[^"]*(?:token|password|matkhau|secret|captcha|otp|session|cookie|jwt)[^"]*)"\s*:\s*)"[^"]*"',
                 r'\1"…"', chu, flags=re.I)
    chu = re.sub(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", "eyJ…", chu)      # JWT
    return re.sub(r"\b[A-Za-z0-9+/_-]{48,}={0,2}\b", lambda m: m.group(0)[:6] + "…", chu)     # chuỗi mã dài


def _hinh_json(o, sau=0):
    """Hình dạng của JSON (khóa, kiểu, độ dài mảng) để biết API trả gì mà không chép nguyên nội dung."""
    if sau > 4:
        return "…"
    if isinstance(o, dict):
        return {k: ("…" if _KHOA_NHAY_CAM.search(k) else _hinh_json(v, sau + 1)) for k, v in list(o.items())[:40]}
    if isinstance(o, list):
        return [f"{len(o)} phần tử", _hinh_json(o[0], sau + 1)] if o else []
    if isinstance(o, str):
        return f"str: {o[:60]}"
    return type(o).__name__


_JS_LIEN_KET = r"""() => Array.from(document.querySelectorAll('a[href], [onclick], [routerlink], [ng-click]'))
  .map(a => ({chu: (a.innerText || a.getAttribute('title') || '').replace(/\s+/g, ' ').trim().slice(0, 60),
              href: a.getAttribute('href') || a.getAttribute('routerlink') || '',
              bam: (a.getAttribute('onclick') || a.getAttribute('ng-click') || '').slice(0, 120)}))
  .filter(x => x.chu && (x.href || x.bam)).slice(0, 250)"""


def _egov_khao_sat_tren(ctx, page, thu_muc: Path):
    """Đi qua Văn bản đến, Văn bản đi, một trang chi tiết, Quản lý nhiệm vụ; ghi HTML, ảnh, bảng, liên kết,
    danh sách lời gọi API (đã che token) vào thu_muc. Trả danh sách bước đã đi."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    mang, buoc = [], []

    def _req(r):
        try:
            if r.resource_type in ("xhr", "fetch", "document"):
                mang.append({"kieu": r.resource_type, "method": r.method, "url": _che(r.url)[:400],
                             "gui": _che(r.post_data or "")[:600], "_url_goc": r.url})
        except Exception:
            pass

    def _resp(r):
        try:
            m = next((x for x in reversed(mang) if x["_url_goc"] == r.url and "status" not in x), None)
            if m is None:
                return
            ct = (r.headers.get("content-type") or "").lower()
            m.update(status=r.status, ct=ct[:60])
            if "json" in ct:
                d = r.json()
                m["hinh"] = _hinh_json(d)
                m["mau"] = _che(json.dumps(d, ensure_ascii=False))[:1500]
        except Exception:
            pass

    def chup(ten):
        try:
            page.wait_for_timeout(2000)
            (thu_muc / f"{ten}.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(thu_muc / f"{ten}.png"), full_page=True)
            bang = _egov_doc_bang(page)
            if bang:
                bang = {**bang, "rows": bang["rows"][:5], "cot_nhan_ra": _egov_anh_xa_cot(bang["heads"])}
            (thu_muc / f"{ten}.json").write_text(json.dumps(
                {"url": page.url, "tieu_de": page.title(), "bang": bang, "lien_ket": page.evaluate(_JS_LIEN_KET),
                 "tep": page.evaluate(_JS_TEP)}, ensure_ascii=False, indent=1), encoding="utf-8")
            buoc.append({"ten": ten, "url": page.url, "co_bang": bool(bang and bang.get("heads"))})
            log(f"  khảo sát: {ten} -> {page.url}")
        except Exception as e:
            buoc.append({"ten": ten, "loi": repr(e)[:200]})
            log(f"  khảo sát {ten} lỗi:", repr(e)[:150])

    page.on("request", _req)
    page.on("response", _resp)
    try:
        try:
            EGOV_TRANG_DA_DO.unlink()          # dò lại từ đầu
        except Exception:
            pass
        kq = _egov_mo_danh_sach(page, "den")
        chup("1-van-ban-den")
        dau = None
        if kq and kq.get("rows"):
            idx = _egov_anh_xa_cot(kq["heads"])
            dau = next((_egov_dong_thanh_vb(h, idx, "den") for h in kq["rows"]
                        if not _egov_la_mat(_egov_dong_thanh_vb(h, idx, "den"))), None)
        if _egov_mo_danh_sach(page, "di"):
            chup("2-van-ban-di")
        if dau:
            try:
                if _egov_mo_chi_tiet(ctx, page, dau):
                    for nhan in ("File đính kèm", "Tệp đính kèm", "Đính kèm"):
                        if _egov_bam(page, nhan):
                            break
                    chup("3-chi-tiet-van-ban-den")
            except Exception as e:
                log("  khảo sát chi tiết lỗi:", repr(e)[:150])
        try:
            page.goto(EGOV_NHIEM_VU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(4000)
            chup("4-quan-ly-nhiem-vu")
            for nhan in ("Chờ xử lý", "Đang thực hiện"):
                if _egov_bam(page, nhan):
                    page.wait_for_timeout(4000)
                    chup("5-nhiem-vu-" + _ten_tep_sach(nhan).lower())
                    page.goto(EGOV_NHIEM_VU, wait_until="domcontentloaded", timeout=90000)
                    page.wait_for_timeout(3000)
            page.goto(EGOV_TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(4000)
            chup("6-tong-quan")
            if _egov_bam(page, "Văn bản đi (1)") or _egov_bam(page, "Văn bản đi"):
                chup("7-tong-quan-van-ban-di")
        except Exception as e:
            log("  khảo sát nhiệm vụ lỗi:", repr(e)[:150])
    finally:
        page.remove_listener("request", _req)
        page.remove_listener("response", _resp)
        for m in mang:
            m.pop("_url_goc", None)
        (thu_muc / "api.json").write_text(json.dumps(mang, ensure_ascii=False, indent=1), encoding="utf-8")
        tom = [f"# Khảo sát egov1.laocai.gov.vn - {datetime.now().strftime('%d/%m/%Y %H:%M')}", "",
               f"Máy: {thong_tin_may().get('may', '')}. Bot tự đi qua các trang dưới đây; mỗi bước có .html, .png và "
               ".json (bảng, cột nhận ra, liên kết, ứng viên tệp). `api.json`: lời gọi API của cổng (đã che token).", ""]
        tom += [f"- {b['ten']}: " + (b.get("url", "") + (" (có bảng)" if b.get("co_bang") else " (KHÔNG thấy bảng)")
                                     if "loi" not in b else "lỗi " + b["loi"]) for b in buoc]
        tom += ["", f"Lời gọi API ghi được: {len(mang)}"]
        (thu_muc / "README.md").write_text("\n".join(tom) + "\n", encoding="utf-8")
    return buoc


def gh_mot_commit(repo, tep: dict, msg, token, lan_thu=4):
    """Ghi nhiều tệp {đường dẫn trong kho: bytes} trong MỘT commit (Git Data API: blob -> tree -> commit -> ref).
    Vụ 29/10/2026: đẩy từng tệp tạo hàng trăm commit/lượt, mỗi commit kích hoạt Vercel (75% dung lượng 10 GB,
    triển khai lỗi). Ref đổi giữa chừng (máy khác vừa đẩy) thì làm lại từ ref mới. Trả số tệp đã ghi."""
    if not tep:
        return 0
    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/git"
    blob = {}
    for duong, nd in tep.items():
        r = gh("POST", f"{api}/blobs", {"content": base64.b64encode(nd).decode(), "encoding": "base64"}, token)
        blob[duong] = r["sha"]
    for lan in range(lan_thu):
        ref = gh("GET", f"{api}/ref/heads/main", token=token)
        cha = ref["object"]["sha"]
        cay_cha = gh("GET", f"{api}/commits/{cha}", token=token)["tree"]["sha"]
        cay = gh("POST", f"{api}/trees", {"base_tree": cay_cha, "tree": [
            {"path": d, "mode": "100644", "type": "blob", "sha": sh} for d, sh in blob.items()]}, token)
        cm = gh("POST", f"{api}/commits", {"message": msg, "tree": cay["sha"], "parents": [cha]}, token)
        try:
            gh("PATCH", f"{api}/refs/heads/main", {"sha": cm["sha"]}, token)
            return len(blob)
        except RuntimeError as e:
            if "422" not in str(e) or lan == lan_thu - 1:
                raise
            time.sleep(2 + lan * 3)
    return 0


def _day_thu_muc(token, thu_muc: Path, duong_kho, msg, repo=REPO_TRI_THUC):
    """Đẩy mọi tệp của một thư mục trên máy lên kho riêng tư trong MỘT commit; lỗi thì đẩy từng tệp như cũ."""
    tep = {f"{duong_kho.rstrip('/')}/{f.relative_to(thu_muc).as_posix()}": f.read_bytes()
           for f in sorted(thu_muc.rglob("*")) if f.is_file()}
    try:
        return gh_mot_commit(repo, tep, msg, token)
    except Exception as e:
        log("  đẩy một commit không được, đẩy từng tệp:", str(e)[:120])
    so = 0
    for f in sorted(thu_muc.rglob("*")):
        if f.is_file():
            try:
                gh_ghi_de(repo, f"{duong_kho.rstrip('/')}/{f.relative_to(thu_muc).as_posix()}", f.read_bytes(), msg, token)
                so += 1
            except Exception as e:
                log(f"  không đẩy được {f.name}:", str(e)[:120])
    return so


def _egov_khao_sat_va_day(ctx, page, token):
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    thu_muc = LOG_DIR / "khao-sat" / ts
    buoc = _egov_khao_sat_tren(ctx, page, thu_muc)
    duong = f"{THU_MUC_TRI_THUC}/egov/soi/{ts}-bot"
    so = _day_thu_muc(token, thu_muc, duong, f"Khảo sát egov1 {ts}") if token else 0
    EGOV_DA_KHAO_SAT.parent.mkdir(parents=True, exist_ok=True)
    EGOV_DA_KHAO_SAT.write_text(json.dumps({"luc": ts, "buoc": buoc, "kho": duong if so else ""},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Khảo sát xong: {len(buoc)} bước" + (f", đã đẩy {so} tệp lên vlncn-laocai/{duong}" if so
                                              else f", lưu trên máy ở {thu_muc}"))
    return duong if so else str(thu_muc)


def _egov_da_khao_sat_len_kho():
    """Đã có lượt khảo sát ĐẨY ĐƯỢC lên kho chưa (vụ 29/10/2026: lượt đầu khảo sát xong nhưng GitHub 401, kết quả chỉ
    nằm trên máy - lượt sau phải khảo sát lại)."""
    try:
        return bool(json.loads(EGOV_DA_KHAO_SAT.read_text(encoding="utf-8")).get("kho", "").startswith("theo-doi/"))
    except Exception:
        return False


def _mo_cong_san_sang(p, ctx=None):
    """Mở Chrome hồ sơ bot ở trang chủ hệ thống đang dùng; phiên hết thì chờ Bạn đăng nhập. Trả (ctx, page) hoặc None."""
    ctx = ctx or mo_trinh_duyet(p, headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(3000)
    if can_dang_nhap(page):
        page.bring_to_front()
        ok, ctx, page = cho_dang_nhap(ctx, page, p)
        if not ok:
            ctx.close()
            return None
    return ctx, page


def khao_sat():
    """--khao-sat: đi một vòng cổng egov1, ghi lại cấu trúc để Claude hoàn thiện bộ đọc."""
    from playwright.sync_api import sync_playwright
    token = doc_config().get("github_token", "")
    with sync_playwright() as p:
        mo = _mo_cong_san_sang(p)
        if not mo:
            return 3
        ctx, page = mo
        try:
            noi = _egov_khao_sat_va_day(ctx, page, token)
        finally:
            ctx.close()
    telegram(f"Bot egov1: đã khảo sát cổng, kết quả ở {noi}. Báo Claude đọc để hoàn thiện bộ đọc.")
    return 0


# ---------------------------------------------------------------- VIỆC CHỜ XỬ LÝ trên egov1 (thay vOffice)
def _la_viec_cho(vb):
    """Trạng thái 'Chưa xử lý' / 'Chờ xử lý' / 'Đang xử lý' trong Văn bản đến = việc của Bạn còn mở."""
    tt = bo_dau(vb.get("trang_thai", ""))
    return tt.startswith(("chua", "cho ", "cho xu", "dang"))


def _egov_lay_viec(ctx, page, van_ban_den, luu_vao: Path, token, toi_da=EGOV_VIEC_TOI_DA, day_len=True):
    """Từ danh sách Văn bản đến đã quét: lọc việc còn mở, tải toàn văn + đính kèm của việc CHƯA lấy lần nào,
    ghi luu_vao/README.md (bảng mọi việc còn mở) + danh-sach.json, rồi đẩy lên theo-doi/viec-cho-xu-ly/<ngày>/."""
    luu_vao.mkdir(parents=True, exist_ok=True)
    viec = [v for v in van_ban_den if _la_viec_cho(v)]
    da_lay, sha_da = (_json_gh(REPO_TRI_THUC, f"{THU_MUC_VIEC}/_da-lay.json", token, {}) if token else ({}, None))
    ngay = date.today().isoformat()
    moi = 0
    for v in viec:
        khoa = f"{v['so_ky_hieu']}|{v['ngay_ban_hanh']}"
        if khoa in da_lay:
            v["tep"] = da_lay[khoa]
            continue
        if moi >= toi_da:
            v["tep"] = ""
            continue
        ten_goc = lam_sach_vn(v["so_ky_hieu"]) or f"vb-{v.get('id_data360x') or moi + 1}"
        try:
            pdf = _egov_tai_pdf(ctx, page, v)
            dinh_kem = _egov_tai_dinh_kem(ctx, page, v)
            luong = doc_luong_xu_ly(page)
        except Exception as e:
            log(f"  [việc] lỗi mở {v['so_ky_hieu']}: {e!r}")
            pdf, dinh_kem, luong = None, [], []
        vai, nguoi_xl, han_xl = suy_vai_tro(luong)
        ct = _egov_api_chi_tiet(page, v)
        v.update({k: ct[k] for k in ("but_phe", "linh_vuc_cong") if ct.get(k)})
        dau = [f"# {v['so_ky_hieu']} - {v['trich_yeu']}", "",
               f"- Vai trò của Bạn: **{v.get('vai_tro') or 'chưa rõ'}** | Người xử lý chính: {v.get('nguoi_xu_ly_chinh', '')}",
               f"- Ngày ban hành: {v['ngay_ban_hanh']} | Ngày nhận: {v.get('ngay_nhan', '')} | "
               f"Trạng thái trên egov1: {v.get('trang_thai', '')} | Cấp độ: {v.get('do_khan', '')}",
               f"- Cơ quan ban hành: {v.get('don_vi', '')} | Người ký: {v.get('nguoi_ky', '')}",
               f"- Bản gốc trên egov1: {v.get('url_chi_tiet', '')}"] + (
                   ["", "## Bút phê / chỉ đạo của lãnh đạo (egov1)", "", ct["but_phe"], ""] if ct.get("but_phe") else []
               ) + dong_luong_md(luong, vai, nguoi_xl, han_xl)
        goi, ten_chinh = dong_goi_ho_so(v, ten_goc, pdf, dinh_kem, dau)
        if not goi:
            (luu_vao / f"{ten_goc}.md").write_text("\n".join(dau) + "\n\n*(Không tải được tệp nào)*\n", encoding="utf-8")
            ten_chinh = f"{ten_goc}.md"
        for ten_t, du_lieu in goi:
            (luu_vao / ten_t).write_bytes(du_lieu)
        v["tep"] = f"{THU_MUC_VIEC}/{ngay}/{ten_chinh}"
        da_lay[khoa] = v["tep"]
        moi += 1
    dong = [f"# Việc chờ xử lý trên egov1 - {date.today().strftime('%d/%m/%Y')}", "",
            f"Văn bản đến có trạng thái Chưa/Chờ/Đang xử lý: **{len(viec)}** việc; lần này tải toàn văn {moi} việc mới.",
            "Claude: việc nào CHƯA có văn bản đi trả lời thì đọc toàn văn và soạn dự thảo; đã trả lời thì chỉ ghi nhận.", "",
            "| # | Số ký hiệu | Ngày nhận | Trạng thái | Vai trò | Người XLC | Cấp độ | Cơ quan ban hành | Trích yếu | Toàn văn |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    uu = lambda x: (0 if "xu ly chinh" in bo_dau(x.get("vai_tro", "")) else 1 if "phoi hop" in bo_dau(x.get("vai_tro", "")) else 2)
    for i, v in enumerate(sorted(sorted(viec, key=lambda x: _egov_ngay(x) or date.min, reverse=True), key=uu), 1):
        tep = f"`{v['tep']}`" if v.get("tep") else "*(để lượt sau)*"
        dong.append(f"| {i} | {v['so_ky_hieu']} | {v.get('ngay_nhan', '')} | {v.get('trang_thai', '')} | "
                    f"{v.get('vai_tro', '')} | {v.get('nguoi_xu_ly_chinh', '')} | "
                    f"{v.get('do_khan', '')} | {v.get('don_vi', '')} | {v['trich_yeu'].replace('|', '/')} | {tep} |")
    try:
        nv = _egov_nhiem_vu(page)
        (luu_vao / "nhiem-vu.md").write_text(_nhiem_vu_md(nv), encoding="utf-8")
        (luu_vao / "nhiem-vu.json").write_text(json.dumps(nv, ensure_ascii=False, indent=1), encoding="utf-8")
        o = {bo_dau(x["nhan"]): x["so"] for x in nv["o_dem"]}
        dong.insert(3, f"Quản lý nhiệm vụ: chờ xử lý {o.get('cho xu ly', '?')}, đang thực hiện {o.get('dang thuc hien', '?')}, "
                       f"đến hạn {o.get('den han', '?')}, quá hạn {o.get('qua han', o.get('da qua han', '?'))}, "
                       f"chờ duyệt {o.get('cho duyet', '?')} - chi tiết `nhiem-vu.md`.")
    except Exception as e:
        log("  [nhiệm vụ] không ghi được:", repr(e)[:120])
    (luu_vao / "README.md").write_text("\n".join(dong) + "\n", encoding="utf-8")
    (luu_vao / "danh-sach.json").write_text(json.dumps(viec, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[việc] {len(viec)} việc còn mở, tải mới {moi} việc -> {luu_vao}")
    if day_len and token:
        so = _day_thu_muc(token, luu_vao, f"{THU_MUC_VIEC}/{ngay}", f"Việc chờ xử lý egov1 {ngay}: {len(viec)} việc")
        try:
            gh_ghi(REPO_TRI_THUC, f"{THU_MUC_VIEC}/_da-lay.json",
                   json.dumps(da_lay, ensure_ascii=False, indent=1).encode(), f"Việc chờ xử lý egov1 {ngay}", token, sha_da)
        except Exception as e:
            log("  [việc] không ghi được _da-lay.json:", repr(e)[:120])
        log(f"[việc] đã đẩy {so} tệp lên vlncn-laocai/{THU_MUC_VIEC}/{ngay}/")
    return len(viec), moi


# ---------------------------------------------------------------- QUẢN LÝ NHIỆM VỤ trên egov1 (Bạn yêu cầu 29/10/2026)
# Ảnh 29/10/2026: /work/unit/main/1 có 11 ô đếm (Chờ xử lý, Đang thực hiện, Chờ duyệt, Chờ phê duyệt, Đến hạn, Đã quá hạn,
# Trả lại, Phối hợp, Phụ trách, Để biết, Đã hoàn thành); /home/default/1 có bảng "Nhiệm vụ UBND tỉnh giao / nội bộ"
# (tổng số, đang thực hiện còn hạn/quá hạn, đã hoàn thành đúng hạn/quá hạn). Bot chép các con số và, nếu bấm ô mở ra
# bảng, chép bảng đó; không bấm gì khác.
_JS_O_DEM = r"""() => {
  const thay = el => !!(el && (el.offsetWidth || el.offsetHeight));
  const ra = [];
  for (const el of document.querySelectorAll('div, a, li, section')) {
    if (!thay(el) || el.children.length < 1 || el.children.length > 6) continue;
    // nhãn và số có thể cách nhau bằng xuống dòng hoặc dính liền ("Chờ xử lý3") -> tách phần số ở cuối/đầu
    const t = (el.innerText || '').trim().split('\n').map(x => x.trim()).filter(Boolean);
    if (t.length < 1 || t.length > 4) continue;
    let so = t.find(x => /^\d{1,5}$/.test(x)), nhan = t.find(x => /^[^\d]*[A-Za-zÀ-ỹ]{3,}[^\d]*$/.test(x) && x.length < 40);
    if (!so || !nhan) {
      const m = t.join(' ').match(/^(\d{1,5})?\s*([^\d]{3,40}?)\s*(\d{1,5})?$/);
      if (m && (m[1] || m[3]) && !(m[1] && m[3])) { so = m[1] || m[3]; nhan = m[2].trim(); }
    }
    if (so && nhan && /[A-Za-zÀ-ỹ]{3,}/.test(nhan) && el.innerText.length < 80) {
      if (!ra.some(x => x.nhan === nhan)) ra.push({nhan, so: parseInt(so, 10)});
    }
  }
  return ra;
}"""
_JS_MOI_BANG = r"""() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const thay = el => !!(el && (el.offsetWidth || el.offsetHeight));
  const ra = [];
  for (const t of document.querySelectorAll('table')) {
    if (!thay(t)) continue;
    const heads = t.tHead ? Array.from(t.tHead.rows).flatMap(r => Array.from(r.cells).map(c => norm(c.innerText))).filter(Boolean) : [];
    const rows = [];
    for (const tb of Array.from(t.tBodies)) for (const tr of Array.from(tb.rows)) {
      const o = Array.from(tr.cells).map(c => norm(c.innerText));
      if (o.length >= 2 && o.some(Boolean)) rows.push(o);
    }
    if (heads.length >= 2 && rows.length) ra.push({heads, rows: rows.slice(0, 200)});
  }
  return ra;
}"""
# Ô bấm thử để lấy danh sách. KHÔNG có "Trả lại": trùng tên nút thao tác hồ sơ ở trang chi tiết nhiệm vụ (ảnh 29/10/2026:
# Giao xử lý / Trình duyệt / Trả lại / Dự thảo văn bản đi / Cập nhật tiến độ) - bot không bao giờ được bấm các nút đó.
O_DEM_MO = ("Chờ xử lý", "Đang thực hiện", "Đến hạn", "Đã quá hạn")


def _egov_nhiem_vu_api(page, kq):
    """Nhiệm vụ qua API (sạch hơn đọc ô đếm trên giao diện). Ghi vào kq, trả True nếu lấy được số đếm."""
    j = _egov_api(page, f"{EGOV_GATEWAY}/work/api/works/reminds/v1?workCreateType=0", "số đếm nhiệm vụ")
    if not isinstance(j, list):
        return False
    kq["o_dem"] = [{"nhan": NHAN_NHIEM_VU.get(x.get("code"), x.get("code")), "so": x.get("count") or 0, "ma": x.get("code")}
                   for x in j if isinstance(x, dict)]
    s = _egov_api(page, f"{EGOV_GATEWAY}/work/api/works/report/works-sumary?isHighestCompany=false", "nhiệm vụ của Sở")
    if isinstance(s, dict) and isinstance(s.get("value"), list):
        kq["tong_quan"] = [{"heads": ["Loại nhiệm vụ", "Tổng số", "Đang làm", "Đang làm - còn hạn", "Đang làm - quá hạn",
                                      "Đã hoàn thành", "Hoàn thành đúng hạn", "Hoàn thành quá hạn"],
                            "rows": [[str(x.get("title", "")), str(x.get("total", "")), str(x.get("workingTotal", "")),
                                      str(x.get("workingInTimeTotal", "")), str(x.get("workingOutTimeTotal", "")),
                                      str(x.get("completeTotal", "")), str(x.get("completeInTimeTotal", "")),
                                      str(x.get("completeOutTimeTotal", ""))] for x in s["value"]]}]
    q = _egov_api(page, f"{EGOV_GATEWAY}/ioffice/Ajax/IworkHandler.ashx?type=get_quyen_nhac_viec", "số đếm văn bản")
    if isinstance(q, dict) and isinstance(q.get("value"), dict):
        kq["dem_van_ban"] = {k: v for k, v in q["value"].items() if isinstance(v, int) and k.startswith("vb_")}
    dem = {o["ma"]: o["so"] for o in kq["o_dem"]}
    for ma in NV_LAY_DANH_SACH:
        if not dem.get(ma):
            continue
        d = _egov_api(page, f"{EGOV_GATEWAY}/work/api/works/v1?page=1&length=100&term=&archiveSearch=false&type={ma}"
                            f"&isLoading=true&defer=true&skip=0", f"nhiệm vụ {ma}")
        ds = (d or {}).get("data") if isinstance(d, dict) else None
        if not isinstance(ds, list):
            continue
        dong = []
        for x in ds:
            vb = (x.get("documentApis") or [{}])[0] if isinstance(x.get("documentApis"), list) else {}
            nguoi = [f"{u.get('fullName', '')} ({u.get('followRoleName', '')})" for u in (x.get("userApis") or [])
                     if isinstance(u, dict)][:4]
            ten = _lay(x, "content", "name", "title", "workName")
            han = _lay(x, "endDate", "deadline", "dueDate", "expiredDate", "toDate", "endTime")
            dong.append([re.sub(r"\s+", " ", str(ten or vb.get("abridgment", "")))[:200], _ngay_vn(han),
                         f"{vb.get('symbol', '')} - {vb.get('documentSentCompany', '')}".strip(" -"),
                         "; ".join(nguoi)])
        if dong:
            kq["danh_sach"][NHAN_NHIEM_VU.get(ma, ma)] = [{"heads": ["Nhiệm vụ", "Hạn", "Văn bản", "Người tham gia"],
                                                            "rows": dong}]
            log(f"  [nhiệm vụ] {NHAN_NHIEM_VU.get(ma, ma)}: {len(dong)} nhiệm vụ")
    return True


def _egov_nhiem_vu(page) -> dict:
    """Trả {"o_dem": [...], "tong_quan": [bảng], "danh_sach": {nhãn: [bảng]}, "luc": ...}."""
    kq = {"luc": datetime.now().isoformat(timespec="minutes"), "o_dem": [], "tong_quan": [], "danh_sach": {}}
    _egov_nghe_api(page)
    try:
        page.goto(EGOV_NHIEM_VU, wait_until="domcontentloaded", timeout=90000)
        _egov_bam(page, "Chờ xử lý", cho_giay=0)       # không bấm gì; chỉ chờ trang gọi API để nhận header
        page.wait_for_timeout(6000)
        if _egov_nhiem_vu_api(page, kq):
            log("  [nhiệm vụ] qua API: " + ", ".join(f"{o['nhan']} {o['so']}" for o in kq["o_dem"] if o["so"]))
            return kq
    except Exception as e:
        log("  [nhiệm vụ] API lỗi, đọc giao diện:", repr(e)[:120])
    try:
        page.goto(EGOV_TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4000)
        _egov_cho_bang(page, 30)
        kq["tong_quan"] = page.evaluate(_JS_MOI_BANG) or []
    except Exception as e:
        log("  [nhiệm vụ] tổng quan lỗi:", repr(e)[:120])
    try:
        page.goto(EGOV_NHIEM_VU, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4000)
        for _ in range(20):
            if not _egov_dang_tai(page):
                break
            page.wait_for_timeout(1500)
        kq["o_dem"] = page.evaluate(_JS_O_DEM) or []
        log(f"  [nhiệm vụ] {len(kq['o_dem'])} ô đếm: " + ", ".join(f"{o['nhan']} {o['so']}" for o in kq["o_dem"][:12]))
        for nhan in O_DEM_MO:
            o = next((x for x in kq["o_dem"] if bo_dau(x["nhan"]) == bo_dau(nhan)), None)
            if not o or not o["so"]:
                continue
            if not _egov_bam(page, nhan):
                continue
            page.wait_for_timeout(3000)
            for _ in range(30):
                if not _egov_dang_tai(page):
                    break
                page.wait_for_timeout(1500)
            bang = [b for b in (page.evaluate(_JS_MOI_BANG) or []) if len(b["rows"]) <= max(o["so"] * 2, 10)]
            if bang:
                kq["danh_sach"][nhan] = bang
                log(f"  [nhiệm vụ] {nhan}: {sum(len(b['rows']) for b in bang)} dòng")
            page.goto(EGOV_NHIEM_VU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3000)
    except Exception as e:
        log("  [nhiệm vụ] lỗi:", repr(e)[:120])
    return kq


def _nhiem_vu_md(nv) -> str:
    dong = [f"# Nhiệm vụ trên egov1 - {date.today().strftime('%d/%m/%Y')} (đọc lúc {nv['luc'][11:]})", ""]
    if nv["o_dem"]:
        dong += ["## Ô đếm ở Quản lý nhiệm vụ", "", "| Mục | Số |", "|---|---|"]
        dong += [f"| {o['nhan']} | {o['so']} |" for o in nv["o_dem"]]
        dong.append("")
    for b in nv["tong_quan"]:
        dong += ["## Tổng quan (trang chủ)", "", "| " + " | ".join(b["heads"]) + " |", "|" + "---|" * len(b["heads"])]
        dong += ["| " + " | ".join(x.replace("|", "/") for x in r) + " |" for r in b["rows"]]
        dong.append("")
    for nhan, bangs in nv["danh_sach"].items():
        dong.append(f"## {nhan}")
        for b in bangs:
            dong += ["", "| " + " | ".join(b["heads"]) + " |", "|" + "---|" * len(b["heads"])]
            dong += ["| " + " | ".join(x.replace("|", "/") for x in r) + " |" for r in b["rows"]]
        dong.append("")
    if nv.get("dem_van_ban"):
        dong += ["## Số đếm văn bản (egov1)", "", "| Mục | Số |", "|---|---|"]
        dong += [f"| {k[3:].replace('_', ' ')} | {v} |" for k, v in nv["dem_van_ban"].items() if v]
        dong.append("")
    if not nv["o_dem"] and not nv["tong_quan"]:
        dong.append("*(Không đọc được ô đếm hay bảng nào - xem khảo sát theo-doi/egov/soi/)*")
    return "\n".join(dong) + "\n"


def viec_cho_xu_ly(luu_vao=None, so_ngay=30, toi_da=EGOV_VIEC_TOI_DA, day_len=True):
    """--viec: lấy việc chờ xử lý trên egov1 (thay vOffice), tải toàn văn, đẩy lên kho riêng tư."""
    from playwright.sync_api import sync_playwright
    if HE_THONG != "egov":
        log("Việc chờ xử lý chỉ có trên egov1 (config he_thong đang là", HE_THONG, ")")
        return 2
    token = doc_config().get("github_token", "")
    luu_vao = Path(luu_vao or (BOT_HOME / "ket-qua" / "viec" / date.today().isoformat()))
    with sync_playwright() as p:
        mo = _mo_cong_san_sang(p)
        if not mo:
            return 3
        ctx, page = mo
        try:
            den = _egov_quet_danh_sach(page, "den", date.today() - timedelta(days=so_ngay), tra_cuu=False)
            if den is None:
                return 3
            tong, moi = _egov_lay_viec(ctx, page, den, luu_vao, token, toi_da, day_len)
        finally:
            ctx.close()
    telegram(f"Bot egov1: {tong} việc chờ xử lý, tải mới {moi} việc.")
    return 0


# ---------------------------------------------------------------- BÊ VĂN BẢN CŨ (Bạn yêu cầu 30/10/2026)
# "Tôi muốn bê hết văn bản cũ sang kho mới": kho kho-van-ban-sct (28/9/2026) chưa từng được tạo, danh mục thời
# Data360X có 3.334 văn bản nhưng chỉ 226 văn bản có toàn văn. Chế độ --lay-lui chạy ĐÊM (TAY gọi 22:15), đi lùi
# trong tab Tra cứu của egov1 (cổng đã chuyển cả văn bản thời Data360X sang), mở từng văn bản chưa có toàn văn,
# lấy CHỮ đẩy lên kho riêng tư (theo-doi/<năm ban hành>/<số>.md + danh-muc-<năm>.json) để plugin van-ban-sct-vn
# mang vào mọi phiên chat. Tệp gốc (PDF, Word...) KHÔNG đẩy lên GitHub (vài chục GB, vượt sức kho) mà cất trên máy.
LAY_LUI_TU_NGAY = date(2025, 1, 1)
LAY_LUI_GIO = 6.5               # mặc định chạy tối đa 6,5 giờ/lượt (22:15 -> 04:45, trước lượt việc 05:50)
LAY_LUI_MOI_COMMIT = 40         # đẩy một commit sau mỗi 40 văn bản (hoặc 30 phút) - không làm Vercel/Actions quá tải
LAY_LUI_LIET_KE_LAI_NGAY = 7    # danh sách Tra cứu đọc lại sau 7 ngày (văn bản mới đã có lượt quét ngày lo)
LAY_LUI_TRANG_API = 400         # 400 trang x 200 dòng = 80.000 dòng mỗi chiều đến/đi
LAY_LUI_CHUA_DOC_NGAY = 30      # văn bản đến CHƯA ĐỌC nhận trong 30 ngày gần đây: không mở (giữ dấu chưa đọc cho Bạn)
LAY_LUI_BO_DOC = 2               # tăng khi sửa bộ đọc danh sách -> danh sách lưu trên máy đọc lại ngay (30/10/2026: API POST)
LAY_LUI_DIA_TRONG_GB = 20       # ổ còn dưới 20 GB thì không cất tệp gốc nữa, chỉ lấy chữ


def _lay_lui_kho_goc() -> Path:
    """Nơi cất tệp gốc trên máy: config "kho_tep_goc", không thì OneDrive "Kho van ban SCT" (Bạn chốt 28/9/2026),
    không thì <du-an>/kho-van-ban."""
    cfg = doc_config().get("kho_tep_goc", "")
    if cfg:
        return Path(cfg)
    for od in (os.environ.get("OneDrive"), os.environ.get("OneDriveConsumer"), str(Path.home() / "OneDrive")):
        if od and Path(od).is_dir():
            return Path(od) / "Kho van ban SCT"
    return BOT_HOME.parent / "kho-van-ban"


def _lay_lui_khoa(vb):
    return f"{vb.get('so_ky_hieu', '')}|{vb.get('ngay_ban_hanh', '')}"


def _lay_lui_doc_trang_thai(tep: Path) -> dict:
    try:
        d = json.loads(tep.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _lay_lui_liet_ke(page, tu_ngay) -> dict:
    """Đọc toàn bộ danh sách Tra cứu đến/đi từ tu_ngay (API 200 dòng/lượt, tối đa LAY_LUI_TRANG_API trang)."""
    global EGOV_API_TRANG_TOI_DA
    cu, EGOV_API_TRANG_TOI_DA = EGOV_API_TRANG_TOI_DA, LAY_LUI_TRANG_API
    ra = {}
    try:
        for nguon in ("den", "di"):
            _EGOV_API["moi"] = None; _EGOV_API["resp"] = []
            ds = _egov_quet_danh_sach(page, nguon, tu_ngay, tra_cuu=True)
            if ds is None:
                return {}
            ra[nguon] = [{k: v for k, v in vb.items() if k != "bytes"} for vb in ds]
            log(f"  [bê văn bản cũ] danh sách {'đến' if nguon == 'den' else 'đi'}: {len(ds)} văn bản từ "
                f"{tu_ngay.strftime('%d/%m/%Y')}")
    finally:
        EGOV_API_TRANG_TOI_DA = cu
    return ra


def _lay_lui_day(cho_ghi: dict, muc_moi: dict, token, ghi_chu) -> int:
    """Một commit: các .md + danh-muc-<năm>.json (đọc LẠI bản mới nhất trên GitHub rồi trộn, để không đè mục lượt
    quét ngày vừa ghi)."""
    if not cho_ghi and not muc_moi:
        return 0
    tep = dict(cho_ghi)
    for nam, muc in muc_moi.items():
        duong = f"{THU_MUC_TRI_THUC}/danh-muc-{nam}.json"
        dm, _ = _json_gh(REPO_TRI_THUC, duong, token, [])
        vi_tri = {_lay_lui_khoa(m): i for i, m in enumerate(dm)}
        for m in muc.values():
            i = vi_tri.get(_lay_lui_khoa(m))
            if i is None:
                dm.append(m)
            elif not dm[i].get("tep"):
                dm[i].update({k: v for k, v in m.items() if v not in ("", None, [])})
        tep[duong] = json.dumps(dm, ensure_ascii=False, indent=1).encode()
    so = gh_mot_commit(REPO_TRI_THUC, tep, f"Bê văn bản cũ egov1: {ghi_chu}", token)
    cho_ghi.clear()
    muc_moi.clear()
    return so


def lay_lui(tu_ngay=None, so_gio=LAY_LUI_GIO, toi_da=None, moi_vong=None):
    """--lay-lui: bê văn bản cũ trên egov1 vào kho riêng tư (chữ) + máy (tệp gốc). Chạy nhiều đêm, nhớ chỗ đã làm.
    moi_vong: hàm gọi trước mỗi văn bản; trả True thì dừng sớm (TAY nhường cho yêu cầu Bạn/Claude vừa gửi)."""
    from playwright.sync_api import sync_playwright
    if HE_THONG != "egov":
        log("Bê văn bản cũ chỉ chạy trên egov1 (config he_thong đang là", HE_THONG, ")")
        return 2
    tu_ngay = tu_ngay or LAY_LUI_TU_NGAY
    het_luc = time.time() + so_gio * 3600
    token = doc_config().get("github_token", "")
    if not token:
        log("Chưa có github_token trong config.json")
        return 2
    tt_tep = BOT_HOME / "lay-lui.json"
    tt = _lay_lui_doc_trang_thai(tt_tep)
    xong = tt.setdefault("xong", {})               # khóa -> đường dẫn .md | "mat" | "loi: ..."
    kho_goc = _lay_lui_kho_goc()
    try:
        cat_goc = shutil.disk_usage(kho_goc.anchor or str(kho_goc)).free > LAY_LUI_DIA_TRONG_GB * 1024 ** 3
    except Exception:
        cat_goc = False
    log(f"[bê văn bản cũ] từ {tu_ngay.strftime('%d/%m/%Y')}, tối đa {so_gio} giờ; tệp gốc "
        + (f"cất ở {kho_goc}" if cat_goc else "KHÔNG cất (ổ gần đầy hoặc không ghi được) - chỉ lấy chữ"))
    # Văn bản đã có toàn văn trên kho (lượt quét ngày, lượt trước) thì bỏ qua
    co_tep, ten_da_dung = set(), set()
    for nam in range(tu_ngay.year, date.today().year + 1):
        dm, _ = _json_gh(REPO_TRI_THUC, f"{THU_MUC_TRI_THUC}/danh-muc-{nam}.json", token, [])
        for m in dm:
            if m.get("tep"):
                co_tep.add(_lay_lui_khoa(m))
                ten_da_dung.add(m["tep"].rsplit(".", 1)[0])
    da_lam = moi = loi = 0
    hang = []
    with sync_playwright() as p:
        mo = _mo_cong_san_sang(p)
        if not mo:
            return 3
        ctx, page = mo
        try:
            ds = tt.get("danh_sach") or {}
            luc = tt.get("liet_ke_luc", "")
            if not ds or not luc or (datetime.now() - datetime.fromisoformat(luc)).days >= LAY_LUI_LIET_KE_LAI_NGAY \
                    or tt.get("tu_ngay") != tu_ngay.isoformat() or tt.get("bo_doc") != LAY_LUI_BO_DOC:
                ds = _lay_lui_liet_ke(page, tu_ngay)
                if not ds:
                    log("[bê văn bản cũ] không đọc được danh sách Tra cứu - dừng")
                    return 3
                for kk in [kk for kk, v in xong.items() if str(v).startswith("loi")]:
                    xong.pop(kk)                    # danh sách mới: thử lại các văn bản lần trước không tải được
                tt.update(danh_sach=ds, liet_ke_luc=datetime.now().isoformat(timespec="minutes"),
                          tu_ngay=tu_ngay.isoformat(), bo_doc=LAY_LUI_BO_DOC)
                tt_tep.write_text(json.dumps(tt, ensure_ascii=False), encoding="utf-8")
                # Đẩy NGAY mục lục đầy đủ (số, ngày, trích yếu... chưa có toàn văn) để mọi phiên chat thống kê, tra
                # được cả năm mà không phải chờ bot mở từng văn bản (vụ 30/10/2026: rà soát VTVL cần 12 tháng).
                muc_ds = {}
                for vbs in ds.values():
                    for vb in vbs:
                        n = (parse_ngay(vb.get("ngay_ban_hanh")) or _egov_ngay(vb) or date.today()).year
                        muc_ds.setdefault(n, {})[_lay_lui_khoa(vb)] = {
                            **{x: vb.get(x, "") for x in ("so_ky_hieu", "ngay_ban_hanh", "ngay_nhan", "trich_yeu",
                                                          "don_vi", "nguoi_ky", "loai", "nguon", "url_chi_tiet",
                                                          "trang_thai", "vai_tro", "nguoi_xu_ly_chinh")},
                            "linh_vuc": xep_linh_vuc(vb), "gom_luc": date.today().isoformat()}
                try:
                    _lay_lui_day({}, muc_ds, token, f"mục lục {sum(len(v) for v in muc_ds.values())} văn bản từ "
                                                    f"{tu_ngay.strftime('%d/%m/%Y')}")
                except Exception as e:
                    log("  [bê văn bản cũ] đẩy mục lục lỗi:", str(e)[:150])
            han_chua_doc = date.today() - timedelta(days=LAY_LUI_CHUA_DOC_NGAY)
            hang = []
            for nguon, vbs in ds.items():
                for vb in vbs:
                    k = _lay_lui_khoa(vb)
                    if k in co_tep or k in xong or _egov_la_mat(vb):
                        continue
                    if nguon == "den" and str(vb.get("da_xem")) == "0" and (_egov_ngay(vb) or date.min) >= han_chua_doc:
                        continue
                    hang.append(vb)
            # Văn bản thuộc lĩnh vực của Bạn trước, rồi mới tới văn bản khác; trong mỗi nhóm mới trước cũ sau
            hang.sort(key=lambda v: (not xep_linh_vuc(v), -((_egov_ngay(v) or date.min).toordinal())))
            log(f"[bê văn bản cũ] còn {len(hang)} văn bản chưa có toàn văn "
                f"({sum(1 for v in hang if xep_linh_vuc(v))} thuộc lĩnh vực của Bạn); đã xong các lượt trước: {len(xong)}")
            cho_ghi, muc_moi, lan_day = {}, {}, time.time()
            for vb in hang:
                if time.time() > het_luc or (toi_da and da_lam >= toi_da):
                    break
                if moi_vong and moi_vong():
                    log("[bê văn bản cũ] có yêu cầu mới trong hàng đợi - dừng để TAY làm yêu cầu đó, lát nữa làm tiếp")
                    break
                da_lam += 1
                k = _lay_lui_khoa(vb)
                nam = (parse_ngay(vb.get("ngay_ban_hanh")) or _egov_ngay(vb) or date.today()).year
                ten_goc = lam_sach_vn(vb["so_ky_hieu"]) or f"vb-{vb.get('id_data360x') or 'khong-so'}"
                thu_muc = f"{THU_MUC_TRI_THUC}/{nam}"
                if f"{thu_muc}/{ten_goc}" in ten_da_dung:      # trùng tên với văn bản khác: thêm mã/ngày
                    ten_goc += "_" + (str(vb.get("id_data360x") or "")[:12] or lam_sach_vn(vb["ngay_ban_hanh"]))
                try:
                    pdf = tai_pdf(ctx, page, vb)
                    dinh_kem = tai_dinh_kem(ctx, page, vb)
                except Exception as e:
                    log(f"  [bê văn bản cũ] lỗi mở {vb['so_ky_hieu']}: {e!r}"[:200])
                    pdf, dinh_kem = None, []
                if can_dang_nhap(page):
                    log("[bê văn bản cũ] phiên egov1 hết - dừng, lượt sau làm tiếp")
                    da_lam -= 1
                    break
                if not pdf and not any(d.get("bytes") for d in dinh_kem):
                    xong[k] = "loi: không tải được tệp"
                    loi += 1
                    continue
                ct = _egov_api_chi_tiet(page, vb)
                linh_vuc = xep_linh_vuc(vb)
                dau = [f"# {vb['so_ky_hieu']} - {vb['trich_yeu']}", "",
                       f"- Ngày ban hành: {vb['ngay_ban_hanh']}"
                       + (f" | Ngày nhận: {vb['ngay_nhan']}" if vb.get("ngay_nhan") else ""),
                       f"- Nguồn: văn bản {'đến' if vb['nguon'] == 'den' else 'đi'}"
                       f" | Đơn vị: {vb.get('don_vi', '')} | Người ký: {vb.get('nguoi_ky', '')}",
                       f"- Lĩnh vực: {', '.join(linh_vuc)}",
                       f"- Bản gốc trên {TEN_HE_THONG}: {vb.get('url_chi_tiet', '')}"]
                if ct.get("but_phe"):
                    dau += ["", "## Bút phê, chỉ đạo trên egov1", ""] + [f"> {x}" for x in ct["but_phe"].splitlines()]
                dau += ["", "> Chữ dưới đây lấy từ lớp text của PDF. Số và ngày ở trường ký số có thể "
                        "không nằm trong lớp text - lấy theo các dòng trên, hoặc mở bản gốc."]
                goi, ten_chinh = dong_goi_ho_so(vb, ten_goc, pdf, dinh_kem, dau)
                md = [(t, b) for t, b in goi if t.lower().endswith(".md")]
                if not any(t == ten_goc + ".md" for t, _ in md):      # bản scan không chữ: vẫn có trang mục lục
                    md.append((ten_goc + ".md", ("\n".join(dau) + "\n\n*(Bản scan, không có lớp chữ. Tệp gốc: "
                               + (f"{kho_goc}\\{nam}\\{ten_chinh}" if cat_goc else "mở trên egov1") + ")*\n").encode()))
                for t, b in md:
                    cho_ghi[f"{thu_muc}/{t}"] = b
                if cat_goc:
                    try:
                        (kho_goc / str(nam)).mkdir(parents=True, exist_ok=True)
                        for t, b in goi:
                            if not t.lower().endswith(".md"):
                                (kho_goc / str(nam) / t).write_bytes(b)
                    except Exception as e:
                        log("  [bê văn bản cũ] không cất được tệp gốc:", str(e)[:120])
                duong = f"{thu_muc}/{ten_goc}.md"
                ten_da_dung.add(f"{thu_muc}/{ten_goc}")
                muc_moi.setdefault(nam, {})[k] = {
                    **{x: vb.get(x, "") for x in ("so_ky_hieu", "ngay_ban_hanh", "trich_yeu", "don_vi", "nguoi_ky",
                                                  "loai", "nguon", "url_chi_tiet")},
                    "loai": vb.get("loai") or ct.get("loai", ""), "linh_vuc": linh_vuc,
                    "gom_luc": date.today().isoformat(), "tep": duong, "lay_lui": True}
                xong[k] = duong
                moi += 1
                if moi % LAY_LUI_MOI_COMMIT == 0 or time.time() - lan_day > 1800:
                    try:
                        _lay_lui_day(cho_ghi, muc_moi, token, f"+{moi} văn bản (tới {vb['ngay_ban_hanh']})")
                        lan_day = time.time()
                        tt_tep.write_text(json.dumps(tt, ensure_ascii=False), encoding="utf-8")
                    except Exception as e:
                        log("  [bê văn bản cũ] đẩy lên GitHub lỗi, giữ lại đẩy lần sau:", str(e)[:150])
                if da_lam % 10 == 0:
                    log(f"  [bê văn bản cũ] {da_lam}/{len(hang)}: mới {moi}, lỗi {loi}")
            # Lượt đẩy cuối (kể cả phần còn lại khi dừng vì hết giờ hay hết phiên)
            try:
                _lay_lui_day(cho_ghi, muc_moi, token, f"tổng {moi} văn bản lượt {date.today().strftime('%d/%m/%Y')}")
            except Exception as e:
                log("  [bê văn bản cũ] đẩy lên GitHub lỗi:", str(e)[:150])
                for kk in [kk for kk, v in xong.items() if v in cho_ghi]:
                    xong.pop(kk, None)              # chưa lên kho thì lượt sau làm lại
        finally:
            tt_tep.write_text(json.dumps(tt, ensure_ascii=False), encoding="utf-8")
            ctx.close()
    con = max(0, len(hang) - da_lam)
    tt.update(lan_cuoi=datetime.now().isoformat(timespec="minutes"), lan_cuoi_moi=moi, con_lai=con)
    tt_tep.write_text(json.dumps(tt, ensure_ascii=False), encoding="utf-8")
    log(f"[bê văn bản cũ] xong lượt: mở {da_lam}, lấy được {moi}, lỗi {loi}, còn khoảng {con} văn bản")
    telegram(f"Bot egov1 bê văn bản cũ: thêm {moi} văn bản vào kho, còn khoảng {con}.")
    return 0


HE_THONG = "data360x"
TEN_HE_THONG = "Data360X"


def chon_he_thong(ten=None):
    """Chọn cổng bot làm việc. Mặc định egov1 (từ 29/10/2026); 'data360x' giữ nguyên bộ đọc cũ.
    Gán lại các hàm theo cổng ở cấp module nên mọi nơi gọi (chay_chinh, lay_theo_yeu_cau, tim_van_ban, tay.py)
    tự dùng bộ đọc đúng mà không phải sửa từng chỗ."""
    global HE_THONG, TEN_HE_THONG, GOC_WEB, TRANG_CHU, TRANG
    global quet_danh_sach, tai_pdf, tai_dinh_kem, tim_tren_cong, can_dang_nhap
    try:
        cfg_ten = doc_config().get("he_thong", "")
    except Exception:
        cfg_ten = ""
    ten = (ten or os.environ.get("BOT_HE_THONG") or cfg_ten or "egov").strip().lower()
    if ten.startswith("data360"):
        HE_THONG, TEN_HE_THONG = "data360x", "Data360X"
        GOC_WEB, TRANG_CHU, TRANG = _D360["GOC_WEB"], _D360["TRANG_CHU"], _D360["TRANG"]
        quet_danh_sach, tai_pdf, tai_dinh_kem, tim_tren_cong, can_dang_nhap = _D360["ham"]
    else:
        HE_THONG, TEN_HE_THONG = "egov", "egov1"
        GOC_WEB, TRANG_CHU = EGOV_GOC, EGOV_DS_DEN
        TRANG = {"den": EGOV_DS_DEN, "di": _egov_trang_da_do().get("di", "")}
        quet_danh_sach, tai_pdf, tai_dinh_kem = _egov_quet_danh_sach, _egov_tai_pdf, _egov_tai_dinh_kem
        tim_tren_cong, can_dang_nhap = _egov_tim_tren_cong, _egov_can_dang_nhap
    return HE_THONG


_D360 = {"GOC_WEB": GOC_WEB, "TRANG_CHU": TRANG_CHU, "TRANG": dict(TRANG),
         "ham": (quet_danh_sach, tai_pdf, tai_dinh_kem, tim_tren_cong, can_dang_nhap)}


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
    ap.add_argument("--he-thong", choices=["egov", "data360x"],
                    help="cổng làm việc (mặc định egov1 từ 29/10/2026; hoặc config.json he_thong)")
    ap.add_argument("--khao-sat", action="store_true",
                    help="(egov1) đi một vòng cổng, ghi HTML/ảnh/API lên kho riêng tư để hoàn thiện bộ đọc")
    ap.add_argument("--viec", action="store_true",
                    help="(egov1) lấy việc Chưa/Chờ/Đang xử lý trong Văn bản đến, tải toàn văn, đẩy lên kho riêng tư")
    ap.add_argument("--lay-lui", action="store_true",
                    help="(egov1) bê văn bản cũ: đi lùi trong Tra cứu, lấy toàn văn văn bản chưa có lên kho riêng tư (chạy đêm)")
    ap.add_argument("--tu-ngay", help="(--lay-lui) lấy từ ngày dd/mm/yyyy (mặc định 01/01/2025)")
    ap.add_argument("--gio", type=float, default=LAY_LUI_GIO, help="(--lay-lui) chạy tối đa bao nhiêu giờ")
    ap.add_argument("--gom-toi-da", type=int, default=TOI_DA_PDF_MOI_LUOT,
                    help=f"tối đa bao nhiêu tệp tri thức tải về mỗi lượt (mặc định {TOI_DA_PDF_MOI_LUOT})")
    a = ap.parse_args()
    tat_quick_edit()
    if a.he_thong:
        chon_he_thong(a.he_thong)
    log(f"Cổng làm việc: {TEN_HE_THONG} ({GOC_WEB})")
    try:
        if a.kiem_tra_token:
            return kiem_tra_token()
        if a.dang_nhap:
            return dang_nhap_lan_dau()
        if a.giu_phien:
            return giu_phien()
        if a.xuat_phien:
            return xuat_phien()
        if a.khao_sat:
            return khao_sat()
        if a.lay_lui:
            return lay_lui(parse_ngay(a.tu_ngay or ""), so_gio=a.gio)
        if a.viec:
            return viec_cho_xu_ly(None if a.luu == "kem-theo" else a.luu, so_ngay=a.ngay or 30)
        if a.lay:
            # "@đường/dẫn.txt" = đọc yêu cầu từ tệp UTF-8 (workflow ghi ra, để chữ Việt không vỡ qua cmd Windows)
            yeu_cau = Path(a.lay[1:]).read_text(encoding="utf-8-sig") if a.lay.startswith("@") else a.lay
            yeu_cau = yeu_cau or os.environ.get("YEU_CAU", "")      # workflow đưa qua biến môi trường
            return lay_theo_yeu_cau(yeu_cau, a.luu, so_ngay=a.ngay or 60, online=a.online)
        if a.tim:
            d = json.loads(Path(a.tim).read_text(encoding="utf-8"))
            can = [{"so_ky_hieu": v["so_ky_hieu"], "ngay": (v.get("ngay") or [""])[0]}
                   for v in d.get("vien_dan", d if isinstance(d, list) else [])]
            return tim_van_ban(can, a.luu, online=a.online)
        return chay_chinh(soi=a.soi, so_ngay=a.ngay, online=a.online,
                          gom=not a.khong_gom, gom_toi_da=a.gom_toi_da)
    except Exception as e:
        log("LỖI:", repr(e))
        telegram(f"Bot {TEN_HE_THONG} lỗi: {e!r}")
        return 1


chon_he_thong()

if __name__ == "__main__":
    sys.exit(main())

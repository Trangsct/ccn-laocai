# -*- coding: utf-8 -*-
"""
TAY - tiến trình duy nhất chạy trên máy ở Lào Cai, cánh tay của Claude (Bạn chốt 30/9/2026, Giai đoạn 1).

Thay cho: GitHub runner (phải đăng ký, hay rớt), Task Scheduler 18h, lượt online (cổng chặn máy chủ nước
ngoài) và 5 workflow chạy trên máy. TAY tự kéo việc từ GitHub, không có gì để "already configured".

Vòng lặp mỗi CHU_KY phút:
  1. tự cập nhật: tay.py và bot-data360x.py trên main đổi thì tải về rồi khởi động lại chính mình
  2. việc theo lịch (giờ Việt Nam, tính trên máy). Cổng mặc định egov1.laocai.gov.vn từ 29/10/2026
     (Data360X nếu config.json "he_thong": "data360x"):
       - giữ phiên mỗi giờ 07-17h thứ Hai-Bảy (Chrome thu nhỏ ~20 giây)
       - SÁNG SỚM 05:50 thứ Hai-Sáu (Bạn yêu cầu 29/10/2026: "7h30 có bản tin, máy chạy trong đêm"): việc chờ xử lý
         (Văn bản đến Chưa/Chờ/Đang xử lý -> toàn văn vào theo-doi/viec-cho-xu-ly/<ngày>/, thay vOffice) rồi quét 7 ngày;
         Routine Claude 07:03 đọc và ra bản tin trước 07:30. Máy phải bật qua đêm (TAY chạy ẩn).
       - quét 30 ngày thứ Tư từ 11:30, hoặc bất cứ lúc nào trong giờ làm việc nếu đã quá 7 ngày chưa quét
       - quét 7 ngày mỗi chiều thứ Hai-Sáu từ 16:30 -> Routine Claude 21:07 nâng cấp plugin
       - mỗi đêm 22:15 -> 05:30 (cả cuối tuần): bê văn bản cũ trên egov1 vào kho (bot --lay-lui, 30/10/2026)
  3. hàng đợi yêu cầu: kho riêng tư vlncn-laocai, thư mục yeu-cau/*.json, trang_thai "cho" -> nhận (ghi
     "dang" bằng sha cũ, hai máy không tranh nhau) -> làm -> đẩy kết quả -> ghi "xong"/"loi"
  4. nhịp tim trang-thai/tay.json (nhiều nhất mỗi giờ một lần, và ngay sau mỗi việc)

Tệp yêu cầu (Claude hoặc workflow yeu-cau.yml ghi):
  {"loai": "lay",  "yeu_cau": "5511/SCT-CN; tiêu chí lựa chọn chủ đầu tư", "ngay": 60, "luu": "theo-doi/yeu-cau/<ten>"}
  {"loai": "tim",  "ho_so": "<thư mục trong du-thao/>"}          # tìm văn bản viện dẫn của dự thảo
  {"loai": "quet", "ngay": 30}
  {"loai": "viec", "ngay": 30}                                     # việc chờ xử lý trên egov1
  {"loai": "khao-sat"}                                             # ghi cấu trúc egov1 lên theo-doi/egov/soi/
  {"loai": "lay-lui", "tu_ngay": "01/01/2025"}                     # bê văn bản cũ (mặc định chạy mỗi đêm 22:15-05:30)
  {"loai": "giu-phien"}
  {"loai": "lich-lanh-dao"}                                        # tải Lịch Lãnh đạo Sở (tự chạy 06:20 thứ Hai–Sáu)
  {"loai": "nhat-ky", "ly_do": "..."}                              # đẩy đuôi nhật ký lên theo-doi/tay/nhat-ky/ (09/11/2026)
  {"loai": "ket-thuc-nv", "viec": [{"id": "<workId>", "so": "<số ký hiệu>"}], "y_kien": "..."}  # Bạn cho phép 05/11/2026
  {"loai": "phoi-hop", "toi_da": 3, "chup_anh": 3}                 # ô Phối hợp: tải rồi bấm Hoàn thành phối hợp (11/11/2026)
  {"loai": "phoi-hop", "bat_lich": true}                           # Bạn duyệt lượt thử -> làm hết, bật lịch hằng sáng
Kết quả về đúng thư mục "luu" trong kho riêng tư (README.md + .md/.pdf), tệp yêu cầu được cập nhật
trang_thai, may, luc, tom_tat.

Chạy: python tay.py                  vòng lặp vô hạn (Task Scheduler gọi qua tay-an.vbs, cửa sổ ẩn)
      python tay.py --mot-lan         một vòng rồi thoát (chạy tay để thử)
      python tay.py --chay-thu        không cần token, không ghi GitHub, không mở Chrome: kiểm tra
                                      nạp được bot, lịch, phân tích yêu cầu mẫu (máy ảo Windows dùng)
Nguyên tắc giữ nguyên: không tự đăng nhập, không giải captcha; kho công khai không chứa hồ sơ nội bộ;
không bịa số/ngày/tên (phần đọc hiểu là của Claude, TAY chỉ chép).
"""

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import os
import socket
import subprocess
import sys
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

# Console Windows mặc định cp1252 không in được tiếng Việt (máy ảo Windows 29/9/2026 bắt được);
# pythonw không có console (stdout = None) thì bỏ qua.
for _luong in (sys.stdout, sys.stderr):
    try:
        _luong.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CHU_KY_PHUT = 10
PHIEN_BAN = "0.4.16 (11/11/2026)"
OWNER = "Trangsct"
KHO_MA = "ccn-laocai"          # công khai: tay.py, bot-data360x.py
KHO_VIEC = "vlncn-laocai"      # riêng tư: yeu-cau/, theo-doi/, trang-thai/
TEP_MA = {"tay.py": "tay/tay.py", "bot-data360x.py": "scripts/bot-data360x.py"}
GIU_LOG_NGAY = 14
QUET_QUA_HAN_NGAY = 7


def goc_du_an() -> Path:
    r"""Thư mục du-an ĐÃ CÓ sẵn trên ổ D/E/F/G, không thì C:\du-an (cùng quy ước với bot)."""
    goc = Path(r"C:\du-an")
    for o in "DEFG":
        if Path(f"{o}:\\du-an").is_dir():
            goc = Path(f"{o}:\\du-an")
    return goc


ROOT = Path(os.environ.get("TAY_ROOT") or goc_du_an())
BOT_DIR = ROOT / "bot"
BOT_HOME = Path(os.environ.get("BOT_HOME") or (ROOT / "bot-profile"))
LOG_DIR = BOT_HOME / "logs"
TRANG_THAI = BOT_HOME / "tay-trang-thai.json"      # lần giữ phiên / quét / nhịp tim gần nhất (trên máy)
KHOA = BOT_HOME / "tay.lock"
os.environ.setdefault("BOT_HOME", str(BOT_HOME))

_log_f = None


def log(*a):
    global _log_f
    s = datetime.now().strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    try:
        if _log_f is None or getattr(_log_f, "ngay", None) != date.today():
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            _log_f = open(LOG_DIR / f"tay-{date.today().isoformat()}.log", "a", encoding="utf-8")
            _log_f.ngay = date.today()
        _log_f.write(s + "\n")
        _log_f.flush()
    except Exception:
        pass


def don_log():
    """Giữ log 14 ngày (tay-*.log và *.log của bot) để không tốn dung lượng máy."""
    han = date.today() - timedelta(days=GIU_LOG_NGAY)
    for f in LOG_DIR.glob("*.log"):
        try:
            ngay = date.fromisoformat(f.stem.replace("tay-", "")[-10:])
            if ngay < han:
                f.unlink()
        except Exception:
            pass


# ---------------------------------------------------------------- nạp bot làm thư viện
def nap_bot():
    """bot-data360x.py có dấu gạch ngang nên nạp bằng importlib; mọi hàm vào Data360X dùng lại từ đó."""
    duong = BOT_DIR / "bot-data360x.py"
    if not duong.exists():
        duong = Path(__file__).resolve().parent.parent / "scripts" / "bot-data360x.py"   # chạy trong kho mã
    spec = importlib.util.spec_from_file_location("botd", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- trạng thái trên máy
def doc_trang_thai() -> dict:
    try:
        return json.loads(TRANG_THAI.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ghi_trang_thai(**kv):
    d = doc_trang_thai()
    d.update(kv)
    TRANG_THAI.parent.mkdir(parents=True, exist_ok=True)
    TRANG_THAI.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return d


def sha_git(duong: Path) -> str:
    """SHA blob kiểu git của một tệp, để so với trường sha của GitHub Contents API mà không cần tải."""
    b = duong.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


# ---------------------------------------------------------------- lịch
def viec_theo_lich(bay_gio: datetime, tt: dict) -> list:
    """Quyết định thuần túy (không mở gì) để thử được trên máy ảo: trả về danh sách việc cần làm lúc này."""
    ra = []
    hom_nay = bay_gio.strftime("%Y-%m-%d")
    gio_phut = (bay_gio.hour, bay_gio.minute)
    ngay_lam = bay_gio.weekday() <= 4                                  # thứ Hai (0) .. thứ Sáu (4)
    gio_lam = bay_gio.weekday() <= 5 and 7 <= bay_gio.hour <= 17       # giữ phiên, quét bù: cả thứ Bảy
    quet = tt.get("quet_luc")
    quet30 = tt.get("quet30_luc")
    if gio_lam:
        gp = tt.get("giu_phien_luc")
        if not gp or gp[:13] != bay_gio.strftime("%Y-%m-%dT%H"):      # mỗi giờ một lần
            ra.append(("giu-phien", {}))
    # sáng sớm: việc chờ xử lý rồi quét 7 ngày, cho bản tin 07:30 (máy bật qua đêm)
    if ngay_lam and gio_phut >= (5, 50) and (tt.get("viec_luc") or "")[:10] != hom_nay:
        ra.append(("viec", {"ngay": 30}))
    # chiều tối: việc chờ xử lý lượt 2 cho bản tin 19:00 (Bạn chốt 06/11/2026: bản tin 7h30 sáng và 19h tối)
    if ngay_lam and gio_phut >= (18, 15) and (tt.get("viec_toi_luc") or "")[:10] != hom_nay:
        ra.append(("viec", {"ngay": 30, "buoi": "toi"}))
    # sau lượt việc sáng: ô Phối hợp (hợp đồng vlncn-laocai/theo-doi/egov/phoi-hop/README.md). Chỉ chạy theo lịch khi Bạn
    # đã duyệt lượt thử 3 việc (yêu cầu "phoi-hop" có "bat_lich": true ghi phoi_hop_tu_dong) - Bạn chốt 11/11/2026.
    if (ngay_lam and tt.get("phoi_hop_tu_dong") and gio_phut >= (6, 0) and gio_phut < (8, 30)
            and (tt.get("viec_luc") or "")[:10] == hom_nay and (tt.get("phoi_hop_luc") or "")[:10] != hom_nay):
        ra.append(("phoi-hop", {}))
    # 06:20: Lịch Lãnh đạo Sở (hợp đồng vlncn-laocai/theo-doi/lich-lanh-dao/README.md, Bạn yêu cầu 09/11/2026)
    if ngay_lam and gio_phut >= (6, 20) and (tt.get("lich_ldao_luc") or "")[:10] != hom_nay:
        ra.append(("lich-lanh-dao", {}))
    if ngay_lam and gio_phut >= (5, 50) and (not quet or quet[:10] != hom_nay):
        ra.append(("quet", {"ngay": 7}))
    if gio_lam:
        qua_han = (not quet) or (bay_gio - datetime.fromisoformat(quet)).days >= QUET_QUA_HAN_NGAY
        thu_tu = bay_gio.weekday() == 2 and gio_phut >= (11, 30) and (not quet30 or quet30[:10] != hom_nay)
        if (thu_tu or qua_han) and not any(l == "quet" for l, _ in ra):
            ra.append(("quet", {"ngay": 30}))
        elif ngay_lam and gio_phut >= (16, 30) and quet and quet[:10] == hom_nay and int(quet[11:13]) < 12:
            ra.append(("quet", {"ngay": 7}))                            # lượt chiều, sau lượt sáng
    # đêm 22:15 -> 05:30, mọi ngày: bê văn bản cũ trên egov1 vào kho (Bạn yêu cầu 30/10/2026), mỗi đêm một lượt
    if gio_phut >= (22, 15) or gio_phut < LAY_LUI_DUNG:
        if (tt.get("lay_lui_luc") or "")[:10] != dem_cua(bay_gio):
            ra.append(("lay-lui", {}))
    return ra


LAY_LUI_DUNG = (5, 30)        # lượt bê văn bản cũ dừng trước lượt việc 05:50


def dem_cua(bay_gio: datetime) -> str:
    """Đêm 30/10 tính từ 22:15 ngày 30 tới 05:30 ngày 31 -> '2026-10-30'."""
    return (bay_gio - timedelta(hours=6)).strftime("%Y-%m-%d")


def gio_con_lai_dem(bay_gio: datetime) -> float:
    """Số giờ từ bây giờ tới 05:30 sáng kế tiếp."""
    dung = bay_gio.replace(hour=LAY_LUI_DUNG[0], minute=LAY_LUI_DUNG[1], second=0, microsecond=0)
    if dung <= bay_gio:
        dung += timedelta(days=1)
    return (dung - bay_gio).total_seconds() / 3600


# ---------------------------------------------------------------- GitHub
def _q(duong: str) -> str:
    """Mã hóa đường dẫn cho Contents API (tên tệp có dấu cách, tiếng Việt — vụ Lịch Lãnh đạo 09/11/2026: InvalidURL)."""
    from urllib.parse import quote
    return quote(duong, safe="/%")


class GitHub:
    def __init__(self, botd, token):
        self.b, self.token = botd, token

    def api(self, method, url, body=None):
        return self.b.gh(method, url, body, token=self.token)

    def liet_ke(self, repo, duong):
        r = self.api("GET", f"https://api.github.com/repos/{OWNER}/{repo}/contents/{duong}?ref=main")
        return r if isinstance(r, list) else []

    def doc(self, repo, duong):
        return self.b.gh_doc(repo, _q(duong), self.token)

    def ghi(self, repo, duong, noi_dung: bytes, msg, sha=None):
        return self.b.gh_ghi(repo, _q(duong), noi_dung, msg, self.token, sha)

    def day_thu_muc(self, repo, thu_muc_may: Path, duong_kho: str, msg):
        """Đẩy mọi tệp trong một thư mục trên máy lên kho (từng tệp, không cần git clone)."""
        so = 0
        for f in sorted(thu_muc_may.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(thu_muc_may).as_posix()
            duong = f"{duong_kho.rstrip('/')}/{rel}"
            _, sha = self.doc(repo, duong)
            self.ghi(repo, duong, f.read_bytes(), msg, sha)
            so += 1
        return so


# ---------------------------------------------------------------- tự cập nhật
def tu_cap_nhat(gh: GitHub) -> bool:
    """Tệp mã trên main khác tệp trên máy thì tải về; trả True nếu tay.py hoặc bot-data360x.py đổi (khởi động lại)."""
    doi_tay = False
    for ten, duong_kho in TEP_MA.items():
        try:
            r = gh.api("GET", f"https://api.github.com/repos/{OWNER}/{KHO_MA}/contents/{duong_kho}?ref=main")
            if not r:
                continue
            dich = (Path(__file__).resolve() if ten == "tay.py" else BOT_DIR / ten)
            if dich.exists() and sha_git(dich) == r["sha"]:
                continue
            noi_dung = base64.b64decode(r["content"])
            dich.parent.mkdir(parents=True, exist_ok=True)
            dich.write_bytes(noi_dung)
            log(f"Đã cập nhật {ten} từ main ({r['sha'][:7]})")
            # bot-data360x.py đã nạp sẵn trong bộ nhớ (nap_bot) nên đổi tệp cũng phải khởi động lại mới có hiệu lực
            # (vụ 05/11/2026: bot mới đọc danh sách Phụ trách đã tải về nhưng lượt việc 11:29 vẫn chạy bản cũ).
            doi_tay = doi_tay or ten in ("tay.py", "bot-data360x.py")
        except Exception as e:
            log(f"Không kiểm tra được bản mới của {ten}:", repr(e))
    return doi_tay


# ---------------------------------------------------------------- làm việc
def lam_viec(botd, gh: GitHub, loai: str, yc: dict, chay_thu=False) -> str:
    """Thực hiện một việc, trả về tóm tắt một dòng. Lỗi thì ném ra để nơi gọi ghi 'loi'."""
    if chay_thu:
        return f"chạy thử: bỏ qua {loai}"
    if loai == "giu-phien":
        ma = botd.giu_phien()
        ghi_trang_thai(giu_phien_luc=datetime.now().isoformat(timespec="minutes"), giu_phien_ma=ma)
        return "giữ phiên OK" if ma == 0 else "phiên đã hết hạn, cần đăng nhập lại (dang-nhap-lan-dau.bat)"
    if loai == "quet":
        ma = botd.chay_chinh(so_ngay=int(yc.get("ngay") or 30))
        if ma == 0:
            luc = datetime.now().isoformat(timespec="minutes")
            ghi_trang_thai(quet_luc=luc, **({"quet30_luc": luc} if int(yc.get("ngay") or 30) >= 30 else {}))
        return f"quét {yc.get('ngay') or 30} ngày, mã {ma}"
    if loai == "viec":
        if getattr(botd, "HE_THONG", "") != "egov":
            ghi_trang_thai(viec_luc=datetime.now().isoformat(timespec="minutes"),
                           **({"viec_toi_luc": datetime.now().isoformat(timespec="minutes")} if yc.get("buoi") == "toi" else {}))
            return "bỏ qua: việc chờ xử lý chỉ có trên egov1"
        luu_may = BOT_HOME / "ket-qua" / "viec" / date.today().isoformat()
        ma = botd.viec_cho_xu_ly(str(luu_may), so_ngay=int(yc.get("ngay") or 30))
        if ma == 0:
            luc = datetime.now().isoformat(timespec="minutes")
            ghi_trang_thai(viec_luc=luc, **({"viec_toi_luc": luc} if yc.get("buoi") == "toi" else {}))
        return f"việc chờ xử lý egov1: mã {ma}, kết quả ở theo-doi/viec-cho-xu-ly/{date.today().isoformat()}/"
    if loai == "khao-sat":
        return f"khảo sát egov1: mã {botd.khao_sat()}, kết quả ở theo-doi/egov/soi/"
    if loai == "lay-lui":
        bay_gio = datetime.now()
        theo_lich = "loai" not in yc                            # yêu cầu trong hàng đợi (ban ngày) không tính lượt đêm
        if theo_lich:
            ghi_trang_thai(lay_lui_luc=dem_cua(bay_gio))       # mỗi đêm một lượt, lỗi cũng không thử lại cả đêm
        gio = min(gio_con_lai_dem(bay_gio), float(yc.get("gio") or 24))
        if theo_lich and gio < 0.5:                             # lệnh trong hàng đợi: chạy đúng số giờ đã ghi
            return "bê văn bản cũ: còn dưới 30 phút trước 05:30, để đêm sau"
        tu = botd.parse_ngay(yc.get("tu_ngay") or "")
        nhuong = {"luc": time.time(), "co": False}

        def moi_vong():
            """Làm mới khóa; cứ 10 phút xem hàng đợi: có yêu cầu "cho" thì dừng lượt đêm để làm yêu cầu trước."""
            if KHOA.exists():
                KHOA.touch()
            if gh is None or time.time() - nhuong["luc"] < CHU_KY_PHUT * 60:
                return False
            nhuong["luc"] = time.time()
            nhuong["co"] = co_yeu_cau_cho(gh)
            return nhuong["co"]

        ma = botd.lay_lui(tu, so_gio=gio, moi_vong=moi_vong)
        day_nhat_ky(gh, f"sau lượt bê văn bản cũ (mã {ma})")
        if nhuong["co"]:
            xu_ly_hang_doi(botd, gh, socket.gethostname())
            if theo_lich:
                ghi_trang_thai(lay_lui_luc="")                 # vòng sau (10 phút) làm tiếp lượt đêm
            return f"bê văn bản cũ: tạm dừng để làm yêu cầu trong hàng đợi (mã {ma}), vòng sau làm tiếp"
        return f"bê văn bản cũ egov1: mã {ma} (tối đa {gio:.1f} giờ), nhật ký trên máy {BOT_HOME / 'lay-lui.json'}"
    if loai == "lich-lanh-dao":
        ghi_trang_thai(lich_ldao_luc=datetime.now().isoformat(timespec="minutes"))
        return tai_lich_lanh_dao(gh, botd)
    if loai == "nhat-ky":
        return "đẩy nhật ký: " + day_nhat_ky(gh, yc.get("ly_do") or "theo yêu cầu", int(yc.get("dong") or 400), int(yc.get("ngay") or 2))
    if loai == "lay":
        ten = yc.get("ten") or datetime.now().strftime("%Y-%m-%d_%H%M")
        luu_kho = yc.get("luu") or f"theo-doi/yeu-cau/{ten}"
        luu_may = BOT_HOME / "ket-qua" / ten
        ma = botd.lay_theo_yeu_cau(yc.get("yeu_cau", ""), str(luu_may), so_ngay=int(yc.get("ngay") or 60))
        so = gh.day_thu_muc(KHO_VIEC, luu_may, luu_kho, f"Lay van ban theo yeu cau: {ten}")
        return f"lấy văn bản: mã {ma}, đẩy {so} tệp vào {luu_kho}/"
    if loai == "ket-thuc-nv":
        # Bạn cho phép 05/11/2026: bấm "Duyệt và kết thúc nhiệm vụ" cho việc chỉ tổng hợp, lưu (danh sách do Claude ghi)
        ten = yc.get("ten") or datetime.now().strftime("%Y-%m-%d_%H%M")
        luu_kho = yc.get("luu") or f"theo-doi/egov/ket-thuc-nv/{ten}"
        luu_may = BOT_HOME / "ket-qua" / "ket-thuc-nv" / ten
        xong, tong = botd.ket_thuc_nhiem_vu(yc.get("viec") or [], yc.get("y_kien", ""), str(luu_may))
        so = gh.day_thu_muc(KHO_VIEC, luu_may, luu_kho, f"Ket thuc nhiem vu egov1: {ten}")
        return f"duyệt và kết thúc nhiệm vụ: {xong}/{tong}, đẩy {so} tệp vào {luu_kho}/"
    if loai == "phoi-hop":
        # Bạn yêu cầu 11/11/2026: tải toàn văn + đính kèm từng việc ô Phối hợp, đủ rồi mới bấm Hoàn thành phối hợp -> Đồng ý!
        if yc.get("bat_lich"):
            ghi_trang_thai(phoi_hop_tu_dong=True)
        if yc.get("tat_lich"):
            ghi_trang_thai(phoi_hop_tu_dong=False)
        if "loai" not in yc:                                   # lượt theo lịch: mỗi sáng một lần, lỗi cũng không thử lại
            ghi_trang_thai(phoi_hop_luc=datetime.now().isoformat(timespec="minutes"))
        ngay = date.today().isoformat()
        xong, tong = botd.phoi_hop(str(BOT_HOME / "ket-qua" / "phoi-hop" / ngay), toi_da=yc.get("toi_da") or None,
                                   chup_anh=int(yc.get("chup_anh") or 0), bam=yc.get("bam", True) is not False)
        return f"phối hợp egov1: bấm hoàn thành {xong}/{tong} việc, kết quả ở theo-doi/egov/phoi-hop/{ngay}/"
    if loai == "tim":
        ho_so = yc["ho_so"]
        raw, _ = gh.doc(KHO_VIEC, f"du-thao/{ho_so}/trich-dan.json")
        if not raw:
            raise RuntimeError(f"không thấy du-thao/{ho_so}/trich-dan.json")
        d = json.loads(raw)
        can = [{"so_ky_hieu": v["so_ky_hieu"], "ngay": (v.get("ngay") or [""])[0]}
               for v in d.get("vien_dan", d if isinstance(d, list) else [])]
        luu_may = BOT_HOME / "ket-qua" / "tim" / ho_so
        ma = botd.tim_van_ban(can, str(luu_may))
        so = gh.day_thu_muc(KHO_VIEC, luu_may, f"du-thao/{ho_so}/kem-theo",
                            f"Soat du thao: tai van ban vien dan cua {ho_so}")
        return f"tìm văn bản viện dẫn: mã {ma}, đẩy {so} tệp"
    raise RuntimeError(f"không biết loại việc '{loai}'")


LICH_LDAO_URL = "http://lichlanhdaosocongthuong.com/WorkingSchedule/Detail?DisplayType=1"
LICH_LDAO_DUOI = (".pdf", ".doc", ".docx", ".xls", ".xlsx")


def _lich_get(url, timeout=60):
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(), dict(r.headers)


def _lich_qua_trinh_duyet(botd) -> bytes:
    """Bảng lịch do JavaScript nạp sau (vụ 09/11/2026: GET thường chỉ được khung trang 6,8 KB, 0 mục) -> mở bằng Chrome riêng
    (chạy ẩn, KHÔNG dùng hồ sơ egov1, không đăng nhập, không bấm gì), chờ bảng #table-plans-id rồi lấy HTML đã dựng.
    Tắt chế độ tự nâng http -> https của Chrome: trang chỉ có http, hồ sơ bot chặn với ERR_BLOCKED_BY_CLIENT (09/11/2026 22:53)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, channel="chrome" if os.name == "nt" else None,
                              args=["--disable-features=HttpsUpgrades,HttpsFirstBalancedModeAutoEnable,HttpsFirstModeV2",
                                    "--disable-blink-features=AutomationControlled"])
        try:
            ctx = b.new_context(ignore_https_errors=True, locale="vi-VN", viewport={"width": 1600, "height": 1000})
            page = ctx.new_page()
            page.goto(LICH_LDAO_URL, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_selector("#table-plans-id", timeout=60000)
            page.wait_for_timeout(3000)
            return page.content().encode("utf-8")
        finally:
            b.close()


def tai_lich_lanh_dao(gh, botd=None) -> str:
    """Tải trang Lịch Lãnh đạo Sở + tệp đính kèm -> theo-doi/lich-lanh-dao/<hôm nay>/ (lich.html, tệp, tep.json; lỗi: loi.txt).
    Không đăng nhập, không bấm gì; chỉ GET trang và các liên kết DownloadPlanAttachmentFile."""
    import html as _h
    import urllib.error
    hom_nay = date.today().isoformat()
    thu = BOT_HOME / "ket-qua" / "lich-lanh-dao" / hom_nay
    if thu.exists():
        for f in thu.iterdir():
            if f.is_file():
                f.unlink()
    thu.mkdir(parents=True, exist_ok=True)
    so_muc, tep = 0, []
    try:
        ma, noi_dung, _ = _lich_get(LICH_LDAO_URL)
        if b"table-plans-id" not in noi_dung and botd is not None:
            noi_dung = _lich_qua_trinh_duyet(botd)
        if b"table-plans-id" not in noi_dung:
            raise RuntimeError(f"trang không có bảng lịch #table-plans-id ({len(noi_dung)} byte) - không ghi đè lich.html")
        (thu / "lich.html").write_bytes(noi_dung)
        chu = noi_dung.decode("utf-8", errors="replace")
        so_muc = len(re.findall(r'title="Nội dung làm việc"', chu))
        da_ten, da_url = set(), set()
        for a in re.finditer(r"<a\b[^>]*download-attachent-td-plans[^>]*>", chu):
            the = a.group(0)
            href = re.search(r'href="([^"]+)"', the)
            ten = re.search(r'title="([^"]*)"', the)
            if not href or "DownloadPlanAttachmentFile" not in href.group(1):
                continue
            from urllib.parse import urljoin
            href_goc = _h.unescape(href.group(1))   # ghi vào tep.json đúng như trong lich.html để bộ đọc ghép được
            url = urljoin(LICH_LDAO_URL, href_goc)  # trang dựng bằng JS cho href tương đối (09/11/2026)
            if url in da_url:                       # một tệp gắn ở nhiều ô lịch: tải một lần
                continue
            da_url.add(url)
            ten = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", _h.unescape(ten.group(1) if ten else "")).strip() or "tep"
            if not ten.lower().endswith(LICH_LDAO_DUOI):
                continue
            goc, duoi = ten.rsplit(".", 1)
            k, ten_luu = 2, ten
            while ten_luu.lower() in da_ten:
                ten_luu, k = f"{goc}_{k}.{duoi}", k + 1
            try:
                _, b, _ = _lich_get(url, timeout=120)
            except Exception as e:
                log(f"  lịch lãnh đạo: không tải được {ten}: {e!r}")
                continue
            if len(b) > 20 * 1024 * 1024:
                log(f"  lịch lãnh đạo: {ten} quá 20 MB - bỏ")
                continue
            da_ten.add(ten_luu.lower())
            (thu / ten_luu).write_bytes(b)
            tep.append({"ten": ten_luu, "url": href_goc, "kich_thuoc": len(b)})
        (thu / "tep.json").write_text(json.dumps(tep, ensure_ascii=False, indent=2), encoding="utf-8")
    except urllib.error.HTTPError as e:
        (thu / "loi.txt").write_text(f"HTTP {e.code}\n{e.read()[:300]!r}", encoding="utf-8")
    except Exception as e:
        (thu / "loi.txt").write_text(f"{e!r}"[:300], encoding="utf-8")
    msg = f"Lịch Lãnh đạo Sở {date.today().strftime('%d/%m/%Y')}: {so_muc} mục, {len(tep)} tệp"
    if (thu / "loi.txt").exists():
        msg += " (lỗi tải trang)"
    so = gh.day_thu_muc(KHO_VIEC, thu, f"theo-doi/lich-lanh-dao/{hom_nay}", msg) if gh else 0
    return f"{msg}; đẩy {so} tệp"


_CHE = [re.compile(r"(?i)(authorization|token|cookie|password|matkhau|secret)([\"']?\s*[:=]\s*)[^\n,;}]+"),
        re.compile(r"(?i)bearer\s+\S+"), re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}"),
        re.compile(r"(ghp|gho|ghs|github_pat)_\w+")]


def _che(dong: str) -> str:
    for i, m in enumerate(_CHE):
        dong = m.sub((lambda x: x.group(1) + x.group(2) + "***") if i == 0 else (lambda x: "***"), dong)
    return dong


def day_nhat_ky(gh, ly_do: str, so_dong=400, so_ngay=2) -> str:
    """Đẩy đuôi nhật ký TAY + bot (hôm nay, hôm qua) và lay-lui.json lên kho riêng tư (Bạn không dùng Telegram — 09/11/2026):
    theo-doi/tay/nhat-ky/<ngày>.log. Che mọi chuỗi giống mã đăng nhập trước khi đẩy."""
    if gh is None:
        return "không có GitHub"
    phan = [f"# Nhật ký TAY {PHIEN_BAN} - {datetime.now().isoformat(timespec='minutes')} - {ly_do}", ""]
    for ngay in [date.today() - timedelta(days=i) for i in range(max(1, so_ngay) - 1, -1, -1)]:
        for ten in (f"tay-{ngay.isoformat()}.log", f"{ngay.isoformat()}.log"):
            f = LOG_DIR / ten
            if f.exists():
                dong = f.read_text(encoding="utf-8", errors="replace").splitlines()[-so_dong:]
                phan += [f"## {ten} ({len(dong)} dòng cuối)"] + [_che(x) for x in dong] + [""]
    tt = BOT_HOME / "lay-lui.json"
    if tt.exists():
        phan += ["## lay-lui.json", _che(tt.read_text(encoding="utf-8", errors="replace")[:20000]), ""]
    duong = f"theo-doi/tay/nhat-ky/{date.today().isoformat()}.log"
    try:
        _, sha = gh.doc(KHO_VIEC, duong)
        gh.ghi(KHO_VIEC, duong, "\n".join(phan).encode("utf-8"), f"tay: nhat ky {ly_do}", sha)
        return duong
    except Exception as e:
        log("Không đẩy được nhật ký:", repr(e))
        return f"lỗi {e!r}"


def co_yeu_cau_cho(gh: GitHub) -> bool:
    """Hàng đợi yeu-cau/ có tệp nào đang "cho" không (lượt bê văn bản cũ dài nhiều giờ dùng để nhường)."""
    try:
        for muc in gh.liet_ke(KHO_VIEC, "yeu-cau"):
            if muc.get("type") == "file" and muc["name"].endswith(".json"):
                raw, _ = gh.doc(KHO_VIEC, muc["path"])
                if raw and json.loads(raw).get("trang_thai", "cho") == "cho":
                    return True
    except Exception as e:
        log("Không đọc được hàng đợi:", repr(e)[:150])
    return False


def xu_ly_hang_doi(botd, gh: GitHub, may: str, chay_thu=False) -> int:
    """Nhận và làm từng yêu cầu 'cho' trong yeu-cau/. Trả về số việc đã làm."""
    lam = 0
    for muc in gh.liet_ke(KHO_VIEC, "yeu-cau"):
        if muc.get("type") != "file" or not muc["name"].endswith(".json"):
            continue
        duong = muc["path"]
        raw, sha = gh.doc(KHO_VIEC, duong)
        try:
            yc = json.loads(raw)
        except Exception:
            continue
        if yc.get("trang_thai", "cho") != "cho":
            continue
        # nhận việc: ghi bằng sha cũ; máy kia đã nhận trước thì GitHub trả 409, bỏ qua
        yc.update(trang_thai="dang", may=may, luc=datetime.now().isoformat(timespec="minutes"))
        try:
            r = gh.ghi(KHO_VIEC, duong, json.dumps(yc, ensure_ascii=False, indent=2).encode(),
                       f"tay {may}: nhan viec {muc['name']}", sha)
            sha = r["content"]["sha"]
        except Exception as e:
            log(f"Không nhận được {muc['name']} (máy khác đã nhận?):", repr(e))
            continue
        log(f"Làm việc {muc['name']}: {yc.get('loai')} {yc.get('yeu_cau') or yc.get('ho_so') or ''}")
        try:
            tom_tat = lam_viec(botd, gh, yc.get("loai", ""), yc, chay_thu)
            yc.update(trang_thai="xong", tom_tat=tom_tat)
        except Exception as e:
            yc.update(trang_thai="loi", tom_tat=repr(e)[:500])
            log("LỖI khi làm việc:", traceback.format_exc())
        yc["xong_luc"] = datetime.now().isoformat(timespec="minutes")
        gh.ghi(KHO_VIEC, duong, json.dumps(yc, ensure_ascii=False, indent=2).encode(),
               f"tay {may}: {yc['trang_thai']} {muc['name']}", sha)
        if yc.get("trang_thai") == "loi":
            day_nhat_ky(gh, f"việc lỗi {muc['name']}")
        botd.telegram(f"TAY {may}: {yc.get('loai')} {muc['name']} -> {yc['trang_thai']}: {yc.get('tom_tat', '')}")
        lam += 1
    return lam


def nhip_tim(botd, gh: GitHub, may: str, ep=False):
    tt = doc_trang_thai()
    gio = datetime.now().strftime("%Y-%m-%dT%H")
    if not ep and tt.get("nhip_tim_gio") == gio:
        return
    thong_tin = botd.thong_tin_may()
    noi_dung = {"may": may, "loai_may": thong_tin.get("loai", ""), "mang": thong_tin.get("mang", ""),
                "luc": datetime.now().isoformat(timespec="minutes"), "phien_ban": PHIEN_BAN,
                "giu_phien_luc": tt.get("giu_phien_luc"), "quet_luc": tt.get("quet_luc"),
                "viec_luc": tt.get("viec_luc"), "cong": getattr(botd, "TEN_HE_THONG", "")}
    try:
        _, sha = gh.doc(KHO_VIEC, "trang-thai/tay.json")
        gh.ghi(KHO_VIEC, "trang-thai/tay.json", json.dumps(noi_dung, ensure_ascii=False, indent=2).encode(),
               f"tay {may}: nhip tim {noi_dung['luc']}", sha)
        ghi_trang_thai(nhip_tim_gio=gio)
    except Exception as e:
        log("Không ghi được nhịp tim:", repr(e))


def mot_vong(botd, gh: GitHub, may: str, chay_thu=False) -> bool:
    """Một vòng: cập nhật, lịch, hàng đợi, nhịp tim. Trả True nếu phải khởi động lại (mã đổi)."""
    if not chay_thu and tu_cap_nhat(gh):
        return True
    for loai, yc in viec_theo_lich(datetime.now(), doc_trang_thai()):
        try:
            log(f"Theo lịch: {loai} -> " + lam_viec(botd, gh, loai, yc, chay_thu))
        except Exception:
            log("LỖI việc theo lịch:", traceback.format_exc())
    da_lam = 0 if chay_thu else xu_ly_hang_doi(botd, gh, may, chay_thu)
    if not chay_thu:
        nhip_tim(botd, gh, may, ep=da_lam > 0)
    don_log()
    return False


def chay_thu(botd):
    """Máy ảo Windows: mọi thứ trừ Chrome và GitHub. Thất bại thì exit 1 để CI đỏ."""
    print("tay", PHIEN_BAN, "| bot:", getattr(botd, "GOC_WEB", "?"), "| ROOT:", ROOT)
    for ham in ("chay_chinh", "giu_phien", "lay_theo_yeu_cau", "tim_van_ban", "gh", "gh_doc", "gh_ghi",
                "telegram", "thong_tin_may", "viec_cho_xu_ly", "khao_sat", "chon_he_thong", "lay_lui", "parse_ngay",
                "phoi_hop"):
        assert hasattr(botd, ham), f"bot thiếu hàm {ham}"
    assert botd.HE_THONG == "egov", botd.HE_THONG      # cổng mặc định từ 29/10/2026
    # các phép thử cũ bỏ "lich-lanh-dao" (thêm 0.4.10, có phép thử riêng ngay dưới)
    L = lambda t, tt: [l for l, _ in viec_theo_lich(t, tt) if l != "lich-lanh-dao"]
    assert "lich-lanh-dao" in [l for l, _ in viec_theo_lich(datetime(2026, 11, 10, 6, 25), {})]
    assert "lich-lanh-dao" not in [l for l, _ in viec_theo_lich(datetime(2026, 11, 10, 6, 10), {})]
    assert "lich-lanh-dao" not in [l for l, _ in viec_theo_lich(datetime(2026, 11, 10, 7, 0),
                                                               {"lich_ldao_luc": "2026-11-10T06:21"})]
    assert L(datetime(2026, 9, 30, 11, 35), {}) == ["giu-phien", "viec", "quet"]        # thứ Tư, chưa làm gì
    v = viec_theo_lich(datetime(2026, 9, 30, 11, 35), {})
    assert [y for _, y in v if _ == "quet"] == [{"ngay": 7}], v                             # không xếp 2 lượt quét
    assert L(datetime(2026, 9, 30, 11, 35), {"giu_phien_luc": "2026-09-30T11:02", "quet_luc": "2026-09-30T05:52",
                                             "viec_luc": "2026-09-30T05:51"}) == ["quet"]   # thứ Tư: lượt 30 ngày
    assert L(datetime(2026, 9, 30, 11, 35), {"giu_phien_luc": "2026-09-30T11:02", "quet_luc": "2026-09-30T11:40",
                                             "quet30_luc": "2026-09-30T11:40", "viec_luc": "2026-09-30T05:51"}) == []
    assert L(datetime(2026, 10, 2, 5, 55), {"quet_luc": "2026-10-01T16:31", "viec_luc": "2026-10-01T05:51"}) \
        == ["viec", "quet"]                                                                  # 05:55: việc + quét sáng
    assert L(datetime(2026, 10, 2, 5, 40), {"quet_luc": "2026-10-01T16:31", "viec_luc": "2026-10-01T05:51"}) == []
    assert L(datetime(2026, 10, 3, 9, 0), {"quet_luc": "2026-10-02T16:31"}) == ["giu-phien"]   # thứ Bảy: chỉ giữ phiên
    assert L(datetime(2026, 10, 4, 22, 0), {}) == []                                       # Chủ nhật đêm: không làm gì
    assert L(datetime(2026, 10, 2, 9, 0), {"quet_luc": "2026-09-20T11:31", "viec_luc": "2026-10-02T05:51"}) \
        == ["giu-phien", "quet"]                                                            # quá 7 ngày -> quét (7 ngày sáng)
    v = viec_theo_lich(datetime(2026, 10, 2, 16, 40), {"quet_luc": "2026-10-02T05:52", "viec_luc": "2026-10-02T05:51",
                                                       "giu_phien_luc": "2026-10-02T16:05"})
    v = [x for x in v if x[0] != "lich-lanh-dao"]
    assert v == [("quet", {"ngay": 7})], v                                                  # chiều: quét 7 ngày lần 2
    assert L(datetime(2026, 10, 2, 17, 5), {"quet_luc": "2026-10-02T16:41", "viec_luc": "2026-10-02T05:51",
                                            "giu_phien_luc": "2026-10-02T17:01"}) == []    # đã quét chiều thì thôi
    # bê văn bản cũ: mỗi đêm 22:15-05:30 một lượt, kể cả cuối tuần; đêm đã chạy thì thôi
    assert L(datetime(2026, 10, 30, 22, 20), {"quet_luc": "2026-10-30T16:31", "viec_luc": "2026-10-30T05:51",
                                              "viec_toi_luc": "2026-10-30T18:20"}) == ["lay-lui"]
    assert L(datetime(2026, 10, 30, 18, 20), {"quet_luc": "2026-10-30T16:31", "viec_luc": "2026-10-30T05:51"}) \
        == ["viec"]                                                                         # 18:15: việc lượt tối
    assert L(datetime(2026, 10, 31, 2, 0), {"lay_lui_luc": "2026-10-30"}) == []           # cùng đêm 30/10
    assert L(datetime(2026, 11, 1, 1, 0), {"lay_lui_luc": "2026-10-30"}) == ["lay-lui"]   # Chủ nhật rạng sáng
    assert L(datetime(2026, 10, 31, 5, 35), {"lay_lui_luc": "2026-10-29"}) == []          # 05:35 thứ Bảy: hết đêm
    assert abs(gio_con_lai_dem(datetime(2026, 10, 30, 22, 15)) - 7.25) < 1e-6
    assert abs(gio_con_lai_dem(datetime(2026, 10, 31, 4, 30)) - 1.0) < 1e-6
    # phối hợp (11/11/2026): chỉ chạy theo lịch khi Bạn đã bật (phoi_hop_tu_dong), sau lượt việc sáng, trước 08:30
    sang = {"quet_luc": "2026-11-12T05:58", "viec_luc": "2026-11-12T05:52", "lich_ldao_luc": "2026-11-12T06:20",
            "giu_phien_luc": "2026-11-12T07:01"}
    assert "phoi-hop" not in L(datetime(2026, 11, 12, 7, 30), sang)                          # chưa bật: không chạy
    assert "phoi-hop" in L(datetime(2026, 11, 12, 7, 30), {**sang, "phoi_hop_tu_dong": True})
    assert "phoi-hop" not in L(datetime(2026, 11, 12, 7, 30), {**sang, "phoi_hop_tu_dong": True,
                                                              "phoi_hop_luc": "2026-11-12T06:05"})
    assert "phoi-hop" not in L(datetime(2026, 11, 14, 7, 30), {**sang, "phoi_hop_tu_dong": True})   # thứ Bảy
    x = {"id": "w1", "content": "phối hợp góp ý", "deadLineDate": "2026-11-20T00:00:00",
         "documentApis": [{"id": "A" * 32, "symbol": "12/UBND-KT", "number": "99", "abridgment": "V/v  thử",
                           "documentSentCompany": "UBND tỉnh", "publishTime": "2026-11-10T00:00:00"}],
         "userApis": [{"fullName": "Lê Quang Trung", "followRoleName": "Xử lý chính"},
                      {"fullName": "Trần Trọng Trang", "followRoleName": "Phối hợp"}]}
    v = botd._ph_viec(x)
    assert (v["so"], v["so_den"], v["ngay"], v["trich_yeu"], v["xu_ly_chinh"], v["han"]) == \
        ("12/UBND-KT", "99", "10/11/2026", "V/v thử", "Lê Quang Trung", "20/11/2026"), v
    assert "| 12/UBND-KT |" in botd._ph_md([{**v, "ket_qua": "da-hoan-thanh"}], "2026-11-11")
    # bộ đọc egov1: nhận cột theo tiêu đề đúng như ảnh chụp danh sách Văn bản đến (29/10/2026)
    cot = botd._egov_anh_xa_cot(["STT", "Cấp độ", "Trích yếu", "Số ký hiệu", "Ngày Ban Hành", "Ngày Nhận",
                                 "Trạng thái", "Cơ quan ban hành", "Người Ký", "Độ mật", "Nguồn văn bản", ""])
    assert cot == {"do_khan": 1, "trich_yeu": 2, "so": 3, "ngay": 4, "ngay_nhan": 5, "trang_thai": 6,
                   "don_vi": 7, "nguoi_ky": 8, "do_mat": 9, "nguon_vb": 10}, cot
    assert botd._egov_la_mat({"do_mat": "Mật"}) and not botd._egov_la_mat({"do_mat": "thường"})
    assert botd._la_viec_cho({"trang_thai": "Chưa xử lý"}) and not botd._la_viec_cho({"trang_thai": "Đã xử lý"})
    yc = {"loai": "lay", "yeu_cau": "5511/SCT-CN; tiêu chí lựa chọn chủ đầu tư", "ngay": 60}
    so, tu_khoa = botd._tach_yeu_cau(yc["yeu_cau"])
    assert so and tu_khoa, (so, tu_khoa)
    ghi_trang_thai(chay_thu_luc=datetime.now().isoformat(timespec="minutes"))
    don_log()
    print("CHAY THU OK: nạp bot, cổng egov1, lịch, phân tích yêu cầu, ghi trạng thái, dọn log.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mot-lan", action="store_true")
    ap.add_argument("--chay-thu", action="store_true")
    a = ap.parse_args()
    botd = nap_bot()
    if a.chay_thu:
        return chay_thu(botd)
    token = botd.doc_config().get("github_token", "")
    if not token:
        log("Chưa có github_token trong config.json (chạy cai-tay.bat để nhập).")
        return 2
    may = socket.gethostname()
    gh = GitHub(botd, token)
    # một tiến trình duy nhất trên máy
    try:
        if (KHOA.exists() and time.time() - KHOA.stat().st_mtime < CHU_KY_PHUT * 60 * 2
                and KHOA.read_text().strip() not in (str(os.getpid()), os.environ.get("TAY_PID_CU", ""))):
            # Không thoát khi khóa là của chính tiến trình vừa os.execv. Trên Windows os.execv tạo tiến trình MỚI (PID khác)
            # nên truyền PID cũ qua biến môi trường TAY_PID_CU (vụ 05/11/2026: TAY 0.4.5 tự thoát sau khi nạp bot mới 14:10,
            # máy im tới khi lịch canh 30 phút gọi lại).
            log("TAY khác đang chạy (tay.lock còn mới) - thoát.")
            return 0
    except Exception:
        pass
    log(f"TAY {PHIEN_BAN} bắt đầu trên {may}, thư mục {ROOT}")
    while True:
        try:
            KHOA.parent.mkdir(parents=True, exist_ok=True)
            KHOA.write_text(str(os.getpid()))
            if mot_vong(botd, gh, may):
                log("Mã đã đổi - khởi động lại.")
                os.environ["TAY_PID_CU"] = str(os.getpid())
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            log("LỖI vòng lặp:", traceback.format_exc())
        if a.mot_lan:
            return 0
        time.sleep(CHU_KY_PHUT * 60)


if __name__ == "__main__":
    sys.exit(main())

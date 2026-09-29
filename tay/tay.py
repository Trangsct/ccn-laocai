# -*- coding: utf-8 -*-
"""
TAY - tiến trình duy nhất chạy trên máy ở Lào Cai, cánh tay của Claude (Bạn chốt 30/9/2026, Giai đoạn 1).

Thay cho: GitHub runner (phải đăng ký, hay rớt), Task Scheduler 18h, lượt online (cổng chặn máy chủ nước
ngoài) và 5 workflow chạy trên máy. TAY tự kéo việc từ GitHub, không có gì để "already configured".

Vòng lặp mỗi CHU_KY phút:
  1. tự cập nhật: tay.py và bot-data360x.py trên main đổi thì tải về rồi khởi động lại chính mình
  2. việc theo lịch (giờ Việt Nam, tính trên máy):
       - giữ phiên Data360X mỗi giờ 07-17h thứ Hai-Bảy (Chrome thu nhỏ ~20 giây)
       - quét 30 ngày thứ Tư từ 11:30, hoặc bất cứ lúc nào trong giờ làm việc nếu đã quá 7 ngày chưa quét
  3. hàng đợi yêu cầu: kho riêng tư vlncn-laocai, thư mục yeu-cau/*.json, trang_thai "cho" -> nhận (ghi
     "dang" bằng sha cũ, hai máy không tranh nhau) -> làm -> đẩy kết quả -> ghi "xong"/"loi"
  4. nhịp tim trang-thai/tay.json (nhiều nhất mỗi giờ một lần, và ngay sau mỗi việc)

Tệp yêu cầu (Claude hoặc workflow yeu-cau.yml ghi):
  {"loai": "lay",  "yeu_cau": "5511/SCT-CN; tiêu chí lựa chọn chủ đầu tư", "ngay": 60, "luu": "theo-doi/yeu-cau/<ten>"}
  {"loai": "tim",  "ho_so": "<thư mục trong du-thao/>"}          # tìm văn bản viện dẫn của dự thảo
  {"loai": "quet", "ngay": 30}
  {"loai": "giu-phien"}
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
PHIEN_BAN = "0.1.1 (30/9/2026)"
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
    gio_lam = bay_gio.weekday() <= 5 and 7 <= bay_gio.hour <= 17      # thứ Hai (0) .. thứ Bảy (5)
    if gio_lam:
        gp = tt.get("giu_phien_luc")
        if not gp or gp[:13] != bay_gio.strftime("%Y-%m-%dT%H"):      # mỗi giờ một lần
            ra.append(("giu-phien", {}))
        quet = tt.get("quet_luc")
        qua_han = (not quet) or (bay_gio - datetime.fromisoformat(quet)).days >= QUET_QUA_HAN_NGAY
        thu_tu = bay_gio.weekday() == 2 and (bay_gio.hour, bay_gio.minute) >= (11, 30) \
            and (not quet or quet[:10] != bay_gio.strftime("%Y-%m-%d"))
        if thu_tu or qua_han:
            ra.append(("quet", {"ngay": 30}))
    return ra


# ---------------------------------------------------------------- GitHub
class GitHub:
    def __init__(self, botd, token):
        self.b, self.token = botd, token

    def api(self, method, url, body=None):
        return self.b.gh(method, url, body, token=self.token)

    def liet_ke(self, repo, duong):
        r = self.api("GET", f"https://api.github.com/repos/{OWNER}/{repo}/contents/{duong}?ref=main")
        return r if isinstance(r, list) else []

    def doc(self, repo, duong):
        return self.b.gh_doc(repo, duong, self.token)

    def ghi(self, repo, duong, noi_dung: bytes, msg, sha=None):
        return self.b.gh_ghi(repo, duong, noi_dung, msg, self.token, sha)

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
    """Tệp mã trên main khác tệp trên máy thì tải về; trả True nếu tay.py đổi (cần khởi động lại)."""
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
            doi_tay = doi_tay or ten == "tay.py"
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
            ghi_trang_thai(quet_luc=datetime.now().isoformat(timespec="minutes"))
        return f"quét {yc.get('ngay') or 30} ngày, mã {ma}"
    if loai == "lay":
        ten = yc.get("ten") or datetime.now().strftime("%Y-%m-%d_%H%M")
        luu_kho = yc.get("luu") or f"theo-doi/yeu-cau/{ten}"
        luu_may = BOT_HOME / "ket-qua" / ten
        ma = botd.lay_theo_yeu_cau(yc.get("yeu_cau", ""), str(luu_may), so_ngay=int(yc.get("ngay") or 60))
        so = gh.day_thu_muc(KHO_VIEC, luu_may, luu_kho, f"Lay van ban theo yeu cau: {ten}")
        return f"lấy văn bản: mã {ma}, đẩy {so} tệp vào {luu_kho}/"
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
                "giu_phien_luc": tt.get("giu_phien_luc"), "quet_luc": tt.get("quet_luc")}
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
                "telegram", "thong_tin_may"):
        assert hasattr(botd, ham), f"bot thiếu hàm {ham}"
    t = datetime(2026, 9, 30, 11, 35)       # thứ Tư 11:35
    v = [l for l, _ in viec_theo_lich(t, {})]
    assert v == ["giu-phien", "quet"], v
    v = [l for l, _ in viec_theo_lich(t, {"giu_phien_luc": "2026-09-30T11:02", "quet_luc": "2026-09-30T11:31"})]
    assert v == [], v
    v = [l for l, _ in viec_theo_lich(datetime(2026, 10, 4, 22, 0), {})]    # Chủ nhật đêm: không làm gì
    assert v == [], v
    v = [l for l, _ in viec_theo_lich(datetime(2026, 10, 2, 9, 0), {"quet_luc": "2026-09-20T11:31"})]
    assert v == ["giu-phien", "quet"], v      # quá 7 ngày chưa quét -> quét bù
    yc = {"loai": "lay", "yeu_cau": "5511/SCT-CN; tiêu chí lựa chọn chủ đầu tư", "ngay": 60}
    so, tu_khoa = botd._tach_yeu_cau(yc["yeu_cau"])
    assert so and tu_khoa, (so, tu_khoa)
    ghi_trang_thai(chay_thu_luc=datetime.now().isoformat(timespec="minutes"))
    don_log()
    print("CHAY THU OK: nạp bot, lịch, phân tích yêu cầu, ghi trạng thái, dọn log.")
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
        if KHOA.exists() and time.time() - KHOA.stat().st_mtime < CHU_KY_PHUT * 60 * 2:
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
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            log("LỖI vòng lặp:", traceback.format_exc())
        if a.mot_lan:
            return 0
        time.sleep(CHU_KY_PHUT * 60)


if __name__ == "__main__":
    sys.exit(main())

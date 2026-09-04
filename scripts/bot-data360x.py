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


def cho_dang_nhap(ctx, page):
    """Mở cửa sổ nhìn thấy được, báo cán bộ đăng nhập, chờ tối đa 6 x 15 phút."""
    thong_bao_windows("Bot cần bạn đăng nhập lại Data360X", "Đăng nhập trong cửa sổ Chrome vừa mở, bot sẽ tự chạy tiếp.")
    telegram("Bot Data360X: phiên đăng nhập hết hạn. Hãy đăng nhập lại trong cửa sổ Chrome trên máy cơ quan.")
    for lan in range(SO_LAN_CHO_DANG_NHAP):
        log(f"Chờ đăng nhập, lần {lan + 1}/{SO_LAN_CHO_DANG_NHAP} (tối đa {CHO_DANG_NHAP_PHUT} phút)")
        het = time.time() + CHO_DANG_NHAP_PHUT * 60
        while time.time() < het:
            page.wait_for_timeout(10000)
            if not can_dang_nhap(page) and "csdlvb.laocai.gov.vn" in page.url:
                log("Đã đăng nhập, chạy tiếp.")
                return True
    log("Hết thời gian chờ đăng nhập.")
    return False


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
        if not rows or (ngay_cu and min(ngay_cu) < tu_ngay) or trang_so >= 20:
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
                if not cho_dang_nhap(ctx, page):
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


# ---------------------------------------------------------------- luồng chính
def chay_chinh(soi=False, so_ngay=None, online=False):
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
    tong_quet, da_day, loi, phien_moi = 0, [], [], None

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
                if not cho_dang_nhap(ctx, page):
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
               f"đẩy {len(da_day)} file" + (": " + "; ".join(da_day) if da_day else "")
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
        if a.tim:
            d = json.loads(Path(a.tim).read_text(encoding="utf-8"))
            can = [{"so_ky_hieu": v["so_ky_hieu"], "ngay": (v.get("ngay") or [""])[0]}
                   for v in d.get("vien_dan", d if isinstance(d, list) else [])]
            return tim_van_ban(can, a.luu, online=a.online)
        return chay_chinh(soi=a.soi, so_ngay=a.ngay, online=a.online)
    except Exception as e:
        log("LỖI:", repr(e))
        telegram(f"Bot Data360X lỗi: {e!r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

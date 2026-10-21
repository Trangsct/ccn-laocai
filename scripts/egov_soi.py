# -*- coding: utf-8 -*-
"""
SOI EGOV - ghi lại cấu trúc nền tảng chính quyền số EGOV (https://egov1.laocai.gov.vn) để dựng bot mới.

Bối cảnh (Bạn báo 21/10/2026): từ 10/10/2026 văn bản đi, đến của Sở chuyển sang EGOV, thay cho Data360X
(csdlvb.laocai.gov.vn — lượt quét cuối 10/10/2026) và vOffice (qlvb.yenbai.gov.vn). Claude trên mây không vào được
egov1 (cổng chặn máy ngoài nước), nên chưa biết trang dùng đường dẫn, bảng, API nào. Công cụ này chạy MỘT LẦN trên
máy ở Lào Cai, chỉ ĐỌC, ghi lại:
  - các trang đã đi qua: địa chỉ, tiêu đề, menu, tiêu đề cột và vài dòng đầu của bảng, ảnh chụp, HTML;
  - mọi yêu cầu XHR/fetch tới máy chủ: phương thức, đường dẫn, tham số, mẫu phản hồi JSON (cắt ngắn);
  - TÊN khóa localStorage/sessionStorage và tên header xác thực (KHÔNG ghi giá trị mã phiên, mật khẩu, cookie);
rồi đẩy lên kho RIÊNG TƯ vlncn-laocai, thư mục theo-doi/egov/soi/<ngày-giờ>/, để Claude viết bot thật.

Hai pha:
  1. tự đi: mở trang chủ, đi theo các liên kết menu có chữ "văn bản", "đến", "đi", "xử lý", "hồ sơ", "tra cứu"...,
     mở thử văn bản đầu tiên của mỗi danh sách. Chỉ đi theo LIÊN KẾT (không bấm nút) và bỏ mọi liên kết có chữ
     xóa, đăng xuất, chuyển, ký, duyệt, trả lại, hoàn thành, gửi, lưu, thu hồi.
  2. Bạn tự bấm (mặc định 10 phút): Văn bản đến -> mở 1 văn bản -> bấm xem tệp đính kèm; Văn bản đi -> tương tự;
     mục Chờ xử lý. Bot ghi lại hết. Xong sớm thì bấm Enter ở cửa sổ đen.

Chạy:  python egov_soi.py                 (soi-egov.bat gọi sẵn)
       python egov_soi.py --phut 5        thời gian Bạn tự bấm
       python egov_soi.py --khong-day     không đẩy GitHub, chỉ lưu trên máy (logs\\soi-egov\\...)
       python egov_soi.py --chay-thu      không mở Chrome, không cần token: tự kiểm tra hàm che mã phiên (máy ảo)
Nguyên tắc giữ nguyên: không tự đăng nhập, không giải captcha, không bấm nút thao tác hồ sơ.
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

for _luong in (sys.stdout, sys.stderr):
    try:
        _luong.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GOC_EGOV = os.environ.get("EGOV_GOC", "https://egov1.laocai.gov.vn")   # biến môi trường chỉ để chạy thử với trang giả
MAY_CHU = urlsplit(GOC_EGOV).netloc
TRANG_CHU = GOC_EGOV + "/home/default/1"
REPO_RIENG = "vlncn-laocai"
THU_MUC_DAY = "theo-doi/egov/soi"
CHO_DANG_NHAP_PHUT = 20
TU_DI_TOI_DA = 30                 # số trang tự đi tối đa
API_TOI_DA = 600                  # số bản ghi yêu cầu tối đa
MAU_PHAN_HOI_KB = 24              # cắt mẫu phản hồi JSON/text
HTML_TOI_DA_KB = 900
DAY_TOI_DA_MB = 40                # tổng dung lượng đẩy lên GitHub mỗi lượt

TU_KHOA_DI = ["van ban", "den", "di", "xu ly", "ho so", "tra cuu", "cong viec", "so van ban", "tiep nhan",
              "phat hanh", "danh sach", "tat ca", "ca nhan", "phong", "don vi", "tai lieu", "lich",
              "dinh kem"]
TU_CAM = ["dang xuat", "logout", "signout", "sign-out", "thoat", "xoa", "delete", "remove", "chuyen", "ky so",
          "ky duyet", "duyet", "tra lai", "hoan thanh", "gui", "luu", "thu hoi", "huy", "phan cong", "giao viec",
          "doi mat khau", "cap nhat", "sua", "edit", "update", "save", "send", "approve", "reject", "upload"]
KHOA_BI_MAT = re.compile(r"(token|password|passwd|matkhau|mat_khau|secret|otp|captcha|jwt|session|cookie|"
                         r"refresh|credential|authorization|apikey|api_key|signature|private_key)", re.I)
JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
CHUOI_DAI = re.compile(r"\b[A-Za-z0-9+/_-]{48,}={0,2}\b")
LOAI_GHI = ("xhr", "fetch", "document", "eventsource", "websocket", "other")


# ---------------------------------------------------------------- che mã phiên (chạy được cả khi không có Chrome)
def che_chuoi(s: str) -> str:
    s = JWT.sub("eyJ***", s)
    return CHUOI_DAI.sub(lambda m: m.group(0)[:6] + "***", s)


def che_url(u: str) -> str:
    try:
        p = urlsplit(u)
        q = [(k, "***" if KHOA_BI_MAT.search(k) else che_chuoi(v)) for k, v in parse_qsl(p.query, keep_blank_values=True)]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q, safe="*/:,"), che_chuoi(p.fragment)))
    except Exception:
        return che_chuoi(u)


def che_json(o, sau=0):
    if sau > 40:
        return "…"
    if isinstance(o, dict):
        return {k: ("***" if KHOA_BI_MAT.search(str(k)) and o[k] not in (None, "", [], {}) else che_json(v, sau + 1))
                for k, v in o.items()}
    if isinstance(o, list):
        ra = [che_json(v, sau + 1) for v in o[:8]]
        if len(o) > 8:
            ra.append(f"… (+{len(o) - 8} phần tử, tổng {len(o)})")
        return ra
    if isinstance(o, str):
        return che_chuoi(o[:600]) + ("…" if len(o) > 600 else "")
    return o


def che_than(chu: str, ct: str):
    """Thân yêu cầu/phản hồi -> đối tượng đã che: JSON thì che theo khóa, form thì che theo tên trường."""
    if not chu:
        return None
    chu = chu[: MAU_PHAN_HOI_KB * 1024 * 4]
    try:
        return che_json(json.loads(chu))
    except Exception:
        pass
    if "=" in chu and "&" in chu and "\n" not in chu[:200]:
        try:
            return {k: ("***" if KHOA_BI_MAT.search(k) else che_chuoi(v[:300])) for k, v in parse_qsl(chu, keep_blank_values=True)}
        except Exception:
            pass
    return che_chuoi(chu[: MAU_PHAN_HOI_KB * 1024])


def mo_ta_header(h: dict) -> dict:
    """Chỉ giữ TÊN header + giá trị vô hại; header xác thực ghi kiểu và độ dài, cookie bỏ hẳn."""
    ra = {}
    for k, v in (h or {}).items():
        kl = k.lower()
        if kl in ("cookie", "set-cookie"):
            ra[k] = f"(bỏ, {len(v)} ký tự)"
        elif KHOA_BI_MAT.search(kl) or kl.startswith("x-auth") or kl in ("x-token", "token"):
            kieu = v.split(" ", 1)[0] if " " in v else ""
            ra[k] = f"({kieu + ' ' if kieu else ''}{len(v)} ký tự)"
        elif kl in ("content-type", "accept", "x-requested-with", "origin", "referer", "content-disposition") \
                or kl.startswith("x-"):
            ra[k] = che_chuoi(che_url(v) if kl == "referer" else v)[:200]
    return ra


def bo_dau(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.replace("đ", "d").replace("Đ", "D")).strip().lower()


def nen_di(chu: str, href: str) -> bool:
    """Liên kết có nên tự đi theo không: cùng máy chủ egov, chữ có từ khóa văn bản, không có chữ thao tác."""
    c = " " + bo_dau(chu) + " "
    h = bo_dau(href)
    if not href or href.startswith(("javascript:", "mailto:", "tel:")) or href == "#":
        return False
    if urlsplit(href).netloc and "laocai.gov.vn" not in urlsplit(href).netloc and urlsplit(href).netloc != MAY_CHU:
        return False
    if any(f" {t} " in c or (len(t) >= 4 and t.replace(" ", "") in h.replace("-", "").replace("_", "")) for t in TU_CAM):
        return False
    # chữ: khớp nguyên từ ("di" không được khớp "dien"); đường dẫn: chỉ từ khóa dài, bỏ gạch nối
    return any(f" {t} " in c for t in TU_KHOA_DI) or any(
        len(t) >= 5 and t.replace(" ", "") in h.replace("-", "").replace("_", "") for t in TU_KHOA_DI)


def nhom_duong(u: str) -> str:
    """/api/van-ban/12345/attach?x=1 -> /api/van-ban/{so}/attach : gom các yêu cầu cùng khuôn."""
    p = urlsplit(u).path
    p = re.sub(r"/\d{2,}(?=/|$)", "/{so}", p)
    p = re.sub(r"/[0-9a-fA-F-]{32,36}(?=/|$)", "/{guid}", p)
    return f"{urlsplit(u).netloc}{p}"


# ---------------------------------------------------------------- tự kiểm tra (máy ảo Windows, không Chrome)
def chay_thu() -> int:
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnopqrstuvwxyz012345"
    loi = []
    u = che_url(f"https://egov1.laocai.gov.vn/api/x?access_token={jwt}&trang=2&q=Phú Thịnh")
    if jwt in u or "trang=2" not in u:
        loi.append("che_url: " + u)
    j = che_json({"data": [{"soKyHieu": "123/SCT-CN", "token": "abc"}], "password": "x", "ghiChu": jwt})
    s = json.dumps(j, ensure_ascii=False)
    if "abc" in s or jwt in s or "123/SCT-CN" not in s:
        loi.append("che_json: " + s)
    h = mo_ta_header({"Authorization": "Bearer " + jwt, "Cookie": "ASP.NET_SessionId=xyz", "Content-Type": "application/json"})
    if jwt in json.dumps(h) or "xyz" in json.dumps(h) or h.get("Content-Type") != "application/json":
        loi.append("mo_ta_header: " + json.dumps(h))
    if not nen_di("Văn bản đến", "/vanban/den") or nen_di("Đăng xuất", "/logout") or nen_di("Xóa văn bản", "/vb/xoa"):
        loi.append("nen_di sai")
    if nen_di("Trang Google", "https://google.com/vanban"):
        loi.append("nen_di đi ra ngoài laocai.gov.vn")
    if nhom_duong("https://egov1.laocai.gov.vn/api/vb/123456/files") != "egov1.laocai.gov.vn/api/vb/{so}/files":
        loi.append("nhom_duong sai")
    t = che_than("username=trang&password=bimat&captcha=1234", "application/x-www-form-urlencoded")
    if "bimat" in json.dumps(t, ensure_ascii=False) or "1234" in json.dumps(t):
        loi.append("che_than form: " + json.dumps(t, ensure_ascii=False))
    for x in loi:
        print("LOI:", x)
    print("CHAY THU egov_soi.py:", "OK" if not loi else f"{len(loi)} loi")
    return 0 if not loi else 1


# ---------------------------------------------------------------- phần chạy trên máy (cần Chrome + Playwright)
def nap_bot():
    duong = Path(__file__).resolve().parent / "bot-data360x.py"
    spec = importlib.util.spec_from_file_location("botd", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GhiChep:
    def __init__(self, thu_muc: Path, log):
        self.d = thu_muc
        self.log = log
        self.api = []
        self.trang = []
        self.dieu_huong = []
        self.dang_nhap = {}
        self._khoa = threading.Lock()
        (self.d / "trang").mkdir(parents=True, exist_ok=True)
        (self.d / "anh").mkdir(parents=True, exist_ok=True)

    def tren_phan_hoi(self, resp):
        try:
            req = resp.request
            if req.resource_type not in LOAI_GHI:
                return
            u = resp.url
            if not u.startswith("http"):
                return
            ct = (resp.headers.get("content-type") or "").lower()
            ban = {"luc": datetime.now().strftime("%H:%M:%S"), "phuong_thuc": req.method, "loai": req.resource_type,
                   "url": che_url(u), "khuon": nhom_duong(u), "trang_thai": resp.status, "content_type": ct[:80],
                   "header_gui": mo_ta_header(req.headers), "header_nhan": mo_ta_header(resp.headers)}
            try:
                if req.post_data:
                    ban["than_gui"] = che_than(req.post_data, req.headers.get("content-type", ""))
            except Exception:
                pass
            if "json" in ct or "javascript" not in ct and ("text/plain" in ct or "xml" in ct):
                try:
                    ban["mau_phan_hoi"] = che_than(resp.text(), ct)
                except Exception as e:
                    ban["mau_phan_hoi"] = f"(không đọc được: {str(e)[:80]})"
            elif any(x in ct for x in ("pdf", "octet-stream", "msword", "officedocument", "zip", "image/")):
                ban["tep"] = {"content_disposition": che_chuoi(resp.headers.get("content-disposition", ""))[:200],
                              "do_dai": resp.headers.get("content-length", "")}
            with self._khoa:
                if len(self.api) < API_TOI_DA:
                    self.api.append(ban)
        except Exception:
            pass

    def chup(self, page, nhan: str):
        """Chụp trang hiện tại: địa chỉ, tiêu đề, menu, bảng, ảnh, HTML (đã che mã phiên)."""
        so = len(self.trang) + 1
        ten = f"{so:02d}-{re.sub(r'[^a-z0-9]+', '-', bo_dau(nhan))[:40].strip('-') or 'trang'}"
        muc = {"so": so, "nhan": nhan, "url": che_url(page.url), "luc": datetime.now().strftime("%H:%M:%S")}
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        try:
            muc["tieu_de"] = page.title()
        except Exception:
            pass
        try:
            muc.update(page.evaluate(JS_DOC_TRANG))
        except Exception as e:
            muc["loi_doc"] = str(e)[:150]
        try:
            html = che_chuoi(page.content())
            (self.d / "trang" / f"{ten}.html").write_text(html[: HTML_TOI_DA_KB * 1024], encoding="utf-8")
            muc["html"] = f"trang/{ten}.html"
        except Exception:
            pass
        try:
            page.screenshot(path=str(self.d / "anh" / f"{ten}.jpg"), type="jpeg", quality=55)
            muc["anh"] = f"anh/{ten}.jpg"
        except Exception:
            pass
        self.trang.append(muc)
        self.log(f"  [{so:02d}] {nhan[:50]} -> {muc.get('url', '')[:90]} | bảng: {len(muc.get('bang', []))}")
        return muc


# Đọc trong trang: menu/liên kết, ô nhập, bảng (tiêu đề + 3 dòng đầu), khung iframe, tên khóa bộ nhớ trình duyệt.
JS_DOC_TRANG = r"""
() => {
  const sach = s => (s || '').replace(/\s+/g, ' ').trim().slice(0, 160);
  const lk = [];
  document.querySelectorAll('a[href], [role=menuitem], [routerlink], [ng-reflect-router-link], li[onclick], [data-href]').forEach(a => {
    if (lk.length >= 300) return;
    const href = a.getAttribute('href') || a.getAttribute('routerlink') || a.getAttribute('ng-reflect-router-link')
               || a.getAttribute('data-href') || '';
    const chu = sach(a.innerText || a.getAttribute('title') || a.getAttribute('aria-label'));
    if (chu || href) lk.push({chu, href, the: a.tagName.toLowerCase(), lop: sach(a.className && a.className.baseVal === undefined ? a.className : '')});
  });
  const bang = [];
  document.querySelectorAll('table').forEach(t => {
    if (bang.length >= 6) return;
    const th = [...t.querySelectorAll('thead th, thead td')].map(x => sach(x.innerText));
    const dong = [...t.querySelectorAll('tbody tr')].slice(0, 3).map(tr =>
      [...tr.querySelectorAll('td')].map(td => {
        const a = td.querySelector('a[href]');
        return sach(td.innerText) + (a ? ' ⟨' + a.getAttribute('href') + '⟩' : '');
      }));
    const so_dong = t.querySelectorAll('tbody tr').length;
    if (th.length || dong.length) bang.push({lop: sach(t.className), tieu_de: th, dong_dau: dong, so_dong});
  });
  // lưới dạng div (DevExtreme, ag-grid, Kendo...) không dùng <table>
  const luoi = [...document.querySelectorAll('[role=grid], .dx-datagrid, .ag-root, .k-grid, .p-datatable, .ant-table, .el-table, .mat-table')]
      .slice(0, 4).map(g => ({lop: sach(g.className), chu: sach(g.innerText).slice(0, 600)}));
  const o_nhap = [...document.querySelectorAll('input, select, textarea')].slice(0, 60).map(i => ({
      the: i.tagName.toLowerCase(), kieu: i.type || '', ten: i.name || '', id: i.id || '',
      goi_y: sach(i.placeholder || i.getAttribute('aria-label') || '')}));
  const nut = [...document.querySelectorAll('button, [role=button], input[type=button], input[type=submit]')].slice(0, 80)
      .map(b => sach(b.innerText || b.value || b.title || b.getAttribute('aria-label'))).filter(x => x);
  const khung = [...document.querySelectorAll('iframe, frame')].map(f => f.getAttribute('src') || '');
  const kho = o => { try { return Object.keys(o).map(k => ({khoa: k, do_dai: (o.getItem(k) || '').length})); } catch (e) { return []; } };
  const thu_vien = [];
  if (window.angular) thu_vien.push('angularjs ' + (window.angular.version || {}).full);
  if (window.ng || document.querySelector('[ng-version]')) thu_vien.push('angular ' + ((document.querySelector('[ng-version]') || {}).getAttribute ? document.querySelector('[ng-version]').getAttribute('ng-version') : ''));
  if (window.React || document.querySelector('[data-reactroot], #__next')) thu_vien.push('react/next');
  if (window.Vue || document.querySelector('[data-v-app], #app[data-v-]')) thu_vien.push('vue');
  if (window.jQuery) thu_vien.push('jquery ' + window.jQuery.fn.jquery);
  if (window.DevExpress) thu_vien.push('devextreme');
  if (window.kendo) thu_vien.push('kendo');
  const script = [...document.querySelectorAll('script[src]')].map(s => s.getAttribute('src')).slice(0, 40);
  return {lien_ket: lk, bang, luoi, o_nhap, nut, khung, thu_vien, script,
          localStorage: kho(window.localStorage), sessionStorage: kho(window.sessionStorage),
          dau_trang: sach(document.body ? document.body.innerText : '').slice(0, 700)};
}
"""


def la_trang_dang_nhap(page) -> bool:
    u = page.url.lower()
    if MAY_CHU not in u:
        return True          # đang ở SSO / trang ngoài
    if any(x in u for x in ("login", "dang-nhap", "dangnhap", "signin", "/sso", "account/log")):
        return True
    try:
        return page.locator("input[type=password]:visible").count() > 0
    except Exception:
        return False


def cho_dang_nhap(page, log, thong_bao) -> bool:
    if not la_trang_dang_nhap(page):
        return True
    log("Cần đăng nhập EGOV: Bạn đăng nhập trong cửa sổ Chrome vừa mở (nhập mã xác thực như thường).")
    print("\n>>> Đăng nhập EGOV trong cửa sổ Chrome. Thấy trang chủ EGOV là bot tự chạy tiếp, không cần bấm gì ở đây.\n")
    thong_bao("Soi EGOV", "Hãy đăng nhập EGOV trong cửa sổ Chrome vừa mở, bot sẽ tự chạy tiếp.")
    het = time.time() + CHO_DANG_NHAP_PHUT * 60
    while time.time() < het:
        page.wait_for_timeout(5000)
        if not la_trang_dang_nhap(page):
            page.wait_for_timeout(4000)
            log("Đã đăng nhập EGOV.")
            return True
    log(f"Quá {CHO_DANG_NHAP_PHUT} phút chưa đăng nhập.")
    return False


def tu_di(ctx, page, ghi: GhiChep, log):
    """Pha 1: đi theo liên kết menu có chữ văn bản/đến/đi/xử lý..., mở thử dòng đầu của mỗi bảng."""
    da_di = {che_url(page.url)}
    goc = ghi.chup(page, "trang chu")
    hang = []
    for lk in goc.get("lien_ket", []):
        href = lk.get("href", "")
        if nen_di(lk.get("chu", ""), href):
            hang.append((lk.get("chu", "") or href, urljoin(page.url, href)))
    log(f"Pha 1: {len(hang)} liên kết menu đáng đi.")
    so_trang = 0
    while hang and so_trang < TU_DI_TOI_DA:
        nhan, u = hang.pop(0)
        if che_url(u) in da_di:
            continue
        da_di.add(che_url(u))
        try:
            page.goto(u, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
        except Exception as e:
            log(f"  không mở được {u[:80]}: {str(e)[:80]}")
            continue
        if la_trang_dang_nhap(page):
            log("  bị đưa về trang đăng nhập - dừng tự đi.")
            return
        so_trang += 1
        muc = ghi.chup(page, nhan)
        # mở thử văn bản đầu tiên của bảng (liên kết trong dòng đầu), để thấy trang chi tiết + API tệp đính kèm
        for b in muc.get("bang", [])[:2]:
            for dong in b.get("dong_dau", [])[:1]:
                for o in dong:
                    m = re.search(r"⟨([^⟩]+)⟩", o)
                    if m and nen_di("van ban", m.group(1)):
                        hang.insert(0, (f"{nhan} - chi tiet dong dau", urljoin(page.url, m.group(1))))
                        break
        # menu con xuất hiện ở trang mới
        for lk in muc.get("lien_ket", []):
            href = lk.get("href", "")
            if nen_di(lk.get("chu", ""), href) and che_url(urljoin(page.url, href)) not in da_di:
                hang.append((lk.get("chu", "") or href, urljoin(page.url, href)))


def ban_tu_bam(ctx, page, ghi: GhiChep, log, phut: int):
    """Pha 2: Bạn tự bấm; mỗi lần trang chính đổi địa chỉ thì chụp lại."""
    print("\n" + "=" * 70)
    print(f"  PHA 2 - BẠN TỰ BẤM TRONG CHROME ({phut} phút, xong sớm thì bấm Enter ở đây)")
    print("  1. Văn bản đến -> mở 1 văn bản bất kỳ -> bấm xem / tải tệp đính kèm (PDF)")
    print("  2. Văn bản đi  -> mở 1 văn bản bất kỳ -> bấm xem / tải tệp đính kèm")
    print("  3. Mục việc CHỜ XỬ LÝ của Bạn (danh sách việc Lãnh đạo giao)")
    print("  4. Ô TÌM KIẾM: gõ thử một số ký hiệu, ví dụ 6468/SCT-CN, bấm tìm")
    print("  KHÔNG bấm Chuyển, Ký, Hoàn thành... - bot chỉ ghi lại, không cần thao tác hồ sơ.")
    print("=" * 70 + "\n")
    xong = threading.Event()

    def _cho_enter():
        try:
            input()
        except Exception:
            return
        xong.set()

    threading.Thread(target=_cho_enter, daemon=True).start()
    het = time.time() + phut * 60
    url_cu = page.url
    trang_hien = page

    while time.time() < het and not xong.is_set():
        try:
            if ctx.pages:
                trang_hien = ctx.pages[-1]          # tab mới mở (xem văn bản) thì theo tab đó
            trang_hien.wait_for_timeout(2000)
            if trang_hien.url != url_cu and "about:blank" not in trang_hien.url:
                url_cu = trang_hien.url
                trang_hien.wait_for_timeout(2500)
                ghi.chup(trang_hien, "ban bam " + (trang_hien.title() or "")[:40])
        except Exception as e:
            if "closed" in str(e).lower() and not ctx.pages:
                log("Chrome đã đóng - kết thúc pha 2.")
                break
            time.sleep(2)
    try:
        if ctx.pages:
            ghi.chup(ctx.pages[-1], "ket thuc")
    except Exception:
        pass


def viet_readme(ghi: GhiChep, may: str) -> str:
    khuon = {}
    for a in ghi.api:
        k = (a["phuong_thuc"], a["khuon"])
        khuon.setdefault(k, {"so": 0, "trang_thai": set(), "ct": set(), "vd": a["url"], "auth": set()})
        khuon[k]["so"] += 1
        khuon[k]["trang_thai"].add(str(a["trang_thai"]))
        khuon[k]["ct"].add(a["content_type"].split(";")[0])
        for h, v in a.get("header_gui", {}).items():
            if "ký tự)" in str(v) and h.lower() not in ("cookie",):
                khuon[k]["auth"].add(h)
    dong = [f"# Soi EGOV — {datetime.now().strftime('%d/%m/%Y %H:%M')} ({may})", "",
            f"{len(ghi.trang)} trang đã chụp, {len(ghi.api)} yêu cầu mạng, {len(khuon)} khuôn đường dẫn.",
            "Mã phiên, mật khẩu, cookie đã che (chỉ còn tên và độ dài). Tệp: `trang.json` (menu, bảng, ô nhập, khóa bộ nhớ "
            "trình duyệt của từng trang), `api.jsonl` (từng yêu cầu, mẫu phản hồi cắt ngắn), `trang/*.html`, `anh/*.jpg`.", "",
            "## Các trang đã đi qua", "", "| # | Nhãn | Địa chỉ | Tiêu đề cột bảng đầu |", "|---|---|---|---|"]
    for t in ghi.trang:
        b = (t.get("bang") or [{}])[0].get("tieu_de", [])
        dong.append(f"| {t['so']} | {t['nhan'][:40]} | `{t.get('url', '')[:90]}` | {', '.join(b)[:120]} |")
    dong += ["", "## Khuôn yêu cầu tới máy chủ (nhiều lần nhất trước)", "",
             "| Lần | PT | Khuôn | Mã | Kiểu | Header xác thực |", "|---|---|---|---|---|---|"]
    for (pt, k), v in sorted(khuon.items(), key=lambda x: -x[1]["so"])[:150]:
        if any(x in k for x in (".js", ".css", ".png", ".woff", ".svg", ".ico", ".jpg", ".gif")):
            continue
        dong.append(f"| {v['so']} | {pt} | `{k[:110]}` | {','.join(sorted(v['trang_thai']))} | "
                    f"{','.join(sorted(v['ct']))[:40]} | {','.join(sorted(v['auth']))} |")
    tv = sorted({x for t in ghi.trang for x in t.get("thu_vien", [])})
    dong += ["", f"Thư viện giao diện nhận ra: {', '.join(tv) or 'không rõ'}", ""]
    return "\n".join(dong)


def chay(phut: int, khong_day: bool) -> int:
    from playwright.sync_api import sync_playwright
    bot = nap_bot()
    log = bot.log
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    d = bot.LOG_DIR / "soi-egov" / stamp
    ghi = GhiChep(d, log)
    log(f"SOI EGOV bắt đầu, lưu tại {d}")
    with sync_playwright() as p:
        ctx = bot.mo_trinh_duyet(p, headless=os.environ.get("EGOV_AN") == "1")
        ctx.on("response", ghi.tren_phan_hoi)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(4000)
            ghi.chup(page, "mo dau (truoc dang nhap)")
            if not cho_dang_nhap(page, log, bot.thong_bao_windows):
                ghi.chup(page, "chua dang nhap")
            else:
                if page.url.rstrip("/") == GOC_EGOV:
                    page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
                tu_di(ctx, page, ghi, log)
                try:
                    page.goto(TRANG_CHU, wait_until="domcontentloaded", timeout=90000)
                except Exception:
                    pass
                ban_tu_bam(ctx, page, ghi, log, phut)
        except Exception as e:
            log("LỖI khi soi:", repr(e)[:300])
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    may = bot.thong_tin_may().get("may", "")
    # che thêm một lượt trên chuỗi JSON: liên kết, mẫu phản hồi còn sót mã phiên dài thì cũng bị cắt
    (d / "trang.json").write_text(che_chuoi(json.dumps(ghi.trang, ensure_ascii=False, indent=1)), encoding="utf-8")
    (d / "api.jsonl").write_text("\n".join(che_chuoi(json.dumps(a, ensure_ascii=False)) for a in ghi.api), encoding="utf-8")
    (d / "README.md").write_text(viet_readme(ghi, may), encoding="utf-8")
    log(f"Đã ghi {len(ghi.trang)} trang, {len(ghi.api)} yêu cầu mạng.")
    if khong_day:
        log("--khong-day: không đẩy GitHub.")
        return 0
    token = bot.doc_config().get("github_token", "")
    if not token:
        log("Chưa có token GitHub trong config.json - kết quả chỉ nằm trên máy:", d)
        return 1
    tong, loi = 0, 0
    # README + trang.json + api.jsonl trước (quan trọng nhất), rồi HTML, ảnh tới khi chạm trần dung lượng
    tep = [d / "README.md", d / "trang.json", d / "api.jsonl"] + sorted((d / "trang").glob("*.html")) + sorted((d / "anh").glob("*.jpg"))
    for f in tep:
        b = f.read_bytes()
        if tong + len(b) > DAY_TOI_DA_MB * 1024 * 1024:
            log(f"  chạm trần {DAY_TOI_DA_MB} MB - bỏ {f.name}")
            continue
        duong = f"{THU_MUC_DAY}/{stamp}/{f.relative_to(d).as_posix()}"
        try:
            bot.gh_ghi_de(REPO_RIENG, duong, b, f"Soi EGOV {stamp}: {f.name} ({may})", token)
            tong += len(b)
        except Exception as e:
            loi += 1
            log(f"  không đẩy được {f.name}: {str(e)[:120]}")
    log(f"Đã đẩy {tong // 1024} KB lên {REPO_RIENG}/{THU_MUC_DAY}/{stamp}/ ({loi} tệp lỗi).")
    bot.telegram(f"Soi EGOV xong: {len(ghi.trang)} trang, {len(ghi.api)} yêu cầu mạng -> {THU_MUC_DAY}/{stamp}/")
    return 0 if loi == 0 else 2


def main():
    ap = argparse.ArgumentParser(description="Soi cấu trúc EGOV (egov1.laocai.gov.vn) để dựng bot mới")
    ap.add_argument("--phut", type=int, default=10, help="thời gian Bạn tự bấm ở pha 2 (mặc định 10)")
    ap.add_argument("--khong-day", action="store_true", help="không đẩy lên GitHub")
    ap.add_argument("--chay-thu", action="store_true", help="tự kiểm tra, không mở Chrome (máy ảo Windows)")
    a = ap.parse_args()
    if a.chay_thu:
        return chay_thu()
    return chay(a.phut, a.khong_day)


if __name__ == "__main__":
    sys.exit(main())

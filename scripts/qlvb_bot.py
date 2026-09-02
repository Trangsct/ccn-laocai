"""
Bot đọc văn bản mới trên qlvb.yenbai.gov.vn và ghi ra JSON cho 2 trang web
(congnghieplaocai.vn - repo ccn-laocai; vlncn-laocai.vercel.app - repo vlncn-laocai).

Luồng:
  1. Mở QLVB. Hệ thống chuyển hướng sang cổng đăng nhập tập trung login.yenbai.gov.vn
     (OAuth2 / SSO). Bot điền tài khoản từ biến môi trường QLVB_USER / QLVB_PASS.
  2. Mở danh sách Văn bản đến + Văn bản đi, đọc các dòng trong bảng.
  3. Giữ lại văn bản có ngày >= hôm qua (giờ VN) và độ mật = Thường.
  4. Phân loại theo từ khóa trong trích yếu -> kccn / vlncn.
  5. Gộp vào van-ban-moi.json (gốc repo ccn-laocai), không trùng số văn bản,
     giữ tối đa 200 văn bản mới nhất. Phần VLNCN ghi ra bot-output/van-ban-moi-vlncn.json
     để workflow đẩy sang repo vlncn-laocai.

Chế độ SOI GIAO DIỆN (--soi, hoặc tự bật khi chưa có QLVB_USER):
  chỉ chụp ảnh + lưu HTML từng bước vào bot-output/ để hoàn thiện selector, KHÔNG ghi dữ liệu.
  Mọi lần chạy đều lưu ảnh/HTML để soi lỗi; workflow tải chúng lên làm artifact.

Các chỗ đánh dấu [CHỜ HTML] là selector đoán theo giao diện ZK / WSO2 chuẩn,
cần đối chiếu với HTML thật lấy từ artifact của lần chạy soi giao diện.
"""

import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

QLVB_URL = "https://qlvb.yenbai.gov.vn/index.zul"
TZ_VN = timezone(timedelta(hours=7))
OUT_DIR = Path("bot-output")
OUT_DIR.mkdir(exist_ok=True)
FILE_KCCN = Path("van-ban-moi.json")               # gốc repo ccn-laocai
FILE_VLNCN = OUT_DIR / "van-ban-moi-vlncn.json"    # workflow đẩy sang repo vlncn-laocai
GIU_TOI_DA = 200
CHE_DO_SOI = "--soi" in sys.argv or not os.environ.get("QLVB_USER")

# Từ khóa phân loại (so khớp cả có dấu và không dấu, không phân biệt hoa thường)
TU_KHOA = {
    "kccn": [
        "khu công nghiệp", "cụm công nghiệp", "kcn", "ccn", "hạ tầng kỹ thuật cụm",
        "chủ đầu tư hạ tầng", "nghị định 32/2024", "nghị định 303/2026",
    ],
    "vlncn": [
        "vật liệu nổ", "vlncn", "nổ mìn", "tiền chất thuốc nổ", "thuốc nổ",
        "kho vật liệu nổ", "huấn luyện kỹ thuật an toàn", "hộ chiếu nổ mìn",
    ],
}

# Selector ứng viên cho trang đăng nhập SSO (WSO2 Identity Server) và trang ZK.
# Thử lần lượt, cái nào có trên trang thì dùng. [CHỜ HTML]
SEL_USER = ["#usernameUserInput", "input[name='username']", "#username",
            "input[type='text']:visible", "input[type='email']:visible"]
SEL_PASS = ["#password", "input[name='password']", "input[type='password']:visible"]
SEL_NUT = ["#loginBtn", "button[type='submit']", "input[type='submit']",
           "button:has-text('Đăng nhập')", "button:has-text('Login')", "button:has-text('Sign in')"]


def bo_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def ten_file(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", bo_dau(s)).strip("-")


def luu(page, ten: str):
    """Chụp ảnh + lưu HTML của trang hiện tại để soi lỗi / soi giao diện."""
    try:
        page.screenshot(path=str(OUT_DIR / f"{ten}.png"), full_page=True)
        html = page.content()
        (OUT_DIR / f"{ten}.html").write_text(html, encoding="utf-8")
        print(f"  [luu] {ten}: {page.url}")
        if CHE_DO_SOI:
            # In cấu trúc form ra log để hoàn thiện selector mà không cần tải artifact
            print(f"  [soi] title: {page.title()}")
            for tag in re.findall(r"<(?:form|input|button|select|textarea)\b[^>]*>", html, flags=re.I)[:60]:
                print("  [soi]", re.sub(r"\s+", " ", tag)[:300])
            for tag in re.findall(r"<img\b[^>]*>", html, flags=re.I)[:30]:
                print("  [img]", re.sub(r"\s+", " ", tag)[:300])
            for m in re.findall(r"<(?:label|a|span|td)\b[^>]*>([^<]{3,80})</", html, flags=re.I)[:80]:
                m = m.strip()
                if m:
                    print("  [chu]", m)
            # Captcha: có hiện không, ảnh lấy từ đâu
            try:
                cap = page.locator("#captcha")
                if cap.count():
                    print("  [captcha] o nhap hien thi:", cap.first.is_visible())
                for s in ("#captchaImg", "img[src*='captcha' i]", "img[id*='captcha' i]", "img[alt*='captcha' i]"):
                    im = page.locator(s)
                    if im.count():
                        print(f"  [captcha] anh {s}: visible={im.first.is_visible()} src={(im.first.get_attribute('src') or '')[:200]}")
                        try:
                            im.first.screenshot(path=str(OUT_DIR / f"{ten}-captcha.png"))
                        except Exception:
                            pass
                # Đoạn JS xử lý captcha / submit để biết cơ chế tải ảnh mới
                for js in re.findall(r"(?:function\s+(?:submitCredentials|reloadCaptcha|refreshCaptcha|loadCaptcha)[^{]*\{[\s\S]{0,900})", html):
                    print("  [js]", re.sub(r"\s+", " ", js)[:900])
                for u in sorted(set(re.findall(r"['\"]([^'\"]*captcha[^'\"]*)['\"]", html, flags=re.I)))[:20]:
                    print("  [captcha-url]", u[:200])
            except Exception as e:
                print("  [captcha] loi soi:", e)
    except Exception as e:  # không để việc lưu ảnh làm hỏng luồng chính
        print(f"  [luu] {ten}: loi {e}")


def chon_selector(page, ds: list[str]):
    for s in ds:
        try:
            loc = page.locator(s).first
            if loc.count() and loc.is_visible():
                return loc, s
        except Exception:
            pass
    return None, None


def phan_loai(trich_yeu: str) -> list[str]:
    ty = trich_yeu.lower()
    ty_kd = bo_dau(trich_yeu)
    return [ten for ten, ds in TU_KHOA.items()
            if any(k in ty or bo_dau(k) in ty_kd for k in ds)]


def parse_ngay(s: str):
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s or "")
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
        except ValueError:
            return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
    return None


def dang_nhap(page):
    page.goto(QLVB_URL, wait_until="networkidle", timeout=90000)
    luu(page, "01-trang-dang-nhap")
    print("URL sau khi mở QLVB:", page.url)

    if CHE_DO_SOI and not os.environ.get("QLVB_USER"):
        print("Chưa có QLVB_USER -> chỉ soi trang đăng nhập, dừng tại đây.")
        return False

    o_user, s1 = chon_selector(page, SEL_USER)
    o_pass, s2 = chon_selector(page, SEL_PASS)
    if not o_user or not o_pass:
        print(f"KHÔNG tìm thấy ô đăng nhập (user={s1}, pass={s2}). Xem 01-trang-dang-nhap.html")
        return False
    print(f"Dùng selector: user={s1}, pass={s2}")
    o_user.fill(os.environ["QLVB_USER"])
    o_pass.fill(os.environ["QLVB_PASS"])
    nut, s3 = chon_selector(page, SEL_NUT)
    if nut:
        nut.click()
    else:
        page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle", timeout=90000)
    # Một số cổng SSO có bước "đồng ý cấp quyền" (consent) lần đầu
    ok, _ = chon_selector(page, ["button:has-text('Approve')", "input[value='Approve']",
                                 "button:has-text('Đồng ý')", "#approve"])
    if ok:
        ok.click()
        page.wait_for_load_state("networkidle", timeout=90000)
    luu(page, "02-sau-dang-nhap")
    print("URL sau khi đăng nhập:", page.url)
    if "login.yenbai.gov.vn" in page.url:
        print("Vẫn ở trang đăng nhập -> sai tài khoản hoặc cần captcha. Xem 02-sau-dang-nhap.png")
        return False
    return True


def doc_bang(page, ten_muc: str) -> list[dict]:
    """Mở mục Văn bản đến / Văn bản đi và đọc từng dòng của bảng."""
    ten = ten_file(ten_muc)
    # [CHỜ HTML] Cách mở menu: thử bấm vào chữ trên menu trái / tab.
    muc, _ = chon_selector(page, [f"text={ten_muc}", f"a:has-text('{ten_muc}')",
                                  f"span:has-text('{ten_muc}')", f"td:has-text('{ten_muc}')"])
    if not muc:
        print(f"Không thấy mục '{ten_muc}' trên trang. Bỏ qua.")
        return []
    muc.click()
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(3000)   # ZK vẽ bảng bằng AJAX sau khi tải xong
    luu(page, f"03-{ten}")

    ket_qua = []
    # [CHỜ HTML] ZK listbox / grid: hàng là tr.z-listitem hoặc tr.z-row
    rows = page.locator("tr.z-listitem, tr.z-row, table tbody tr")
    n = rows.count()
    tho = []
    for i in range(n):
        cells = rows.nth(i).locator("td")
        txt = [cells.nth(j).inner_text().strip() for j in range(cells.count())]
        tho.append(txt)
        if len(txt) < 4:
            continue
        # [CHỜ HTML] Sửa chỉ số cột: số ký hiệu, ngày, cơ quan, trích yếu, độ mật
        ket_qua.append({
            "so_ky_hieu": txt[0],
            "ngay": txt[1],
            "co_quan": txt[2],
            "trich_yeu": txt[3],
            "do_mat": txt[4] if len(txt) > 4 else "Thường",
            "nguon": ten_muc,
        })
    (OUT_DIR / f"bang-tho-{ten}.json").write_text(
        json.dumps(tho, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{ten_muc}: {n} hàng, {len(ket_qua)} hàng đủ cột")
    return ket_qua


def main():
    hom_qua = datetime.now(TZ_VN).date() - timedelta(days=1)
    moi = []
    print("Chế độ:", "SOI GIAO DIỆN" if CHE_DO_SOI else "CẬP NHẬT")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900},
                                locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh")
        try:
            if dang_nhap(page):
                for muc in ("Văn bản đến", "Văn bản đi"):
                    moi.extend(doc_bang(page, muc))
            elif not CHE_DO_SOI:
                sys.exit(1)
        except PWTimeout as e:
            luu(page, "99-loi-timeout")
            print("LOI TIMEOUT:", e)
            sys.exit(1)
        finally:
            browser.close()

    print(f"Đọc được {len(moi)} dòng từ QLVB")
    if CHE_DO_SOI:
        print("Chế độ soi giao diện: không ghi dữ liệu. Xem artifact bot-output.")
        return

    chon = []
    for vb in moi:
        d = parse_ngay(vb["ngay"])
        if not d or d < hom_qua:
            continue
        if vb["do_mat"] and "thường" not in vb["do_mat"].lower():
            continue                      # bỏ mọi độ mật khác Thường
        nhom = phan_loai(vb["trich_yeu"])
        if not nhom:
            continue
        vb["ngay"] = d.isoformat()
        vb["nhom"] = nhom
        vb["cap_nhat"] = datetime.now(TZ_VN).strftime("%Y-%m-%d %H:%M")
        chon.append(vb)
    print(f"Văn bản mới thuộc lĩnh vực theo dõi: {len(chon)}")

    # Gộp vào file kccn hiện có
    cu = json.loads(FILE_KCCN.read_text(encoding="utf-8")) if FILE_KCCN.exists() else []
    da_co = {v["so_ky_hieu"] for v in cu}
    them_kccn = [v for v in chon if "kccn" in v["nhom"] and v["so_ky_hieu"] not in da_co]
    if them_kccn:
        FILE_KCCN.write_text(
            json.dumps((them_kccn + cu)[:GIU_TOI_DA], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"KCCN thêm mới: {len(them_kccn)}")

    them_vlncn = [v for v in chon if "vlncn" in v["nhom"]]
    if them_vlncn:
        FILE_VLNCN.write_text(json.dumps(them_vlncn, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    print(f"VLNCN thêm mới: {len(them_vlncn)}")


if __name__ == "__main__":
    main()

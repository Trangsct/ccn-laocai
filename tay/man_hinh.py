# -*- coding: utf-8 -*-
"""
MÀN HÌNH - đôi mắt và ngón tay của TAY trên Windows (Bạn yêu cầu 22/11/2026: "viết thêm công cụ điều khiển màn hình").

Chỉ dùng ctypes (user32) và Pillow đã có sẵn; không cần pyautogui. Hai nơi dùng chung tệp này:
  - tay.py, yêu cầu {"loai": "man-hinh", "buoc": [...]} trong hàng đợi yeu-cau/ (Claude trên mạng, Routine)
  - man_hinh_mcp.py, máy chủ MCP cho Claude Code chạy NGAY trên máy (VS Code, terminal)

TỌA ĐỘ: mọi x, y là điểm ảnh trên ẢNH CHỤP TOÀN MÀN HÌNH do chup() trả về (đã thu về rộng tối đa RONG_TOI_DA),
không phải điểm ảnh thật. Tỉ lệ cố định theo kích thước màn hình nên không cần nhớ trạng thái giữa các lần gọi.
Ảnh phóng to một vùng (chup(vung=...)) chỉ để đọc chữ nhỏ; bấm vẫn theo tọa độ ảnh toàn màn hình.

Bước (dict, khóa "lam"):
  {"lam": "chup"}                                   chụp toàn màn hình
  {"lam": "chup", "vung": [x, y, rong, cao]}        phóng to một vùng (độ phân giải thật) để đọc chữ nhỏ
  {"lam": "bam", "x": 100, "y": 200}                bấm chuột trái; "nut": "phai"/"giua"; "lan": 2 = bấm đúp
  {"lam": "di", "x": 100, "y": 200}                 chỉ di chuột (rê để hiện chú thích, menu)
  {"lam": "keo", "x": 1, "y": 2, "x2": 3, "y2": 4}  giữ chuột trái kéo từ (x, y) tới (x2, y2)
  {"lam": "go", "chu": "Sở Công Thương"}            gõ chữ (Unicode, tiếng Việt có dấu; "\n" = Enter)
  {"lam": "phim", "phim": "ctrl+s"}                 phím / tổ hợp phím; "lan": 3 = bấm 3 lần
  {"lam": "cuon", "so": -5}                         cuộn chuột (âm = xuống); "x", "y" để cuộn tại một điểm
  {"lam": "cho", "giay": 2}                         chờ (tối đa 30 giây)
  {"lam": "cua-so", "tieu_de": "Google Drive"}      đưa cửa sổ có tiêu đề chứa chuỗi này lên trước

AN TOÀN (giữ nguyên các nguyên tắc của TAY):
  - DỪNG KHẨN: Bạn kéo chuột lên GÓC TRÊN BÊN TRÁI màn hình -> mọi bước còn lại bị hủy.
  - Không gõ mật khẩu, không tự đăng nhập, không giải captcha, không chuyển tiền, không mở liên kết lạ.
  - Màn hình đang khóa thì không làm gì (ảnh chụp sẽ đen, bấm vào màn khóa là vô ích).
  - Mỗi bước ghi nhật ký (chữ gõ chỉ ghi 40 ký tự đầu).
"""

import base64
import ctypes
import io
import os
import time
from ctypes import wintypes as W

RONG_TOI_DA = 1568          # Claude thu ảnh về cạnh dài 1568 điểm ảnh: gửi đúng cỡ đó, không phí và không mờ thêm
TOI_DA_BUOC = 60
TOI_DA_CHU = 4000
TOI_DA_CHO = 30
NUT = {"trai": (0x0002, 0x0004), "phai": (0x0008, 0x0010), "giua": (0x0020, 0x0040)}

LA_WINDOWS = os.name == "nt"
if LA_WINDOWS:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # Khai báo kiểu: mặc định ctypes coi mọi thứ là int 32 bit, handle trên Python 64 bit sẽ bị cắt
    for _ten, _vao, _ra in (("GetForegroundWindow", [], W.HWND), ("IsWindowVisible", [W.HWND], W.BOOL),
                            ("GetWindowTextLengthW", [W.HWND], ctypes.c_int),
                            ("GetWindowTextW", [W.HWND, W.LPWSTR, ctypes.c_int], ctypes.c_int),
                            ("GetWindowRect", [W.HWND, ctypes.POINTER(W.RECT)], W.BOOL),
                            ("IsIconic", [W.HWND], W.BOOL), ("ShowWindow", [W.HWND, ctypes.c_int], W.BOOL),
                            ("SetForegroundWindow", [W.HWND], W.BOOL),
                            ("GetWindowThreadProcessId", [W.HWND, ctypes.POINTER(W.DWORD)], W.DWORD),
                            ("OpenInputDesktop", [W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
                            ("SwitchDesktop", [W.HANDLE], W.BOOL), ("CloseDesktop", [W.HANDLE], W.BOOL),
                            ("SetCursorPos", [ctypes.c_int, ctypes.c_int], W.BOOL),
                            ("GetSystemMetrics", [ctypes.c_int], ctypes.c_int)):
        getattr(user32, _ten).argtypes, getattr(user32, _ten).restype = _vao, _ra
    for _ten, _vao, _ra in (("OpenProcess", [W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
                            ("QueryFullProcessImageNameW", [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)], W.BOOL),
                            ("CloseHandle", [W.HANDLE], W.BOOL)):
        getattr(kernel32, _ten).argtypes, getattr(kernel32, _ten).restype = _vao, _ra
    # Tọa độ thật (không bị Windows co giãn 125%, 150%): phải đặt trước mọi lệnh đo màn hình.
    try:
        ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


class DungKhan(Exception):
    """Bạn kéo chuột lên góc trên bên trái: dừng mọi bước còn lại."""


# ---------------------------------------------------------------- SendInput
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", W.LONG), ("dy", W.LONG), ("mouseData", W.DWORD), ("dwFlags", W.DWORD),
                ("time", W.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", W.WORD), ("wScan", W.WORD), ("dwFlags", W.DWORD), ("time", W.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", W.DWORD), ("wParamL", W.WORD), ("wParamH", W.WORD)]


class _UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", W.DWORD), ("u", _UNION)]


KEYUP, UNICODE, EXTENDED = 0x0002, 0x0004, 0x0001
VK = {"ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B, "cmd": 0x5B,
      "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "backspace": 0x08,
      "delete": 0x2E, "del": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23, "pageup": 0x21, "pgup": 0x21,
      "pagedown": 0x22, "pgdn": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "space": 0x20,
      "printscreen": 0x2C, "menu": 0x5D, "apps": 0x5D, "capslock": 0x14}
VK.update({f"f{i}": 0x6F + i for i in range(1, 13)})
VK_MO_RONG = {0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x5B, 0x5D}
DAU = {"-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF,
       "\\": 0xDC, "`": 0xC0}


def _gui(*ds):
    mang = (INPUT * len(ds))(*ds)
    if user32.SendInput(len(ds), mang, ctypes.sizeof(INPUT)) != len(ds):
        raise RuntimeError(f"SendInput bị chặn (mã {ctypes.get_last_error()}): cửa sổ đang chọn chạy quyền Administrator?")


def _phim_ao(vk, len_=False):
    co = (KEYUP if len_ else 0) | (EXTENDED if vk in VK_MO_RONG else 0)
    return INPUT(type=1, ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=co, time=0, dwExtraInfo=0))


def _chuot(co, du_lieu=0):
    return INPUT(type=0, mi=MOUSEINPUT(dx=0, dy=0, mouseData=du_lieu & 0xFFFFFFFF, dwFlags=co, time=0, dwExtraInfo=0))


def ma_phim(ten: str) -> int:
    t = ten.strip().lower()
    if t in VK:
        return VK[t]
    if len(t) == 1 and (t.isascii() and t.isalnum()):
        return ord(t.upper())
    if t in DAU:
        return DAU[t]
    raise ValueError(f"không biết phím '{ten}'")


def tach_to_hop(phim: str) -> list:
    """'ctrl+shift+s' -> [0x11, 0x10, 0x53]; 'ctrl++' hiểu là ctrl và phím '+' (=)."""
    p = phim.strip()
    if not p:
        raise ValueError("thiếu tên phím")
    phan = p.split("+")
    if p.endswith("++"):
        phan = phan[:-2] + ["="]
    return [ma_phim(x) for x in phan if x != ""]


# ---------------------------------------------------------------- màn hình
def man_hinh_ao():
    """(trái, trên, rộng, cao) của toàn bộ các màn hình gộp lại, điểm ảnh thật."""
    g = user32.GetSystemMetrics
    return g(76), g(77), g(78), g(79)


def ti_le(rong=None) -> float:
    rong = rong or man_hinh_ao()[2]
    return min(1.0, RONG_TOI_DA / max(1, rong))


def sang_that(x, y):
    """Tọa độ trên ảnh chụp -> tọa độ thật trên màn hình."""
    l, t, w, h = man_hinh_ao()
    k = ti_le(w)
    return l + min(w - 1, max(0, round(x / k))), t + min(h - 1, max(0, round(y / k)))


def sang_anh(x, y):
    l, t, w, _ = man_hinh_ao()
    k = ti_le(w)
    return round((x - l) * k), round((y - t) * k)


def kich_thuoc_anh():
    _, _, w, h = man_hinh_ao()
    k = ti_le(w)
    return round(w * k), round(h * k)


def vi_tri_chuot():
    p = W.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def kiem_dung_khan():
    x, y = vi_tri_chuot()
    l, t, _, _ = man_hinh_ao()
    if (x <= 1 and y <= 1) or (x <= l + 1 and y <= t + 1):
        raise DungKhan("Bạn kéo chuột lên góc trên bên trái: dừng khẩn, các bước còn lại bị hủy")


def man_hinh_khoa() -> bool:
    """Màn khóa / UAC (bàn làm việc an toàn) thì không mở được bàn làm việc nhập liệu."""
    h = user32.OpenInputDesktop(0, False, 0x0100)
    if not h:
        return True
    try:
        return not user32.SwitchDesktop(h)
    finally:
        user32.CloseDesktop(h)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", W.UINT), ("dwTime", W.DWORD)]


def giay_ranh() -> float:
    """Bạn đã không đụng chuột, bàn phím bao nhiêu giây."""
    li = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
    if not user32.GetLastInputInfo(ctypes.byref(li)):
        return 0.0
    return ((kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000.0


def chup(vung=None):
    """Chụp màn hình -> (ảnh PIL, ghi chú). Có con trỏ chuột vẽ thành dấu thập đỏ để Claude biết chuột đang ở đâu."""
    from PIL import Image, ImageDraw, ImageGrab
    l, t, w, h = man_hinh_ao()
    anh = ImageGrab.grab(all_screens=True)
    if anh.size != (w, h):                       # Pillow cũ / DPI lệch: vẫn dùng được, đo lại theo ảnh thật
        w, h = anh.size
    k = ti_le(w)
    cx, cy = vi_tri_chuot()
    cx, cy = cx - l, cy - t
    if vung:
        x, y, rw, rh = [int(v) for v in vung]
        hop = (max(0, round(x / k)), max(0, round(y / k)), min(w, round((x + rw) / k)), min(h, round((y + rh) / k)))
        if hop[2] <= hop[0] or hop[3] <= hop[1]:
            raise ValueError(f"vùng {vung} nằm ngoài màn hình")
        anh = anh.crop(hop)
        if anh.width > RONG_TOI_DA:
            anh = anh.resize((RONG_TOI_DA, round(anh.height * RONG_TOI_DA / anh.width)), Image.LANCZOS)
        return anh, (f"ảnh PHÓNG TO vùng {list(vung)} (tọa độ ảnh toàn màn hình), {anh.width}x{anh.height}; "
                     "đừng dùng tọa độ trên ảnh này để bấm")
    if k < 1:
        anh = anh.resize((round(w * k), round(h * k)), Image.LANCZOS)
    ve = ImageDraw.Draw(anh)
    ax, ay = round(cx * k), round(cy * k)
    for d in (-1, 0, 1):
        ve.line([(ax - 9, ay + d), (ax + 9, ay + d)], fill=(255, 0, 0))
        ve.line([(ax + d, ay - 9), (ax + d, ay + 9)], fill=(255, 0, 0))
    cs = cua_so_dang_chon()
    return anh, (f"ảnh toàn màn hình {anh.width}x{anh.height} (tọa độ bấm theo ảnh này); chuột ở ({ax}, {ay}); "
                 f"cửa sổ đang chọn: {cs.get('tieu_de', '') or '(không có)'}")


def anh_png(anh) -> bytes:
    b = io.BytesIO()
    anh.save(b, "PNG", optimize=True)
    return b.getvalue()


def anh_base64(anh) -> str:
    return base64.b64encode(anh_png(anh)).decode()


# ---------------------------------------------------------------- chuột, bàn phím
def bam(x, y, nut="trai", lan=1):
    xuong, len_ = NUT[nut]
    user32.SetCursorPos(*sang_that(x, y))
    time.sleep(0.05)
    for _ in range(lan):
        _gui(_chuot(xuong), _chuot(len_))
        time.sleep(0.06)


def di(x, y):
    user32.SetCursorPos(*sang_that(x, y))


def keo(x, y, x2, y2):
    user32.SetCursorPos(*sang_that(x, y))
    time.sleep(0.05)
    _gui(_chuot(0x0002))
    a, b = sang_that(x, y)
    c, d = sang_that(x2, y2)
    for i in range(1, 21):                       # đi từ từ để ứng dụng nhận ra là kéo
        user32.SetCursorPos(a + (c - a) * i // 20, b + (d - b) * i // 20)
        time.sleep(0.015)
    _gui(_chuot(0x0004))


def cuon(so, x=None, y=None):
    if x is not None and y is not None:
        user32.SetCursorPos(*sang_that(x, y))
    _gui(_chuot(0x0800, int(so) * 120))


def go(chu: str):
    for ky in chu.replace("\r\n", "\n"):
        if ky == "\n":
            _gui(_phim_ao(0x0D), _phim_ao(0x0D, True))
        elif ky == "\t":
            _gui(_phim_ao(0x09), _phim_ao(0x09, True))
        else:
            ma = ky.encode("utf-16-le")
            for i in range(0, len(ma), 2):       # ký tự ngoài BMP (biểu tượng cảm xúc) = 2 đơn vị UTF-16
                don_vi = int.from_bytes(ma[i:i + 2], "little")
                _gui(INPUT(type=1, ki=KEYBDINPUT(wVk=0, wScan=don_vi, dwFlags=UNICODE, time=0, dwExtraInfo=0)),
                     INPUT(type=1, ki=KEYBDINPUT(wVk=0, wScan=don_vi, dwFlags=UNICODE | KEYUP, time=0, dwExtraInfo=0)))
        time.sleep(0.008)


def phim(to_hop: str, lan=1):
    ma = tach_to_hop(to_hop)
    for _ in range(lan):
        _gui(*[_phim_ao(v) for v in ma], *[_phim_ao(v, True) for v in reversed(ma)])
        time.sleep(0.05)


# ---------------------------------------------------------------- cửa sổ
_ENUM = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM) if LA_WINDOWS else None


def _ten_tien_trinh(hwnd) -> str:
    pid = W.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(520)
        n = W.DWORD(520)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return os.path.basename(buf.value)
        return ""
    finally:
        kernel32.CloseHandle(h)


def _thong_tin(hwnd) -> dict:
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    r = W.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    thu_nho = bool(user32.IsIconic(hwnd))
    d = {"hwnd": int(hwnd or 0), "tieu_de": buf.value, "ung_dung": _ten_tien_trinh(hwnd), "thu_nho": thu_nho}
    if not thu_nho:
        x1, y1 = sang_anh(r.left, r.top)
        x2, y2 = sang_anh(r.right, r.bottom)
        d["khung"] = [x1, y1, x2 - x1, y2 - y1]
    return d


def liet_ke_cua_so() -> list:
    ra = []

    def goi(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            r = W.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            if r.right - r.left > 1 and r.bottom - r.top > 1:
                ra.append(_thong_tin(hwnd))
        return True

    user32.EnumWindows(_ENUM(goi), 0)
    return ra


def cua_so_dang_chon() -> dict:
    h = user32.GetForegroundWindow()
    return _thong_tin(h) if h else {}


def chon_cua_so(tieu_de: str) -> dict:
    can = tieu_de.strip().lower()
    if not can:
        raise ValueError("thiếu tiêu đề cửa sổ")
    ung = [c for c in liet_ke_cua_so() if can in c["tieu_de"].lower() or can == c["ung_dung"].lower()]
    if not ung:
        raise RuntimeError(f"không thấy cửa sổ nào có tiêu đề chứa '{tieu_de}'")
    h = ung[0]["hwnd"]
    if user32.IsIconic(h):
        user32.ShowWindow(h, 9)                   # SW_RESTORE
    # Windows chỉ cho tiến trình vừa nhận phím đưa cửa sổ lên trước: nhấn nhả Alt một lần để được phép
    _gui(_phim_ao(0x12), _phim_ao(0x12, True))
    user32.SetForegroundWindow(h)
    time.sleep(0.3)
    if user32.GetForegroundWindow() != h:
        raise RuntimeError(f"Windows không cho đưa '{ung[0]['tieu_de']}' lên trước (thử bấm vào cửa sổ trên thanh tác vụ)")
    return _thong_tin(h)


# ---------------------------------------------------------------- bước
def _so(b, k, mac_dinh=None):
    v = b.get(k, mac_dinh)
    if v is None:
        raise ValueError(f"bước {b.get('lam')} thiếu '{k}'")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"bước {b.get('lam')}: '{k}' phải là số, nhận {v!r}")
    return int(v)


def _toa_do(b, kx="x", ky="y"):
    x, y = _so(b, kx), _so(b, ky)
    if x < 0 or y < 0:
        raise ValueError(f"tọa độ âm ({x}, {y})")
    if x <= 2 and y <= 2:
        raise ValueError("không bấm vào góc trên bên trái: đó là chỗ Bạn kéo chuột để DỪNG KHẨN")
    return x, y


def kiem_buoc(ds) -> list:
    """Kiểm tra và chuẩn hóa danh sách bước TRƯỚC khi làm bước nào (sai một bước thì không làm gì cả)."""
    if not isinstance(ds, list) or not ds:
        raise ValueError("'buoc' phải là danh sách khác rỗng")
    if len(ds) > TOI_DA_BUOC:
        raise ValueError(f"tối đa {TOI_DA_BUOC} bước mỗi yêu cầu, nhận {len(ds)}")
    ra = []
    for i, b in enumerate(ds, 1):
        if not isinstance(b, dict) or not b.get("lam"):
            raise ValueError(f"bước {i} thiếu 'lam'")
        lam = str(b["lam"]).strip().lower()
        n = {"lam": lam}
        if lam == "chup":
            if b.get("vung") is not None:
                v = b["vung"]
                if not (isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v)
                        and v[2] > 0 and v[3] > 0):
                    raise ValueError(f"bước {i}: 'vung' phải là [x, y, rong, cao]")
                n["vung"] = [int(x) for x in v]
        elif lam == "bam":
            n["x"], n["y"] = _toa_do(b)
            n["nut"] = str(b.get("nut") or "trai").lower()
            if n["nut"] not in NUT:
                raise ValueError(f"bước {i}: 'nut' là trai/phai/giua")
            n["lan"] = _so(b, "lan", 1)
            if not 1 <= n["lan"] <= 3:
                raise ValueError(f"bước {i}: 'lan' từ 1 đến 3")
        elif lam == "di":
            n["x"], n["y"] = _toa_do(b)
        elif lam == "keo":
            n["x"], n["y"] = _toa_do(b)
            n["x2"], n["y2"] = _toa_do(b, "x2", "y2")
        elif lam == "go":
            chu = b.get("chu")
            if not isinstance(chu, str) or not chu:
                raise ValueError(f"bước {i}: 'chu' phải là chuỗi khác rỗng")
            if len(chu) > TOI_DA_CHU:
                raise ValueError(f"bước {i}: tối đa {TOI_DA_CHU} ký tự")
            n["chu"] = chu
        elif lam == "phim":
            if not isinstance(b.get("phim"), str):
                raise ValueError(f"bước {i} thiếu 'phim'")
            tach_to_hop(b["phim"])
            n["phim"] = b["phim"]
            n["lan"] = _so(b, "lan", 1)
            if not 1 <= n["lan"] <= 50:
                raise ValueError(f"bước {i}: 'lan' từ 1 đến 50")
        elif lam == "cuon":
            n["so"] = _so(b, "so")
            if not -50 <= n["so"] <= 50 or n["so"] == 0:
                raise ValueError(f"bước {i}: 'so' từ -50 đến 50, khác 0")
            if b.get("x") is not None or b.get("y") is not None:
                n["x"], n["y"] = _toa_do(b)
        elif lam == "cho":
            g = b.get("giay", 1)
            if isinstance(g, bool) or not isinstance(g, (int, float)) or not 0 < g <= TOI_DA_CHO:
                raise ValueError(f"bước {i}: 'giay' từ 0 đến {TOI_DA_CHO}")
            n["giay"] = float(g)
        elif lam == "cua-so":
            if not isinstance(b.get("tieu_de"), str) or not b["tieu_de"].strip():
                raise ValueError(f"bước {i} thiếu 'tieu_de'")
            n["tieu_de"] = b["tieu_de"]
        else:
            raise ValueError(f"bước {i}: không biết thao tác '{lam}'")
        ra.append(n)
    return ra


def mo_ta(b: dict) -> str:
    lam = b["lam"]
    if lam == "go":
        c = b["chu"].replace("\n", "⏎")
        return f"go '{c[:40]}{'…' if len(c) > 40 else ''}' ({len(b['chu'])} ký tự)"
    return lam + " " + ", ".join(f"{k}={v}" for k, v in b.items() if k != "lam")


def lam_buoc(b: dict):
    """Làm MỘT bước đã kiểm. Trả (ảnh PIL hoặc None, ghi chú)."""
    kiem_dung_khan()
    lam = b["lam"]
    if lam == "chup":
        return chup(b.get("vung"))
    if lam == "bam":
        bam(b["x"], b["y"], b["nut"], b["lan"])
    elif lam == "di":
        di(b["x"], b["y"])
    elif lam == "keo":
        keo(b["x"], b["y"], b["x2"], b["y2"])
    elif lam == "go":
        go(b["chu"])
    elif lam == "phim":
        phim(b["phim"], b["lan"])
    elif lam == "cuon":
        cuon(b["so"], b.get("x"), b.get("y"))
    elif lam == "cho":
        het = time.time() + b["giay"]
        while time.time() < het:                  # chờ mà vẫn nghe dừng khẩn
            time.sleep(0.2)
            kiem_dung_khan()
    elif lam == "cua-so":
        cs = chon_cua_so(b["tieu_de"])
        return None, f"đã chọn cửa sổ '{cs['tieu_de']}' ({cs['ung_dung']})"
    return None, "OK"


def chay(ds, thu_muc, chup_cuoi=True, log=print) -> dict:
    """Làm cả danh sách bước, lưu ảnh và README.md vào thu_muc. Không ném lỗi: lỗi ghi vào kết quả."""
    from pathlib import Path
    thu_muc = Path(thu_muc)
    thu_muc.mkdir(parents=True, exist_ok=True)
    buoc = kiem_buoc(ds)
    _log = log

    def log(s):                                    # nhật ký hỏng (console cp1252...) không được làm hỏng các bước
        try:
            _log(s)
        except Exception:
            pass

    dong, anh_ds, loi, xong = [], [], None, 0
    if man_hinh_khoa():
        loi = "màn hình đang khóa (hoặc đang hiện hộp UAC): không làm bước nào"
    else:
        for i, b in enumerate(buoc, 1):
            try:
                anh, ghi_chu = lam_buoc(b)
                if anh is not None:
                    ten = f"{i:02d}-chup.png"
                    (thu_muc / ten).write_bytes(anh_png(anh))
                    anh_ds.append(ten)
                    ghi_chu = f"{ghi_chu} -> {ten}"
                dong.append((i, mo_ta(b), ghi_chu))
                log(f"  màn hình bước {i}: {mo_ta(b)} -> {ghi_chu}")
                xong += 1
                time.sleep(0.15)
            except Exception as e:
                loi = f"bước {i} ({mo_ta(b)}): {e}"
                dong.append((i, mo_ta(b), f"LỖI: {e}"))
                log("  màn hình LỖI " + loi)
                break
        if chup_cuoi and not (buoc[-1]["lam"] == "chup" and loi is None):
            try:
                time.sleep(0.5)
                anh, ghi_chu = chup()
                (thu_muc / "cuoi.png").write_bytes(anh_png(anh))
                anh_ds.append("cuoi.png")
                dong.append(("cuối", "chup", f"{ghi_chu} -> cuoi.png"))
            except Exception as e:
                dong.append(("cuối", "chup", f"LỖI: {e}"))
    cua_so = []
    try:
        cua_so = [c for c in liet_ke_cua_so() if not c["thu_nho"]][:25]
    except Exception:
        pass
    md = [f"# Màn hình: {xong}/{len(buoc)} bước", "",
          f"Lúc {time.strftime('%Y-%m-%d %H:%M:%S')}. Ảnh {kich_thuoc_anh()[0]}x{kich_thuoc_anh()[1]}, "
          "tọa độ bấm theo ảnh toàn màn hình.", ""]
    if loi:
        md += [f"**Dừng:** {loi}", ""]
    md += ["| # | Thao tác | Kết quả |", "|---|---|---|"]
    md += [f"| {i} | {m.replace('|', '/')} | {k.replace('|', '/')} |" for i, m, k in dong]
    md += ["", "## Cửa sổ đang mở", "", "| Tiêu đề | Ứng dụng | Khung [x, y, rộng, cao] |", "|---|---|---|"]
    md += [f"| {c['tieu_de'].replace('|', '/')[:90]} | {c['ung_dung']} | {c.get('khung', '')} |" for c in cua_so]
    (thu_muc / "README.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"xong": xong, "tong": len(buoc), "anh": anh_ds, "loi": loi}

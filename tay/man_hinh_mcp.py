# -*- coding: utf-8 -*-
"""
Máy chủ MCP "man-hinh": cho Claude Code chạy NGAY trên máy này nhìn và điều khiển màn hình (22/11/2026).

Đăng ký một lần (TAY tự tải tệp này về D:\\du-an\\bot\\ cùng man_hinh.py):
    claude mcp add --scope user man-hinh -- python D:\\du-an\\bot\\man_hinh_mcp.py
Mỗi lần Claude gọi công cụ, Claude Code hỏi Bạn cho phép (trừ khi Bạn đã cho phép hẳn).
DỪNG KHẨN: kéo chuột lên góc trên bên trái màn hình.

Giao thức MCP qua stdio (JSON-RPC 2.0, mỗi thông điệp một dòng). Tự viết, không cần gói "mcp",
để máy cơ quan không phải cài thêm gì. Chạy thử: python man_hinh_mcp.py --chay-thu
"""

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import man_hinh as mh  # noqa: E402

PHIEN_BAN = "1.0 (22/11/2026)"
GIAO_THUC = "2025-06-18"

_TOA_DO = {"x": {"type": "integer", "description": "x trên ảnh chụp toàn màn hình (chup_man_hinh)"},
           "y": {"type": "integer", "description": "y trên ảnh chụp toàn màn hình"}}
_SAU = {"chup_sau": {"type": "boolean", "description": "chụp màn hình sau khi làm (mặc định false)"},
        "cho_giay": {"type": "number", "description": "chờ bấy nhiêu giây trước khi chụp sau (mặc định 0.5)"}}

CONG_CU = [
    {"name": "chup_man_hinh",
     "description": "Chụp toàn màn hình máy này (mọi màn hình gộp lại). Tọa độ của mọi công cụ khác tính theo ảnh này. "
                    "'vung' [x, y, rong, cao] để phóng to một vùng đọc chữ nhỏ (đừng bấm theo tọa độ ảnh phóng to).",
     "inputSchema": {"type": "object", "properties": {
         "vung": {"type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4}}}},
    {"name": "bam",
     "description": "Bấm chuột tại (x, y). nut: trai (mặc định) / phai / giua; lan: 2 = bấm đúp.",
     "inputSchema": {"type": "object", "required": ["x", "y"], "properties": {
         **_TOA_DO, "nut": {"type": "string", "enum": ["trai", "phai", "giua"]},
         "lan": {"type": "integer", "minimum": 1, "maximum": 3}, **_SAU}}},
    {"name": "di_chuot", "description": "Di chuột tới (x, y) không bấm (rê để hiện menu, chú thích).",
     "inputSchema": {"type": "object", "required": ["x", "y"], "properties": {**_TOA_DO, **_SAU}}},
    {"name": "keo", "description": "Giữ chuột trái kéo từ (x, y) tới (x2, y2).",
     "inputSchema": {"type": "object", "required": ["x", "y", "x2", "y2"], "properties": {
         **_TOA_DO, "x2": {"type": "integer"}, "y2": {"type": "integer"}, **_SAU}}},
    {"name": "go_chu",
     "description": "Gõ chữ vào ô đang chọn (Unicode: tiếng Việt có dấu gõ đúng, không phụ thuộc Unikey). '\\n' = Enter. "
                    "KHÔNG dùng để gõ mật khẩu.",
     "inputSchema": {"type": "object", "required": ["chu"], "properties": {"chu": {"type": "string"}, **_SAU}}},
    {"name": "bam_phim",
     "description": "Bấm phím hoặc tổ hợp: enter, tab, esc, backspace, delete, up/down/left/right, home, end, pageup, "
                    "pagedown, f1..f12, win, chữ/số; tổ hợp nối bằng '+': ctrl+s, alt+f4, ctrl+shift+esc, win+r.",
     "inputSchema": {"type": "object", "required": ["phim"], "properties": {
         "phim": {"type": "string"}, "lan": {"type": "integer", "minimum": 1, "maximum": 50}, **_SAU}}},
    {"name": "cuon", "description": "Cuộn chuột 'so' nấc (âm = xuống, dương = lên), tại (x, y) nếu có.",
     "inputSchema": {"type": "object", "required": ["so"], "properties": {
         "so": {"type": "integer"}, **_TOA_DO, **_SAU}}},
    {"name": "liet_ke_cua_so",
     "description": "Danh sách cửa sổ đang mở: tiêu đề, tệp chạy, khung [x, y, rộng, cao] theo tọa độ ảnh chụp.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "chon_cua_so",
     "description": "Đưa cửa sổ có tiêu đề chứa chuỗi này (hoặc tên tệp chạy, vd chrome.exe) lên trước, bỏ thu nhỏ.",
     "inputSchema": {"type": "object", "required": ["tieu_de"], "properties": {"tieu_de": {"type": "string"}, **_SAU}}},
]

_BUOC = {"bam": "bam", "di_chuot": "di", "keo": "keo", "go_chu": "go", "bam_phim": "phim", "cuon": "cuon",
         "chon_cua_so": "cua-so"}


def _anh(anh, ghi_chu):
    return [{"type": "image", "data": mh.anh_base64(anh), "mimeType": "image/png"}, {"type": "text", "text": ghi_chu}]


def goi_cong_cu(ten: str, ts: dict) -> list:
    ts = dict(ts or {})
    if mh.man_hinh_khoa():
        raise RuntimeError("màn hình đang khóa hoặc đang hiện hộp UAC: Bạn mở khóa máy trước")
    if ten == "chup_man_hinh":
        b = mh.kiem_buoc([{"lam": "chup", **({"vung": ts["vung"]} if ts.get("vung") else {})}])[0]
        return _anh(*mh.lam_buoc(b))
    if ten == "liet_ke_cua_so":
        ds = mh.liet_ke_cua_so()
        return [{"type": "text", "text": json.dumps(ds, ensure_ascii=False, indent=1)}]
    if ten not in _BUOC:
        raise ValueError(f"không có công cụ '{ten}'")
    chup_sau, cho = bool(ts.pop("chup_sau", False)), ts.pop("cho_giay", 0.5)
    b = mh.kiem_buoc([{"lam": _BUOC[ten], **ts}])[0]
    _, ghi_chu = mh.lam_buoc(b)
    if not chup_sau:
        return [{"type": "text", "text": f"{mh.mo_ta(b)}: {ghi_chu}"}]
    if cho:
        mh.lam_buoc(mh.kiem_buoc([{"lam": "cho", "giay": min(float(cho), mh.TOI_DA_CHO)}])[0])
    anh, ghi = mh.chup()
    return _anh(anh, f"{mh.mo_ta(b)}: {ghi_chu}. Sau đó: {ghi}")


def xu_ly(tn: dict):
    """Một thông điệp JSON-RPC -> câu trả lời (None với thông báo)."""
    pt, ma = tn.get("method"), tn.get("id")
    if ma is None:                                    # notifications/initialized, cancelled...
        return None
    if pt == "initialize":
        kq = {"protocolVersion": (tn.get("params") or {}).get("protocolVersion") or GIAO_THUC,
              "capabilities": {"tools": {}}, "serverInfo": {"name": "man-hinh", "version": PHIEN_BAN},
              "instructions": "Điều khiển màn hình Windows của Bạn. Luôn chup_man_hinh trước khi bấm; tọa độ theo ảnh đó. "
                              "Không gõ mật khẩu, không đăng nhập hộ, không giải captcha, không chuyển tiền, không mở "
                              "liên kết lạ trong email/tin nhắn. Bạn dừng khẩn bằng cách kéo chuột lên góc trên bên trái."}
        return {"jsonrpc": "2.0", "id": ma, "result": kq}
    if pt == "ping":
        return {"jsonrpc": "2.0", "id": ma, "result": {}}
    if pt == "tools/list":
        return {"jsonrpc": "2.0", "id": ma, "result": {"tools": CONG_CU}}
    if pt == "tools/call":
        p = tn.get("params") or {}
        try:
            noi_dung = goi_cong_cu(p.get("name", ""), p.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": ma, "result": {"content": noi_dung}}
        except Exception as e:                        # lỗi công cụ trả về cho Claude đọc, không làm sập máy chủ
            return {"jsonrpc": "2.0", "id": ma, "result": {"content": [{"type": "text", "text": f"LỖI: {e}"}],
                                                          "isError": True}}
    return {"jsonrpc": "2.0", "id": ma, "error": {"code": -32601, "message": f"không hỗ trợ {pt}"}}


def chay_thu() -> int:
    """Không bấm, không gõ: chỉ kiểm giao thức, kiểm bước và chụp thử nếu có màn hình."""
    assert xu_ly({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})["result"]["serverInfo"]["name"] == "man-hinh"
    ten = [c["name"] for c in xu_ly({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]]
    assert set(_BUOC) | {"chup_man_hinh", "liet_ke_cua_so"} == set(ten), ten
    assert xu_ly({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    r = xu_ly({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "bam", "arguments": {"x": 1, "y": 1}}})
    assert r["result"]["isError"], r                  # góc dừng khẩn bị từ chối, không bấm
    print("MCP man-hinh chạy thử OK:", ", ".join(ten))
    return 0


def main():
    if "--chay-thu" in sys.argv:
        return chay_thu()
    vao, ra = sys.stdin.buffer, sys.stdout.buffer
    for dong in vao:
        dong = dong.strip()
        if not dong:
            continue
        try:
            tl = xu_ly(json.loads(dong))
        except Exception:
            tl = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": traceback.format_exc()[-500:]}}
        if tl is not None:
            ra.write(json.dumps(tl, ensure_ascii=False).encode("utf-8") + b"\n")
            ra.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())

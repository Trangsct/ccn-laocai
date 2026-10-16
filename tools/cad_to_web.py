#!/usr/bin/env python3
"""
Chuyển bản vẽ CAD (DWG/DXF, tọa độ VN-2000) thành ảnh xem trước + lớp phủ bản đồ cho trang web.

Mỗi bản vẽ khai báo trong bảng BAN_VE bên dưới. Script sinh, trong thư mục `ra` của bản vẽ:
  - <id>.png      ảnh xem trước (nền trắng, có vẽ đè ranh giới KCN liên quan) — dùng cho trang chi tiết và trình chiếu
  - <id>.geojson  lớp phủ WGS84 (gộp theo layer CAD) — trang chi tiết bật/tắt trên bản đồ Leaflet

Đầu vào là DXF. DWG đổi sang DXF bằng LibreDWG (https://www.gnu.org/software/libredwg/):
    dwg2dxf -y -o ten.dxf ten.dwg
LibreDWG 0.13 đọc DWG 2007 (AC1021) được phần lớn đối tượng nhưng có thể bỏ sót một ít
(báo "Invalid num_pages", "Invalid object type") — tệp DWG gốc vẫn là bản chuẩn để tải về.

Phụ thuộc: pip install ezdxf matplotlib pyproj shapely

Chạy:
    python3 tools/cad_to_web.py --dxf-dir <thư mục chứa DXF>            # sinh tất cả
    python3 tools/cad_to_web.py --dxf-dir <...> --chi nut-giao-ic17     # một bản vẽ
"""
import argparse
import json
import math
import os
import re
import sys

import ezdxf
from ezdxf import recover, bbox, disassemble
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches
from pyproj import Transformer
from shapely.geometry import LineString, Polygon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# VN-2000, múi chiếu 3°, kinh tuyến trục 104°45' (phía Tây tỉnh Lào Cai — gồm xã Gia Phú)
VN2000_TM3_10445 = ('+proj=tmerc +lat_0=0 +lon_0=104.75 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 '
                    '+towgs84=-191.90441429,-39.30318279,-111.45032835,-0.00928836,0.01975479,-0.00427372,0.252906278 '
                    '+units=m')
TO_WGS84 = Transformer.from_crs(VN2000_TM3_10445, 'EPSG:4326', always_xy=True)
TO_VN2000 = Transformer.from_crs('EPSG:4326', VN2000_TM3_10445, always_xy=True)

# Vùng hợp lệ (VN-2000) — đối tượng nằm ngoài là rác do đọc DWG lỗi, bỏ qua
CUA_SO = (425000, 2465000, 440000, 2478000)

PX = 'unit-files/kcn-phu-xuan/ban-ve-cad'

BAN_VE = [
    {
        'id': 'dia-hinh-phu-xuan',
        'dxf': 'XRF._DIA_HINH_PHU_XUAN_GHEP.dxf',
        'ra': PX,
        'tieuDe': 'Bình đồ địa hình hiện trạng khu vực Khu công nghiệp Phú Xuân',
        'ranh': ['kcn-phu-xuan', 'kcn-phu-xuan-1'],
        'chu': False,          # bình đồ có ~900 ghi chú — không đưa lên lớp phủ bản đồ
        'donGian': 0.5,
    },
    {
        'id': 'tram-110kv',
        'dxf': 'xref_-_tram_110kV.dxf',
        'ra': PX,
        'tieuDe': 'Mặt bằng Trạm biến áp 110 kV và tuyến đường dây đấu nối',
        'ranh': ['kcn-phu-xuan', 'kcn-phu-xuan-1'],
        'chu': True,
        'donGian': 0.1,
        # trạm chỉ ~90 x 100 m trên khung 3 km — thêm ô phóng to (tọa độ VN-2000; vị trí theo tỷ lệ khung ảnh)
        'phongTo': {'khung': (433690, 2471230, 433860, 2471620), 'viTri': [0.66, 0.50, 0.32, 0.44],
                    'nhan': 'Phóng to: trạm 110 kV và nhánh rẽ từ vị trí cột VT22'},
    },
    {
        'id': 'nut-giao-ic17',
        'dxf': 'NUT_GIAO_IC17.dxf',
        'ra': PX,
        'tieuDe': 'Nút giao IC17 cao tốc Nội Bài - Lào Cai',
        'ranh': ['kcn-phu-xuan', 'kcn-phu-xuan-1'],
        'chu': True,
        'donGian': 0.1,
    },
    {
        'id': 'cap-nuoc-tho',
        'dxf': 'vi_tri_Cap_nuoc_tho_PHU_XUAN.dxf',
        'ra': PX,
        'tieuDe': 'Vị trí công trình cấp nước thô cho Khu công nghiệp Phú Xuân',
        'ranh': ['kcn-phu-xuan', 'kcn-phu-xuan-1'],
        'chu': True,
        'donGian': 0.1,
    },
]

# ---------------------------------------------------------------- TCVN3 (ABC) -> Unicode
_TCVN3 = dict(zip(
    '¸µ¶·¹¨¾»¼½Æ©ÊÇÈÉË®ÐÌÎÏÑªÕÒÓÔÖÝ×ØÜÞãßáâä«èåæçé¬íêëìîóïñòô\xadøõö÷ùýúûüþ¡¢§£¤¥¦',
    'áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵĂÂĐÊÔƠƯ'))
# Ký tự chỉ xuất hiện khi chuỗi là TCVN3 (không phải chữ Việt Unicode hợp lệ)
_DAU_HIEU_TCVN3 = set('¸µ¶·¹¨¾»¼½Æ©ÊÇÈÉË®ÐÌÎÏÑªÕÒÓÔÖ×ØÜÞßäåæçë«¬îïñö÷øûüþ\xad¡¢§£¤¥¦')


def tcvn3(s):
    if not s or not (set(s) & _DAU_HIEU_TCVN3):
        return s
    out = ''.join(_TCVN3.get(ch, ch) for ch in s)
    # Phông chữ hoa TCVN3 (.VnTimeH…) dùng mã chữ thường — chuỗi gốc toàn chữ in hoa thì in hoa lại
    latin = [ch for ch in s if ch.isascii() and ch.isalpha()]
    if latin and all(ch.isupper() for ch in latin):
        out = out.upper()
    return out


def chu_cua(e):
    t = e.dxftype()
    if t == 'TEXT':
        return e.dxf.text
    if t == 'MTEXT':
        return e.plain_text()
    return None


def hop_le(x, y):
    return (math.isfinite(x) and math.isfinite(y)
            and CUA_SO[0] < x < CUA_SO[2] and CUA_SO[1] < y < CUA_SO[3])


def doc_dxf(path):
    """Đọc DXF; vá handle 0 trùng (LibreDWG đôi khi sinh XRECORD handle 0)."""
    try:
        doc, _ = recover.readfile(path)
        return doc
    except ValueError as err:
        if 'Invalid handle' not in str(err):
            raise
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    lon_nhat = 0
    for i in range(len(lines) - 1):
        if lines[i] in ('  5', '105'):
            try:
                lon_nhat = max(lon_nhat, int(lines[i + 1], 16))
            except ValueError:
                pass
    for i in range(len(lines) - 1):
        if lines[i] in ('  5', '105') and lines[i + 1].strip() == '0':
            lon_nhat += 1
            lines[i + 1] = format(lon_nhat, 'X')
    tam = path + '.va.dxf'
    open(tam, 'w', encoding='utf-8').write('\n'.join(lines))
    doc, _ = recover.readfile(tam)
    os.remove(tam)
    return doc


def lam_sach(doc):
    """Xóa đối tượng ngoài vùng hợp lệ; đổi chữ TCVN3 sang Unicode (cả trong block)."""
    msp = doc.modelspace()
    xoa = []
    for e in msp:
        try:
            b = bbox.extents([e], fast=True)
        except Exception:
            xoa.append(e)
            continue
        if not b.has_data or not (hop_le(b.extmin.x, b.extmin.y) and hop_le(b.extmax.x, b.extmax.y)):
            xoa.append(e)
    for e in xoa:
        msp.delete_entity(e)
    for layout in [msp] + [blk for blk in doc.blocks]:
        for e in layout:
            if e.dxftype() == 'TEXT':
                e.dxf.text = tcvn3(e.dxf.text)
            elif e.dxftype() == 'MTEXT':
                e.text = tcvn3(e.text)
    return len(xoa)


def ranh_kcn(slugs):
    d = json.load(open(os.path.join(ROOT, 'unit-details.json'), encoding='utf-8'))
    out = []
    for s in slugs:
        u = d.get(s) or {}
        if u.get('polygon'):
            out.append((u['ten'], Polygon([TO_VN2000.transform(p[1], p[0]) for p in u['polygon']])))
    return out


def ve_png(doc, bv, ranh, path):
    msp = doc.modelspace()
    b = bbox.extents(msp, fast=True)
    x0, y0, x1, y1 = b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y
    for _, poly in ranh:
        bx = poly.bounds
        # chỉ nới khung theo ranh KCN ở gần (≤ 1,5 km) để ảnh không bị loãng
        if poly.distance(Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])) < 1500:
            x0, y0, x1, y1 = min(x0, bx[0]), min(y0, bx[1]), max(x1, bx[2]), max(y1, bx[3])
    pad = max(x1 - x0, y1 - y0) * 0.04
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    rong = 16.0
    fig = plt.figure(figsize=(rong, rong * h / w + 0.9), dpi=150)
    ax = fig.add_axes([0, 0, 1, (rong * h / w) / (rong * h / w + 0.9)])
    ax.set_facecolor('white')
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.COLOR,
                        lineweight_policy=LineweightPolicy.RELATIVE,
                        min_lineweight=0.12)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=False)
    pz = bv.get('phongTo')
    if pz:
        k = pz['khung']
        ax.add_patch(matplotlib.patches.Rectangle((k[0], k[1]), k[2] - k[0], k[3] - k[1], fill=False,
                                                  ec='#0d47a1', lw=1.8, zorder=60))
        ax2 = fig.add_axes(pz['viTri'])
        Frontend(RenderContext(doc), MatplotlibBackend(ax2), config=cfg).draw_layout(msp, finalize=False)
        ax2.set_xlim(k[0], k[2])
        ax2.set_ylim(k[1], k[3])
        ax2.set_aspect('equal', adjustable='box')
        for _, poly in ranh:
            xs, ys = poly.exterior.xy
            ax2.plot(xs, ys, color='#dc2626', lw=2.2, ls=(0, (6, 3)), zorder=50)
        ax2.add_patch(matplotlib.patches.Rectangle((0, 0), 1, 1, transform=ax2.transAxes, fill=False,
                                                   ec='#0d47a1', lw=3, zorder=100, clip_on=False))
        ax2.set_facecolor('white')
        ax2.set_xticks([])
        ax2.set_yticks([])
        for sp in ax2.spines.values():
            sp.set_edgecolor('#0d47a1')
            sp.set_linewidth(2)
        ax2.set_title(pz['nhan'], fontsize=12, color='#0d47a1', fontweight='bold')
    for ten, poly in ranh:
        xs, ys = poly.exterior.xy
        ax.plot(xs, ys, color='#dc2626', lw=2.2, ls=(0, (6, 3)), zorder=50)
        c = poly.representative_point()
        if x0 < c.x < x1 and y0 < c.y < y1:
            ax.text(c.x, c.y, ten.upper(), color='#dc2626', fontsize=13, fontweight='bold',
                    ha='center', va='center', zorder=51,
                    bbox=dict(facecolor='white', edgecolor='#dc2626', alpha=0.85, boxstyle='round,pad=0.3'))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.text(0.012, 1 - 0.45 / (rong * h / w + 0.9), bv['tieuDe'].upper(), fontsize=17,
             fontweight='bold', color='#0d47a1', va='center')
    fig.text(0.988, 1 - 0.45 / (rong * h / w + 0.9),
             'Nét đứt đỏ: ranh giới KCN · Hệ tọa độ VN-2000, KTT 104°45′', fontsize=11,
             color='#475569', va='center', ha='right')
    fig.savefig(path, dpi=150, facecolor='white', pil_kwargs={'optimize': True})
    plt.close(fig)


def r6(v):
    return round(v, 6)


def xuat_geojson(doc, bv, path):
    msp = doc.modelspace()
    theo_layer = {}
    diem_chu = []
    for prim in disassemble.to_primitives(disassemble.recursive_decompose(msp), max_flattening_distance=0.3):
        e = prim.entity
        layer = (e.dxf.layer if e is not None else '0') or '0'
        if e is not None and e.dxftype() in ('TEXT', 'MTEXT', 'ATTRIB'):
            continue  # chữ xử lý riêng bên dưới
        try:
            pts = [(v.x, v.y) for v in prim.vertices()]
        except (ZeroDivisionError, ValueError):
            continue  # cung/elip suy biến do đọc DWG lỗi
        pts = [p for p in pts if hop_le(*p)]
        if len(pts) < 2:
            continue
        line = LineString(pts).simplify(bv['donGian'])
        if line.length < 0.5:
            continue
        ll = [[r6(c) for c in TO_WGS84.transform(x, y)] for x, y in line.coords]
        theo_layer.setdefault(layer, []).append(ll)
    if bv['chu']:
        for e in msp.query('TEXT MTEXT'):
            s = (tcvn3(chu_cua(e)) or '').strip()
            if len(s) < 3:
                continue
            p = e.dxf.insert
            if not hop_le(p.x, p.y):
                continue
            lng, lat = TO_WGS84.transform(p.x, p.y)
            diem_chu.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [r6(lng), r6(lat)]},
                             'properties': {'chu': s}})
    feats = [{'type': 'Feature', 'properties': {'layer': tcvn3(k)},
              'geometry': {'type': 'MultiLineString', 'coordinates': v}}
             for k, v in sorted(theo_layer.items())]
    gj = {'type': 'FeatureCollection', 'name': bv['id'],
          'nguon': 'Chuyển từ bản vẽ CAD ' + bv['dxf'].replace('.dxf', '.dwg') + ' (VN-2000, KTT 104°45′) bằng tools/cad_to_web.py',
          'features': feats + diem_chu}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(gj, f, ensure_ascii=False, separators=(',', ':'))
    return sum(len(v) for v in theo_layer.values()), len(diem_chu)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dxf-dir', required=True)
    ap.add_argument('--chi', help='chỉ xử lý bản vẽ có id này')
    a = ap.parse_args()
    for bv in BAN_VE:
        if a.chi and bv['id'] != a.chi:
            continue
        src = os.path.join(a.dxf_dir, bv['dxf'])
        if not os.path.exists(src):
            print('  bỏ qua (không thấy)', src)
            continue
        doc = doc_dxf(src)
        bo = lam_sach(doc)
        out_dir = os.path.join(ROOT, bv['ra'])
        os.makedirs(out_dir, exist_ok=True)
        png = os.path.join(out_dir, bv['id'] + '.png')
        gj = os.path.join(out_dir, bv['id'] + '.geojson')
        ve_png(doc, bv, ranh_kcn(bv['ranh']), png)
        n, c = xuat_geojson(doc, bv, gj)
        print('%-20s bỏ %d đối tượng lỗi · %d đường, %d nhãn · png %d KB · geojson %d KB'
              % (bv['id'], bo, n, c, os.path.getsize(png) // 1024, os.path.getsize(gj) // 1024))


if __name__ == '__main__':
    sys.exit(main())

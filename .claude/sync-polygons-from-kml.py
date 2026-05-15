"""Đồng bộ polygon ranh giới từ KML chuẩn → ccn-polygons.json.

Quy trình chuẩn của Sở:
  1. Cán bộ có "Bảng tọa độ ranh giới CCN.docx" (hệ VN-2000 TM-3 105-00 hoặc 104-45)
  2. Chuyển sang WGS-84 (Leaflet/Google Earth dùng) — Google Earth Pro hỗ trợ sẵn
  3. Save file `unit-files/ccn-<slug>/ranh-gioi.kml` (đây là chuẩn vàng)
  4. Chạy script này → tự cập nhật polygon trên bản đồ web

Cách dùng:
    python .claude/sync-polygons-from-kml.py            # chế độ thường (ghi đè)
    python .claude/sync-polygons-from-kml.py --dry-run  # chỉ in diff, không ghi
"""

import re
import json
import sys
import os
import glob

sys.stdout.reconfigure(encoding='utf-8')

# Mapping slug folder unit-files/ → name trong ccn-polygons.json
# Bổ sung khi có CCN/KCN mới có KML chuẩn
MAPPING = {
    'ccn-thong-nhat-1':   'CCN Thống Nhất 1',
    'ccn-bat-xat':        'CCN Bát Xát',
    'ccn-cam-duong-1':    'CCN Cam Đường 1',
    'ccn-cam-duong-2':    'CCN Cam Đường 2',
    'ccn-quang-kim-so-1': 'CCN Quang Kim 1',
    'ccn-phu-thinh-4':    'CCN Phú Thịnh 4',
    'ccn-phu-thinh-5':    'CCN Phú Thịnh 5',
    'ccn-phu-thinh-6':    'CCN Phú Thịnh 6',
}


def parse_kml_polygon(kml_text):
    """Trả về list [[lat, lng], ...] từ <Polygon><coordinates> đầu tiên.

    KML lưu lng,lat,alt — đảo lại thành [lat, lng] cho khớp với Leaflet.
    """
    m = re.search(r'<Polygon>.*?<coordinates>\s*(.+?)\s*</coordinates>',
                  kml_text, re.DOTALL)
    if not m:
        return None
    coords = []
    for p in m.group(1).strip().split():
        parts = p.strip().split(',')
        if len(parts) >= 2:
            try:
                lng = round(float(parts[0]), 7)
                lat = round(float(parts[1]), 7)
                coords.append([lat, lng])
            except ValueError:
                pass
    return coords if coords else None


def main():
    dry_run = '--dry-run' in sys.argv
    poly_path = 'ccn-polygons.json'

    with open(poly_path, encoding='utf-8') as f:
        polys = json.load(f)

    name_to_idx = {p.get('name'): i for i, p in enumerate(polys)}
    updated = []
    skipped = []

    for slug, poly_name in MAPPING.items():
        kml_path = f'unit-files/{slug}/ranh-gioi.kml'
        if not os.path.exists(kml_path):
            skipped.append((slug, 'không có KML'))
            continue
        with open(kml_path, encoding='utf-8') as f:
            kml = f.read()
        coords = parse_kml_polygon(kml)
        if not coords:
            skipped.append((slug, 'KML không có Polygon'))
            continue
        if poly_name not in name_to_idx:
            skipped.append((slug, f'không tìm thấy "{poly_name}" trong ccn-polygons.json'))
            continue
        idx = name_to_idx[poly_name]
        old = polys[idx]
        # Số điểm "thật" — KML thường khép kín (point đầu = point cuối)
        is_closed = len(coords) >= 2 and coords[0] == coords[-1]
        real_points = len(coords) - 1 if is_closed else len(coords)
        # Bỏ qua nếu không thay đổi gì
        if old.get('coords') == coords and old.get('is_approx') is False:
            skipped.append((slug, 'đã đồng bộ'))
            continue
        new_entry = dict(old)
        new_entry['coords'] = coords
        new_entry['num_points'] = real_points
        new_entry['is_approx'] = False
        new_entry['source'] = f'unit-files/{slug}/ranh-gioi.kml'
        polys[idx] = new_entry
        updated.append((slug, poly_name, old.get('num_points'), real_points, old.get('is_approx')))

    # In kết quả
    print(f'\n{"slug":<22} | {"old pts":<8} | {"new pts":<8} | {"old approx":<10} | new approx')
    print('-' * 75)
    for slug, name, old_n, new_n, old_a in updated:
        print(f'{slug:<22} | {str(old_n):<8} | {str(new_n):<8} | {str(old_a):<10} | False')

    if skipped:
        print('\nSkipped:')
        for s, reason in skipped:
            print(f'  - {s}: {reason}')

    if dry_run:
        print('\n[DRY-RUN] Không ghi file.')
        return

    if updated:
        with open(poly_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(polys, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f'\n✓ Đã cập nhật {len(updated)} entry vào {poly_path}')
    else:
        print('\nKhông có gì để cập nhật.')


if __name__ == '__main__':
    main()

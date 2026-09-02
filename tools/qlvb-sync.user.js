// ==UserScript==
// @name         QLVB -> congnghieplaocai.vn + vlncn-laocai (đồng bộ văn bản mới)
// @namespace    https://www.congnghieplaocai.vn/
// @version      1.1.0
// @description  Khi bảng Văn bản đến / Văn bản đi trên QLVB hiện ra: đọc số ký hiệu, ngày, cơ quan, trích yếu, độ mật; chỉ lấy độ mật Thường; phân loại KCN/CCN và VLNCN; gửi văn bản chưa có lên GitHub (van-ban-moi.json) bằng Contents API. Vercel tự deploy.
// @author       Sở Công Thương Lào Cai
// @match        https://qlvb.yenbai.gov.vn/*
// @match        http://qlvb.yenbai.gov.vn/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_deleteValue
// @grant        GM_registerMenuCommand
// @connect      api.github.com
// @connect      raw.githubusercontent.com
// @updateURL    https://raw.githubusercontent.com/Trangsct/ccn-laocai/main/tools/qlvb-sync.user.js
// @downloadURL  https://raw.githubusercontent.com/Trangsct/ccn-laocai/main/tools/qlvb-sync.user.js
// @run-at       document-idle
// ==/UserScript==

/*
 * HƯỚNG DẪN CÀI (chỉ bấm chuột, không sửa code):
 * 1. Cài tiện ích Tampermonkey từ Chrome Web Store.
 * 2. Tạo token GitHub (fine-grained, 2 repo ccn-laocai + vlncn-laocai, Contents: Read and write).
 * 3. Dán link này vào thanh địa chỉ Chrome, bấm Install:
 *    https://raw.githubusercontent.com/Trangsct/ccn-laocai/main/tools/qlvb-sync.user.js
 * 4. Mở QLVB, đăng nhập, vào Văn bản đến. Hộp thoại hiện lên hỏi token: dán token, bấm OK.
 *    Token lưu trong Tampermonkey, các lần sau tự dùng. Muốn đổi: bấm biểu tượng Tampermonkey
 *    -> menu "Đổi token GitHub (QLVB sync)".
 * Script tự cập nhật khi file này trên GitHub (nhánh main) có phiên bản mới.
 */

(function () {
    'use strict';

    // ================= CẤU HÌNH =================
    const KHOA_TOKEN = 'qlvb_github_token';   // token lưu trong kho Tampermonkey, không nằm trong code
    const REPO = {
        kccn:  { owner: 'Trangsct', repo: 'ccn-laocai',   path: 'van-ban-moi.json', branch: 'main' },
        vlncn: { owner: 'Trangsct', repo: 'vlncn-laocai', path: 'van-ban-moi.json', branch: 'main' },
    };
    const GIU_TOI_DA = 200;         // số văn bản giữ lại trong mỗi file JSON
    const SO_NGAY_LUI = 7;          // chỉ xét văn bản có ngày trong N ngày gần đây (chống gửi lại cả bảng cũ)
    const CHU_KY_QUET_MS = 4000;    // quét lại bảng mỗi 4 giây (ZK vẽ bảng bằng AJAX)

    // Từ khóa phân loại - chép từ scripts/qlvb_bot.py (TU_KHOA). Sửa ở cả 2 nơi nếu đổi.
    const TU_KHOA = {
        kccn: [
            'khu công nghiệp', 'cụm công nghiệp', 'kcn', 'ccn', 'hạ tầng kỹ thuật cụm',
            'chủ đầu tư hạ tầng', 'nghị định 32/2024', 'nghị định 303/2026',
        ],
        vlncn: [
            'vật liệu nổ', 'vlncn', 'nổ mìn', 'tiền chất thuốc nổ', 'thuốc nổ',
            'kho vật liệu nổ', 'huấn luyện kỹ thuật an toàn', 'hộ chiếu nổ mìn',
        ],
    };

    // Chỉ số cột trong bảng QLVB. null = tự nhận diện theo tiêu đề cột.
    // [CHỜ HTML] Khi có file HTML thật của trang Văn bản đến / đi, khóa cứng tại đây, ví dụ:
    // const COT = { so: 1, ngay: 2, coQuan: 3, trichYeu: 4, doMat: 5 };
    const COT = null;

    // ================= TIỆN ÍCH =================
    function boDau(s) {
        return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
    }
    function phanLoai(trichYeu) {
        const ty = (trichYeu || '').toLowerCase();
        const tyKd = boDau(trichYeu);
        return Object.keys(TU_KHOA).filter(nhom =>
            TU_KHOA[nhom].some(k => ty.includes(k) || tyKd.includes(boDau(k))));
    }
    function parseNgay(s) {
        let m = /(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})/.exec(s || '');
        if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
        m = /(\d{4})-(\d{2})-(\d{2})/.exec(s || '');
        if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
        return null;
    }
    function isoNgay(d) {
        const p = n => String(n).padStart(2, '0');
        return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
    }
    function bayGio() {
        const d = new Date();
        const p = n => String(n).padStart(2, '0');
        return isoNgay(d) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
    }
    function utf8ToBase64(str) {
        return btoa(unescape(encodeURIComponent(str)));
    }
    function base64ToUtf8(b64) {
        return decodeURIComponent(escape(atob((b64 || '').replace(/\n/g, ''))));
    }

    // Thông báo nhỏ góc dưới phải
    let hop;
    function thongBao(msg, mau) {
        if (!hop) {
            hop = document.createElement('div');
            hop.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:99999;max-width:360px;' +
                'padding:10px 14px;border-radius:8px;font:13px/1.4 Arial,sans-serif;color:#fff;' +
                'box-shadow:0 2px 10px rgba(0,0,0,.3);transition:opacity .4s;white-space:pre-line';
            document.body.appendChild(hop);
        }
        hop.style.background = mau || '#1565c0';
        hop.style.opacity = '1';
        hop.textContent = msg;
        clearTimeout(hop._t);
        hop._t = setTimeout(() => { hop.style.opacity = '0'; }, 8000);
    }

    // ================= TOKEN GITHUB =================
    function layToken() {
        return (GM_getValue(KHOA_TOKEN, '') || '').trim();
    }
    function hoiToken(loiTruoc) {
        const t = prompt(
            (loiTruoc ? loiTruoc + '\n\n' : '') +
            'QLVB sync: dán token GitHub (bắt đầu bằng github_pat_) rồi bấm OK.\n' +
            'Token tạo tại github.com/settings/personal-access-tokens/new, chọn 2 repo ccn-laocai và vlncn-laocai, quyền Contents: Read and write.\n' +
            'Token chỉ lưu trong Tampermonkey trên máy này.',
            layToken());
        if (t === null) return '';           // bấm Cancel
        const sach = t.trim();
        if (sach) {
            GM_setValue(KHOA_TOKEN, sach);
            thongBao('QLVB sync: đã lưu token GitHub', '#2e7d32');
        }
        return sach;
    }
    let daHoiToken = false;
    function tokenSanSang() {
        let t = layToken();
        if (!t && !daHoiToken) {
            daHoiToken = true;               // mỗi lần tải trang chỉ hỏi 1 lần, không làm phiền
            t = hoiToken('');
        }
        return t;
    }
    if (typeof GM_registerMenuCommand === 'function') {
        GM_registerMenuCommand('Đổi token GitHub (QLVB sync)', () => hoiToken(''));
        GM_registerMenuCommand('Xóa token GitHub (QLVB sync)', () => {
            GM_deleteValue(KHOA_TOKEN);
            thongBao('QLVB sync: đã xóa token. Tải lại trang sẽ hỏi token mới.', '#546e7a');
        });
        GM_registerMenuCommand('Quên danh sách đã gửi (gửi lại từ đầu)', () => {
            GM_deleteValue('qlvb_da_gui');
            daGui = new Set();
            dauBangTruoc = '';
            thongBao('QLVB sync: đã xóa bộ nhớ văn bản đã gửi', '#546e7a');
        });
    }

    // ================= GITHUB API =================
    function ghRequest(method, url, body) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method, url,
                headers: {
                    'Authorization': 'Bearer ' + layToken(),
                    'Accept': 'application/vnd.github+json',
                    'Content-Type': 'application/json',
                    'X-GitHub-Api-Version': '2022-11-28',
                },
                data: body ? JSON.stringify(body) : undefined,
                onload: r => {
                    let json = null;
                    try { json = JSON.parse(r.responseText); } catch (e) { /* bỏ qua */ }
                    if (r.status >= 200 && r.status < 300) resolve(json);
                    else if (r.status === 404 && method === 'GET') resolve(null);
                    else reject(new Error('GitHub ' + r.status + ': ' + (json && json.message || r.responseText.slice(0, 200))));
                },
                onerror: () => reject(new Error('Không gọi được api.github.com')),
                ontimeout: () => reject(new Error('api.github.com quá thời gian')),
            });
        });
    }
    async function docFile(cfg) {
        const url = `https://api.github.com/repos/${cfg.owner}/${cfg.repo}/contents/${cfg.path}?ref=${cfg.branch}`;
        const r = await ghRequest('GET', url);
        if (!r) return { sha: null, data: [] };
        let data = [];
        try { data = JSON.parse(base64ToUtf8(r.content)); } catch (e) { data = []; }
        return { sha: r.sha, data: Array.isArray(data) ? data : [] };
    }
    async function ghiFile(cfg, sha, data, msg) {
        const url = `https://api.github.com/repos/${cfg.owner}/${cfg.repo}/contents/${cfg.path}`;
        const body = {
            message: msg,
            content: utf8ToBase64(JSON.stringify(data, null, 2) + '\n'),
            branch: cfg.branch,
        };
        if (sha) body.sha = sha;
        return ghRequest('PUT', url, body);
    }

    // ================= ĐỌC BẢNG QLVB =================
    function chuanHoa(s) { return (s || '').replace(/\s+/g, ' ').trim(); }

    // Tìm tên mục đang mở (Văn bản đến / Văn bản đi) theo chữ nổi bật trên trang
    function tenMuc() {
        const cand = document.querySelectorAll('.z-caption-content, .z-tab-selected, .z-tab-selected .z-tab-text, ' +
            '.z-groupbox-title, .z-panel-header, .z-window-header, .z-navitem-selected, h1, h2, h3');
        for (const el of cand) {
            const t = chuanHoa(el.textContent);
            if (/văn bản đến/i.test(t)) return 'Văn bản đến';
            if (/văn bản đi/i.test(t)) return 'Văn bản đi';
        }
        const t = chuanHoa(document.title);
        if (/văn bản đến/i.test(t)) return 'Văn bản đến';
        if (/văn bản đi/i.test(t)) return 'Văn bản đi';
        return 'QLVB';
    }

    // Nhận diện cột theo tiêu đề bảng (ZK: .z-listheader-content / .z-column-content; HTML thường: th)
    function nhanDienCot(bang) {
        if (COT) return COT;
        const heads = bang.querySelectorAll('.z-listheader-content, .z-column-content, th, .z-auxheader-content');
        const map = { so: -1, ngay: -1, coQuan: -1, trichYeu: -1, doMat: -1 };
        let i = 0;
        for (const h of heads) {
            const t = boDau(chuanHoa(h.textContent));
            if (map.so < 0 && /(so|ky hieu)/.test(t) && !/so trang|so to|so ban/.test(t)) map.so = i;
            else if (map.ngay < 0 && /ngay (ban hanh|van ban|ky|den|di)|^ngay/.test(t)) map.ngay = i;
            else if (map.coQuan < 0 && /co quan|noi ban hanh|don vi|nguoi ky/.test(t)) map.coQuan = i;
            else if (map.trichYeu < 0 && /trich yeu|noi dung|tieu de/.test(t)) map.trichYeu = i;
            else if (map.doMat < 0 && /do mat|mat/.test(t)) map.doMat = i;
            i++;
        }
        if (map.so < 0 || map.trichYeu < 0) return null;   // chưa nhận ra được bảng văn bản
        return map;
    }

    // Trả về danh sách bảng ứng viên: ZK listbox/grid hoặc table thường
    function timBang() {
        const ds = [];
        document.querySelectorAll('.z-listbox, .z-grid, table').forEach(b => {
            if (b.closest('.z-listbox, .z-grid') && b.tagName === 'TABLE' && !b.classList.contains('z-listbox') && !b.classList.contains('z-grid')) return;
            ds.push(b);
        });
        return ds;
    }

    function docHang(bang, cot) {
        const rows = bang.querySelectorAll('tr.z-listitem, tr.z-row, tbody tr');
        const ketQua = [];
        rows.forEach(tr => {
            const cells = tr.querySelectorAll('td');
            if (cells.length <= Math.max(cot.so, cot.trichYeu)) return;
            const lay = k => (k >= 0 && cells[k]) ? chuanHoa(cells[k].textContent) : '';
            const so = lay(cot.so);
            const trichYeu = lay(cot.trichYeu);
            if (!so || !trichYeu || /^(số|ký hiệu)/i.test(so)) return;
            ketQua.push({
                so_ky_hieu: so,
                ngay: lay(cot.ngay),
                co_quan: lay(cot.coQuan),
                trich_yeu: trichYeu,
                do_mat: lay(cot.doMat) || 'Thường',
            });
        });
        return ketQua;
    }

    // ================= LUỒNG CHÍNH =================
    let dangGui = false;
    let dauBangTruoc = '';
    let daGui = new Set(JSON.parse(GM_getValue('qlvb_da_gui', '[]')));

    function luuDaGui() {
        GM_setValue('qlvb_da_gui', JSON.stringify([...daGui].slice(-2000)));
    }

    async function quet() {
        if (dangGui) return;
        let vanBan = [];
        for (const bang of timBang()) {
            const cot = nhanDienCot(bang);
            if (!cot) continue;
            vanBan = vanBan.concat(docHang(bang, cot));
        }
        if (!vanBan.length) return;

        // Chỉ xử lý khi nội dung bảng đổi so với lần quét trước (tránh làm lại mỗi 4 giây)
        const dauBang = vanBan.map(v => v.so_ky_hieu).join('|');
        if (dauBang === dauBangTruoc) return;
        dauBangTruoc = dauBang;

        const nguon = tenMuc();
        const gioiHan = new Date(); gioiHan.setDate(gioiHan.getDate() - SO_NGAY_LUI);
        const chon = [];
        for (const vb of vanBan) {
            if (daGui.has(vb.so_ky_hieu)) continue;
            if (vb.do_mat && !/thường|thuong/i.test(vb.do_mat)) continue;   // bỏ mọi độ mật khác Thường
            const d = parseNgay(vb.ngay);
            if (!d || d < gioiHan) continue;
            const nhom = phanLoai(vb.trich_yeu);
            if (!nhom.length) continue;
            chon.push(Object.assign({}, vb, { ngay: isoNgay(d), nguon, nhom, cap_nhat: bayGio() }));
        }
        if (!chon.length) return;

        // Có văn bản cần gửi mới hỏi token (lần đầu). Chưa có token thì để lần quét sau thử lại.
        if (!tokenSanSang()) {
            thongBao('QLVB sync: chưa có token GitHub. Bấm biểu tượng Tampermonkey -> "Đổi token GitHub (QLVB sync)".', '#c62828');
            dauBangTruoc = '';
            return;
        }

        dangGui = true;
        try {
            let tong = 0;
            const ketQua = [];
            for (const key of ['kccn', 'vlncn']) {
                const them = chon.filter(v => v.nhom.includes(key));
                if (!them.length) continue;
                const cfg = REPO[key];
                const { sha, data } = await docFile(cfg);
                const daCo = new Set(data.map(v => v.so_ky_hieu));
                const moi = them.filter(v => !daCo.has(v.so_ky_hieu));
                if (moi.length) {
                    await ghiFile(cfg, sha, moi.concat(data).slice(0, GIU_TOI_DA),
                        'QLVB sync: ' + moi.length + ' văn bản ' + key.toUpperCase() + ' mới ngày ' + bayGio().slice(0, 10));
                    tong += moi.length;
                }
                ketQua.push(key.toUpperCase() + ': ' + moi.length + ' mới');
                them.forEach(v => daGui.add(v.so_ky_hieu));
            }
            luuDaGui();
            thongBao('QLVB sync (' + nguon + '): đã gửi ' + tong + ' văn bản lên GitHub\n' + ketQua.join(' · '),
                tong ? '#2e7d32' : '#546e7a');
        } catch (e) {
            console.error('[QLVB sync]', e);
            if (/GitHub (401|403)/.test(e.message)) {
                // Token sai / hết hạn / thiếu quyền: hỏi lại ngay
                hoiToken('Token GitHub bị từ chối (' + e.message + '). Nhập lại token:');
            } else {
                thongBao('QLVB sync lỗi: ' + e.message, '#c62828');
            }
            dauBangTruoc = '';   // để lần sau thử lại
        } finally {
            dangGui = false;
        }
    }

    setInterval(quet, CHU_KY_QUET_MS);
    setTimeout(quet, 1500);
})();

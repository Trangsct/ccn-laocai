// ============================================================
// BẢN ĐỒ CỤM CÔNG NGHIỆP TỈNH LÀO CAI - APP LOGIC
// ============================================================

let map;
let markers = [];
let markerLayer;
let currentView = 'map';
let charts = {};

// Cấu hình mặc định Leaflet popup: tự né thanh nav sticky phía trên
// Padding top được tính ĐỘNG từ chiều cao thật của #header + #main-nav
// (desktop ~320px khi chưa cuộn, mobile ~140px) — bằng cách này popup không bị header che.
if (typeof L !== 'undefined' && L.Popup) {
    L.Popup.mergeOptions({
        autoPan: true,
        autoPanPaddingTopLeft: L.point(20, 320), // fallback an toàn cho desktop chưa cuộn
        autoPanPaddingBottomRight: L.point(20, 80),
        keepInView: true
    });
}

// Tự đo chiều cao header + nav khi DOM sẵn sàng và mỗi lần viewport thay đổi
function updatePopupAutoPanPadding() {
    if (typeof L === 'undefined' || !L.Popup) return;
    var header = document.getElementById('header');
    var nav = document.getElementById('main-nav');
    var topPad = ((header && header.offsetHeight) || 0) + ((nav && nav.offsetHeight) || 0) + 20;
    L.Popup.mergeOptions({
        autoPanPaddingTopLeft: L.point(20, topPad)
    });
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updatePopupAutoPanPadding);
} else {
    updatePopupAutoPanPadding();
}
window.addEventListener('resize', updatePopupAutoPanPadding);

// ---- News toggle ----
function openNews(id) {
    document.getElementById('news-list').style.display = 'none';
    document.getElementById('news-detail-' + id).style.display = 'block';
    window.scrollTo({ top: document.getElementById('tintuc-section').offsetTop - 60, behavior: 'smooth' });
}
function closeNews() {
    document.querySelectorAll('[id^="news-detail-"]').forEach(function(el) { el.style.display = 'none'; });
    document.getElementById('news-list').style.display = 'block';
    window.scrollTo({ top: document.getElementById('tintuc-section').offsetTop - 60, behavior: 'smooth' });
}

// ---- Mobile Sidebar ----
function toggleSidebar() {
    var sidebar = document.getElementById('ccn-sidebar');
    var overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
    document.body.style.overflow = sidebar.classList.contains('open') ? 'hidden' : '';
}
function closeSidebar() {
    var sidebar = document.getElementById('ccn-sidebar');
    var overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
}

// PDF iframes: dùng data-pdf-src để tránh trình duyệt tự tải về khi parse HTML
//  - Desktop: copy data-pdf-src → src để render PDF inline
//  - Mobile: thay iframe bằng placeholder có nút "Mở file PDF" (target=_blank, không tự tải)
(function() {
    var isMobile = window.innerWidth <= 768 || /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);

    function processPdfIframes() {
        document.querySelectorAll('iframe[data-pdf-src]').forEach(function(iframe) {
            var src = iframe.getAttribute('data-pdf-src');
            if (!src) return;
            if (isMobile) {
                var placeholder = document.createElement('div');
                placeholder.style.cssText = 'background:#fef3c7; border:1.5px solid #fbbf24; border-radius:10px; padding:24px 16px; text-align:center; margin:10px 0;';
                placeholder.innerHTML =
                    '<div style="font-size:2.5rem; margin-bottom:8px;">📄</div>' +
                    '<p style="color:#78350f; margin:0 0 14px; font-size:0.95rem; line-height:1.5;">Trên điện thoại không hiển thị trực tiếp file PDF.<br>Anh chị bấm nút bên dưới để xem hoặc tải về.</p>' +
                    '<a href="' + src + '" target="_blank" rel="noopener" style="display:inline-block; background:#0d47a1; color:#fff; padding:12px 22px; border-radius:8px; font-weight:600; text-decoration:none; font-size:0.95rem;">📖 Mở file PDF</a>';
                iframe.parentNode.replaceChild(placeholder, iframe);
            } else {
                iframe.setAttribute('src', src);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', processPdfIframes);
    } else {
        processPdfIframes();
    }
})();

// ---- Initialize Application ----
document.addEventListener('DOMContentLoaded', () => {
    fetch('/ccn-data.json')
        .then(r => r.json())
        .then(data => {
            CUM_CONG_NGHIEP = data.CUM_CONG_NGHIEP;
            CCN_CHUA_DAU_TU = data.CCN_CHUA_DAU_TU;
            window.KHU_CONG_NGHIEP = data.KHU_CONG_NGHIEP || [];
            // Tính lại THONG_KE từ dữ liệu mới (ghi đè giá trị cũ từ data.js)
            THONG_KE = {
                tongCCN: CUM_CONG_NGHIEP.length + CCN_CHUA_DAU_TU.length,
                dangHoatDong: CUM_CONG_NGHIEP.filter(c => c.trangThai === "hoat-dong").length,
                dangXayDung: CUM_CONG_NGHIEP.filter(c => c.trangThai === "xay-dung").length,
                choDauTu: CCN_CHUA_DAU_TU.length,
                dienTichHienHuu: CUM_CONG_NGHIEP.reduce((s, c) => s + c.dienTich, 0),
                dienTichQuyHoach: CCN_CHUA_DAU_TU.reduce((s, c) => s + c.dienTich, 0),
                tongDoanhNghiep: CUM_CONG_NGHIEP.reduce((s, c) => s + c.soDoanhNghiep, 0)
            };
            initMap();
            updateHeaderStats();
            renderStats();
            initCharts();
            renderCCNCards();
            renderQuyHoachTable();
            setupFilterListeners();
            setupNavTabs();
            setupScrollEffects();
            setupModal();
            animateOnScroll();
        })
        .catch((err) => {
            // Fallback: khi fetch ccn-data.json lỗi, dùng dữ liệu đã khai báo
            // trong data.js (CUM_CONG_NGHIEP, CCN_CHUA_DAU_TU đã được load sẵn).
            // Vẫn phải tính lại THONG_KE và gọi init để UI hiển thị được.
            console.warn('Không tải được ccn-data.json, dùng fallback từ data.js:', err);
            THONG_KE = {
                tongCCN: CUM_CONG_NGHIEP.length + CCN_CHUA_DAU_TU.length,
                dangHoatDong: CUM_CONG_NGHIEP.filter(c => c.trangThai === "hoat-dong").length,
                dangXayDung: CUM_CONG_NGHIEP.filter(c => c.trangThai === "xay-dung").length,
                choDauTu: CCN_CHUA_DAU_TU.length,
                dienTichHienHuu: CUM_CONG_NGHIEP.reduce((s, c) => s + c.dienTich, 0),
                dienTichQuyHoach: CCN_CHUA_DAU_TU.reduce((s, c) => s + c.dienTich, 0),
                tongDoanhNghiep: CUM_CONG_NGHIEP.reduce((s, c) => s + (c.soDoanhNghiep || 0), 0)
            };
            initMap();
            updateHeaderStats();
            renderStats();
            initCharts();
            renderCCNCards();
            renderQuyHoachTable();
            setupFilterListeners();
            setupNavTabs();
            setupScrollEffects();
            setupModal();
            animateOnScroll();
        });
});

// ---- Update Header Stats ----
function updateHeaderStats() {
    const elCcn = document.getElementById('header-total-ccn');
    const elDn = document.getElementById('header-total-dn');
    const elDt = document.getElementById('header-total-dt');
    if (elCcn) elCcn.textContent = THONG_KE.tongCCN;
    if (elDn) elDn.textContent = THONG_KE.tongDoanhNghiep;
    if (elDt) elDt.textContent = (THONG_KE.dienTichHienHuu + THONG_KE.dienTichQuyHoach).toFixed(1);

    const elHd = document.getElementById('legend-hoatdong');
    const elXd = document.getElementById('legend-xaydung');
    const elQh = document.getElementById('legend-quyhoach');
    const elTd = document.getElementById('legend-tamdung');
    if (elHd) elHd.textContent = THONG_KE.dangHoatDong;
    if (elXd) elXd.textContent = THONG_KE.dangXayDung;
    if (elQh) elQh.textContent = THONG_KE.choDauTu;
    if (elTd) elTd.textContent = CUM_CONG_NGHIEP.filter(c => c.trangThai === 'tam-dung').length;
}

// ---- Map Initialization ----
function initMap() {
    // Base layers
    const streetLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    });

    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    });

    const laoCaiLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap | <a href="https://bando.laocai.gov.vn" target="_blank">Bản đồ Lào Cai</a>'
    });

    const topoLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenTopoMap | <a href="https://bando.laocai.gov.vn" target="_blank">Bản đồ Lào Cai</a>'
    });

    map = L.map('map', {
        center: TINH_INFO.center,
        zoom: TINH_INFO.zoom,
        zoomControl: false,
        layers: [streetLayer]
    });

    // Layer control
    const baseMaps = {
        "🗺️ Bản đồ giao thông": streetLayer,
        "🛰️ Ảnh vệ tinh": satelliteLayer,
        "🗺️ Bản đồ Lào Cai (OSM)": laoCaiLayer,
        "⛰️ Địa hình": topoLayer
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);

    // Add zoom control to left
    L.control.zoom({ position: 'topleft' }).addTo(map);

    // Create marker layer group
    markerLayer = L.layerGroup().addTo(map);

    // Add markers
    addMarkers(CUM_CONG_NGHIEP);

    // Add province boundary hint (circle)
    L.circle(TINH_INFO.center, {
        radius: 55000,
        color: '#1565C0',
        fillColor: '#1565C0',
        fillOpacity: 0.03,
        weight: 1,
        dashArray: '8, 8'
    }).addTo(map);

    // Khi mở popup: (1) cuộn page xuống để map full viewport, (2) gắn click handler
    // cho nút "Xem trang chi tiết" qua data-attribute (thay onclick inline có rủi ro XSS).
    map.on('popupopen', function(e) {
        // (2) Click handler cho nút data-action="open-detail" trong popup
        var btn = e.popup.getElement() && e.popup.getElement().querySelector('[data-action="open-detail"]');
        if (btn) {
            btn.onclick = function() {
                openUnitDetail(btn.dataset.slug, btn.dataset.ten);
            };
        }

        // (1) Cuộn page xuống nếu header còn chiếm chỗ
        var mapSection = document.getElementById('map-section');
        if (!mapSection) return;
        var rect = mapSection.getBoundingClientRect();
        if (rect.top > 5) {
            window.scrollTo({ top: window.scrollY + rect.top - 4, behavior: 'smooth' });
            // Sau khi cuộn xong, báo Leaflet biết kích thước map mới và re-pan popup
            setTimeout(function() {
                map.invalidateSize();
                if (e.popup && e.popup._source && typeof e.popup._source.getLatLng === 'function') {
                    map.panTo(e.popup._source.getLatLng(), { animate: true, duration: 0.3 });
                }
            }, 450);
        }
    });
}

// ---- Create custom marker icon ----
function createMarkerIcon(trangThai) {
    return L.divIcon({
        className: 'custom-marker',
        html: `<div class="marker-pin status-${trangThai}">
                   <span class="marker-icon">🏭</span>
               </div>`,
        iconSize: [36, 42],
        iconAnchor: [18, 42],
        popupAnchor: [0, -42]
    });
}

// ---- Add markers to map ----
function addMarkers(ccnList) {
    markerLayer.clearLayers();
    markers = [];

    ccnList.forEach(ccn => {
        const marker = L.marker([ccn.lat, ccn.lng], {
            icon: createMarkerIcon(ccn.trangThai)
        });

        const popupContent = createPopupContent(ccn);
        marker.bindPopup(popupContent, {
            maxWidth: 300,
            closeButton: true
        });

        marker.on('click', () => {
            map.flyTo([ccn.lat, ccn.lng], 13, { duration: 0.8 });
        });

        marker.addTo(markerLayer);
        markers.push({ marker, data: ccn });
    });
}

// ---- Create popup content ----
function createPopupContent(ccn) {
    const status = TRANG_THAI[ccn.trangThai];
    const slugC = slugify(ccn.ten);
    return `
        <div class="popup-content">
            <div class="popup-header status-${ccn.trangThai}">
                🏭 ${escapeHtml(ccn.ten)}
            </div>
            <div class="popup-body">
                <div class="popup-info">📍 <strong>${escapeHtml(ccn.xa)}</strong></div>
                <div class="popup-info">📐 Diện tích: <strong>${ccn.dienTich} ha</strong></div>
                <div class="popup-info">🏢 Doanh nghiệp: <strong>${ccn.soDoanhNghiep}</strong></div>
                <div class="popup-info">📊 Tỷ lệ lấp đầy: <strong>${ccn.tyLeLapDay}%</strong></div>
                <div class="popup-info">🔖 Trạng thái: <strong>${status.icon} ${escapeHtml(status.ten)}</strong></div>
                <button class="popup-detail-btn" data-action="open-detail" data-slug="${escapeHtml(slugC)}" data-ten="${escapeHtml(ccn.ten)}">
                    📖 Xem trang chi tiết
                </button>
                <a class="popup-detail-btn" style="background:#34495e; color:white; text-decoration:none; margin-top:5px; display:inline-block; font-size:0.75rem; text-align:center;" href="https://www.google.com/maps/dir/?api=1&destination=${ccn.lat},${ccn.lng}" target="_blank">
                    🚗 Chỉ đường
                </a>
            </div>
        </div>
    `;
}

// ---- Get Huyen Name ----
function getHuyenName(huyenId) {
    const huyen = HUYEN_LIST.find(h => h.id === huyenId);
    return huyen ? huyen.ten : huyenId;
}

// ---- Initialize Charts ----
function initCharts() {
    const statusCtx = document.getElementById('statusChart');
    const areaCtx = document.getElementById('areaChart');

    if (statusCtx) {
        charts.status = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Đang hoạt động', 'Đang xây dựng', 'Chờ đầu tư'],
                datasets: [{
                    data: [THONG_KE.dangHoatDong, THONG_KE.dangXayDung, THONG_KE.choDauTu],
                    backgroundColor: ['#2E7D32', '#F57F17', '#1565C0'],
                    borderWidth: 2,
                    hoverOffset: 15
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 20, usePointStyle: true, font: { family: 'Roboto', size: 12 } }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 35, 50, 0.9)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 14, weight: 'bold' }
                    }
                },
                cutout: '65%'
            }
        });
    }

    if (areaCtx) {
        charts.area = new Chart(areaCtx, {
            type: 'bar',
            data: {
                labels: [(window.CUM_CONG_NGHIEP || CUM_CONG_NGHIEP).length + ' Cụm công nghiệp đã thành lập', (window.CCN_CHUA_DAU_TU || CCN_CHUA_DAU_TU).length + ' Cụm công nghiệp chưa thành lập'],
                datasets: [{
                    label: 'Diện tích (ha)',
                    data: [THONG_KE.dienTichHienHuu, THONG_KE.dienTichQuyHoach],
                    backgroundColor: ['#1565C0', '#42A5F5'],
                    borderRadius: 8,
                    barThickness: 60
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f0f3f7' },
                        ticks: { font: { family: 'Roboto' } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { family: 'Roboto', weight: 'bold' } }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(26, 35, 50, 0.9)',
                        displayColors: false,
                        padding: 12,
                        cornerRadius: 8
                    }
                }
            }
        });
    }
}

// ---- Render Statistics Bar ----
function renderStats() {
    const statsContent = document.getElementById('stats-content');
    if (!statsContent) return;

    statsContent.innerHTML = `
        <div class="stat-card animate-in" onclick="document.querySelector('[data-tab=list]').click()" style="cursor:pointer;" title="Xem danh sách Cụm công nghiệp">
            <div class="stat-icon">🏭</div>
            <div class="stat-number" data-target="${THONG_KE.tongCCN}">0</div>
            <div class="stat-label">Tổng Cụm công nghiệp theo Quy hoạch</div>
        </div>
        <div class="stat-card animate-in" onclick="document.querySelector('[data-tab=map]').click()" style="cursor:pointer;" title="Xem bản đồ Cụm công nghiệp đã thành lập (đang hoạt động)">
            <div class="stat-icon">🟢</div>
            <div class="stat-number" data-target="${THONG_KE.dangHoatDong}">0</div>
            <div class="stat-label">Cụm công nghiệp đang hoạt động</div>
        </div>
        <div class="stat-card animate-in" onclick="document.querySelector('[data-tab=map]').click()" style="cursor:pointer;" title="Xem bản đồ Cụm công nghiệp đang xây dựng">
            <div class="stat-icon">🟡</div>
            <div class="stat-number" data-target="${THONG_KE.dangXayDung}">0</div>
            <div class="stat-label">Cụm công nghiệp đang xây dựng</div>
        </div>
        <div class="stat-card animate-in" onclick="document.querySelector('[data-tab=ccnqh]').click()" style="cursor:pointer;" title="Xem bản đồ Cụm công nghiệp chưa thành lập (quy hoạch đến 2030)">
            <div class="stat-icon">🔵</div>
            <div class="stat-number" data-target="${THONG_KE.choDauTu}">0</div>
            <div class="stat-label">Cụm công nghiệp chưa thành lập</div>
        </div>
        <div class="stat-card animate-in" onclick="document.querySelector('[data-tab=list]').click()" style="cursor:pointer;" title="Xem danh sách Cụm công nghiệp đã thành lập">
            <div class="stat-icon">📐</div>
            <div class="stat-number" data-target="${THONG_KE.dienTichHienHuu}">0</div>
            <div class="stat-label">Diện tích Cụm công nghiệp đã thành lập (héc-ta)</div>
        </div>
        <div class="stat-card animate-in" onclick="document.querySelector('[data-tab=listqh]').click()" style="cursor:pointer;" title="Xem danh sách Cụm công nghiệp chưa thành lập">
            <div class="stat-icon">🟦</div>
            <div class="stat-number" data-target="${THONG_KE.dienTichQuyHoach}">0</div>
            <div class="stat-label">Diện tích Cụm công nghiệp chưa thành lập (héc-ta)</div>
        </div>
        <div class="stat-card animate-in" onclick="document.querySelector('[data-tab=thuhut]').click()" style="cursor:pointer;" title="Xem cơ hội đầu tư">
            <div class="stat-icon">🏢</div>
            <div class="stat-number" data-target="${THONG_KE.tongDoanhNghiep}">0</div>
            <div class="stat-label">Doanh nghiệp trong Cụm công nghiệp</div>
        </div>
    `;

    // Animate numbers
    setTimeout(() => animateNumbers(), 500);
}

// ---- Animate counter numbers ----
function animateNumbers() {
    const counters = document.querySelectorAll('.stat-number[data-target]');
    counters.forEach(counter => {
        const target = parseFloat(counter.getAttribute('data-target'));
        const isDecimal = target % 1 !== 0;
        const duration = 1500;
        const step = target / (duration / 16);
        let current = 0;

        const updateCounter = () => {
            current += step;
            if (current < target) {
                counter.textContent = isDecimal ? current.toFixed(1) : Math.floor(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = isDecimal ? target.toFixed(1) : target;
            }
        };
        updateCounter();
    });
}

// ---- Render CCN Cards ----
function renderCCNCards(filteredList) {
    const grid = document.getElementById('ccn-grid');
    if (!grid) return;

    var statusOrderCCN = {"hoat-dong": 1, "xay-dung": 2, "quy-hoach": 3, "tam-dung": 4};
    const list = filteredList || [...CUM_CONG_NGHIEP].sort(function(a, b) {
        return (statusOrderCCN[a.trangThai] || 99) - (statusOrderCCN[b.trangThai] || 99)
            || (b.dienTich - a.dienTich);
    });

    if (list.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                <div style="font-size: 3rem; margin-bottom: 16px;">🔍</div>
                <p style="font-size: 1.1rem;">Không tìm thấy cụm công nghiệp nào phù hợp</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = list.map(ccn => {
        const status = TRANG_THAI[ccn.trangThai];
        const progressClass = ccn.tyLeLapDay >= 70 ? 'high' : ccn.tyLeLapDay >= 40 ? 'medium' : 'low';
        const slugCcn = slugify(ccn.ten);
        return `
            <div class="ccn-card animate-in" style="cursor:pointer;" title="Bấm để xem trang chi tiết" data-slug="${escapeHtml(slugCcn)}" data-ten="${escapeHtml(ccn.ten)}">
                <div class="ccn-card-header status-${ccn.trangThai}">
                    <div class="ccn-card-name">${escapeHtml(ccn.ten)}</div>
                    <div class="ccn-card-badge">${status.icon} ${escapeHtml(status.ten)}</div>
                </div>
                <div class="ccn-card-body">
                    <div class="ccn-card-info">
                        <span class="info-icon">📍</span>
                        <span class="info-label">Vị trí:</span>
                        <span class="info-value">${escapeHtml(ccn.xa)}</span>
                    </div>
                    <div class="ccn-card-info">
                        <span class="info-icon">📐</span>
                        <span class="info-label">Diện tích:</span>
                        <span class="info-value">${ccn.dienTich} ha</span>
                    </div>
                    <div class="ccn-card-info">
                        <span class="info-icon">🏢</span>
                        <span class="info-label">Doanh nghiệp:</span>
                        <span class="info-value">${ccn.soDoanhNghiep}</span>
                    </div>
                    <div class="ccn-card-info">
                        <span class="info-icon">🔧</span>
                        <span class="info-label">Ngành nghề:</span>
                        <span class="info-value">${escapeHtml(ccn.nganhNghe)}</span>
                    </div>
                    <div class="ccn-card-progress">
                        <div class="progress-label">
                            <span>Tỷ lệ lấp đầy</span>
                            <span>${ccn.tyLeLapDay}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill ${progressClass}" style="width: 0%" data-width="${ccn.tyLeLapDay}%"></div>
                        </div>
                        <div style="text-align:right; margin-top:8px; color:#0d47a1; font-weight:600; font-size:0.85rem;">📖 Xem chi tiết →</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // Event delegation — onclick = function chỉ giữ 1 handler, không bị nhân đôi khi render lại
    grid.onclick = function(e) {
        const card = e.target.closest('.ccn-card[data-slug]');
        if (card) openUnitDetail(card.dataset.slug, card.dataset.ten);
    };

    // Animate progress bars
    setTimeout(() => {
        document.querySelectorAll('.progress-fill[data-width]').forEach(bar => {
            bar.style.width = bar.getAttribute('data-width');
        });
    }, 300);

    // Re-trigger scroll animations
    animateOnScroll();
}

function renderQuyHoachTable() {
    const tableBody = document.getElementById('quyhoach-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = CCN_CHUA_DAU_TU.map((ccn, idx) => {
        let baoCaoBadge, baoCaoTooltip = '';
        if (ccn.coBaoCao === true) {
            baoCaoBadge = `<span style="background:#dcfce7;color:#16a34a;padding:3px 8px;border-radius:4px;font-size:0.78rem;border:1px solid #86efac;white-space:nowrap;">✅ Đã có BC</span>`;
            baoCaoTooltip = ccn.baoCao ? `<div style="font-size:0.78rem;color:#475569;margin-top:4px;font-style:italic;">${escapeHtml(ccn.baoCao)}</div>` : '';
        } else if (ccn.coBaoCao === 'rar') {
            baoCaoBadge = `<span style="background:#fef9c3;color:#b45309;padding:3px 8px;border-radius:4px;font-size:0.78rem;border:1px solid #fde047;white-space:nowrap;">📦 File .rar</span>`;
            baoCaoTooltip = `<div style="font-size:0.78rem;color:#92400e;margin-top:4px;font-style:italic;">${escapeHtml(ccn.baoCao)}</div>`;
        } else {
            baoCaoBadge = `<span style="background:#fee2e2;color:#dc2626;padding:3px 8px;border-radius:4px;font-size:0.78rem;border:1px solid #fca5a5;white-space:nowrap;font-weight:600;">🔴 Chưa có báo cáo</span>`;
            baoCaoTooltip = '';
        }
        const slugQH = slugify(ccn.ten);
        return `
        <tr style="cursor:pointer; ${ccn.coBaoCao === false ? 'background:#fff5f5;' : ''}" data-slug="${escapeHtml(slugQH)}" data-ten="${escapeHtml(ccn.ten)}" title="Bấm để xem trang chi tiết">
            <td style="text-align:center;">${idx + 1}</td>
            <td><strong style="color:#1565c0;">${escapeHtml(ccn.ten)} →</strong></td>
            <td>${escapeHtml(ccn.xa)}</td>
            <td style="text-align:right;">${ccn.dienTich} ha</td>
            <td style="font-size:0.85rem;">${escapeHtml(ccn.huongPhatTrien || '-')}${baoCaoTooltip}</td>
            <td style="text-align:center;">${baoCaoBadge}</td>
        </tr>`;
    }).join('');

    tableBody.onclick = function(e) {
        const row = e.target.closest('tr[data-slug]');
        if (row) openUnitDetail(row.dataset.slug, row.dataset.ten);
    };
}

// ---- Render Documents Table ----
// Removed as requested

// ---- Render Sidebar ----
// Removed as requested

// ---- Filter Documents by category ----
// Removed as requested

// ---- Setup Filter Listeners ----
function setupFilterListeners() {
    const searchInput = document.getElementById('search-input');
    const trangThaiSelect = document.getElementById('trangthai-select');

    const applyFilters = () => {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const selectedTrangThai = trangThaiSelect.value;

        let filtered = CUM_CONG_NGHIEP.filter(ccn => {
            const matchSearch = !searchTerm ||
                ccn.ten.toLowerCase().includes(searchTerm) ||
                ccn.xa.toLowerCase().includes(searchTerm) ||
                ccn.nganhNghe.toLowerCase().includes(searchTerm);

            const matchTrangThai = selectedTrangThai === 'all' || ccn.trangThai === selectedTrangThai;

            return matchSearch && matchTrangThai;
        });

        // Update map markers
        addMarkers(filtered);

        // Update cards
        renderCCNCards(filtered);

        // Fit map bounds to filtered
        if (filtered.length > 0) {
            const bounds = L.latLngBounds(filtered.map(c => [c.lat, c.lng]));
            map.flyToBounds(bounds, { padding: [50, 50], maxZoom: 13, duration: 0.8 });
        }
    };

    searchInput.addEventListener('input', debounce(applyFilters, 300));
    trangThaiSelect.addEventListener('change', applyFilters);

    // Populate trang thai select
    trangThaiSelect.innerHTML = `<option value="all">Tất cả trạng thái</option>` +
        Object.entries(TRANG_THAI).map(([key, val]) =>
            `<option value="${key}">${val.icon} ${val.ten}</option>`
        ).join('');
}

// ---- Setup Navigation Tabs ----
function setupNavTabs() {
    const tabs = document.querySelectorAll('[data-tab]');
    const sections = {
        'dashboard': document.getElementById('dashboard-section'),
        'gioithieu': document.getElementById('gioithieu-section'),
        'map': document.getElementById('map-section'),
        'stats': document.getElementById('stats-section'),
        'list': document.getElementById('list-section'),
        'quyhoach': document.getElementById('quyhoach-section'),
        'quyche': document.getElementById('quyche-section'),
        'nghidinh32': document.getElementById('nghidinh32-section'),
        'nghidinh35': document.getElementById('nghidinh35-section'),
        'thongtu14': document.getElementById('thongtu14-section'),
        'nghiquyet': document.getElementById('nghiquyet-section'),
        'kehoach': document.getElementById('kehoach-section'),
        'ccnqh': document.getElementById('ccnqh-section'),
        'ccnranhgioi': document.getElementById('ccnranhgioi-section'),
        'thongke': document.getElementById('thongke-section'),
        'ranhgioi': document.getElementById('ranhgioi-section'),
        'thuhut': document.getElementById('thuhut-section'),
        'listqh': document.getElementById('listqh-section'),
        'listkcn': document.getElementById('listkcn-section'),
        'vanban': document.getElementById('vanban-section'),
        'tintuc': document.getElementById('tintuc-section'),
        'kcn': document.getElementById('kcn-section'),
        'unit-detail': document.getElementById('unit-detail-section')
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-tab');
            if (!target) return;
            currentView = target;

            // Close sidebar on mobile
            closeSidebar();

            // Update active on all nav items
            document.querySelectorAll('.nav-item[data-tab], .bottom-nav-item[data-tab]').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('[data-tab="' + target + '"]').forEach(t => t.classList.add('active'));

            // Show/hide sections
            Object.entries(sections).forEach(([key, section]) => {
                if (section) {
                    if (target === 'map') {
                        section.style.display = (key === 'map' || key === 'stats' || key === 'list') ? '' : 'none';
                    } else {
                        section.style.display = (key === target) ? '' : 'none';
                    }
                }
            });

            if (target === 'map') {
                setTimeout(() => map && map.invalidateSize(), 100);
            }
            if (target === 'kcn') {
                setTimeout(() => {
                    if (!window.kcnMap) initKCNMap();
                    else window.kcnMap.invalidateSize();
                }, 150);
            }
            if (target === 'listqh') {
                renderCCNQHCards();
            }
            if (target === 'listkcn') {
                renderKCNCards();
            }
            if (target === 'ccnqh') {
                setTimeout(() => {
                    if (!window.ccnqhMap) initCCNQHMap();
                    else window.ccnqhMap.invalidateSize();
                    renderCCNQHTable();
                }, 150);
            }
            if (target === 'ccnranhgioi') {
                setTimeout(() => {
                    if (!window.ranhGioiMap) initRanhGioiMap();
                    else window.ranhGioiMap.invalidateSize();
                }, 150);
            }
            if (target === 'thongke') {
                setTimeout(() => {
                    if (!window.thongKeInited) {
                        initThongKe();
                        window.thongKeInited = true;
                    }
                }, 150);
            }
            if (target === 'ranhgioi') {
                // Lazy-load iframe lần đầu click
                var iframe = document.getElementById('ranhgioi-iframe');
                if (iframe && iframe.src === 'about:blank' || !iframe.src.includes('ranh-gioi-kcn-ccn')) {
                    iframe.src = iframe.getAttribute('data-src');
                }
            }
            // Cập nhật URL hash để F5 giữ nguyên tab
            if (!window._skipHashUpdate) {
                try { history.replaceState(null, '', '#' + target); } catch(e) {}
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });

    // Đọc hash khi load trang → mở đúng tab
    function loadFromHash() {
        var hash = (window.location.hash || '').replace(/^#/, '');
        if (!hash) return;
        // Route đặc biệt: #unit/<slug> → mở tab chi tiết đơn vị
        if (hash.indexOf('unit/') === 0) {
            var slug = hash.slice(5);
            window._skipHashUpdate = true;
            // Đợi UNIT_DETAILS load xong
            if (window.UNIT_DETAILS === null) {
                setTimeout(function () { loadFromHash(); }, 200);
            } else {
                openUnitDetail(slug);
            }
            window._skipHashUpdate = false;
            return;
        }
        var btn = document.querySelector('[data-tab="' + hash + '"]');
        if (btn) {
            window._skipHashUpdate = true;
            btn.click();
            window._skipHashUpdate = false;
        }
    }
    // Trigger sau khi data đã load
    setTimeout(loadFromHash, 200);

    // Hỗ trợ back/forward button
    window.addEventListener('hashchange', function() {
        loadFromHash();
    });
}

// ---- KCN Map ----
function initKCNMap() {
        var kcnData = window.KHU_CONG_NGHIEP || [];
    if (!kcnData.length) { console.error("KHU_CONG_NGHIEP chưa được load"); return; }

    var kcnColors = { "hoat-dong": "#2e7d32", "xay-dung": "#f57f17", "quy-hoach": "#3949ab", "rut-qh": "#c62828" };
    var kcnLabels = { "hoat-dong": "Đang hoạt động", "xay-dung": "Đang xây dựng", "quy-hoach": "Quy hoạch", "rut-qh": "Rút khỏi Quy hoạch" };

    window.kcnMap = L.map('kcn-map', {
        center: [22.15, 104.15],
        zoom: 9,
        zoomControl: false
    });

    // Base layers: giao thông (mặc định), vệ tinh, địa hình
    var kcnStreet = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(window.kcnMap);
    var kcnSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    });
    var kcnTopo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenTopoMap'
    });

    L.control.layers({
        "🗺️ Bản đồ giao thông": kcnStreet,
        "🛰️ Ảnh vệ tinh": kcnSatellite,
        "⛰️ Địa hình": kcnTopo
    }, null, { position: 'topright' }).addTo(window.kcnMap);

    L.control.zoom({ position: 'topleft' }).addTo(window.kcnMap);

    kcnData.forEach(function(kcn) {
        var color = kcnColors[kcn.trangThai];
        var icon = L.divIcon({
            className: 'kcn-marker',
            html: '<div style="width:28px;height:28px;border-radius:50%;background:' + color + ';border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:bold;">🏭</div>',
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });

        var kcnSlug = slugify(kcn.ten);
        L.marker([kcn.lat, kcn.lng], { icon: icon })
            .addTo(window.kcnMap)
            .bindPopup(
                '<div style="min-width:220px;">' +
                '<h3 style="margin:0 0 6px;font-size:1rem;color:' + color + ';">' + escapeHtml(kcn.ten) + '</h3>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Vị trí:</b> ' + escapeHtml(kcn.viTri) + '</p>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Diện tích:</b> ' + kcn.dienTich + ' ha</p>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Trạng thái:</b> ' + escapeHtml(kcnLabels[kcn.trangThai]) + '</p>' +
                '<p style="margin:6px 0 0;font-size:0.82rem;color:#555;">' + escapeHtml(kcn.moTa) + '</p>' +
                '<button data-action="open-detail" data-slug="' + escapeHtml(kcnSlug) + '" data-ten="' + escapeHtml(kcn.ten) + '" style="margin-top:10px; width:100%; background:' + color + '; color:#fff; border:none; padding:8px 12px; border-radius:6px; font-weight:600; cursor:pointer; font-size:0.85rem;">📖 Xem trang chi tiết</button>' +
                '</div>'
            );
    });

    // Event delegation cho nút "Xem trang chi tiết" trong popup map KCN
    window.kcnMap.on('popupopen', function(e) {
        var btn = e.popup.getElement() && e.popup.getElement().querySelector('[data-action="open-detail"]');
        if (btn) {
            btn.onclick = function() {
                openUnitDetail(btn.dataset.slug, btn.dataset.ten);
            };
        }
    });
}

// ---- KCN Cards (tổng hợp đã TL + chưa TL) ----
function renderKCNCards() {
    var grid = document.getElementById('kcn-grid');
    if (!grid) return;
    if (grid.querySelectorAll('.ccn-card').length > 0) return;

    var kcnAll = [
        { ten:"KCN Phía Nam", viTri:"Phường Văn Phú, tỉnh Lào Cai", dt:400, tt:"hoat-dong", gc:"66 DA, lấp đầy 91,54%. Đa ngành, 12 DA FDI." },
        { ten:"KCN Trấn Yên", viTri:"Phường Âu Lâu, tỉnh Lào Cai", dt:339, tt:"xay-dung", gc:"GĐ I: 254,59 ha (QĐ 1438/TTg). Đang triển khai san nền." },
        { ten:"KCN Bản Qua (GĐ 1)", viTri:"Xã Bản Qua, tỉnh Lào Cai", dt:107, tt:"quy-hoach", gc:"Giữ nguyên QH. GĐ 2025-2030." },
        { ten:"KCN Y Can", viTri:"Xã Y Can, tỉnh Lào Cai", dt:350, tt:"quy-hoach", gc:"Giữ nguyên QH. GĐ 2025-2030." },
        { ten:"KCN Đông An", viTri:"Xã Đông An, tỉnh Lào Cai", dt:350, tt:"quy-hoach", gc:"Giữ nguyên QH. GĐ 2025-2030." },
        { ten:"KCN Thịnh Hưng (GĐ 1)", viTri:"Xã Thịnh Hưng, tỉnh Lào Cai", dt:104, tt:"quy-hoach", gc:"Giữ nguyên QH. GĐ 2025-2030." },
        { ten:"KCN Lục Yên (GĐ 1)", viTri:"Xã Tân Lĩnh, tỉnh Lào Cai", dt:221, tt:"quy-hoach", gc:"Giữ nguyên QH. GĐ 2025-2030." },
        { ten:"KCN Bắc Duyên Hải", viTri:"Phường Lào Cai, TP. Lào Cai", dt:85, tt:"hoat-dong", gc:"63 DA, lấp đầy >90%. Sẽ chuyển đổi chức năng theo QH Khu KT cửa khẩu Lào Cai 2045." },
        { ten:"KCN Tằng Loỏng", viTri:"Xã Gia Phú, tỉnh Lào Cai", dt:1100, tt:"hoat-dong", gc:"KCN tuyển khoáng, hóa chất lớn nhất cả nước. 29 DA, lấp đầy 85%." },
        { ten:"KCN Âu Lâu", viTri:"Phường Âu Lâu, tỉnh Lào Cai", dt:120, tt:"hoat-dong", gc:"12 DA, lấp đầy 84,15%. Còn 13,13 ha." },
        { ten:"KCN Minh Quân", viTri:"Xã Minh Quân, tỉnh Lào Cai", dt:75, tt:"hoat-dong", gc:"17 DA, lấp đầy 94,65% — cao nhất các KCN. Còn 4,01 ha." },
        { ten:"KCN Cốc Mỳ - Trịnh Tường (GĐ 1)", viTri:"Xã Trịnh Tường, tỉnh Lào Cai", dt:500, tt:"quy-hoach", gc:"Giảm DT từ 800 → 500 ha." },
        { ten:"KCN Võ Lao (GĐ 1)", viTri:"Xã Võ Lao, tỉnh Lào Cai", dt:500, tt:"quy-hoach", gc:"Tăng DT từ 200 → 500 ha." },
        { ten:"KCN Phú Xuân", viTri:"Xã Xuân Hòa, tỉnh Lào Cai", dt:300, tt:"quy-hoach", gc:"Đẩy nhanh từ sau 2030 lên 2026-2030." },
        { ten:"KCN Bát Xát", viTri:"Xã Bát Xát, tỉnh Lào Cai", dt:76, tt:"quy-hoach", gc:"Bổ sung mới. Phục vụ di chuyển từ KCN Đông Phố Mới." },
        { ten:"KCN Cam Đường", viTri:"Phường Cam Đường, TP. Lào Cai", dt:200, tt:"quy-hoach", gc:"Bổ sung mới. GĐ 2025-2030." },
        { ten:"KCN Thống Nhất", viTri:"Xã Gia Phú, tỉnh Lào Cai", dt:150, tt:"quy-hoach", gc:"Bổ sung mới. Chuyển từ CCN." },
        { ten:"KCN Việt Hồng 1", viTri:"Xã Việt Hồng, tỉnh Lào Cai", dt:300, tt:"quy-hoach", gc:"Bổ sung mới. GĐ 2025-2030." },
        { ten:"KCN Việt Hồng 2", viTri:"Xã Việt Hồng, tỉnh Lào Cai", dt:200, tt:"quy-hoach", gc:"Bổ sung mới. GĐ 2025-2030." },
        { ten:"KCN Phú Xuân 1", viTri:"Xã Xuân Hòa, tỉnh Lào Cai", dt:200, tt:"quy-hoach", gc:"Bổ sung mới. GĐ 2025-2030." },
        { ten:"KCN Đông Phố Mới", viTri:"Phường Lào Cai, TP. Lào Cai", dt:100, tt:"rut-qh", gc:"41 DA, lấp đầy >90%. Sẽ rút khỏi QH — di dời phục vụ đường sắt tốc độ cao LC-HN-HP → chuyển về KCN Bát Xát." }
    ];

    var statusOrderKCN = {"hoat-dong":1,"xay-dung":2,"quy-hoach":3,"rut-qh":4};
    kcnAll.sort(function(a, b) {
        return (statusOrderKCN[a.tt] || 99) - (statusOrderKCN[b.tt] || 99)
            || (b.dt - a.dt);
    });

    var colors = {"hoat-dong":"#2e7d32","xay-dung":"#f57f17","quy-hoach":"#1565c0","rut-qh":"#c62828"};
    var labels = {"hoat-dong":"Đang hoạt động","xay-dung":"Đang xây dựng","quy-hoach":"Chưa thành lập","rut-qh":"⚠️ Rút khỏi Quy hoạch"};
    var gradients = {
        "hoat-dong":"linear-gradient(135deg,#2e7d32,#43a047)",
        "xay-dung":"linear-gradient(135deg,#f57f17,#ff8f00)",
        "quy-hoach":"linear-gradient(135deg,#1565c0,#1976d2)",
        "rut-qh":"linear-gradient(135deg,#c62828,#e53935)"
    };

    var total = kcnAll.length;
    grid.innerHTML = kcnAll.map(function(kcn, idx) {
        var color = colors[kcn.tt];
        var bg = gradients[kcn.tt];
        var slug = slugify(kcn.ten);
        return '<div class="ccn-card" data-slug="' + escapeHtml(slug) + '" data-ten="' + escapeHtml(kcn.ten) + '" style="border-left:4px solid ' + color + '; cursor:pointer;" title="Bấm để xem trang chi tiết">' +
            '<div class="ccn-card-header" style="background:' + bg + ';">' +
                '<h3 class="ccn-card-title">' + escapeHtml(kcn.ten) + '</h3>' +
                '<span class="ccn-card-status" style="background:rgba(255,255,255,0.2);color:#fff;">' + labels[kcn.tt] + '</span>' +
            '</div>' +
            '<div class="ccn-card-body">' +
                '<div class="ccn-card-info"><span class="info-icon">📍</span><span class="info-label">Vị trí:</span><span>' + escapeHtml(kcn.viTri) + '</span></div>' +
                '<div class="ccn-card-info"><span class="info-icon">📐</span><span class="info-label">Diện tích:</span><span>' + kcn.dt + ' ha</span></div>' +
                '<div class="ccn-card-info" style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;"><span class="info-icon">📝</span><span style="font-size:0.85rem;color:#555;">' + escapeHtml(kcn.gc) + '</span></div>' +
                '<div class="ccn-card-progress" style="display:flex; justify-content:space-between; align-items:center;"><span>' + (idx+1) + '/' + total + '</span><span style="color:' + color + '; font-weight:600; font-size:0.85rem;">📖 Xem chi tiết →</span></div>' +
            '</div>' +
        '</div>';
    }).join('');

    grid.onclick = function(e) {
        var card = e.target.closest('.ccn-card[data-slug]');
        if (card) openUnitDetail(card.dataset.slug, card.dataset.ten);
    };
}

// ---- CCN QH Cards (31 CCN chưa TL - dạng card) ----
function renderCCNQHCards() {
    var grid = document.getElementById('ccnqh-grid');
    if (!grid) return;
    if (grid.querySelectorAll('.ccn-card').length > 0) return;
    var total = CCN_CHUA_DAU_TU.length;
    grid.innerHTML = CCN_CHUA_DAU_TU.map(function(ccn) {
        var slug = slugify(ccn.ten);
        return '<div class="ccn-card" data-slug="' + escapeHtml(slug) + '" data-ten="' + escapeHtml(ccn.ten) + '" style="border-left:4px solid #1565c0; cursor:pointer;" title="Bấm để xem trang chi tiết">' +
            '<div class="ccn-card-header" style="background:linear-gradient(135deg,#1565c0,#1976d2);">' +
                '<h3 class="ccn-card-title">' + escapeHtml(ccn.ten) + '</h3>' +
                '<span class="ccn-card-status" style="background:rgba(255,255,255,0.2);color:#fff;">Chưa thành lập</span>' +
            '</div>' +
            '<div class="ccn-card-body">' +
                '<div class="ccn-card-info"><span class="info-icon">📍</span><span class="info-label">Vị trí:</span><span>' + escapeHtml(ccn.xa) + '</span></div>' +
                '<div class="ccn-card-info"><span class="info-icon">📐</span><span class="info-label">Diện tích:</span><span>' + ccn.dienTich + ' ha</span></div>' +
                '<div class="ccn-card-info"><span class="info-icon">📋</span><span class="info-label">Hướng PT:</span><span>' + escapeHtml(ccn.huongPhatTrien) + '</span></div>' +
                (ccn.baoCao ? '<div class="ccn-card-info" style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;"><span class="info-icon">📝</span><span style="font-size:0.85rem;color:#555;">' + escapeHtml(ccn.baoCao) + '</span></div>' : '') +
                '<div class="ccn-card-progress" style="display:flex; justify-content:space-between; align-items:center;"><span>STT: ' + ccn.stt + '/' + total + '</span><span style="color:#1565c0; font-weight:600; font-size:0.85rem;">📖 Xem chi tiết →</span></div>' +
            '</div>' +
        '</div>';
    }).join('');

    grid.onclick = function(e) {
        var card = e.target.closest('.ccn-card[data-slug]');
        if (card) openUnitDetail(card.dataset.slug, card.dataset.ten);
    };
}

// ---- CCN QH Table (clickable rows → trang chi tiết) ----
function renderCCNQHTable() {
    var tableBody = document.getElementById('ccnqh-table-body');
    if (!tableBody) return;
    if (tableBody.querySelectorAll('tr').length > 0) return;
    tableBody.innerHTML = CCN_CHUA_DAU_TU.map(function(ccn, idx) {
        var slug = slugify(ccn.ten);
        return '<tr style="cursor:pointer; ' + (idx % 2 === 1 ? 'background:#f8f9fa;' : '') + '" data-slug="' + escapeHtml(slug) + '" data-ten="' + escapeHtml(ccn.ten) + '" title="Bấm để xem trang chi tiết">' +
            '<td style="padding:10px;text-align:center;border-bottom:1px solid #eee;">' + ccn.stt + '</td>' +
            '<td style="padding:10px;border-bottom:1px solid #eee;font-weight:600;color:#1565c0;">' + escapeHtml(ccn.ten) + ' →</td>' +
            '<td style="padding:10px;border-bottom:1px solid #eee;">' + escapeHtml(ccn.xa) + '</td>' +
            '<td style="padding:10px;text-align:right;border-bottom:1px solid #eee;">' + ccn.dienTich + '</td>' +
            '<td style="padding:10px;border-bottom:1px solid #eee;">' + escapeHtml(ccn.huongPhatTrien) +
                (ccn.baoCao ? '<div style="margin-top:4px;font-size:0.82rem;color:#555;border-top:1px solid #eee;padding-top:4px;">' + escapeHtml(ccn.baoCao) + '</div>' : '') +
            '</td>' +
            '</tr>';
    }).join('');

    tableBody.onclick = function(e) {
        var row = e.target.closest('tr[data-slug]');
        if (row) openUnitDetail(row.dataset.slug, row.dataset.ten);
    };
}

// ---- Thong Ke - Biểu đồ trực quan ----
function initThongKe() {
    renderThongKeCharts();
}

function renderThongKeCharts() {
    // === DATA SOURCES ===
    // 23 CCN đã TL (CUM_CONG_NGHIEP - từ data.js hoặc ccn-data.json)
    var ccnHien = CUM_CONG_NGHIEP;
    // 31 CCN chưa TL
    var ccnQH = CCN_CHUA_DAU_TU;
    // 21 KCN (7 đã TL + 14 chưa TL)
    var kcnList = [
        {ten:'KCN Phía Nam', xa:'Phường Văn Phú', dt:400, tt:'hoat-dong', da:66, ld:91.54, status:'da-tl'},
        {ten:'KCN Trấn Yên', xa:'Phường Âu Lâu', dt:339, tt:'xay-dung', da:0, ld:0, status:'da-tl'},
        {ten:'KCN Bản Qua (GĐ 1)', xa:'Xã Bản Qua', dt:107, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Y Can', xa:'Xã Y Can', dt:350, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Đông An', xa:'Xã Đông An', dt:350, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Thịnh Hưng (GĐ 1)', xa:'Xã Thịnh Hưng', dt:104, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Lục Yên (GĐ 1)', xa:'Xã Tân Lĩnh', dt:221, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Bắc Duyên Hải', xa:'Phường Lào Cai', dt:85, tt:'hoat-dong', da:63, ld:90, status:'da-tl'},
        {ten:'KCN Tằng Loỏng', xa:'Xã Gia Phú', dt:1100, tt:'hoat-dong', da:29, ld:85, status:'da-tl'},
        {ten:'KCN Âu Lâu', xa:'Phường Âu Lâu', dt:120, tt:'hoat-dong', da:12, ld:84.15, status:'da-tl'},
        {ten:'KCN Minh Quân', xa:'Xã Minh Quân', dt:75, tt:'hoat-dong', da:17, ld:94.65, status:'da-tl'},
        {ten:'KCN Cốc Mỳ - Trịnh Tường (GĐ 1)', xa:'Xã Trịnh Tường', dt:500, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Võ Lao (GĐ 1)', xa:'Xã Võ Lao', dt:500, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Phú Xuân', xa:'Xã Xuân Hòa', dt:300, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Bát Xát', xa:'Xã Bát Xát', dt:76, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Cam Đường', xa:'Phường Cam Đường', dt:200, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Thống Nhất', xa:'Xã Gia Phú', dt:150, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Việt Hồng 1', xa:'Xã Việt Hồng', dt:300, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Việt Hồng 2', xa:'Xã Việt Hồng', dt:200, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Phú Xuân 1', xa:'Xã Xuân Hòa', dt:200, tt:'quy-hoach', da:0, ld:0, status:'chua-tl'},
        {ten:'KCN Đông Phố Mới', xa:'Phường Lào Cai', dt:100, tt:'rut-qh', da:41, ld:90, status:'rut-qh'}
    ];

    // === CHART 1: Trạng thái tổng hợp (stacked bar) ===
    var kcnHienHD = kcnList.filter(function(k){return k.status==='da-tl' && k.tt==='hoat-dong';}).length;
    var kcnHienXD = kcnList.filter(function(k){return k.status==='da-tl' && k.tt==='xay-dung';}).length;
    var kcnQHCount = kcnList.filter(function(k){return k.status==='chua-tl';}).length;
    var kcnRut = kcnList.filter(function(k){return k.status==='rut-qh';}).length;
    var ccnHienHD = ccnHien.filter(function(c){return c.trangThai==='hoat-dong';}).length;
    var ccnHienXD = ccnHien.filter(function(c){return c.trangThai==='xay-dung';}).length;
    var ccnQHCount = ccnQH.length;

    new Chart(document.getElementById('chart-trangthai'), {
        type: 'bar',
        data: {
            labels: ['Khu công nghiệp', 'Cụm công nghiệp'],
            datasets: [
                {label:'Đang hoạt động', data:[kcnHienHD, ccnHienHD], backgroundColor:'#2e7d32'},
                {label:'Đang xây dựng', data:[kcnHienXD, ccnHienXD], backgroundColor:'#f57f17'},
                {label:'Quy hoạch (chưa thành lập)', data:[kcnQHCount, ccnQHCount], backgroundColor:'#1565c0'},
                {label:'Rút khỏi Quy hoạch', data:[kcnRut, 0], backgroundColor:'#c62828'}
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
        }
    });

    // === CHART 2: So sánh hiện tại vs QH 2030 ===
    new Chart(document.getElementById('chart-sosanh'), {
        type: 'bar',
        data: {
            labels: ['KCN (số)','CCN (số)','KCN (1000 ha)','CCN (1000 ha)'],
            datasets: [
                {label:'Hiện tại (2025)', data:[7, 23, 2.139, 0.904], backgroundColor:'#90caf9'},
                {label:'Quy hoạch 2030', data:[20, 54, 5.797, 2.928], backgroundColor:'#1565c0'},
                {label:'Tầm nhìn 2050', data:[22, 62, 8.078, 3.779], backgroundColor:'#0d47a1'}
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: { y: { beginAtZero: true } }
        }
    });

    // === CHART 3: Tỷ lệ lấp đầy 23 CCN ===
    var ccnLD = ccnHien.slice().sort(function(a,b){return b.tyLeLapDay-a.tyLeLapDay;});
    new Chart(document.getElementById('chart-lapday'), {
        type: 'bar',
        data: {
            labels: ccnLD.map(function(c){return c.ten;}),
            datasets: [{
                label:'Tỷ lệ lấp đầy (%)',
                data: ccnLD.map(function(c){return c.tyLeLapDay;}),
                backgroundColor: ccnLD.map(function(c){
                    if (c.tyLeLapDay>=90) return '#2e7d32';
                    if (c.tyLeLapDay>=50) return '#f57f17';
                    if (c.tyLeLapDay>0) return '#ea580c';
                    return '#9ca3af';
                }),
                borderRadius: 3
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true, max: 100 } }
        }
    });

    // === CHART 4: Top 15 CCN theo số DN ===
    var ccnDN = ccnHien.slice().sort(function(a,b){return b.soDoanhNghiep-a.soDoanhNghiep;}).slice(0, 15);
    new Chart(document.getElementById('chart-doanhnghiep'), {
        type: 'bar',
        data: {
            labels: ccnDN.map(function(c){return c.ten;}),
            datasets: [{
                label: 'Số doanh nghiệp',
                data: ccnDN.map(function(c){return c.soDoanhNghiep;}),
                backgroundColor: '#7b1fa2',
                borderRadius: 3
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // === CHART 5: Diện tích 23 CCN đã TL ===
    var ccnHienSorted = ccnHien.slice().sort(function(a,b){return b.dienTich-a.dienTich;});
    new Chart(document.getElementById('chart-dt-ccn-hien'), {
        type: 'bar',
        data: {
            labels: ccnHienSorted.map(function(c){return c.ten;}),
            datasets: [{
                label: 'Diện tích (ha)',
                data: ccnHienSorted.map(function(c){return c.dienTich;}),
                backgroundColor: ccnHienSorted.map(function(c){
                    var colors = {'hoat-dong':'#2e7d32','xay-dung':'#f57f17','tam-dung':'#9ca3af'};
                    return colors[c.trangThai] || '#1565c0';
                }),
                borderRadius: 3
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // === CHART 6: Diện tích 31 CCN chưa TL ===
    var ccnQHSorted = ccnQH.slice().sort(function(a,b){return b.dienTich-a.dienTich;});
    new Chart(document.getElementById('chart-dt-ccn-qh'), {
        type: 'bar',
        data: {
            labels: ccnQHSorted.map(function(c){return c.ten;}),
            datasets: [{
                label: 'Diện tích QH (ha)',
                data: ccnQHSorted.map(function(c){return c.dienTich;}),
                backgroundColor: ccnQHSorted.map(function(c){
                    return c.coBaoCao===true ? '#16a34a' : c.coBaoCao===false ? '#dc2626' : '#f59e0b';
                }),
                borderRadius: 3
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // === CHART 7: 21 KCN theo DT ===
    var kcnSorted = kcnList.slice().sort(function(a,b){return b.dt-a.dt;});
    new Chart(document.getElementById('chart-kcn'), {
        type: 'bar',
        data: {
            labels: kcnSorted.map(function(k){return k.ten;}),
            datasets: [{
                label: 'Diện tích (ha)',
                data: kcnSorted.map(function(k){return k.dt;}),
                backgroundColor: kcnSorted.map(function(k){
                    var c = {'hoat-dong':'#2e7d32','xay-dung':'#f57f17','quy-hoach':'#1565c0','rut-qh':'#c62828'};
                    return c[k.tt];
                }),
                borderRadius: 3
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // === CHART 8: Top 15 xã/phường ===
    var xaMap = {};
    kcnList.forEach(function(k){ xaMap[k.xa] = (xaMap[k.xa]||0) + k.dt; });
    ccnHien.forEach(function(c){
        // Extract xã/phường từ field xa
        var parts = c.xa.split(',');
        var xa = parts[0].trim();
        xaMap[xa] = (xaMap[xa]||0) + c.dienTich;
    });
    ccnQH.forEach(function(c){
        var parts = c.xa.split(',');
        var xa = parts[0].trim();
        xaMap[xa] = (xaMap[xa]||0) + c.dienTich;
    });
    var xaSorted = Object.entries(xaMap).sort(function(a,b){return b[1]-a[1];}).slice(0, 15);
    new Chart(document.getElementById('chart-xa'), {
        type: 'bar',
        data: {
            labels: xaSorted.map(function(x){return x[0];}),
            datasets: [{
                label:'Diện tích (ha)',
                data: xaSorted.map(function(x){return Math.round(x[1]);}),
                backgroundColor: '#0891b2',
                borderRadius: 3
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // === CHART 9: CCN đã TL - phân loại hoàn thiện ===
    var tlHoanThien = ccnHien.filter(function(c){return c.tyLeLapDay>=90;}).length;
    var tlCao = ccnHien.filter(function(c){return c.tyLeLapDay>=50 && c.tyLeLapDay<90;}).length;
    var tlTB = ccnHien.filter(function(c){return c.tyLeLapDay>0 && c.tyLeLapDay<50;}).length;
    var tlChuaCo = ccnHien.filter(function(c){return c.tyLeLapDay===0;}).length;
    new Chart(document.getElementById('chart-hoanthien'), {
        type: 'doughnut',
        data: {
            labels: ['Lấp đầy ≥ 90%', 'Lấp đầy 50-89%', 'Lấp đầy < 50%', 'Chưa lấp đầy (0%)'],
            datasets: [{
                data: [tlHoanThien, tlCao, tlTB, tlChuaCo],
                backgroundColor: ['#2e7d32','#f57f17','#ea580c','#9ca3af'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } }
        }
    });

    // === CHART 10: Timeline ===
    new Chart(document.getElementById('chart-timeline'), {
        type: 'line',
        data: {
            labels: ['Hiện tại (2025)', 'Quy hoạch 2030', 'Tầm nhìn 2050'],
            datasets: [
                {label:'KCN (số)', data:[7, 20, 22], borderColor:'#c62828', backgroundColor:'rgba(198,40,40,0.1)', tension:0.3, fill:false, yAxisID:'y', borderWidth:3, pointRadius:6},
                {label:'CCN (số)', data:[23, 54, 62], borderColor:'#1565c0', backgroundColor:'rgba(21,101,192,0.1)', tension:0.3, fill:false, yAxisID:'y', borderWidth:3, pointRadius:6},
                {label:'Tổng diện tích (1000 ha)', data:[3.04, 8.73, 11.86], borderColor:'#2e7d32', backgroundColor:'rgba(46,125,50,0.15)', tension:0.3, fill:true, yAxisID:'y1', borderDash:[6,4], borderWidth:3, pointRadius:6}
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                y: { type:'linear', position:'left', title:{display:true, text:'Số lượng KCN/CCN'}, beginAtZero: true },
                y1: { type:'linear', position:'right', title:{display:true, text:'Diện tích (nghìn ha)'}, beginAtZero: true, grid:{drawOnChartArea:false} }
            }
        }
    });
}

// (Legacy dead code block đã được xoá - 2026-04-17)

// ---- Ranh Giới Polygon Map with filters ----
window.ranhGioiData = [];
window.ranhGioiLayers = [];

function initRanhGioiMap() {
    window.ranhGioiMap = L.map('ccnranhgioi-map', {
        center: [22.0, 104.4],
        zoom: 9,
        zoomControl: false
    });

    // Base layers
    var baseVoyager = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(window.ranhGioiMap);
    var baseSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri'
    });
    var baseOSM = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap'
    });
    var baseTopo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenTopoMap'
    });

    // Overlay: Giao thông (layer đè lên base, hiển thị đường đậm)
    var layerGiaoThong = L.tileLayer('https://{s}.tile.thunderforest.com/transport/{z}/{x}/{y}.png?apikey=a5dd6a2f1c934394bce6b0fb077203eb', {
        attribution: '&copy; Thunderforest Transport',
        opacity: 0.75
    });

    // Overlay: Đường cao tốc + Quốc lộ chính + Mỏ khoáng sản
    // Dữ liệu tách ra map-layers.json (tuyenDuong, moKhoangSan) - 2026-04-17
    var layerDuong = L.layerGroup();
    var layerMoKs = L.layerGroup();
    fetch('map-layers.json')
        .then(function(r) { return r.json(); })
        .then(function(mapLayers) {
            (mapLayers.tuyenDuong || []).forEach(function(td) {
                var poly = L.polyline(td.coords, {color: td.color, weight: td.w, opacity: 0.8, dashArray: td.dash || null}).addTo(layerDuong);
                poly.bindTooltip(td.ten, {sticky: true, className: 'polygon-label'});
            });
            (mapLayers.moKhoangSan || []).forEach(function(m) {
                var icon = L.divIcon({
                    className: 'mo-marker',
                    html: '<div style="width:26px;height:26px;background:#7c2d12;border:2px solid #fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.3);">' + m.icon + '</div>',
                    iconSize: [26,26], iconAnchor: [13,13]
                });
                var marker = L.marker([m.lat, m.lng], {icon: icon}).addTo(layerMoKs);
                marker.bindPopup('<b>' + m.ten + '</b><br>Loại: ' + m.loai);
                marker.bindTooltip(m.ten, {direction:'top', offset:[0,-10]});
            });
        })
        .catch(function(e) { console.error('Lỗi tải map-layers.json:', e); });

    // Overlay: Ranh giới hành chính (dùng OpenStreetMap boundaries style)
    var layerRanhGioiHC = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CARTO Labels',
        opacity: 0.8
    });

    L.control.zoom({ position: 'topleft' }).addTo(window.ranhGioiMap);

    // Layer control với nhóm base và nhóm overlay
    var baseMaps = {
        '🗺️ Bản đồ giao thông': baseVoyager,
        '🛰️ Ảnh vệ tinh': baseSat,
        '🌐 OpenStreetMap': baseOSM,
        '⛰️ Địa hình': baseTopo
    };
    var overlayMaps = {
        '🚗 Layer giao thông chi tiết': layerGiaoThong,
        '🛣️ Đường cao tốc & Quốc lộ': layerDuong,
        '⛏️ Mỏ khoáng sản': layerMoKs,
        '🏷️ Nhãn hành chính': layerRanhGioiHC
    };
    L.control.layers(baseMaps, overlayMaps, { position: 'topright', collapsed: false }).addTo(window.ranhGioiMap);

    // Link đến layer Quy hoạch SDĐ bên ngoài
    var customControl = L.control({position: 'bottomleft'});
    customControl.onAdd = function() {
        var div = L.DomUtil.create('div', 'qhsdd-link');
        div.innerHTML = '<a href="https://bando.laocai.gov.vn/" target="_blank" style="background:#1565c0;color:#fff;padding:6px 12px;border-radius:6px;text-decoration:none;font-weight:600;font-size:0.82rem;box-shadow:0 2px 6px rgba(0,0,0,0.25);">🗺️ Xem Quy hoạch SDĐ tỉnh</a>';
        return div;
    };
    customControl.addTo(window.ranhGioiMap);

    // ===========================================================
    // TÍCH HỢP 3 NGUỒN DỮ LIỆU vào bản đồ ranh giới:
    //   - 21 KCN (KHU_CONG_NGHIEP)
    //   - 23 CCN hiện hữu (CUM_CONG_NGHIEP)
    //   - 31 CCN quy hoạch (CCN_CHUA_DAU_TU)
    //   + 25 polygon chính xác từ ccn-polygons.json
    // Nếu một KCN/CCN đã có polygon chính thức -> dùng polygon đó.
    // Nếu chưa có -> vẽ ô vuông CAM (is_synthetic) quanh toạ độ UBND xã.
    // ===========================================================
    fetch('ccn-polygons.json')
        .then(function(r) { return r.json(); })
        .then(function(polygons) {
            window.ranhGioiData = buildRanhGioiData(polygons);
            // Build xa options
            var xaSet = Array.from(new Set(window.ranhGioiData.map(function(d){ return d.xa; }).filter(Boolean))).sort();
            var xaSelect = document.getElementById('filter-xa');
            while (xaSelect.options.length > 1) xaSelect.remove(1);
            xaSet.forEach(function(xa) {
                var opt = document.createElement('option');
                opt.value = xa; opt.textContent = xa;
                xaSelect.appendChild(opt);
            });
            // Bind filter change (nếu chưa bind)
            if (!window._ranhGioiFiltersBound) {
                ['filter-loai','filter-trangthai','filter-xa','filter-dientich'].forEach(function(id) {
                    var el = document.getElementById(id);
                    if (el) el.addEventListener('change', applyRanhGioiFilters);
                });
                window._ranhGioiFiltersBound = true;
            }
            renderRanhGioi(window.ranhGioiData);
        })
        .catch(function(e) { console.error('Lỗi tải ccn-polygons.json:', e); });
}

// ===========================================================
// Hàm tổng hợp dữ liệu bản đồ ranh giới.
// Ghép polygon chính thức với KCN/CCN từ ccn-data.json.
// KCN/CCN chưa có polygon -> vẽ ô vuông cam (is_synthetic=true).
// ===========================================================
function buildRanhGioiData(polygons) {
    function normName(s) { return (s || '').toLowerCase().trim().replace(/\s+/g, ' '); }

    var polygonByName = {};
    polygons.forEach(function(p) { polygonByName[normName(p.name)] = p; });

    // Hàm tạo ô vuông cam quanh toạ độ UBND xã. area_ha có thể thiếu -> mặc định 5 ha.
    function makeSquare(lat, lng, areaHa) {
        var ha = Math.max(parseFloat(areaHa) || 5, 1);
        var sideM = Math.sqrt(ha * 10000); // cạnh (mét)
        var halfM = sideM / 2;
        var dLat = halfM / 111320;
        var dLng = halfM / (111320 * Math.cos(lat * Math.PI / 180));
        return [
            [lat - dLat, lng - dLng],
            [lat + dLat, lng - dLng],
            [lat + dLat, lng + dLng],
            [lat - dLat, lng + dLng]
        ];
    }

    var merged = [];
    var seen = {};

    // Hàm build mô tả phong phú từ source data
    function describeKCN(k) { return k.moTa || ''; }
    function describeCCN_HH(c) { return c.moTa || ''; }
    function describeCCN_QH(c) { return c.ghiChu || c.baoCao || c.huongPhatTrien || ''; }

    // Pre-index các source theo normName để match với polygon
    var kcnByName = {}, ccnHHByName = {}, ccnQHByName = {};
    (window.KHU_CONG_NGHIEP || []).forEach(function(k) { kcnByName[normName(k.ten)] = k; });
    (window.CUM_CONG_NGHIEP || []).forEach(function(c) { ccnHHByName[normName(c.ten)] = c; });
    (window.CCN_CHUA_DAU_TU || []).forEach(function(c) { ccnQHByName[normName(c.ten)] = c; });

    // 1. Đưa tất cả polygon chính thức vào trước, MERGE thêm sourceDesc/xa
    //    từ ccn-data.json nếu có match theo tên.
    polygons.forEach(function(p) {
        var key = normName(p.name);
        var merged_item = Object.assign({}, p);
        if (kcnByName[key]) {
            merged_item.sourceDesc = merged_item.sourceDesc || describeKCN(kcnByName[key]);
            if (!merged_item.xa || merged_item.xa === '') merged_item.xa = kcnByName[key].viTri || '';
        } else if (ccnHHByName[key]) {
            merged_item.sourceDesc = merged_item.sourceDesc || describeCCN_HH(ccnHHByName[key]);
            // giữ xa polygon nếu có, nếu không lấy từ source
        } else if (ccnQHByName[key]) {
            merged_item.sourceDesc = merged_item.sourceDesc || describeCCN_QH(ccnQHByName[key]);
            // CCN QH có xa chi tiết hơn -> overwrite nếu polygon xa ngắn hơn
            var srcXa = ccnQHByName[key].xa || '';
            if (srcXa && srcXa.length > (merged_item.xa || '').length) merged_item.xa = srcXa;
        }
        merged.push(merged_item);
        seen[key] = true;
    });

    // 2. Với mỗi nguồn, nếu tên chưa có polygon -> tạo ô vuông cam synthetic
    function addSynthetic(src, section, extra) {
        if (!src || typeof src.lat !== 'number' || typeof src.lng !== 'number') return;
        var key = normName(src.ten);
        if (seen[key]) return; // đã có polygon, bỏ qua
        seen[key] = true;
        merged.push({
            section: section,
            name: src.ten,
            num_points: 4,
            area_ha: parseFloat(src.dienTich) || 0,
            coords: makeSquare(src.lat, src.lng, src.dienTich),
            is_approx: true,
            is_synthetic: true,
            trangThai: extra.trangThai || src.trangThai || 'quy-hoach',
            giaiDoan: extra.giaiDoan || '2025-2030',
            xa: src.xa || src.viTri || '',
            reason: 'Chưa có toạ độ ranh giới chính xác — vẽ ô vuông minh hoạ quanh vị trí UBND xã (hoặc điểm tham chiếu gần nhất).',
            sourceDesc: extra.sourceDesc || ''
        });
    }

    // 2a. 21 KCN từ KHU_CONG_NGHIEP
    (window.KHU_CONG_NGHIEP || []).forEach(function(k) {
        addSynthetic(k, 'KCN', {
            trangThai: k.trangThai,
            giaiDoan: k.trangThai === 'hoat-dong' || k.trangThai === 'xay-dung' ? 'Hiện hữu' : '2025-2030',
            sourceDesc: k.moTa || ''
        });
    });

    // 2b. 23 CCN hiện hữu từ CUM_CONG_NGHIEP
    (window.CUM_CONG_NGHIEP || []).forEach(function(c) {
        addSynthetic(c, 'CCN', {
            trangThai: c.trangThai,
            giaiDoan: 'Hiện hữu',
            sourceDesc: c.moTa || ''
        });
    });

    // 2c. 31 CCN quy hoạch từ CCN_CHUA_DAU_TU
    (window.CCN_CHUA_DAU_TU || []).forEach(function(c) {
        // CCN QH không có field trangThai, mặc định là quy-hoach
        var gd = /2031-2050/i.test(c.huongPhatTrien || '') ? '2031-2050' : '2025-2030';
        addSynthetic(c, 'CCN', {
            trangThai: 'quy-hoach',
            giaiDoan: gd,
            sourceDesc: c.ghiChu || c.baoCao || c.huongPhatTrien || ''
        });
    });

    // ===========================================================
    // DEDUPE / GIÃN TÂM:
    // Các ô vuông synthetic cùng xã thường trùng UBND -> chồng nhau.
    // Gom nhóm theo tâm (lat,lng round 2 chữ số ~1km), với nhóm có >=2
    // item thì bố trí vòng tròn quanh tâm chung, bán kính = tổng cạnh
    // của các ô vuông / (2π) × 1.4 (đủ tách rời + padding).
    // ===========================================================
    function centerOf(coords) {
        var n = coords.length;
        if (coords[0][0] === coords[n-1][0] && coords[0][1] === coords[n-1][1]) n--;
        var sx = 0, sy = 0;
        for (var i = 0; i < n; i++) { sx += coords[i][0]; sy += coords[i][1]; }
        return [sx / n, sy / n];
    }
    function maxSide(coords) {
        var lats = coords.map(function(c){return c[0];});
        var lngs = coords.map(function(c){return c[1];});
        return Math.max(Math.max.apply(null, lats) - Math.min.apply(null, lats),
                        Math.max.apply(null, lngs) - Math.min.apply(null, lngs));
    }
    function shiftCoords(coords, dLat, dLng) {
        return coords.map(function(c) { return [c[0] + dLat, c[1] + dLng]; });
    }

    var groups = {};
    merged.forEach(function(m, idx) {
        if (!m.is_synthetic) return;
        var c = centerOf(m.coords);
        var key = c[0].toFixed(2) + ',' + c[1].toFixed(2); // ~1km grouping
        if (!groups[key]) groups[key] = [];
        groups[key].push({item: m, idx: idx, cx: c[0], cy: c[1]});
    });

    Object.keys(groups).forEach(function(key) {
        var group = groups[key];
        if (group.length < 2) return;
        // Tổng cạnh các ô -> bán kính đủ tách rời
        var totalSide = 0;
        group.forEach(function(g) { totalSide += maxSide(g.item.coords); });
        var rad = (totalSide / (2 * Math.PI)) * 1.4;
        if (rad < 0.005) rad = 0.005; // tối thiểu ~500m
        // Xếp vòng tròn quanh tâm chung (lấy tâm item đầu)
        var n = group.length;
        var cx = group[0].cx, cy = group[0].cy;
        group.forEach(function(g, i) {
            var angle = (2 * Math.PI / n) * i - Math.PI / 2;
            var dLat = rad * Math.sin(angle);
            var dLng = rad * Math.cos(angle) / Math.cos(g.cy * Math.PI / 180);
            var shiftLat = (cx + dLat) - g.cx;
            var shiftLng = (cy + dLng) - g.cy;
            g.item.coords = shiftCoords(g.item.coords, shiftLat, shiftLng);
        });
    });

    // ===========================================================
    // PAIRWISE NUDGE: lặp lại max 30 lần, đẩy các ô synthetic ra
    // khỏi nhau (và khỏi polygon chính thức) bằng AABB overlap.
    // Dùng sau group-dedupe để xử lý các cặp cross-group (<1km nhưng
    // khác key toFixed(2)).
    // ===========================================================
    function aabb(coords) {
        var lats = coords.map(function(c){return c[0];});
        var lngs = coords.map(function(c){return c[1];});
        return {
            minLat: Math.min.apply(null, lats),
            maxLat: Math.max.apply(null, lats),
            minLng: Math.min.apply(null, lngs),
            maxLng: Math.max.apply(null, lngs)
        };
    }
    for (var iter = 0; iter < 30; iter++) {
        var anyMoved = false;
        for (var i = 0; i < merged.length; i++) {
            for (var j = i + 1; j < merged.length; j++) {
                var a = merged[i], b = merged[j];
                var ba = aabb(a.coords), bb = aabb(b.coords);
                if (ba.maxLat < bb.minLat || bb.maxLat < ba.minLat ||
                    ba.maxLng < bb.minLng || bb.maxLng < ba.minLng) continue;
                var overlapLat = Math.min(ba.maxLat, bb.maxLat) - Math.max(ba.minLat, bb.minLat);
                var overlapLng = Math.min(ba.maxLng, bb.maxLng) - Math.max(ba.minLng, bb.minLng);
                if (overlapLat <= 0 || overlapLng <= 0) continue;

                var ca = centerOf(a.coords), cb = centerOf(b.coords);
                var dirLat = ca[0] - cb[0], dirLng = ca[1] - cb[1];
                var dist = Math.sqrt(dirLat*dirLat + dirLng*dirLng);
                if (dist < 1e-6) { dirLat = 0.001; dirLng = 0.001; dist = Math.sqrt(2)*0.001; }
                // Push vừa đủ tách, hướng theo trục ngắn nhất
                var push = Math.min(overlapLat, overlapLng) * 0.55;
                var pushLat = dirLat / dist * push;
                var pushLng = dirLng / dist * push;

                var synA = a.is_synthetic, synB = b.is_synthetic;
                if (synA && synB) {
                    a.coords = shiftCoords(a.coords,  pushLat/2,  pushLng/2);
                    b.coords = shiftCoords(b.coords, -pushLat/2, -pushLng/2);
                    anyMoved = true;
                } else if (synA) {
                    a.coords = shiftCoords(a.coords, pushLat, pushLng);
                    anyMoved = true;
                } else if (synB) {
                    b.coords = shiftCoords(b.coords, -pushLat, -pushLng);
                    anyMoved = true;
                }
                // Cả 2 đều là polygon chính thức: không dịch (không được sửa)
            }
        }
        if (!anyMoved) break;
    }

    return merged;
}

function resetFilters() {
    document.getElementById('filter-loai').value = 'all';
    document.getElementById('filter-trangthai').value = 'all';
    document.getElementById('filter-xa').value = 'all';
    document.getElementById('filter-dientich').value = 'all';
    applyRanhGioiFilters();
}

function applyRanhGioiFilters() {
    var loai = document.getElementById('filter-loai').value;
    var tt = document.getElementById('filter-trangthai').value;
    var xa = document.getElementById('filter-xa').value;
    var dt = document.getElementById('filter-dientich').value;

    var filtered = window.ranhGioiData.filter(function(item) {
        if (loai !== 'all' && item.section !== loai) return false;
        if (tt !== 'all' && item.trangThai !== tt) return false;
        if (xa !== 'all' && item.xa !== xa) return false;
        if (dt !== 'all') {
            var parts = dt.split('-');
            var min = parseFloat(parts[0]), max = parseFloat(parts[1]);
            if (item.area_ha < min || item.area_ha > max) return false;
        }
        return true;
    });
    document.getElementById('filter-count').textContent = 'Hiện: ' + filtered.length + '/' + window.ranhGioiData.length;
    renderRanhGioi(filtered);
}

function renderRanhGioi(data) {
    // Remove old layers
    window.ranhGioiLayers.forEach(function(l) { window.ranhGioiMap.removeLayer(l); });
    window.ranhGioiLayers = [];

    var bounds = [];
    var statusColors = {
        'hoat-dong': '#2e7d32',
        'xay-dung': '#f57f17',
        'quy-hoach': '#1565c0',
        'rut-qh': '#c62828'
    };
    var statusFillColors = {
        'hoat-dong': '#66bb6a',
        'xay-dung': '#ffa726',
        'quy-hoach': '#42a5f5',
        'rut-qh': '#ef5350'
    };
    var statusLabels = {
        'hoat-dong': 'Đang hoạt động',
        'xay-dung': 'Đang xây dựng',
        'quy-hoach': 'Quy hoạch (chưa thành lập)',
        'rut-qh': 'Rút khỏi Quy hoạch'
    };

    // Helper: tính tâm polygon (bỏ điểm khép kín nếu có)
    function polyCentroid(coords) {
        var n = coords.length;
        if (n >= 2 && coords[0][0] === coords[n-1][0] && coords[0][1] === coords[n-1][1]) n--;
        var sx = 0, sy = 0;
        for (var i = 0; i < n; i++) { sx += coords[i][0]; sy += coords[i][1]; }
        return [sx / n, sy / n];
    }

    data.forEach(function(item) {
        var isKCN = item.section === 'KCN';
        var isApprox = item.is_approx === true;
        var isSynthetic = item.is_synthetic === true;
        var color = statusColors[item.trangThai] || '#1565c0';
        var fillColor = statusFillColors[item.trangThai] || '#42a5f5';
        if (isApprox) {
            color = '#ea580c';
            fillColor = '#fb923c';
        }

        var displayName = (isKCN ? '🏭 ' : '📦 ') + item.name + (isApprox ? ' 📍' : '');
        var statusBadge = '<span style="display:inline-block; padding:2px 8px; border-radius:10px; background:' + color + '; color:#fff; font-size:0.72rem; font-weight:600;">' + (statusLabels[item.trangThai] || item.trangThai) + '</span>';

        // ---- Polygon chưa chuẩn (is_approx=true bao gồm cả ô vuông synthetic và polygon ước lượng) -> hiển thị bằng chấm tròn ----
        var layer;
        if (isApprox) {
            var center = polyCentroid(item.coords);
            // Bán kính dấu chấm theo diện tích công bố: sqrt(area)/2 + 6, giới hạn 7-16 px
            var radius = Math.min(16, Math.max(7, Math.round(Math.sqrt(parseFloat(item.area_ha) || 1) / 2 + 6)));
            layer = L.circleMarker(center, {
                radius: radius,
                color: color,
                weight: 2,
                fillColor: fillColor,
                fillOpacity: 0.85,
                opacity: 1
            }).addTo(window.ranhGioiMap);
            bounds.push(center);
        } else {
            // Polygon chính xác (is_approx=false) -> giữ nguyên hình polygon
            layer = L.polygon(item.coords, {
                color: color,
                weight: 2,
                fillColor: fillColor,
                fillOpacity: 0.4,
                dashArray: null
            }).addTo(window.ranhGioiMap);
            item.coords.forEach(function(c) { bounds.push(c); });
        }
        window.ranhGioiLayers.push(layer);

        var approxNote = '';
        if (isApprox) {
            approxNote = '<div style="margin-top:8px;padding:8px;background:#fff7ed;border-left:3px solid #ea580c;font-size:0.82rem;color:#9a3412;border-radius:4px;">' +
                '<b>📍 CHƯA CẬP NHẬT TỌA ĐỘ RANH GIỚI CHÍNH XÁC</b><br>' +
                'Dấu chấm chỉ vị trí gần đúng (theo tọa độ trung tâm xã/phường hoặc điểm tham chiếu). ' +
                (isSynthetic
                    ? 'Sẽ được thay bằng ranh giới chính xác khi có quyết định phê duyệt quy hoạch chi tiết.'
                    : (item.reason ? 'Lý do: ' + item.reason : 'Ranh giới chính thức đang được rà soát.')) +
                '</div>';
        }
        var sourceNote = item.sourceDesc
            ? '<p style="margin:6px 0 0;padding:6px 8px;background:#f8fafc;border-radius:4px;font-size:0.82rem;color:#334155;line-height:1.4;">' + item.sourceDesc + '</p>'
            : '';

        layer.bindPopup(
            '<div style="min-width:240px;max-width:320px;">' +
            '<h3 style="margin:0 0 6px;font-size:1rem;color:' + color + ';">' + displayName + '</h3>' +
            '<p style="margin:2px 0;font-size:0.85rem;">' + statusBadge + ' &nbsp; <b>' + (item.giaiDoan || '') + '</b></p>' +
            (item.xa ? '<p style="margin:2px 0;font-size:0.85rem;"><b>Vị trí:</b> ' + item.xa + '</p>' : '') +
            '<p style="margin:2px 0;font-size:0.85rem;"><b>Diện tích:</b> ' + item.area_ha + ' ha' +
            (isApprox ? ' (công bố)' : ' (tính từ tọa độ)') + '</p>' +
            (!isApprox ? '<p style="margin:2px 0;font-size:0.85rem;"><b>Số điểm ranh giới:</b> ' + item.num_points + '</p>' : '') +
            sourceNote +
            approxNote +
            (!isApprox ? '<p style="margin:6px 0 0;font-size:0.78rem;color:#666;font-style:italic;">VN-2000, KT trục 104°45\'</p>' : '') +
            '</div>'
        );

        layer.bindTooltip(displayName, { permanent: false, direction: isApprox ? 'top' : 'center', offset: isApprox ? [0, -8] : [0, 0], className: 'polygon-label' });
    });

    if (bounds.length > 0) {
        window.ranhGioiMap.fitBounds(bounds, { padding: [20, 20] });
    }
}

// ---- CCN Quy Hoach Map (31 CCN chưa thành lập) ----
function initCCNQHMap() {
    // Tọa độ 31 CCN - ưu tiên từ báo cáo xã, fallback về tọa độ UBND xã (Wikidata)
    // Lấy từ window.CCN_CHUA_DAU_TU (đã có lat/lng + ghiChu được merge vào ccn-data.json)
    var src = (typeof CCN_CHUA_DAU_TU !== 'undefined' ? CCN_CHUA_DAU_TU : (window.CCN_CHUA_DAU_TU || []));
    var ccnqhData = src.map(function(c) {
        return {
            stt: c.stt,
            ten: c.ten,
            xa: c.xa,
            dt: c.dienTich,
            gc: c.ghiChu || c.baoCao || c.huongPhatTrien || '',
            lat: c.lat,
            lng: c.lng
        };
    }).filter(function(c) { return typeof c.lat === 'number' && typeof c.lng === 'number'; });
    if (!ccnqhData.length) { console.error('CCN_CHUA_DAU_TU chưa được load hoặc thiếu lat/lng'); return; }

    var legendEl = document.getElementById('ccnqh-legend-count');
    if (legendEl) legendEl.textContent = ccnqhData.length;

    window.ccnqhMap = L.map('ccnqh-map', {
        center: [22.05, 104.35],
        zoom: 9,
        zoomControl: false
    });

    // Base layers: giao thông (mặc định), vệ tinh, địa hình
    var ccnqhStreet = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(window.ccnqhMap);
    var ccnqhSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    });
    var ccnqhTopo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenTopoMap'
    });

    L.control.layers({
        "🗺️ Bản đồ giao thông": ccnqhStreet,
        "🛰️ Ảnh vệ tinh": ccnqhSatellite,
        "⛰️ Địa hình": ccnqhTopo
    }, null, { position: 'topright' }).addTo(window.ccnqhMap);

    L.control.zoom({ position: 'topleft' }).addTo(window.ccnqhMap);

    ccnqhData.forEach(function(ccn) {
        var color = '#1565c0';
        var icon = L.divIcon({
            className: 'ccnqh-marker',
            html: '<div style="width:26px;height:26px;border-radius:50%;background:' + color + ';border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:10px;font-weight:bold;">' + ccn.stt + '</div>',
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });

        var ghiChu = ccn.gc ? '<p style="margin:6px 0 0;font-size:0.82rem;color:#555;border-top:1px solid #eee;padding-top:6px;">' + escapeHtml(ccn.gc) + '</p>' : '';

        var ccnSlug = slugify(ccn.ten);
        L.marker([ccn.lat, ccn.lng], { icon: icon })
            .addTo(window.ccnqhMap)
            .bindPopup(
                '<div style="min-width:240px;max-width:320px;">' +
                '<h3 style="margin:0 0 6px;font-size:1rem;color:#1565c0;">' + ccn.stt + '. ' + escapeHtml(ccn.ten) + '</h3>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Vị trí:</b> ' + escapeHtml(ccn.xa) + '</p>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Diện tích quy hoạch:</b> ' + ccn.dt + ' ha</p>' +
                ghiChu +
                '<button data-action="open-detail" data-slug="' + escapeHtml(ccnSlug) + '" data-ten="' + escapeHtml(ccn.ten) + '" style="margin-top:10px; width:100%; background:#1565c0; color:#fff; border:none; padding:8px 12px; border-radius:6px; font-weight:600; cursor:pointer; font-size:0.85rem;">📖 Xem trang chi tiết</button>' +
                '</div>'
            );
    });

    // Event delegation cho nút "Xem trang chi tiết" trong popup map CCN QH
    window.ccnqhMap.on('popupopen', function(e) {
        var btn = e.popup.getElement() && e.popup.getElement().querySelector('[data-action="open-detail"]');
        if (btn) {
            btn.onclick = function() {
                openUnitDetail(btn.dataset.slug, btn.dataset.ten);
            };
        }
    });
}

// ---- Setup Scroll Effects ----
function setupScrollEffects() {
    const scrollTopBtn = document.getElementById('scroll-top');
    if (scrollTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) {
                scrollTopBtn.classList.add('visible');
            } else {
                scrollTopBtn.classList.remove('visible');
            }
        });

        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
}

// ---- Setup Modal ----
function setupModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });
    }

    const guideOverlay = document.getElementById('modal-guide-overlay');
    if (guideOverlay) {
        guideOverlay.addEventListener('click', (e) => {
            if (e.target === guideOverlay) closeGuideModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeGuideModal();
        }
    });
}

// ---- Open Detail Modal ----
function openDetailModal(ccnId) {
    const ccn = CUM_CONG_NGHIEP.find(c => c.id === ccnId);
    if (!ccn) return;

    const status = TRANG_THAI[ccn.trangThai];
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('modal-content');

    var mailtoSubject = encodeURIComponent('Yêu cầu hồ sơ pháp lý ' + ccn.ten);
    modal.innerHTML = `
        <div class="modal-header status-${ccn.trangThai}">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div class="modal-title">🏭 <span data-field="ten-header"></span></div>
            <div class="modal-status">${status.icon} ${escapeHtml(status.ten)}</div>
        </div>
        <div class="modal-body">
            <div class="modal-description" data-field="moTa"></div>
            <div class="modal-info-grid">
                <div class="modal-info-item">
                    <div class="modal-info-label">📍 Vị trí</div>
                    <div class="modal-info-value">${escapeHtml(ccn.xa)}</div>
                </div>
                <div class="modal-info-item">
                    <div class="modal-info-label">📐 Diện tích</div>
                    <div class="modal-info-value">${ccn.dienTich} ha</div>
                </div>
                <div class="modal-info-item">
                    <div class="modal-info-label">📊 Tỷ lệ lấp đầy</div>
                    <div class="modal-info-value">${ccn.tyLeLapDay}%</div>
                </div>
                <div class="modal-info-item">
                    <div class="modal-info-label">🏢 Doanh nghiệp</div>
                    <div class="modal-info-value">${ccn.soDoanhNghiep}</div>
                </div>
                ${ccn.namThanhLap ? `
                <div class="modal-info-item">
                    <div class="modal-info-label">📅 Năm thành lập</div>
                    <div class="modal-info-value">${ccn.namThanhLap}</div>
                </div>` : ''}
                <div class="modal-info-item">
                    <div class="modal-info-label">📋 Diện tích cho thuê</div>
                    <div class="modal-info-value">${ccn.dienTichDaChoThue} ha</div>
                </div>
                <div class="modal-info-item full-width">
                    <div class="modal-info-label">🔧 Ngành nghề</div>
                    <div class="modal-info-value">${escapeHtml(ccn.nganhNghe)}</div>
                </div>
                <div class="modal-info-item full-width">
                    <div class="modal-info-label">🏗️ Hạ tầng</div>
                    <div class="modal-info-value">${escapeHtml(ccn.haTang)}</div>
                </div>
                <div class="modal-info-item full-width">
                    <div class="modal-info-label">📜 Quyết định</div>
                    <div class="modal-info-value">${escapeHtml(ccn.quyetDinh)}</div>
                </div>
                <div class="modal-info-item full-width mt-3">
                    <div class="modal-info-label">📂 Tài liệu đính kèm</div>
                    <div class="modal-info-value" style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
                        <a href="mailto:sct@laocai.gov.vn?subject=${mailtoSubject}" style="padding:8px 12px; background:#f1f5f9; border-radius:6px; text-decoration:none; display:flex; align-items:center; color:#1e293b; border:1px solid #e2e8f0; transition:all 0.2s; font-weight:500;" onmouseover="this.style.background='#e2e8f0'" onmouseout="this.style.background='#f1f5f9'">📧 Yêu cầu hồ sơ pháp lý <span data-field="ten-email"></span> qua Email</a>
                    </div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap:wrap;">
                <button class="modal-btn-locate" data-action="open-detail" style="flex:1; min-width:160px; background:#0d47a1; color:#fff;">
                    📖 Xem trang chi tiết
                </button>
                <button class="modal-btn-locate" onclick="locateOnMap(${ccn.id})" style="flex: 1; min-width:140px;">
                    🗺️ Xem trên bản đồ
                </button>
                <a class="modal-btn-locate" style="flex: 1; min-width:160px; background: #34495e; color: white; text-decoration: none; display: flex; align-items: center; justify-content: center;" href="https://www.google.com/maps/dir/?api=1&destination=${ccn.lat},${ccn.lng}" target="_blank">
                    🚗 Chỉ đường Google Maps
                </a>
            </div>
        </div>
    `;

    // Demo textContent — 2 trường rủi ro cao nhất (header + mô tả) set qua textContent thay vì innerHTML
    modal.querySelector('[data-field="ten-header"]').textContent = ccn.ten;
    modal.querySelector('[data-field="moTa"]').textContent = ccn.moTa;
    modal.querySelector('[data-field="ten-email"]').textContent = ccn.ten;

    // Nút "Xem trang chi tiết" — gắn handler thay cho onclick inline có escape thủ công
    modal.querySelector('[data-action="open-detail"]').addEventListener('click', function() {
        closeModal();
        openUnitDetail(slugify(ccn.ten), ccn.ten);
    });

    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

// ---- Close Modal ----
function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if(overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
}

// ---- Investment Guide Modal ----
function showHuongDanDauTu() {
    const overlay = document.getElementById('modal-guide-overlay');
    if(overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeGuideModal() {
    const overlay = document.getElementById('modal-guide-overlay');
    if(overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
}


// ---- Export to Excel ----
function exportToExcel() {
    // Generate CSV content for 31 planned clusters
    let csvContent = "\ufeff"; // BOM for UTF-8
    csvContent += "STT,Ten Cum Cong Nghiep,Xa/Phuong,Dien tich (ha),Huong phat trien\n";
    
    CCN_CHUA_DAU_TU.forEach(ccn => {
        csvContent += `${ccn.stt},"${ccn.ten}","${ccn.xa}",${ccn.dienTich},"${ccn.huongPhatTrien || ''}"\n`;
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "Danh_sach_31_CCN_Quy_hoach_Lao_Cai.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ---- Locate on Map ----
function locateOnMap(ccnId) {
    const ccn = CUM_CONG_NGHIEP.find(c => c.id === ccnId);
    if (!ccn) return;

    closeModal();

    // Switch to map view
    const mapTab = document.querySelector('[data-tab="map"]');
    if (mapTab) mapTab.click();

    // Scroll to map
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Fly to location
    setTimeout(() => {
        map.flyTo([ccn.lat, ccn.lng], 14, { duration: 1 });

        // Open popup
        setTimeout(() => {
            const found = markers.find(m => m.data.id === ccnId);
            if (found) found.marker.openPopup();
        }, 1200);
    }, 500);
}

// ---- Animate on Scroll ----
function animateOnScroll() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.animate-in').forEach(el => {
        observer.observe(el);
    });
}

// ---- Debounce utility ----
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ---- Locate user on map ----
function locateUser() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const { latitude, longitude } = pos.coords;
                map.flyTo([latitude, longitude], 14, { duration: 1 });
                L.marker([latitude, longitude], {
                    icon: L.divIcon({
                        className: 'custom-marker',
                        html: '<div style="width:16px;height:16px;background:#4285F4;border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>',
                        iconSize: [16, 16],
                        iconAnchor: [8, 8]
                    })
                }).addTo(map).bindPopup('📍 Vị trí của bạn').openPopup();
            },
            () => {
                alert('Không thể xác định vị trí của bạn. Vui lòng bật định vị.');
            }
        );
    }
}

// ============================================================
// CHI TIẾT ĐƠN VỊ (Khu/Cụm công nghiệp) — tab dùng chung
// ============================================================

window.UNIT_DETAILS = null;
window._lastTabBeforeUnit = 'dashboard';

// Chuẩn hóa chuỗi tiếng Việt thành slug ASCII
function slugify(s) {
    if (!s) return '';
    return s.toString()
        .replace(/^Cụm công nghiệp\s+/i, 'CCN ')
        .replace(/^Khu công nghiệp\s+/i, 'KCN ')
        .toLowerCase()
        .normalize('NFD').replace(/[̀-ͯ]/g, '')
        .replace(/đ/g, 'd')
        .replace(/[^a-z0-9\s-]/g, '')
        .trim()
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-');
}

// Lấy slug của một đơn vị (KCN hoặc CCN) từ object data
function getUnitSlug(u) {
    if (!u || !u.ten) return '';
    return slugify(u.ten);
}

// Load file unit-details.json (gọi 1 lần khi khởi động)
function loadUnitDetails() {
    return fetch('/unit-details.json')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            window.UNIT_DETAILS = data || {};
            console.log('[Unit] Loaded ' + (Object.keys(data).length - 1) + ' unit detail entries');
            return data;
        })
        .catch(function (err) {
            console.warn('[Unit] Không tải được unit-details.json:', err);
            window.UNIT_DETAILS = {};
            return {};
        });
}

// Tìm thông tin gốc của đơn vị từ tất cả 3 nguồn data
function findUnitByName(name) {
    if (!name) return null;
    var nameNorm = slugify(name);
    // 1. KHU_CONG_NGHIEP (từ ccn-data.json qua window) — phải tra TRƯỚC vì
    //    có 1 số KCN trùng tên xã/phường với CCN (vd. "KCN/CCN Đông Phố Mới")
    if (window.KHU_CONG_NGHIEP && window.KHU_CONG_NGHIEP.length) {
        for (var k = 0; k < window.KHU_CONG_NGHIEP.length; k++) {
            if (slugify(window.KHU_CONG_NGHIEP[k].ten) === nameNorm) {
                return { src: 'KCN', data: window.KHU_CONG_NGHIEP[k] };
            }
        }
    }
    // 2. CUM_CONG_NGHIEP đã thành lập
    if (typeof CUM_CONG_NGHIEP !== 'undefined') {
        for (var i = 0; i < CUM_CONG_NGHIEP.length; i++) {
            if (slugify(CUM_CONG_NGHIEP[i].ten) === nameNorm) {
                return { src: 'CCN_TL', data: CUM_CONG_NGHIEP[i] };
            }
        }
    }
    // 3. CCN_CHUA_DAU_TU
    if (typeof CCN_CHUA_DAU_TU !== 'undefined') {
        for (var j = 0; j < CCN_CHUA_DAU_TU.length; j++) {
            if (slugify(CCN_CHUA_DAU_TU[j].ten) === nameNorm) {
                return { src: 'CCN_QH', data: CCN_CHUA_DAU_TU[j] };
            }
        }
    }
    return null;
}

// Mở tab chi tiết đơn vị theo slug
function openUnitDetail(slug, optionalName) {
    if (!slug && optionalName) slug = slugify(optionalName);
    if (!slug) return;

    // Nhớ tab trước đó để khi bấm "Quay lại" về đúng chỗ
    if (currentView && currentView !== 'unit-detail') {
        window._lastTabBeforeUnit = currentView;
    }

    // Hiển thị section
    var section = document.getElementById('unit-detail-section');
    if (!section) return;
    Object.values({
        d: document.getElementById('dashboard-section'),
        m: document.getElementById('map-section'),
        // các section khác — JS ẩn hết
    });
    // Ẩn tất cả section khác
    document.querySelectorAll('main.main-container > section').forEach(function (s) {
        s.style.display = (s.id === 'unit-detail-section') ? '' : 'none';
    });
    currentView = 'unit-detail';

    // Cập nhật URL hash
    if (!window._skipHashUpdate) {
        try { history.replaceState(null, '', '#unit/' + slug); } catch (e) {}
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Lấy chi tiết
    var details = (window.UNIT_DETAILS || {})[slug];
    var srcMatch = null;
    if (optionalName) srcMatch = findUnitByName(optionalName);
    if (!srcMatch && details && details.ten) srcMatch = findUnitByName(details.ten);

    renderUnitDetail(slug, details, srcMatch, optionalName);
}

// Fallback: chuyển slug như "ccn-khanh-yen-thuong" thành tên hiển thị
// "Cụm công nghiệp Khánh Yên Thượng" — best-effort khi dữ liệu chưa load
function prettifySlug(slug) {
    if (!slug) return '';
    var prefix = '';
    var rest = slug;
    if (rest.indexOf('ccn-') === 0) { prefix = 'Cụm công nghiệp '; rest = rest.slice(4); }
    else if (rest.indexOf('kcn-') === 0) { prefix = 'Khu công nghiệp '; rest = rest.slice(4); }
    // capitalize từng từ
    rest = rest.split('-').map(function (w) {
        return w ? w[0].toUpperCase() + w.slice(1) : w;
    }).join(' ');
    return (prefix + rest).trim();
}

// Render nội dung tab chi tiết
function renderUnitDetail(slug, details, srcMatch, optionalName) {
    // Default fields nếu không có details — ưu tiên tên đẹp từ optionalName trước khi rơi xuống slug
    var ten = (details && details.ten) || (srcMatch && srcMatch.data.ten) || optionalName || prettifySlug(slug) || slug;
    var type = (details && details.type)
        || (srcMatch && srcMatch.src === 'CCN_TL' ? 'Cụm công nghiệp đã thành lập' :
            srcMatch && srcMatch.src === 'CCN_QH' ? 'Cụm công nghiệp quy hoạch' :
            srcMatch && srcMatch.src === 'KCN' ? 'Khu công nghiệp' :
            ten.toLowerCase().indexOf('khu công nghiệp') === 0 || ten.toLowerCase().indexOf('kcn') === 0 ? 'Khu công nghiệp' : 'Cụm công nghiệp');
    var viTri = (details && details.viTriMoTa) || (srcMatch && (srcMatch.data.xa || srcMatch.data.viTri)) || '';
    var dienTich = (details && details.dienTich) || (srcMatch && (srcMatch.data.dienTich || srcMatch.data.dt)) || null;
    var namTL = (details && details.namThanhLap) || (srcMatch && srcMatch.data.namThanhLap) || null;
    var trangThai = (details && details.trangThai) || (srcMatch && srcMatch.data.trangThai) || '';

    document.getElementById('unit-type-badge').textContent = type.toUpperCase();
    document.getElementById('unit-name').textContent = ten;

    // Meta dòng
    var metaHtml = '';
    if (viTri) metaHtml += '<div><b>📍 Vị trí:</b> ' + escapeHtml(viTri) + '</div>';
    if (dienTich) metaHtml += '<div><b>📐 Diện tích:</b> ' + dienTich + ' héc-ta</div>';
    if (namTL) metaHtml += '<div><b>📅 Năm thành lập:</b> ' + namTL + '</div>';
    if (trangThai) {
        var ttLabel = {
            'hoat-dong': '🟢 Đang hoạt động',
            'xay-dung': '🟡 Đang xây dựng',
            'quy-hoach': '🔵 Quy hoạch',
            'tam-dung': '🔴 Tạm dừng'
        }[trangThai] || trangThai;
        metaHtml += '<div><b>📊 Trạng thái:</b> ' + ttLabel + '</div>';
    }
    document.getElementById('unit-meta').innerHTML = metaHtml;

    // Có dữ liệu chi tiết không?
    var hasDetails = details && (details.gioiThieu || details.polygon || details.kml ||
                                 details.video || details.anhDaiDien ||
                                 (details.vanBan && details.vanBan.length));

    // Ảnh đại diện
    var coverWrap = document.getElementById('unit-cover-wrap');
    if (details && details.anhDaiDien) {
        document.getElementById('unit-cover-img').src = details.anhDaiDien;
        coverWrap.style.display = '';
    } else {
        coverWrap.style.display = 'none';
    }

    // Video (hỗ trợ archive.org, YouTube, Vimeo qua URL embed)
    var videoWrap = document.getElementById('unit-video-wrap');
    var videoIframe = document.getElementById('unit-video-iframe');
    if (details && details.video) {
        var src = details.video;
        // Tự động chuyển URL archive.org/details/... → embed
        var arcMatch = src.match(/archive\.org\/details\/([^\/\?#]+)/);
        if (arcMatch) src = 'https://archive.org/embed/' + arcMatch[1];
        // YouTube watch?v=... → embed
        var ytMatch = src.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?#]+)/);
        if (ytMatch) src = 'https://www.youtube.com/embed/' + ytMatch[1];
        videoIframe.src = src;
        document.getElementById('unit-video-caption').textContent = details.videoCaption || '';
        videoWrap.style.display = '';
    } else {
        videoIframe.src = 'about:blank'; // dừng phát khi chuyển sang đơn vị khác
        videoWrap.style.display = 'none';
    }

    // Giới thiệu
    var introWrap = document.getElementById('unit-intro-wrap');
    if (details && details.gioiThieu) {
        document.getElementById('unit-intro').innerHTML = details.gioiThieu;
        introWrap.style.display = '';
    } else {
        introWrap.style.display = 'none';
    }

    // Bản đồ + KML
    var mapWrap = document.getElementById('unit-map-wrap');
    if (details && (details.polygon || details.centerLat)) {
        mapWrap.style.display = '';
        setTimeout(function () { renderUnitMap(details, srcMatch); }, 80);

        // Nút tải KML
        var actions = document.getElementById('unit-kml-actions');
        actions.innerHTML = '';
        if (details.kml) {
            actions.innerHTML =
                '<a href="' + escapeHtml(details.kml) + '" download style="background:#0d47a1; color:#fff; padding:10px 18px; border-radius:8px; text-decoration:none; font-weight:600; font-size:0.9rem; display:inline-flex; align-items:center; gap:6px;">⬇️ Tải file KML</a>' +
                '<a href="https://earth.google.com/web/" target="_blank" rel="noopener" style="background:#fff; color:#0d47a1; border:1.5px solid #0d47a1; padding:10px 18px; border-radius:8px; text-decoration:none; font-weight:600; font-size:0.9rem;">🌍 Mở Google Earth Web</a>';
        }
    } else {
        mapWrap.style.display = 'none';
    }

    // Văn bản pháp lý
    var docsWrap = document.getElementById('unit-docs-wrap');
    if (details && details.vanBan && details.vanBan.length) {
        var list = document.getElementById('unit-docs-list');
        list.innerHTML = details.vanBan.map(function (vb) {
            return '<div style="display:flex; align-items:center; gap:14px; padding:14px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;">' +
                '<div style="font-size:1.8rem;">📄</div>' +
                '<div style="flex:1; min-width:0;">' +
                    '<div style="font-weight:600; color:#1e293b; font-size:0.96rem;">' + escapeHtml(vb.ten || 'Văn bản') + '</div>' +
                    (vb.ngay ? '<div style="font-size:0.82rem; color:#64748b; margin-top:2px;">Ngày ' + escapeHtml(vb.ngay) + '</div>' : '') +
                '</div>' +
                '<a href="' + escapeHtml(vb.file) + '" target="_blank" rel="noopener" style="background:#fff; color:#0d47a1; border:1px solid #0d47a1; padding:6px 14px; border-radius:6px; font-size:0.85rem; text-decoration:none; font-weight:600;">Xem</a>' +
                '<a href="' + escapeHtml(vb.file) + '" download style="background:#0d47a1; color:#fff; padding:6px 14px; border-radius:6px; font-size:0.85rem; text-decoration:none; font-weight:600;">Tải về</a>' +
            '</div>';
        }).join('');
        docsWrap.style.display = '';
    } else {
        docsWrap.style.display = 'none';
    }

    // Trạng thái "chưa có dữ liệu"
    document.getElementById('unit-empty').style.display = hasDetails ? 'none' : '';
}

// Render bản đồ Leaflet cho đơn vị
function renderUnitMap(details, srcMatch) {
    var mapEl = document.getElementById('unit-map');
    if (!mapEl) return;

    // Reset map nếu đã tồn tại
    if (window.unitMap) {
        try { window.unitMap.remove(); } catch (e) {}
        window.unitMap = null;
    }

    var center = null;
    var zoom = 14;
    if (details.centerLat && details.centerLng) {
        center = [details.centerLat, details.centerLng];
    } else if (details.polygon && details.polygon.length) {
        // Tính trung tâm polygon
        var sumLat = 0, sumLng = 0;
        details.polygon.forEach(function (p) { sumLat += p[0]; sumLng += p[1]; });
        center = [sumLat / details.polygon.length, sumLng / details.polygon.length];
    } else if (srcMatch && srcMatch.data.lat && srcMatch.data.lng) {
        center = [srcMatch.data.lat, srcMatch.data.lng];
    } else {
        center = [22.0, 104.3]; // Lào Cai fallback
    }

    window.unitMap = L.map('unit-map').setView(center, zoom);

    // Layer
    var streets = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap, © CARTO'
    });
    var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Esri'
    });
    streets.addTo(window.unitMap);
    L.control.layers({ 'Bản đồ thường': streets, 'Vệ tinh': satellite }, null, { position: 'topright' }).addTo(window.unitMap);

    // Vẽ polygon
    if (details.polygon && details.polygon.length >= 3) {
        var poly = L.polygon(details.polygon, {
            color: '#0d47a1', weight: 2.5, opacity: 0.9,
            fillColor: '#1976d2', fillOpacity: 0.25
        }).addTo(window.unitMap);
        window.unitMap.fitBounds(poly.getBounds(), { padding: [30, 30] });
    } else {
        L.marker(center).addTo(window.unitMap);
    }
}

// Quay lại tab trước đó
function closeUnitDetail() {
    var prev = window._lastTabBeforeUnit || 'dashboard';
    var btn = document.querySelector('[data-tab="' + prev + '"]');
    if (btn) btn.click();
}

// Escape HTML
function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return s.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function initVisitorCounter() {
    var el = document.getElementById('visitor-count');
    if (!el) return;
    var KEY_COUNT = 'visitor_count';
    var KEY_LAST = 'visitor_last_visit';
    var stored = localStorage.getItem(KEY_COUNT);
    var count;
    if (stored === null) {
        count = 2000 + 10 + Math.floor(Math.random() * 41);
    } else {
        count = parseInt(stored, 10);
        if (isNaN(count)) count = 2000;
        count += 1;
        var lastVisit = parseInt(localStorage.getItem(KEY_LAST), 10);
        if (!isNaN(lastVisit)) {
            var intervals = Math.floor((Date.now() - lastVisit) / (10 * 60 * 1000));
            if (intervals > 0) {
                var simulated = 0;
                for (var i = 0; i < intervals; i++) {
                    simulated += 1 + Math.floor(Math.random() * 3);
                }
                if (simulated > 150) simulated = 150;
                count += simulated;
            }
        }
    }
    localStorage.setItem(KEY_COUNT, String(count));
    localStorage.setItem(KEY_LAST, String(Date.now()));
    el.textContent = count.toLocaleString('vi-VN');
}

// ===========================================================
// AI CHATBOT — gọi /api/chat (Vercel Edge Function proxy Gemini)
// ===========================================================
function initChatbot() {
    var toggle = document.getElementById('chatbot-toggle');
    var panel = document.getElementById('chatbot-panel');
    var msgsEl = document.getElementById('chatbot-messages');
    var form = document.getElementById('chatbot-form');
    var input = document.getElementById('chatbot-input');
    var sendBtn = document.getElementById('chatbot-send');
    var clearBtn = document.getElementById('chatbot-clear');
    var modelSelect = document.getElementById('chatbot-model');
    var footerEl = document.querySelector('.chatbot-footer');
    if (!toggle || !panel || !msgsEl || !form || !input) return;

    var STORAGE_KEY = 'chatbot_history_v1';

    function updateFooter() {
        if (!footerEl) return;
        var selected = modelSelect ? modelSelect.value : 'gemini';
        if (selected === 'claude') {
            footerEl.innerHTML = 'Trợ lý AI dùng Anthropic Claude · có thể có sai sót';
        } else {
            footerEl.innerHTML = 'Trợ lý AI dùng Google Gemini · có thể có sai sót';
        }
    }

    if (modelSelect) {
        var savedModel = localStorage.getItem('chatbot_selected_model');
        if (savedModel && (savedModel === 'gemini' || savedModel === 'claude')) {
            modelSelect.value = savedModel;
        }
        updateFooter();
        modelSelect.addEventListener('change', function() {
            localStorage.setItem('chatbot_selected_model', modelSelect.value);
            updateFooter();
        });
    }
    var SUGGESTIONS = [
        'Tỉnh Lào Cai có bao nhiêu Khu công nghiệp?',
        'Cụm công nghiệp nào đang lấp đầy 100%?',
        'Khu công nghiệp Tằng Loỏng có ngành nghề gì?',
        'Cụm Phú Thịnh 1 do ai làm chủ đầu tư?'
    ];

    var history = [];
    try {
        var saved = localStorage.getItem(STORAGE_KEY);
        if (saved) history = JSON.parse(saved) || [];
    } catch (e) {}

    var isOpen = false;
    var isSending = false;

    function escapeHTML(s) {
        return String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function renderBotMarkdown(text) {
        // Tóm tắt nhẹ: \n\n -> <br><br>, **bold**, *italic* (đơn giản, không cài full markdown)
        var s = escapeHTML(text);
        s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
        s = s.replace(/\n/g, '<br>');
        return s;
    }

    function addMessage(role, text, opts) {
        opts = opts || {};
        var div = document.createElement('div');
        div.className = 'chatbot-msg is-' + (role === 'user' ? 'user' : 'bot');
        if (opts.typing) div.classList.add('is-typing');
        if (opts.error) div.classList.add('is-error');
        div.innerHTML = role === 'user' ? escapeHTML(text) : renderBotMarkdown(text);
        msgsEl.appendChild(div);
        msgsEl.scrollTop = msgsEl.scrollHeight;
        return div;
    }

    function renderSuggestions() {
        var wrap = document.createElement('div');
        wrap.className = 'chatbot-suggestions';
        SUGGESTIONS.forEach(function (q) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'chatbot-suggestion';
            btn.textContent = q;
            btn.addEventListener('click', function () {
                input.value = q;
                sendMessage();
            });
            wrap.appendChild(btn);
        });
        msgsEl.appendChild(wrap);
    }

    function renderHistory() {
        msgsEl.innerHTML = '';
        if (history.length === 0) {
            addMessage('bot', 'Xin chào! Tôi là **Trợ lý thông tin Khu, Cụm công nghiệp tỉnh Lào Cai**. Bạn cần biết gì về 21 Khu công nghiệp, 23 Cụm công nghiệp đã thành lập hoặc các Cụm công nghiệp quy hoạch trên địa bàn tỉnh?');
            renderSuggestions();
        } else {
            history.forEach(function (m) { addMessage(m.role === 'user' ? 'user' : 'bot', m.text); });
        }
    }

    function persistHistory() {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(-40))); } catch (e) {}
    }

    function setOpen(open) {
        isOpen = open;
        panel.classList.toggle('is-open', open);
        toggle.classList.toggle('is-open', open);
        panel.setAttribute('aria-hidden', open ? 'false' : 'true');
        toggle.setAttribute('aria-label', open ? 'Đóng Trợ lý AI' : 'Mở Trợ lý AI');
        if (open) {
            // Render lần đầu hoặc khi mở lại
            if (msgsEl.children.length === 0) renderHistory();
            setTimeout(function () { input.focus(); }, 250);
        }
    }

    function sendMessage() {
        if (isSending) return;
        var text = (input.value || '').trim();
        if (!text) return;
        input.value = '';
        input.style.height = 'auto';

        addMessage('user', text);
        history.push({ role: 'user', text: text });
        persistHistory();

        isSending = true;
        sendBtn.disabled = true;
        var typing = addMessage('bot', 'Đang suy nghĩ…', { typing: true });

        var selectedModel = modelSelect ? modelSelect.value : 'gemini';
        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: history.slice(-20),
                model: selectedModel
            })
        })
            .then(function (r) {
                return r.json().then(function (data) { return { ok: r.ok, status: r.status, data: data }; });
            })
            .then(function (res) {
                typing.remove();
                if (!res.ok) {
                    var err = (res.data && (res.data.error || res.data.detail)) || ('Lỗi máy chủ ' + res.status);
                    addMessage('bot', '⚠ ' + err, { error: true });
                    return;
                }
                var reply = (res.data && res.data.reply) || 'Không có phản hồi.';
                addMessage('bot', reply);
                history.push({ role: 'model', text: reply });
                persistHistory();
            })
            .catch(function (e) {
                typing.remove();
                addMessage('bot', '⚠ Không thể kết nối tới Trợ lý AI: ' + e.message, { error: true });
            })
            .finally(function () {
                isSending = false;
                sendBtn.disabled = false;
                input.focus();
            });
    }

    toggle.addEventListener('click', function () { setOpen(!isOpen); });

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        sendMessage();
    });

    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-grow textarea
    input.addEventListener('input', function () {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 100) + 'px';
    });

    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            if (history.length === 0) return;
            if (confirm('Xóa toàn bộ cuộc trò chuyện?')) {
                history = [];
                persistHistory();
                renderHistory();
            }
        });
    }
}

// Khởi tạo nút Quay lại
document.addEventListener('DOMContentLoaded', function () {
    var backBtn = document.getElementById('unit-back-btn');
    if (backBtn) backBtn.addEventListener('click', closeUnitDetail);
    loadUnitDetails();
    initVisitorCounter();
    initChatbot();
});

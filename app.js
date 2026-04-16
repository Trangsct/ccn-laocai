// ============================================================
// BẢN ĐỒ CỤM CÔNG NGHIỆP TỈNH LÀO CAI - APP LOGIC
// ============================================================

let map;
let markers = [];
let markerLayer;
let currentView = 'map';
let charts = {};

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

// Remove PDF iframes on mobile to prevent auto-download
(function() {
    if (window.innerWidth <= 768 || /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent)) {
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.pdf-iframe').forEach(function(iframe) {
                iframe.removeAttribute('src');
                iframe.style.display = 'none';
            });
        });
    }
})();

// ---- Initialize Application ----
document.addEventListener('DOMContentLoaded', () => {
    fetch('/ccn-data.json')
        .then(r => r.json())
        .then(data => {
            CUM_CONG_NGHIEP = data.CUM_CONG_NGHIEP;
            CCN_CHUA_DAU_TU = data.CCN_CHUA_DAU_TU;
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
        .catch(() => {
            // fallback: dùng data.js nếu fetch lỗi
            CUM_CONG_NGHIEP = window._CCN_DATA || [];
            CCN_CHUA_DAU_TU = window._CCN_CHUA_DAU_TU || [];
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
    return `
        <div class="popup-content">
            <div class="popup-header status-${ccn.trangThai}">
                🏭 ${ccn.ten}
            </div>
            <div class="popup-body">
                <div class="popup-info">📍 <strong>${ccn.xa}</strong></div>
                <div class="popup-info">📐 Diện tích: <strong>${ccn.dienTich} ha</strong></div>
                <div class="popup-info">🏢 Doanh nghiệp: <strong>${ccn.soDoanhNghiep}</strong></div>
                <div class="popup-info">📊 Tỷ lệ lấp đầy: <strong>${ccn.tyLeLapDay}%</strong></div>
                <div class="popup-info">🔖 Trạng thái: <strong>${status.icon} ${status.ten}</strong></div>
                <button class="popup-detail-btn" onclick="openDetailModal(${ccn.id})">
                    📋 Chi tiết
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
                labels: ['23 CCN đã thành lập', '31 CCN chưa thành lập'],
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
        <div class="stat-card animate-in">
            <div class="stat-icon">🏭</div>
            <div class="stat-number" data-target="${THONG_KE.tongCCN}">0</div>
            <div class="stat-label">Tổng CCN theo QH</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🟢</div>
            <div class="stat-number" data-target="${THONG_KE.dangHoatDong}">0</div>
            <div class="stat-label">CCN đang hoạt động</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🟡</div>
            <div class="stat-number" data-target="${THONG_KE.dangXayDung}">0</div>
            <div class="stat-label">CCN đang xây dựng</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🔵</div>
            <div class="stat-number" data-target="${THONG_KE.choDauTu}">0</div>
            <div class="stat-label">CCN chưa thành lập</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">📐</div>
            <div class="stat-number" data-target="${THONG_KE.dienTichHienHuu}">0</div>
            <div class="stat-label">DT 23 CCN đã TL (ha)</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🟦</div>
            <div class="stat-number" data-target="${THONG_KE.dienTichQuyHoach}">0</div>
            <div class="stat-label">DT 31 CCN chưa TL (ha)</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🏢</div>
            <div class="stat-number" data-target="${THONG_KE.tongDoanhNghiep}">0</div>
            <div class="stat-label">Doanh nghiệp trong CCN</div>
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

    const list = filteredList || CUM_CONG_NGHIEP;

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

        return `
            <div class="ccn-card animate-in" onclick="openDetailModal(${ccn.id})">
                <div class="ccn-card-header status-${ccn.trangThai}">
                    <div class="ccn-card-name">${ccn.ten}</div>
                    <div class="ccn-card-badge">${status.icon} ${status.ten}</div>
                </div>
                <div class="ccn-card-body">
                    <div class="ccn-card-info">
                        <span class="info-icon">📍</span>
                        <span class="info-label">Vị trí:</span>
                        <span class="info-value">${ccn.xa}</span>
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
                        <span class="info-value">${ccn.nganhNghe}</span>
                    </div>
                    <div class="ccn-card-progress">
                        <div class="progress-label">
                            <span>Tỷ lệ lấp đầy</span>
                            <span>${ccn.tyLeLapDay}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill ${progressClass}" style="width: 0%" data-width="${ccn.tyLeLapDay}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

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
            baoCaoTooltip = ccn.baoCao ? `<div style="font-size:0.78rem;color:#475569;margin-top:4px;font-style:italic;">${ccn.baoCao}</div>` : '';
        } else if (ccn.coBaoCao === 'rar') {
            baoCaoBadge = `<span style="background:#fef9c3;color:#b45309;padding:3px 8px;border-radius:4px;font-size:0.78rem;border:1px solid #fde047;white-space:nowrap;">📦 File .rar</span>`;
            baoCaoTooltip = `<div style="font-size:0.78rem;color:#92400e;margin-top:4px;font-style:italic;">${ccn.baoCao}</div>`;
        } else {
            baoCaoBadge = `<span style="background:#fee2e2;color:#dc2626;padding:3px 8px;border-radius:4px;font-size:0.78rem;border:1px solid #fca5a5;white-space:nowrap;font-weight:600;">🔴 Chưa có báo cáo</span>`;
            baoCaoTooltip = '';
        }
        return `
        <tr style="${ccn.coBaoCao === false ? 'background:#fff5f5;' : ''}">
            <td style="text-align:center;">${idx + 1}</td>
            <td><strong>${ccn.ten}</strong></td>
            <td>${ccn.xa}</td>
            <td style="text-align:right;">${ccn.dienTich} ha</td>
            <td style="font-size:0.85rem;">${ccn.huongPhatTrien || '-'}${baoCaoTooltip}</td>
            <td style="text-align:center;">${baoCaoBadge}</td>
        </tr>`;
    }).join('');
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
        'listqh': document.getElementById('listqh-section'),
        'listkcn': document.getElementById('listkcn-section'),
        'vanban': document.getElementById('vanban-section'),
        'tintuc': document.getElementById('tintuc-section'),
        'kcn': document.getElementById('kcn-section')
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
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
}

// ---- KCN Map ----
function initKCNMap() {
    var kcnData = [
        { ten: "KCN Đông Phố Mới ⚠️", viTri: "Phường Lào Cai, TP. Lào Cai", dienTich: 100, trangThai: "rut-qh", moTa: "41 DA, lấp đầy >90%. SẼ RÚT KHỎI QUY HOẠCH — di dời phục vụ đường sắt tốc độ cao LC-HN-HP → chuyển về KCN Bát Xát.", lat: 22.5017, lng: 103.9566 },
        { ten: "KCN Bắc Duyên Hải", viTri: "Phường Lào Cai, TP. Lào Cai", dienTich: 85, trangThai: "hoat-dong", moTa: "63 DA, lấp đầy >90%. Sẽ chuyển đổi chức năng theo QH Khu KT cửa khẩu Lào Cai 2045.", lat: 22.5024, lng: 103.9562 },
        { ten: "KCN Tằng Loỏng", viTri: "Xã Gia Phú, tỉnh Lào Cai", dienTich: 1100, trangThai: "hoat-dong", moTa: "KCN tuyển khoáng, hóa chất lớn nhất cả nước. 29 DA, lấp đầy 85%. Tiền thân từ NM Apatit (1994).", lat: 22.3331, lng: 104.1253 },
        { ten: "KCN Phía Nam", viTri: "Phường Văn Phú, tỉnh Lào Cai", dienTich: 400, trangThai: "hoat-dong", moTa: "66 DA (289,27 ha), lấp đầy 91,54%. Còn 26,72 ha. Đa ngành, 12 DA FDI.", lat: 21.6805, lng: 104.9485 },
        { ten: "KCN Âu Lâu", viTri: "Phường Âu Lâu, tỉnh Lào Cai", dienTich: 120, trangThai: "hoat-dong", moTa: "12 DA (69,69 ha), lấp đầy 84,15%. Còn 13,13 ha.", lat: 21.6920, lng: 104.8420 },
        { ten: "KCN Minh Quân", viTri: "Xã Minh Quân, tỉnh Lào Cai", dienTich: 75, trangThai: "hoat-dong", moTa: "17 DA (70,97 ha), lấp đầy 94,65% — cao nhất các KCN. Còn 4,01 ha.", lat: 21.6367, lng: 104.9022 },
        { ten: "KCN Trấn Yên", viTri: "Phường Âu Lâu, tỉnh Lào Cai", dienTich: 339, trangThai: "xay-dung", moTa: "GĐ I: 254,59 ha (QĐ 1438/TTg 20/11/2024). Đang triển khai san nền.", lat: 21.7750, lng: 104.8206 },
        // 14 KCN chưa thành lập (QH đến 2030)
        { ten: "KCN Bản Qua", viTri: "Xã Bản Qua, tỉnh Lào Cai", dienTich: 107, trangThai: "quy-hoach", moTa: "Giữ nguyên QH. GĐ 2025-2030.", lat: 22.5400, lng: 103.8583 },
        { ten: "KCN Y Can", viTri: "Xã Y Can, tỉnh Lào Cai", dienTich: 350, trangThai: "quy-hoach", moTa: "Giữ nguyên QH. GĐ 2025-2030.", lat: 21.7178, lng: 104.7931 },
        { ten: "KCN Đông An", viTri: "Xã Đông An, tỉnh Lào Cai", dienTich: 350, trangThai: "quy-hoach", moTa: "Giữ nguyên QH. GĐ 2025-2030.", lat: 21.9767, lng: 104.5603 },
        { ten: "KCN Thịnh Hưng", viTri: "Xã Thịnh Hưng, tỉnh Lào Cai", dienTich: 104, trangThai: "quy-hoach", moTa: "Giữ nguyên QH. GĐ 2025-2030.", lat: 21.7111, lng: 104.9992 },
        { ten: "KCN Lục Yên", viTri: "Xã Tân Lĩnh, tỉnh Lào Cai", dienTich: 221, trangThai: "quy-hoach", moTa: "Giữ nguyên QH. GĐ 2025-2030.", lat: 22.1264, lng: 104.7197 },
        { ten: "KCN Võ Lao GĐ 1", viTri: "Xã Võ Lao, tỉnh Lào Cai", dienTich: 500, trangThai: "quy-hoach", moTa: "Điều chỉnh tăng DT từ 200 → 500 ha.", lat: 22.1931, lng: 104.1958 },
        { ten: "KCN Cốc Mỳ-Trịnh Tường", viTri: "Xã Trịnh Tường, tỉnh Lào Cai", dienTich: 500, trangThai: "quy-hoach", moTa: "Điều chỉnh giảm DT từ 800 → 500 ha.", lat: 22.6581, lng: 103.7131 },
        { ten: "KCN Phú Xuân", viTri: "Xã Xuân Hòa, tỉnh Lào Cai", dienTich: 300, trangThai: "quy-hoach", moTa: "Đẩy nhanh tiến độ: từ sau 2030 lên GĐ 2026-2030.", lat: 22.3028, lng: 104.5178 },
        { ten: "KCN Bát Xát", viTri: "Xã Bát Xát, tỉnh Lào Cai", dienTich: 76, trangThai: "quy-hoach", moTa: "Bổ sung mới. Phục vụ di chuyển từ KCN Đông Phố Mới.", lat: 22.5422, lng: 103.8900 },
        { ten: "KCN Cam Đường", viTri: "Phường Cam Đường, TP. Lào Cai", dienTich: 200, trangThai: "quy-hoach", moTa: "Bổ sung mới. GĐ 2025-2030.", lat: 22.4139, lng: 103.9936 },
        { ten: "KCN Thống Nhất", viTri: "Xã Gia Phú, tỉnh Lào Cai", dienTich: 150, trangThai: "quy-hoach", moTa: "Bổ sung mới. Chuyển từ CCN Thống Nhất.", lat: 22.3397, lng: 104.0681 },
        { ten: "KCN Việt Hồng 1", viTri: "Xã Việt Hồng, tỉnh Lào Cai", dienTich: 300, trangThai: "quy-hoach", moTa: "Bổ sung mới. GĐ 2025-2030.", lat: 21.5653, lng: 104.8325 },
        { ten: "KCN Việt Hồng 2", viTri: "Xã Việt Hồng, tỉnh Lào Cai", dienTich: 200, trangThai: "quy-hoach", moTa: "Bổ sung mới. GĐ 2025-2030.", lat: 21.5680, lng: 104.8350 },
        { ten: "KCN Phú Xuân 1", viTri: "Xã Xuân Hòa, tỉnh Lào Cai", dienTich: 200, trangThai: "quy-hoach", moTa: "Bổ sung mới. GĐ 2025-2030.", lat: 22.3050, lng: 104.5200 }
    ];

    var kcnColors = { "hoat-dong": "#2e7d32", "xay-dung": "#f57f17", "quy-hoach": "#3949ab", "rut-qh": "#c62828" };
    var kcnLabels = { "hoat-dong": "Đang hoạt động", "xay-dung": "Đang xây dựng", "quy-hoach": "Quy hoạch", "rut-qh": "Rút khỏi QH" };

    window.kcnMap = L.map('kcn-map', {
        center: [22.15, 104.15],
        zoom: 9,
        zoomControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(window.kcnMap);

    L.control.zoom({ position: 'topleft' }).addTo(window.kcnMap);

    kcnData.forEach(function(kcn) {
        var color = kcnColors[kcn.trangThai];
        var icon = L.divIcon({
            className: 'kcn-marker',
            html: '<div style="width:28px;height:28px;border-radius:50%;background:' + color + ';border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:bold;">🏭</div>',
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });

        L.marker([kcn.lat, kcn.lng], { icon: icon })
            .addTo(window.kcnMap)
            .bindPopup(
                '<div style="min-width:220px;">' +
                '<h3 style="margin:0 0 6px;font-size:1rem;color:' + color + ';">' + kcn.ten + '</h3>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Vị trí:</b> ' + kcn.viTri + '</p>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Diện tích:</b> ' + kcn.dienTich + ' ha</p>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Trạng thái:</b> ' + kcnLabels[kcn.trangThai] + '</p>' +
                '<p style="margin:6px 0 0;font-size:0.82rem;color:#555;">' + kcn.moTa + '</p>' +
                '</div>'
            );
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

    var colors = {"hoat-dong":"#2e7d32","xay-dung":"#f57f17","quy-hoach":"#1565c0","rut-qh":"#c62828"};
    var labels = {"hoat-dong":"Đang hoạt động","xay-dung":"Đang xây dựng","quy-hoach":"Chưa thành lập","rut-qh":"⚠️ Rút khỏi QH"};
    var gradients = {
        "hoat-dong":"linear-gradient(135deg,#2e7d32,#43a047)",
        "xay-dung":"linear-gradient(135deg,#f57f17,#ff8f00)",
        "quy-hoach":"linear-gradient(135deg,#1565c0,#1976d2)",
        "rut-qh":"linear-gradient(135deg,#c62828,#e53935)"
    };

    grid.innerHTML = kcnAll.map(function(kcn, idx) {
        var color = colors[kcn.tt];
        var bg = gradients[kcn.tt];
        return '<div class="ccn-card" style="border-left:4px solid ' + color + ';">' +
            '<div class="ccn-card-header" style="background:' + bg + ';">' +
                '<h3 class="ccn-card-title">' + kcn.ten + '</h3>' +
                '<span class="ccn-card-status" style="background:rgba(255,255,255,0.2);color:#fff;">' + labels[kcn.tt] + '</span>' +
            '</div>' +
            '<div class="ccn-card-body">' +
                '<div class="ccn-card-info"><span class="info-icon">📍</span><span class="info-label">Vị trí:</span><span>' + kcn.viTri + '</span></div>' +
                '<div class="ccn-card-info"><span class="info-icon">📐</span><span class="info-label">Diện tích:</span><span>' + kcn.dt + ' ha</span></div>' +
                '<div class="ccn-card-info" style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;"><span class="info-icon">📝</span><span style="font-size:0.85rem;color:#555;">' + kcn.gc + '</span></div>' +
                '<div class="ccn-card-progress"><span>' + (idx+1) + '/21</span></div>' +
            '</div>' +
        '</div>';
    }).join('');
}

// ---- CCN QH Cards (31 CCN chưa TL - dạng card) ----
function renderCCNQHCards() {
    var grid = document.getElementById('ccnqh-grid');
    if (!grid) return;
    if (grid.querySelectorAll('.ccn-card').length > 0) return;
    grid.innerHTML = CCN_CHUA_DAU_TU.map(function(ccn) {
        return '<div class="ccn-card" style="border-left:4px solid #1565c0;">' +
            '<div class="ccn-card-header" style="background:linear-gradient(135deg,#1565c0,#1976d2);">' +
                '<h3 class="ccn-card-title">' + ccn.ten + '</h3>' +
                '<span class="ccn-card-status" style="background:rgba(255,255,255,0.2);color:#fff;">Chưa thành lập</span>' +
            '</div>' +
            '<div class="ccn-card-body">' +
                '<div class="ccn-card-info"><span class="info-icon">📍</span><span class="info-label">Vị trí:</span><span>' + ccn.xa + '</span></div>' +
                '<div class="ccn-card-info"><span class="info-icon">📐</span><span class="info-label">Diện tích:</span><span>' + ccn.dienTich + ' ha</span></div>' +
                '<div class="ccn-card-info"><span class="info-icon">📋</span><span class="info-label">Hướng PT:</span><span>' + ccn.huongPhatTrien + '</span></div>' +
                (ccn.baoCao ? '<div class="ccn-card-info" style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;"><span class="info-icon">📝</span><span style="font-size:0.85rem;color:#555;">' + ccn.baoCao + '</span></div>' : '') +
                '<div class="ccn-card-progress"><span>STT: ' + ccn.stt + '/31</span></div>' +
            '</div>' +
        '</div>';
    }).join('');
}

// ---- CCN QH Table (31 CCN) ----
function renderCCNQHTable() {
    var tableBody = document.getElementById('ccnqh-table-body');
    if (!tableBody) return;
    if (tableBody.querySelectorAll('tr').length > 0) return;
    tableBody.innerHTML = CCN_CHUA_DAU_TU.map(function(ccn, idx) {
        return '<tr style="' + (idx % 2 === 1 ? 'background:#f8f9fa;' : '') + '">' +
            '<td style="padding:10px;text-align:center;border-bottom:1px solid #eee;">' + ccn.stt + '</td>' +
            '<td style="padding:10px;border-bottom:1px solid #eee;font-weight:600;">' + ccn.ten + '</td>' +
            '<td style="padding:10px;border-bottom:1px solid #eee;">' + ccn.xa + '</td>' +
            '<td style="padding:10px;text-align:right;border-bottom:1px solid #eee;">' + ccn.dienTich + '</td>' +
            '<td style="padding:10px;border-bottom:1px solid #eee;">' + ccn.huongPhatTrien +
                (ccn.baoCao ? '<div style="margin-top:4px;font-size:0.82rem;color:#555;border-top:1px solid #eee;padding-top:4px;">' + ccn.baoCao + '</div>' : '') +
            '</td>' +
            '</tr>';
    }).join('');
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
                {label:'Quy hoạch (chưa TL)', data:[kcnQHCount, ccnQHCount], backgroundColor:'#1565c0'},
                {label:'Rút khỏi QH', data:[kcnRut, 0], backgroundColor:'#c62828'}
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
                {label:'Tổng DT (1000 ha)', data:[3.04, 8.73, 11.86], borderColor:'#2e7d32', backgroundColor:'rgba(46,125,50,0.15)', tension:0.3, fill:true, yAxisID:'y1', borderDash:[6,4], borderWidth:3, pointRadius:6}
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

// ---- Legacy dead code removed - wrap to prevent syntax errors ----
/*
DEAD_CODE_START
    var ttCount = {};
    var ttKeys = Object.keys(ttCount);
    new Chart(document.getElementById('chart-trangthai'), {
        type: 'doughnut',
        data: {
            labels: ttKeys.map(function(k) { return statusLabels[k] || k; }),
            datasets: [{
                data: ttKeys.map(function(k) { return ttCount[k]; }),
                backgroundColor: ttKeys.map(function(k) { return statusColors[k] || '#999'; }),
                borderWidth: 2,
                hoverOffset: 12
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } }
        }
    });

    // === Chart 2: Giai đoạn ===
    var gdCount = {};
    data.forEach(function(d) { gdCount[d.giaiDoan] = (gdCount[d.giaiDoan] || 0) + 1; });
    var gdKeys = Object.keys(gdCount).sort();
    new Chart(document.getElementById('chart-giaidoan'), {
        type: 'pie',
        data: {
            labels: gdKeys,
            datasets: [{
                data: gdKeys.map(function(k) { return gdCount[k]; }),
                backgroundColor: ['#1565c0', '#7b1fa2'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } }
        }
    });

    // === Chart 3: KCN vs CCN ===
    var kcnData = data.filter(function(d){return d.section==='KCN';});
    var ccnData = data.filter(function(d){return d.section==='CCN';});
    var kcnCount = kcnData.length, ccnCount = ccnData.length;
    var kcnArea = Math.round(kcnData.reduce(function(s,d){return s+d.area_ha;},0));
    var ccnArea = Math.round(ccnData.reduce(function(s,d){return s+d.area_ha;},0));
    new Chart(document.getElementById('chart-loai'), {
        type: 'bar',
        data: {
            labels: ['Số lượng', 'Diện tích (ha)'],
            datasets: [
                { label: 'Khu CN', data: [kcnCount, kcnArea], backgroundColor: '#c62828' },
                { label: 'Cụm CN', data: [ccnCount, ccnArea], backgroundColor: '#1565c0' }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: { y: { beginAtZero: true } }
        }
    });

    // === Chart 4: Top xã/phường ===
    var xaArea = {};
    data.forEach(function(d) {
        if (d.xa) xaArea[d.xa] = (xaArea[d.xa] || 0) + d.area_ha;
    });
    var xaSorted = Object.entries(xaArea).sort(function(a,b){return b[1]-a[1];}).slice(0, 12);
    new Chart(document.getElementById('chart-xa'), {
        type: 'bar',
        data: {
            labels: xaSorted.map(function(x){return x[0];}),
            datasets: [{
                label: 'Diện tích (ha)',
                data: xaSorted.map(function(x){return Math.round(x[1]);}),
                backgroundColor: '#2e7d32',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // === Chart 5: Top 12 lớn nhất ===
    var top12 = data.slice().sort(function(a,b){return b.area_ha-a.area_ha;}).slice(0, 12);
    new Chart(document.getElementById('chart-top'), {
        type: 'bar',
        data: {
            labels: top12.map(function(d){return (d.section==='KCN'?'🏭 ':'📦 ') + d.name;}),
            datasets: [{
                label: 'Diện tích (ha)',
                data: top12.map(function(d){return d.area_ha;}),
                backgroundColor: top12.map(function(d){return d.section==='KCN'?'#c62828':'#1565c0';}),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // === Chart 6: Timeline (line chart hiện trạng → 2030 → 2050) ===
    new Chart(document.getElementById('chart-timeline'), {
        type: 'line',
        data: {
            labels: ['Hiện tại (2025)', 'Quy hoạch 2030', 'Tầm nhìn 2050'],
            datasets: [
                {
                    label: 'Số Khu CN',
                    data: [7, 20, 22],
                    borderColor: '#c62828',
                    backgroundColor: 'rgba(198,40,40,0.1)',
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Số Cụm CN',
                    data: [23, 54, 62],
                    borderColor: '#1565c0',
                    backgroundColor: 'rgba(21,101,192,0.1)',
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Tổng DT (nghìn ha)',
                    data: [3.04, 8.73, 11.86],
                    borderColor: '#2e7d32',
                    backgroundColor: 'rgba(46,125,50,0.1)',
                    tension: 0.3,
                    fill: false,
                    yAxisID: 'y1',
                    borderDash: [6, 4]
                }
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
DEAD_CODE_END
*/

// ---- Ranh Giới Polygon Map with filters ----
window.ranhGioiData = [];
window.ranhGioiLayers = [];

function initRanhGioiMap() {
    window.ranhGioiMap = L.map('ccnranhgioi-map', {
        center: [22.0, 104.4],
        zoom: 9,
        zoomControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(window.ranhGioiMap);

    var satLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri'
    });

    L.control.zoom({ position: 'topleft' }).addTo(window.ranhGioiMap);
    L.control.layers({
        '🗺️ Bản đồ': L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'),
        '🛰️ Ảnh vệ tinh': satLayer
    }, {}, { position: 'topright' }).addTo(window.ranhGioiMap);

    fetch('ccn-polygons.json')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            window.ranhGioiData = data;
            // Build xa options
            var xaSet = Array.from(new Set(data.map(function(d){ return d.xa; }).filter(Boolean))).sort();
            var xaSelect = document.getElementById('filter-xa');
            xaSet.forEach(function(xa) {
                var opt = document.createElement('option');
                opt.value = xa; opt.textContent = xa;
                xaSelect.appendChild(opt);
            });
            // Bind filter change
            ['filter-loai','filter-trangthai','filter-xa','filter-dientich'].forEach(function(id) {
                var el = document.getElementById(id);
                if (el) el.addEventListener('change', applyRanhGioiFilters);
            });
            renderRanhGioi(data);
        })
        .catch(function(e) { console.error('Lỗi tải polygon:', e); });
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
        'quy-hoach': 'Quy hoạch (chưa TL)',
        'rut-qh': 'Rút khỏi QH'
    };

    data.forEach(function(item) {
        var isKCN = item.section === 'KCN';
        var isApprox = item.is_approx === true;
        var color = statusColors[item.trangThai] || '#1565c0';
        var fillColor = statusFillColors[item.trangThai] || '#42a5f5';
        if (isApprox) {
            color = '#ea580c';
            fillColor = '#fb923c';
        }

        var polygon = L.polygon(item.coords, {
            color: color,
            weight: 2,
            fillColor: fillColor,
            fillOpacity: 0.4,
            dashArray: isApprox ? '6, 6' : null
        }).addTo(window.ranhGioiMap);
        window.ranhGioiLayers.push(polygon);

        var displayName = (isKCN ? '🏭 ' : '📦 ') + item.name + (isApprox ? ' ⚠️' : '');
        var statusBadge = '<span style="display:inline-block; padding:2px 8px; border-radius:10px; background:' + color + '; color:#fff; font-size:0.72rem; font-weight:600;">' + (statusLabels[item.trangThai] || item.trangThai) + '</span>';
        var approxNote = isApprox
            ? '<div style="margin-top:8px;padding:8px;background:#fff7ed;border-left:3px solid #ea580c;font-size:0.82rem;color:#9a3412;border-radius:4px;">' +
              '<b>⚠️ Ranh giới tạm (minh họa quy mô)</b><br>' +
              (item.reason ? 'Lý do: ' + item.reason + '<br>' : '') +
              'Polygon chính thức đang được rà soát.' +
              '</div>'
            : '';

        polygon.bindPopup(
            '<div style="min-width:240px;max-width:320px;">' +
            '<h3 style="margin:0 0 6px;font-size:1rem;color:' + color + ';">' + displayName + '</h3>' +
            '<p style="margin:2px 0;font-size:0.85rem;">' + statusBadge + ' &nbsp; <b>' + item.giaiDoan + '</b></p>' +
            (item.xa ? '<p style="margin:2px 0;font-size:0.85rem;"><b>Vị trí:</b> ' + item.xa + '</p>' : '') +
            '<p style="margin:2px 0;font-size:0.85rem;"><b>Diện tích:</b> ' + item.area_ha + ' ha' +
            (isApprox ? ' (công bố)' : ' (tính từ tọa độ)') + '</p>' +
            (!isApprox ? '<p style="margin:2px 0;font-size:0.85rem;"><b>Số điểm ranh giới:</b> ' + item.num_points + '</p>' : '') +
            approxNote +
            '<p style="margin:6px 0 0;font-size:0.78rem;color:#666;font-style:italic;">VN-2000, KT trục 104°45\'</p>' +
            '</div>'
        );

        polygon.bindTooltip(displayName, { permanent: false, direction: 'center', className: 'polygon-label' });

        item.coords.forEach(function(c) { bounds.push(c); });
    });

    if (bounds.length > 0) {
        window.ranhGioiMap.fitBounds(bounds, { padding: [20, 20] });
    }
}

// ---- CCN Quy Hoach Map (31 CCN chưa thành lập) ----
function initCCNQHMap() {
    // Tọa độ 31 CCN - ưu tiên từ báo cáo xã, fallback về tọa độ UBND xã (Wikidata)
    var ccnqhData = [
        { stt:1, ten:"CCN Phú Thịnh 4", xa:"Phường Văn Phú", dt:75, gc:"Đất rừng SX 26ha. ~20 hộ ảnh hưởng. Cách IC cao tốc NB-LC ~7km. Điện 35kV có sẵn. Có ống cấp nước D300 từ hồ Thác Bà.", lat:21.7107, lng:104.9358 },
        { stt:2, ten:"CCN Mông Sơn", xa:"Xã Bảo Ái", dt:50, gc:"GĐ 2031-2050. Xã Bảo Ái đã có báo cáo.", lat:21.6750, lng:104.9100 },
        { stt:3, ten:"CCN Tân Nguyên", xa:"Xã Bảo Ái", dt:55, gc:"GĐ 2031-2050. Xã Bảo Ái đã có báo cáo.", lat:21.6800, lng:104.9150 },
        { stt:4, ten:"CCN Bát Xát", xa:"Thôn 9+10, xã Bát Xát", dt:57, gc:"Địa hình bằng phẳng, ven sông Hồng. Tiếp giáp QL4D. Đất nông nghiệp, ít hộ ảnh hưởng. Hạ tầng điện, nước thuận lợi.", lat:22.5422, lng:103.8900 },
        { stt:5, ten:"CCN Mường Khương", xa:"Xã Mường Khương", dt:30, gc:"20ha rừng phòng hộ, 7ha nương rẫy. ~30 hộ DTTS. Cách QL4D ~400m. Khái toán 113 tỷ. Thủ tục chuyển rừng PH phức tạp.", lat:22.7650, lng:104.1283 },
        { stt:6, ten:"CCN Bản Phiệt 1", xa:"TDP Làng Chung, P. Lào Cai", dt:75, gc:"53 hộ ảnh hưởng, TĐC 3-5ha. Cách CK Kim Thành ~19km, ga ĐS ~9km. Đang lập QH phân khu Bản Phiệt.", lat:22.4600, lng:103.9500 },
        { stt:7, ten:"CCN Bản Phiệt 2", xa:"TDP Pạc Tà+Cốc Lầy, P. Lào Cai", dt:75, gc:"60 hộ ảnh hưởng, TĐC ~80 hộ. Kết nối QL4D, QL70. Cách CK Kim Thành + ga ĐS ~13km.", lat:22.4550, lng:103.9450 },
        { stt:8, ten:"CCN Cam Đường 1", xa:"TDP Đất Đèn+Tát, P. Cam Đường", dt:40, gc:"GĐ 1: 11,36ha. Đã có NĐT đăng ký nghiên cứu đầu tư hạ tầng. Gần trung tâm TP Lào Cai.", lat:22.4139, lng:103.9936 },
        { stt:9, ten:"CCN Cam Đường 2", xa:"TDP Thác, P. Cam Đường", dt:12.75, gc:"Địa hình thuận lợi, gần khu vực đô thị.", lat:22.4100, lng:103.9980 },
        { stt:10, ten:"CCN Bảo Thắng", xa:"Thôn Tân Thành, xã Bảo Thắng", dt:40, gc:"Rừng SX 13ha, đất lúa 22,5ha. ~100 hộ ảnh hưởng. Cách QL4E 6km, giáp sông Hồng. Cần nâng cấp TL161.", lat:22.3397, lng:104.0681 },
        { stt:11, ten:"CCN Trà Trẩu", xa:"Thôn Trà Trẩu, xã Bảo Thắng", dt:35, gc:"Rừng SX 31ha. ~60 hộ (50 DTTS). Hầm chui cao tốc NB-LC tiết diện nhỏ → hạn chế xe tải lớn.", lat:22.3300, lng:104.0750 },
        { stt:12, ten:"CCN Phố Ràng 1", xa:"Thôn 9B, xã Bảo Yên", dt:56, gc:"~35 hộ ảnh hưởng. Giáp QL70. Khái toán ~443 tỷ. Đề xuất cầu Phố Ràng 2 kết nối TL160.", lat:22.1800, lng:104.3600 },
        { stt:13, ten:"CCN Phố Ràng 2", xa:"Thôn 9A, xã Bảo Yên", dt:75, gc:"~125 hộ ảnh hưởng (GPMB quy mô lớn). Khái toán ~587 tỷ. Rừng SX 340.877m².", lat:22.1750, lng:104.3650 },
        { stt:14, ten:"CCN Tân An", xa:"Thôn Mai Hồng 1, xã Bảo Hà", dt:40, gc:"46 hộ ảnh hưởng (43 DTTS). Giáp TL151C và sông Hồng. Điện 35kV cách 0,65km. Cách IC16 ~14km.", lat:22.1600, lng:104.2900 },
        { stt:15, ten:"CCN Bản Phùng", xa:"Thôn Nậm Cọ, xã Văn Bàn", dt:40, gc:"Rừng SX 31,1ha. ~20 hộ DTTS, GPMB thuận lợi. Cách QL279 ~1,5km. TL162 cắt qua CCN. Cấp nước suối tự chảy.", lat:22.0817, lng:104.2857 },
        { stt:16, ten:"CCN Hòa Mạc", xa:"Xã Văn Bàn", dt:20, gc:"GĐ 2031-2050. Thông tin từ báo cáo xã Văn Bàn ngày 02/4/2026.", lat:22.0900, lng:104.2800 },
        { stt:17, ten:"CCN Tân Hợp", xa:"Xã Tân Hợp", dt:75, gc:"Xã Tân Hợp đã có báo cáo. GĐ 2025-2030.", lat:21.8700, lng:104.6500 },
        { stt:18, ten:"CCN Ngòi A", xa:"Xã Mậu A", dt:62, gc:"GĐ 2031-2050. Xã Mậu A đã có báo cáo.", lat:21.8600, lng:104.6100 },
        { stt:19, ten:"CCN Yên Hưng", xa:"Xã Mậu A", dt:42, gc:"GĐ 2031-2050. Xã Mậu A đã có báo cáo.", lat:21.8550, lng:104.6150 },
        { stt:20, ten:"CCN An Thịnh", xa:"Xã Mậu A", dt:30, gc:"GĐ 2025-2030. Xã Mậu A đã có báo cáo.", lat:21.8500, lng:104.6200 },
        { stt:21, ten:"CCN Thống Nhất 2", xa:"Xã Gia Phú", dt:75, gc:"GĐ 2025-2030.", lat:22.3397, lng:104.0681 },
        { stt:22, ten:"CCN Thống Nhất 3", xa:"Xã Gia Phú", dt:30, gc:"GĐ 2025-2030.", lat:22.3350, lng:104.0720 },
        { stt:23, ten:"CCN Tân Lĩnh", xa:"Xã Tân Lĩnh", dt:75, gc:"GĐ 2025-2030.", lat:22.1264, lng:104.7197 },
        { stt:24, ten:"CCN Thượng Bằng La", xa:"Xã Thượng Bằng La", dt:20, gc:"GĐ 2025-2030, mở rộng 50ha sau 2030.", lat:21.5300, lng:104.6200 },
        { stt:25, ten:"CCN Văn Chấn", xa:"Xã Văn Chấn", dt:75, gc:"GĐ 2031-2050.", lat:21.5800, lng:104.5700 },
        { stt:26, ten:"CCN An Bình", xa:"Xã Đông Cuông", dt:50, gc:"GĐ 2031-2050.", lat:21.8400, lng:104.5900 },
        { stt:27, ten:"CCN Châu Quế", xa:"Xã Châu Quế", dt:75, gc:"GĐ 2031-2050.", lat:21.7600, lng:104.5500 },
        { stt:28, ten:"CCN Yên Hợp 1", xa:"Xã Xuân Ái", dt:63, gc:"GĐ II mở rộng CCN Yên Hợp sau 2030.", lat:21.8950, lng:104.6430 },
        { stt:29, ten:"CCN Xuân Ái (mở rộng)", xa:"Xã Xuân Ái", dt:75, gc:"Mở rộng CCN Yên Hợp GĐ II (tăng lên 75ha theo QĐ 525/2026).", lat:21.9000, lng:104.6380 },
        { stt:30, ten:"CCN Hợp Minh", xa:"Phường Âu Lâu", dt:37.4, gc:"GĐ 2025-2030.", lat:21.6920, lng:104.8420 },
        { stt:31, ten:"CCN Bảo Hưng 2", xa:"Phường Âu Lâu", dt:75, gc:"GĐ 2025-2030.", lat:21.6950, lng:104.8380 }
    ];

    window.ccnqhMap = L.map('ccnqh-map', {
        center: [22.05, 104.35],
        zoom: 9,
        zoomControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO'
    }).addTo(window.ccnqhMap);

    L.control.zoom({ position: 'topleft' }).addTo(window.ccnqhMap);

    ccnqhData.forEach(function(ccn) {
        var color = '#1565c0';
        var icon = L.divIcon({
            className: 'ccnqh-marker',
            html: '<div style="width:26px;height:26px;border-radius:50%;background:' + color + ';border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:10px;font-weight:bold;">' + ccn.stt + '</div>',
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });

        var ghiChu = ccn.gc ? '<p style="margin:6px 0 0;font-size:0.82rem;color:#555;border-top:1px solid #eee;padding-top:6px;">' + ccn.gc + '</p>' : '';

        L.marker([ccn.lat, ccn.lng], { icon: icon })
            .addTo(window.ccnqhMap)
            .bindPopup(
                '<div style="min-width:240px;max-width:320px;">' +
                '<h3 style="margin:0 0 6px;font-size:1rem;color:#1565c0;">' + ccn.stt + '. ' + ccn.ten + '</h3>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Vị trí:</b> ' + ccn.xa + '</p>' +
                '<p style="margin:2px 0;font-size:0.85rem;"><b>Diện tích QH:</b> ' + ccn.dt + ' ha</p>' +
                ghiChu +
                '</div>'
            );
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

    modal.innerHTML = `
        <div class="modal-header status-${ccn.trangThai}">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div class="modal-title">🏭 ${ccn.ten}</div>
            <div class="modal-status">${status.icon} ${status.ten}</div>
        </div>
        <div class="modal-body">
            <div class="modal-description">
                ${ccn.moTa}
            </div>
            <div class="modal-info-grid">
                <div class="modal-info-item">
                    <div class="modal-info-label">📍 Vị trí</div>
                    <div class="modal-info-value">${ccn.xa}</div>
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
                    <div class="modal-info-value">${ccn.nganhNghe}</div>
                </div>
                <div class="modal-info-item full-width">
                    <div class="modal-info-label">🏗️ Hạ tầng</div>
                    <div class="modal-info-value">${ccn.haTang}</div>
                </div>
                <div class="modal-info-item full-width">
                    <div class="modal-info-label">📜 Quyết định</div>
                    <div class="modal-info-value">${ccn.quyetDinh}</div>
                </div>
                <div class="modal-info-item full-width mt-3">
                    <div class="modal-info-label">📂 Tài liệu đính kèm</div>
                    <div class="modal-info-value" style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
                        <a href="mailto:sct@laocai.gov.vn?subject=Yêu cầu hồ sơ ${ccn.ten}" style="padding:8px 12px; background:#f1f5f9; border-radius:6px; text-decoration:none; display:flex; align-items:center; color:#1e293b; border:1px solid #e2e8f0; transition:all 0.2s; font-weight:500;" onmouseover="this.style.background='#e2e8f0'" onmouseout="this.style.background='#f1f5f9'">📧 Yêu cầu hồ sơ pháp lý ${ccn.ten} qua Email</a>
                    </div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button class="modal-btn-locate" onclick="locateOnMap(${ccn.id})" style="flex: 1;">
                    🗺️ Xem trên bản đồ
                </button>
                <a class="modal-btn-locate" style="flex: 1; background: #34495e; color: white; text-decoration: none; display: flex; align-items: center; justify-content: center;" href="https://www.google.com/maps/dir/?api=1&destination=${ccn.lat},${ccn.lng}" target="_blank">
                    🚗 Chỉ đường Google Maps
                </a>
            </div>
        </div>
    `;

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

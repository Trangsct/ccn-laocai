// ============================================================
// BẢN ĐỒ CỤM CÔNG NGHIỆP TỈNH LÀO CAI - APP LOGIC
// ============================================================

let map;
let markers = [];
let markerLayer;
let currentView = 'map';
let charts = {};

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
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EBP, and the GIS User Community'
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
        "🛰️ Ảnh vệ tinh": satelliteLayer
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
                labels: ['23 CCN Hiện hữu', '31 CCN Quy hoạch mới'],
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
            <div class="stat-label">Tổng số CCN</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🟢</div>
            <div class="stat-number" data-target="${THONG_KE.dangHoatDong}">0</div>
            <div class="stat-label">Đang hoạt động</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🟡</div>
            <div class="stat-number" data-target="${THONG_KE.dangXayDung}">0</div>
            <div class="stat-label">Đang xây dựng</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🔵</div>
            <div class="stat-number" data-target="${THONG_KE.choDauTu}">0</div>
            <div class="stat-label">Quy hoạch (Chờ đầu tư)</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">📐</div>
            <div class="stat-number" data-target="${THONG_KE.dienTichHienHuu}">0</div>
            <div class="stat-label">Diện tích 23 CCN hiện hữu (ha)</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🟦</div>
            <div class="stat-number" data-target="${THONG_KE.dienTichQuyHoach}">0</div>
            <div class="stat-label">Diện tích 31 CCN chờ đầu tư (ha)</div>
        </div>
        <div class="stat-card animate-in">
            <div class="stat-icon">🏢</div>
            <div class="stat-number" data-target="${THONG_KE.tongDoanhNghiep}">0</div>
            <div class="stat-label">Tổng doanh nghiệp</div>
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

    tableBody.innerHTML = CCN_CHUA_DAU_TU.map((ccn, idx) => `
        <tr>
            <td style="text-align:center;">${idx + 1}</td>
            <td><strong>${ccn.ten}</strong></td>
            <td>${ccn.xa}</td>
            <td style="text-align:right;">${ccn.dienTich} ha</td>
            <td>${ccn.huongPhatTrien || '-'}</td>
            <td style="text-align:center;"><span class="status-badge" style="background:#fef3c7; color:#d97706; padding:4px 8px; border-radius:4px; font-size:0.8rem; border:1px solid #fde68a;">⏳ Chờ đầu tư</span></td>
        </tr>
    `).join('');
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
    const tabs = document.querySelectorAll('.nav-tab');
    const sections = {
        'map': document.getElementById('map-section'),
        'list': document.getElementById('list-section'),
        'quyhoach': document.getElementById('quyhoach-section')
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-tab');
            currentView = target;

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show/hide sections
            Object.entries(sections).forEach(([key, section]) => {
                if (section) {
                    if (target === 'map') {
                        section.style.display = (key === 'map' || key === 'list') ? '' : 'none';
                    } else {
                        section.style.display = (key === target) ? '' : 'none';
                    }
                }
            });

            if (target === 'map') {
                setTimeout(() => map.invalidateSize(), 100);
            }
        });
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
    const mapTab = document.querySelector('.nav-tab[data-tab="map"]');
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

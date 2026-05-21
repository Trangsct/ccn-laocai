// Service Worker — Khu, Cụm công nghiệp tỉnh Lào Cai
// Chiến lược: Network-first cho HTML/JSON (luôn lấy bản mới nhất),
// Cache-first cho tài nguyên tĩnh (CSS, JS, ảnh, font, PDF).

const CACHE_VERSION = 'ccn-laocai-v15';
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/app.js',
  '/data.js',
  '/style.css',
  '/manifest.json',
  '/pwa-icon-192.png',
  '/pwa-icon-512.png'
];

// Cài đặt — precache file lõi
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(function (cache) {
      return cache.addAll(PRECACHE_URLS).catch(function (err) {
        console.warn('[SW] Precache thất bại một phần:', err);
      });
    }).then(function () { return self.skipWaiting(); })
  );
});

// Kích hoạt — xóa cache phiên bản cũ và thông báo cho các tab đang mở để tải lại
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE_VERSION) return caches.delete(k);
      }));
    }).then(function () {
      return self.clients.claim();
    }).then(function () {
      // Thông báo các tab đang mở để tự reload (chỉ khi đã có client cũ)
      return self.clients.matchAll({ type: 'window' }).then(function (clients) {
        clients.forEach(function (client) {
          try { client.postMessage({ type: 'sw-updated', version: CACHE_VERSION }); } catch (e) {}
        });
      });
    })
  );
});

// Fetch — chiến lược lai
self.addEventListener('fetch', function (event) {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Bỏ qua các domain bên ngoài (Leaflet tile, fonts, CDN)
  if (url.origin !== self.location.origin) return;

  // Bỏ qua endpoint API (Vercel Edge Function) — không cache, không can thiệp
  if (url.pathname.startsWith('/api/')) return;

  const isHTML = req.mode === 'navigate' || req.destination === 'document';
  const isJSON = url.pathname.endsWith('.json');

  // Network-first cho HTML và JSON (cập nhật mới nhất)
  if (isHTML || isJSON) {
    event.respondWith(
      fetch(req).then(function (resp) {
        const respClone = resp.clone();
        caches.open(CACHE_VERSION).then(function (cache) {
          cache.put(req, respClone);
        });
        return resp;
      }).catch(function () {
        return caches.match(req).then(function (cached) {
          return cached || caches.match('/index.html');
        });
      })
    );
    return;
  }

  // Cache-first cho tài nguyên tĩnh
  event.respondWith(
    caches.match(req).then(function (cached) {
      if (cached) return cached;
      return fetch(req).then(function (resp) {
        if (resp.ok) {
          const respClone = resp.clone();
          caches.open(CACHE_VERSION).then(function (cache) {
            cache.put(req, respClone);
          });
        }
        return resp;
      });
    })
  );
});

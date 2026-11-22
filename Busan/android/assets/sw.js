/* 釜山 AI 旅行助手 · PWA service worker（v2.8）
 * 只缓存同源静态资源；天气接口（Open-Meteo）与云端库始终走网络，避免给用户过期数据。
 */
const CACHE = 'busan-3.1';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-180.png',
  './icon-192.png',
  './admin_base.js',
  './sync.js',
  './data.js',
  './cloud_snapshot.js',
  './photos.js',
  './cloud.js',
  './app.js',
  './live.js',
  './session.js',
  './planner.js',
  './weather.js',
  './ratings.js',
  './mix.js'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(SHELL);
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // 内容/版本接口永远走网络：后台一改就能立刻拿到 rev，不吃缓存。
  if (url.pathname.indexOf("/api/") >= 0) {
    event.respondWith(
      fetch(req).catch(function () {
        return caches.match(req, { ignoreSearch: true }).then(function (hit) {
          return hit || new Response("{}", { status: 503, headers: { "Content-Type": "application/json" } });
        });
      })
    );
    return;
  }

  // 导航/HTML 走网络优先：保证每次打开拿到最新版本，断网时回退到缓存。
  if (req.mode === 'navigate' || /\.html?$/i.test(url.pathname)) {
    event.respondWith(
      fetch(req).then(function (res) {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match(req, { ignoreSearch: true }).then(function (hit) {
          return hit || caches.match('./index.html');
        });
      })
    );
    return;
  }

  event.respondWith(
    caches.match(req, { ignoreSearch: true }).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res && res.status === 200 && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () { return Response.error(); });
    })
  );
});

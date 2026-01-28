// Service Worker для PWA
const CACHE_NAME = 'tender-site-v2';
const STATIC_CACHE = 'tender-static-v2';
const DYNAMIC_CACHE = 'tender-dynamic-v2';

const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/offline.html',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js'
];

// Установка Service Worker
self.addEventListener('install', function(event) {
  console.log('[ServiceWorker] Install');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(function(cache) {
        console.log('[ServiceWorker] Caching app shell');
        return cache.addAll(urlsToCache).catch(function(err) {
          console.log('[ServiceWorker] Cache addAll failed:', err);
        });
      })
  );
  self.skipWaiting();
});

// Активация Service Worker
self.addEventListener('activate', function(event) {
  console.log('[ServiceWorker] Activate');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('[ServiceWorker] Removing old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// Перехват запросов с стратегией Network First, затем Cache
self.addEventListener('fetch', function(event) {
  // Пропускаем запросы не-GET
  if (event.request.method !== 'GET') {
    return;
  }
  
  // Пропускаем запросы к внешним ресурсам (кроме CDN)
  const url = new URL(event.request.url);
  if (url.origin !== location.origin && !urlsToCache.includes(event.request.url)) {
    return;
  }
  
  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Клонируем ответ для кэширования
        const responseToCache = response.clone();
        
        // Кэшируем успешные ответы
        if (response.status === 200) {
          caches.open(DYNAMIC_CACHE).then(function(cache) {
            cache.put(event.request, responseToCache);
          });
        }
        
        return response;
      })
      .catch(function() {
        // Если сеть недоступна, пытаемся получить из кэша
        return caches.match(event.request).then(function(response) {
          if (response) {
            return response;
          }
          
          // Если это HTML запрос, возвращаем offline страницу
          if (event.request.headers.get('accept').includes('text/html')) {
            return caches.match('/static/offline.html');
          }
        });
      })
  );
});


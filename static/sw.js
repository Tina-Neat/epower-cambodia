/**
 * Service Worker for E-Power Offline & Online Support
 * Caches essential static assets and provides offline fallbacks.
 */

const CACHE_NAME = 'epower-cache-v8';
const ASSETS_TO_CACHE = [
  '/',
  '/login',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/img/E-power-logo.png',
  '/static/img/E-power-logo.png',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/favicon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Network-First with Cache Fallback for dynamic pages
self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Return from cache when offline
        return caches.match(event.request);
      })
  );
});

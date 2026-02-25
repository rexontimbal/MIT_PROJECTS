// AGNES PWA Service Worker
// Handles caching and offline functionality

const CACHE_NAME = 'agnes-pwa-v1';
const OFFLINE_URL = '/offline/';

// Static assets to cache immediately on install
const STATIC_ASSETS = [
    '/',
    '/offline/',
    '/static/css/main.css',
    '/static/images/pnp-logo.png',
    '/static/manifest.json',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js',
    'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css',
    'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css',
];

// Pages to cache when visited (network-first strategy)
const CACHEABLE_PAGES = [
    '/dashboard/',
    '/accidents/',
    '/map/',
    '/hotspots/',
    '/analytics/',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                // Force this service worker to become active immediately
                return self.skipWaiting();
            })
            .catch((err) => {
                console.log('[SW] Cache failed for some assets:', err);
                // Don't fail install if CDN assets fail - cache what we can
                return caches.open(CACHE_NAME).then((cache) => {
                    return cache.addAll([
                        '/',
                        '/offline/',
                        '/static/css/main.css',
                        '/static/images/pnp-logo.png',
                    ]);
                });
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            // Take control of all pages immediately
            return self.clients.claim();
        })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // Skip non-GET requests (POST, PUT, DELETE etc.)
    if (request.method !== 'GET') {
        return;
    }

    // Skip admin panel, API calls, and auth-related requests
    if (url.pathname.startsWith('/admin/') ||
        url.pathname.startsWith('/api/') ||
        url.pathname.startsWith('/login/') ||
        url.pathname.startsWith('/logout/') ||
        url.pathname.startsWith('/register/')) {
        return;
    }

    // Strategy: Network-first for HTML pages, Cache-first for static assets
    if (request.headers.get('Accept') && request.headers.get('Accept').includes('text/html')) {
        // Network-first for pages - always try fresh content
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Cache successful page loads for offline use
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Offline - try cache first, then offline page
                    return caches.match(request).then((cachedResponse) => {
                        return cachedResponse || caches.match(OFFLINE_URL);
                    });
                })
        );
    } else if (url.pathname.startsWith('/static/') ||
               url.hostname !== location.hostname) {
        // Cache-first for static assets and CDN resources
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cache but also update in background
                    fetch(request).then((response) => {
                        if (response.ok) {
                            caches.open(CACHE_NAME).then((cache) => {
                                cache.put(request, response);
                            });
                        }
                    }).catch(() => {});
                    return cachedResponse;
                }
                // Not in cache - fetch from network
                return fetch(request).then((response) => {
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                });
            })
        );
    }
});

// Listen for messages from the main page
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

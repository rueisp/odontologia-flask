// static/service-worker.js

// Cambiamos el nombre para invalidar la caché anterior (sgc-cache-v1)
const CACHE_NAME = 'clinica-v-rescate-01';
const ASSETS_TO_CACHE = [
    '/static/img/icon-192.png',
    '/static/img/icon-512.png',
    // NO cacheamos '/' ni HTML en esta fase para garantizar que la web cargue siempre
];

// 1. INSTALACIÓN: Forzar la espera para activar el nuevo SW inmediatamente
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Instalando versión de rescate...');
    self.skipWaiting(); // Fuerza activación inmediata
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// 2. ACTIVACIÓN: Borrar TODAS las cachés antiguas (incluida sgc-cache-v1)
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activando y limpiando cachés antiguas...');
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    console.log('[Service Worker] Borrando caché antigua:', key);
                    return caches.delete(key);
                }
            }));
        }).then(() => {
            return self.clients.claim(); // Tomar control de los clientes
        })
    );
});

// 3. FETCH: Estrategia "Network First" (Red primero)
// Intenta ir a Fly.io primero. Solo si no hay internet mira la caché.
self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                return response;
            })
            .catch(() => {
                // Solo si no hay internet (offline)
                return caches.match(event.request);
            })
    );
});
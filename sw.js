// AshaStats - Service Worker
// Version 1.0.1

const CACHE_NAME = 'fpl-analyzer-v1.0.1';
const urlsToCache = [
  '/',
  '/search', // Add this line
  '/static/css/styles.css',
  '/static/css/components.css',
  '/static/js/app.js',
  '/static/js/stats.js',
  '/static/js/settings.js',
  '/static/manifest.json',
  '/static/assets/app-icon-192.png',
  '/static/assets/app-icon-512.png'
];

// Install event - cache resources
self.addEventListener('install', function(event) {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        console.log('Service Worker: Installation complete');
        return self.skipWaiting();
      })
      .catch(function(error) {
        console.log('Service Worker: Installation failed', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      console.log('Service Worker: Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', function(event) {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip external requests (other domains)
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Return cached version if available
        if (response) {
          console.log('Service Worker: Serving from cache', event.request.url);
          return response;
        }

        // Otherwise fetch from network
        return fetch(event.request).then(function(response) {
          // Don't cache if not a valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          var responseToCache = response.clone();

          // Add to cache for future use
          caches.open(CACHE_NAME)
            .then(function(cache) {
              // Cache static assets, main page, and manifest
              if (event.request.url.includes('/static/') || 
                  event.request.url === self.location.origin + '/' ||
                  event.request.url.includes('manifest.json')) {
                cache.put(event.request, responseToCache);
                console.log('Service Worker: Cached new resource', event.request.url);
              }
            });

          return response;
        }).catch(function() {
          // Network failed, try to serve offline fallback
          if (event.request.destination === 'document') {
            return caches.match('/');
          }
        });
      })
  );
});

// Background sync for offline functionality
self.addEventListener('sync', function(event) {
  if (event.tag === 'background-sync') {
    console.log('Service Worker: Background sync triggered');
    event.waitUntil(
      // Add background sync logic here if needed
      Promise.resolve()
    );
  }
});

// Push notification support (for future use)
self.addEventListener('push', function(event) {
  console.log('Service Worker: Push message received');
  
  const options = {
    body: event.data ? event.data.text() : 'FPL League Analyzer notification',
    icon: '/static/assets/app-icon-192.png',
    badge: '/static/assets/app-icon-192.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    }
  };

  event.waitUntil(
    self.registration.showNotification('FPL League Analyzer', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', function(event) {
  console.log('Service Worker: Notification click received');
  
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/')
  );
});

// Message handler for communication with main app
self.addEventListener('message', function(event) {
  console.log('Service Worker: Message received', event.data);
  
  if (event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
  
  if (event.data.action === 'clearCache') {
    event.waitUntil(
      caches.delete(CACHE_NAME).then(function() {
        console.log('Service Worker: Cache cleared');
        event.ports[0].postMessage({success: true});
      })
    );
  }
});

// Error handler
self.addEventListener('error', function(event) {
  console.error('Service Worker: Error occurred', event.error);
});

// Unhandled rejection handler
self.addEventListener('unhandledrejection', function(event) {
  console.error('Service Worker: Unhandled promise rejection', event.reason);
});

console.log('Service Worker: Script loaded');
/**
 * RescueAI Service Worker
 *
 * Strategy
 * --------
 * - App shell (JS/CSS/HTML): cache-first with network fallback.
 *   Ensures the app loads instantly and works offline where possible.
 *
 * - POST /api/reports/intake: network-first.
 *   If the network request fails (offline), the report payload is saved
 *   to IndexedDB under the key "offline-queue" and retried automatically
 *   when the browser regains connectivity (via the "sync" event, with a
 *   polling fallback for browsers that don't support Background Sync).
 *
 * - API requests: network-first with cache fallback for resilience.
 *
 * Offline queue storage: IndexedDB, database "rescueai", store "queue".
 * Each entry: { id: timestamp, payload: {...}, attempts: 0 }
 */

const CACHE_NAME   = 'rescueai-v2'
const INTAKE_URL   = '/api/reports/intake'
const DB_NAME      = 'rescueai'
const DB_VERSION   = 1
const STORE_NAME   = 'queue'
const SYNC_TAG     = 'rescueai-report-sync'

// Assets to pre-cache on install (app shell)
const PRECACHE_ASSETS = [
  '/',
  '/dashboard',
]

// ---------------------------------------------------------------------------
// IndexedDB helpers
// ---------------------------------------------------------------------------
function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = e => {
      const db = e.target.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' })
      }
    }
    req.onsuccess = e => resolve(e.target.result)
    req.onerror   = e => reject(e.target.error)
  })
}

async function enqueue(payload) {
  const db    = await openDB()
  const entry = { id: Date.now(), payload, attempts: 0 }
  return new Promise((resolve, reject) => {
    const tx  = db.transaction(STORE_NAME, 'readwrite')
    const req = tx.objectStore(STORE_NAME).add(entry)
    req.onsuccess = () => resolve(entry.id)
    req.onerror   = e  => reject(e.target.error)
  })
}

async function getAll() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx  = db.transaction(STORE_NAME, 'readonly')
    const req = tx.objectStore(STORE_NAME).getAll()
    req.onsuccess = e => resolve(e.target.result)
    req.onerror   = e => reject(e.target.error)
  })
}

async function remove(id) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx  = db.transaction(STORE_NAME, 'readwrite')
    const req = tx.objectStore(STORE_NAME).delete(id)
    req.onsuccess = () => resolve()
    req.onerror   = e  => reject(e.target.error)
  })
}

async function bumpAttempts(entry) {
  const db = await openDB()
  const updated = { ...entry, attempts: entry.attempts + 1 }
  return new Promise((resolve, reject) => {
    const tx  = db.transaction(STORE_NAME, 'readwrite')
    const req = tx.objectStore(STORE_NAME).put(updated)
    req.onsuccess = () => resolve()
    req.onerror   = e  => reject(e.target.error)
  })
}

// ---------------------------------------------------------------------------
// Flush queued reports
// ---------------------------------------------------------------------------
async function flushQueue() {
  const entries = await getAll()
  for (const entry of entries) {
    // Drop after 5 failed attempts to prevent infinite retries
    if (entry.attempts >= 5) {
      console.warn('[SW] Dropping queued report after 5 attempts:', entry.id)
      await remove(entry.id)
      continue
    }
    try {
      const res = await fetch(INTAKE_URL, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(entry.payload),
      })
      if (res.ok) {
        console.log('[SW] Queued report delivered:', entry.id)
        await remove(entry.id)
      } else {
        console.warn('[SW] Server rejected queued report, status:', res.status)
        await bumpAttempts(entry)
      }
    } catch {
      // Still offline — leave in queue, bump counter
      await bumpAttempts(entry)
    }
  }
}

// ---------------------------------------------------------------------------
// Install — pre-cache app shell
// ---------------------------------------------------------------------------
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  )
})

// ---------------------------------------------------------------------------
// Activate — clean up old caches
// ---------------------------------------------------------------------------
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  )
})

// ---------------------------------------------------------------------------
// Fetch — intercept requests
// ---------------------------------------------------------------------------
self.addEventListener('fetch', event => {
  const { request } = event

  // Intake POST: network-first, queue on failure
  if (request.method === 'POST' && request.url.includes(INTAKE_URL)) {
    event.respondWith(
      request.clone().json().then(async payload => {
        try {
          const res = await fetch(request)
          return res
        } catch {
          // Offline: save to queue and return a synthetic "accepted" response
          // so the UI can show a success message with the queued ID
          const queuedId = await enqueue(payload)
          console.log('[SW] Report queued for later delivery, id:', queuedId)

          // Register background sync if supported
          if ('sync' in self.registration) {
            await self.registration.sync.register(SYNC_TAG)
          }

          return new Response(
            JSON.stringify({ report_id: `queued-${queuedId}`, queued: true }),
            {
              status:  202,
              headers: { 'Content-Type': 'application/json' },
            }
          )
        }
      }).catch(() => fetch(request))   // JSON parse failed, pass through
    )
    return
  }

  // All other requests: cache-first, network fallback
  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) return cached
      return fetch(request).then(response => {
        // Cache successful GET responses for static assets
        if (
          request.method === 'GET' &&
          response.ok &&
          !request.url.includes('/api/')
        ) {
          const clone = response.clone()
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone))
        }
        return response
      }).catch(() => {
        // For navigation requests when offline, serve cached index
        if (request.mode === 'navigate') {
          return caches.match('/') || caches.match('/dashboard')
        }
      })
    })
  )
})

// ---------------------------------------------------------------------------
// Background Sync — fires when connectivity is restored (Chrome/Edge)
// ---------------------------------------------------------------------------
self.addEventListener('sync', event => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(flushQueue())
  }
})

// ---------------------------------------------------------------------------
// Polling fallback — for browsers without Background Sync (Firefox, Safari)
// Re-try every 30 s while the SW is active
// ---------------------------------------------------------------------------
setInterval(() => {
  flushQueue().catch(() => {})
}, 30_000)

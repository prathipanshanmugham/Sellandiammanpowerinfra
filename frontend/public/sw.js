/* Sellandiamman Power Infra service worker.
   Kept deliberately small so it can never serve stale data:
   - pages: always from the network; only when the network fails, a cached "You're offline" page;
   - /assets/* (file names carry a content hash, so a file never changes): cached on first use;
   - /api/* and everything else: not touched (straight to the network).
   Bump VERSION when this file's logic changes; old caches are removed on activation. */
const VERSION = "spi-v1";
const SHELL = `${VERSION}-shell`;
const ASSETS = `${VERSION}-assets`;
const OFFLINE = "/offline.html";
const MAX_ASSETS = 120;

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll([OFFLINE])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (!key.startsWith(VERSION)) await caches.delete(key);
    if (self.registration.navigationPreload) await self.registration.navigationPreload.enable();
    await self.clients.claim();
  })());
});

async function trim(cache) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - MAX_ASSETS; i += 1) await cache.delete(keys[i]);
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (req.mode === "navigate") {
    event.respondWith((async () => {
      try {
        return (await event.preloadResponse) || (await fetch(req));
      } catch (e) {
        return (await caches.match(OFFLINE)) || Response.error();
      }
    })());
    return;
  }

  if (url.pathname.startsWith("/assets/")) {
    event.respondWith((async () => {
      const cache = await caches.open(ASSETS);
      const hit = await cache.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok && res.type === "basic") { cache.put(req, res.clone()); trim(cache); }
      return res;
    })());
  }
});

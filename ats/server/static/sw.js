/* ATS service worker (QA-11): a minimal offline shell for the PWA.
 * Cache-first for the static app shell; always network for live data
 * (/api, /ws) so the dashboard never shows stale prices. Served from / (via a
 * root route) so its scope covers the whole app.
 */
const CACHE = "ats-shell-v1";
const SHELL = ["/", "/static/app.css", "/static/app.js", "/static/themes.js"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Never intercept live data or non-GET — always go to the network.
  if (e.request.method !== "GET" || url.pathname.startsWith("/api") || url.pathname === "/ws") {
    return;
  }
  e.respondWith(
    caches.match(e.request).then((hit) =>
      hit || fetch(e.request).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return resp;
      }).catch(() => caches.match("/"))
    )
  );
});

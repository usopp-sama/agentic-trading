/* ATS service worker (QA-11, fixed): offline shell for the PWA.
 *
 * v1 served EVERY page cache-first and never revalidated, so browsers kept
 * showing week-old HTML after each deploy (stale nav, missing new pages).
 * v2 policy:
 *   - pages/HTML (navigations): NETWORK-FIRST, cache only as offline fallback
 *   - /static assets:           cache-first, but revalidate in the background
 *   - /api, /ws, non-GET:       never intercepted (always live)
 */
const CACHE = "ats-shell-v2";
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
  if (e.request.method !== "GET" || url.pathname.startsWith("/api") || url.pathname === "/ws") {
    return; // live data is never intercepted
  }

  const isPage = e.request.mode === "navigate" ||
    (e.request.headers.get("accept") || "").includes("text/html");

  if (isPage) {
    // network-first: fresh HTML whenever the server is up; cache = offline fallback
    e.respondWith(
      fetch(e.request).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return resp;
      }).catch(() => caches.match(e.request).then((hit) => hit || caches.match("/")))
    );
    return;
  }

  // static assets: cache-first + background revalidate (stale-while-revalidate)
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const refresh = fetch(e.request).then((resp) => {
        caches.open(CACHE).then((c) => c.put(e.request, resp.clone()));
        return resp;
      }).catch(() => hit);
      return hit || refresh;
    })
  );
});

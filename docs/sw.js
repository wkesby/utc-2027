// v2 — the shell is network-first so a deploy actually reaches installed phones.
// v1 served index.html cache-first, which froze installed apps on whatever HTML they
// cached first; the cache only ever refreshed if this file itself changed.
const SHELL = "utc-shell-v2";
const DATA = "utc-data-v2";
const FILES = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL)
    // cache:"reload" so precaching never picks up a stale HTTP-cached copy
    .then(c => Promise.all(FILES.map(f => fetch(f, {cache: "reload"}).then(r => r.ok && c.put(f, r)).catch(() => {}))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== DATA).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const fresh = (req, cacheName, key) => fetch(req).then(r => {
  const copy = r.clone();
  caches.open(cacheName).then(c => c.put(key, copy));
  return r;
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  const bare = url.pathname + (url.pathname.endsWith("/") ? "" : "");
  const isDoc = e.request.mode === "navigate" || url.pathname.endsWith(".html") || url.pathname.endsWith("/");
  if (url.pathname.endsWith(".json")) {                     // data: network first, cache as backup
    e.respondWith(fresh(e.request, DATA, e.request.url.split("?")[0])
      .catch(() => caches.match(e.request.url.split("?")[0])));
  } else if (isDoc) {                                       // the app itself: always try the network
    e.respondWith(fresh(e.request, SHELL, bare)
      .catch(() => caches.match(bare).then(r => r || caches.match("./index.html"))));
  } else {                                                  // icons and manifest: cache first
    e.respondWith(caches.match(e.request, {ignoreSearch: true}).then(r => r || fetch(e.request)));
  }
});

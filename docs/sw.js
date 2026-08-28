// v2 — the shell is network-first so a deploy actually reaches installed phones.
// v1 served index.html cache-first, which froze installed apps on whatever HTML they
// cached first; the cache only ever refreshed if this file itself changed.
// v3 adds web-push handlers for the banter wall and weekly wrap.
// v4 stops caching error responses, and the rename drops the v3 caches that had a
// 404 stored for photos/dt.jpg and photos/wayne.jpg from before those files existed.
const SHELL = "utc-shell-v4";
const DATA = "utc-data-v4";
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

// Web push: the GitHub workflow sends {title, body, url, tag} as JSON.
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data.json(); } catch (_) {}
  e.waitUntil(self.registration.showNotification(d.title || "UTC 2027", {
    body: d.body || "", icon: "./icon-192.png", badge: "./icon-192.png",
    tag: d.tag || "utc", data: { url: d.url || "./" }
  }));
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "./", self.location.href).href;
  e.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then(ws => {
    for (const w of ws) {
      if (w.url.split("#")[0] === url.split("#")[0] && "focus" in w) {
        if ("navigate" in w) w.navigate(url).catch(() => {});
        return w.focus();
      }
    }
    return clients.openWindow(url);
  }));
});

const fresh = (req, cacheName, key) => fetch(req).then(r => {
  // Only ever cache a good response. Caching a 404 permanently masks a file that is
  // added later — that is what hid the drafter photos added after an install's first run.
  if (r.ok) {
    const copy = r.clone();
    caches.open(cacheName).then(c => c.put(key, copy));
  }
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
  } else if (url.pathname.includes("/photos/")) {            // drafter photos: cache once, keep offline
    e.respondWith(caches.match(e.request).then(r => r || fresh(e.request, SHELL, e.request.url)));
  } else {                                                  // icons and manifest: cache first
    e.respondWith(caches.match(e.request, {ignoreSearch: true}).then(r => r || fetch(e.request)));
  }
});

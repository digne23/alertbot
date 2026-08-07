/* AlertBot service worker.
   Caches the shell so the PWA opens instantly and degrades gracefully when the
   phone has no signal. API responses are never cached — a stale incident list
   is worse than no incident list. */

// Bumped with the Esicia light restyle so cached dark-theme CSS and icons are
// dropped rather than served alongside the new markup.
const CACHE = "alertbot-shell-v2";

const SHELL = [
  "/static/style.css",
  "/static/app.js",
  "/static/icons/icon.svg",
  "/static/icons/icon-192.png",
  "/offline",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Always go to the network for data and pages; fall back to the cache.
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(request));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/offline")));
    return;
  }

  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        }),
    ),
  );
});

/* Web push (iOS 16.4+ in installed mode, Android Chrome, desktop).
   The payload matches what NotificationService sends. */
self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (_) {
    payload = { title: "AlertBot", message: event.data ? event.data.text() : "" };
  }

  const title = payload.title || "AlertBot incident";
  const options = {
    body: payload.message || "",
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    tag: `alertbot-${payload.incident_id || "generic"}`,
    renotify: true,
    requireInteraction: payload.alarm !== "0",
    vibrate: [400, 200, 400, 200, 400],
    data: { incident_id: payload.incident_id },
    actions: payload.incident_id ? [{ action: "ack", title: "Acknowledge" }] : [],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  const incidentId = event.notification.data && event.notification.data.incident_id;
  event.notification.close();

  if (event.action === "ack" && incidentId) {
    event.waitUntil(fetch(`/api/incidents/${incidentId}/ack`, { method: "POST" }));
    return;
  }

  const target = incidentId ? `/incident/${incidentId}` : "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      return self.clients.openWindow(target);
    }),
  );
});

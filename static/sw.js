// Minimal service worker: exists so the browser considers this page
// installable as an app. Deliberately does no offline caching — this
// dashboard shows live schedule data, and a stale cache would be
// actively misleading (showing a slot as "open" after it's full/passed).
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.clients.claim());
self.addEventListener("fetch", () => {});

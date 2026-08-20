// Service worker: makes the page installable as an app, and receives the
// "a spot opened" push notifications.
//
// Deliberately does no offline caching — this dashboard shows live schedule
// data, and a stale cache would be actively misleading (showing a slot as
// "open" after it's full/passed).
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.clients.claim());
self.addEventListener("fetch", () => {});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (err) {
    payload = { title: "A watched activity opened up" };
  }

  const title = payload.title || "A watched activity opened up";
  const options = {
    body: payload.body || "",
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    // Tapping should land on the session's registration page.
    data: { url: payload.url || "/" },
    // Spot alerts are time-sensitive; keep them on screen until acted on.
    requireInteraction: true,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      // Reuse an already-open tab on this origin when there is one.
      for (const client of windowClients) {
        if ("focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

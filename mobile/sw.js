const CACHE_NAME = "jarvis-mobile-v2";
const SHELL_FILES = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network-first for the app shell too: always try to fetch the latest
// deployed version first, and only fall back to the cached copy if the
// network request fails (e.g. offline). This way every new GitHub Pages
// deploy shows up immediately instead of being stuck behind an old cache.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const isShell = SHELL_FILES.some((f) => url.pathname.endsWith(f.replace("./", "")));

  if (isShell) {
    event.respondWith(
      fetch(event.request)
        .then((freshResponse) => {
          const clone = freshResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return freshResponse;
        })
        .catch(() => caches.match(event.request))
    );
  }
  // All other requests (weather API, AI API, google search, wa.me, etc.)
  // just go to the network normally.
});

// Haushöd Service Worker: hält die App offline startbereit.
// Daten synchronisiert Firestore selbst; die werden hier nie zwischengespeichert.
const VERSION = 'haushoed-v7';
// Pfade relativ zum Ordner der App, damit sie auch unter <name>.github.io/haushoed/ läuft
const BASE = self.registration.scope;
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png', 'icons/favicon-64.png'].map(p => new URL(p, BASE).href);
const INDEX = new URL('index.html', BASE).href;
const CDN = /^(www\.gstatic\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)$/;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
async function networkFirst(req){
  const cache = await caches.open(VERSION);
  try { const res = await fetch(req); if (res.ok) cache.put(INDEX, res.clone()); return res; }
  catch (e) { return (await cache.match(INDEX)) || Response.error(); }
}
async function staleWhileRevalidate(req){
  const cache = await caches.open(VERSION);
  const hit = await cache.match(req);
  const net = fetch(req).then(res => { if (res.ok || res.type === 'opaque') cache.put(req, res.clone()); return res; }).catch(() => hit);
  return hit || net;
}
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    if (req.mode === 'navigate') { e.respondWith(networkFirst(req)); return; }
    e.respondWith(staleWhileRevalidate(req));
    return;
  }
  if (CDN.test(url.hostname)) e.respondWith(staleWhileRevalidate(req)); // Firebase-SDK und Schriften
});

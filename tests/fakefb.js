// Firestore-Imitat für die Tests. Ersetzt window.HFB und verhält sich in den Punkten, auf die es ankommt,
// wie der echte Server:
// - serverTimestamp() wird beim Schreiben zur Serverzeit (FAKE.clock, vorstellbar), Abfragen mit
//   where('updated', '>=', Timestamp) liefern nur passende Dokumente
// - Lesezugriffe werden wie bei Firebase gezählt: erster Stand = Zahl der gelieferten Dokumente (mindestens 1),
//   danach 1 je geändertem Dokument, das zur Abfrage passt
// - der Datenbestand bleibt über ein Neuladen der Seite erhalten (sessionStorage), wie bei einem Server
// - FAKE.mute = true: Änderungen gehen an keine Live-Verbindung, wie bei einem Gerät, das gerade zu ist
(() => {
  const PKEY = '__fakefb_store';
  const store = new Map(); const listeners = new Set(); let reads = 0; const writes = [];
  const clone = o => o === undefined ? undefined : JSON.parse(JSON.stringify(o));
  const AU = '__arrayUnion', ST = '__serverTimestamp', TS = '__ts';
  const clock = {skew: 0, last: 0, now(){ const t = Math.max(Date.now() + this.skew, this.last + 1); this.last = t; return t; }};
  class Timestamp { constructor(ms){ this.ms = ms; } toMillis(){ return this.ms; } static fromMillis(ms){ return new Timestamp(ms); } }
  const tsOut = v => v && typeof v === 'object' && TS in v ? new Timestamp(v[TS]) : v;
  const out = o => { if (!o) return o; const c = clone(o); for (const k of Object.keys(c)) c[k] = tsOut(c[k]); return c; };
  const persist = () => { try { sessionStorage.setItem(PKEY, JSON.stringify([...store.entries()])); } catch(e) {} };
  const ref = (path) => ({path, id: path.split('/').pop(), type: path.split('/').length % 2 ? 'col' : 'doc'});
  const doc = (base, ...segs) => {
    let p = base && base.path ? base.path : '';
    if (base && base.path && base.type === 'col' && segs.length === 0) segs = [Math.random().toString(36).slice(2, 12)];
    p = [p, ...segs].filter(Boolean).join('/'); return ref(p);
  };
  const collection = (base, ...segs) => ref([base && base.path ? base.path : '', ...segs].filter(Boolean).join('/'));
  const childrenOf = col => [...store.keys()].filter(k => k.startsWith(col + '/') && k.split('/').length === col.split('/').length + 1);
  const cmp = (a, b) => (a && a[TS] != null ? a[TS] : a) - (b instanceof Timestamp ? b.ms : b);
  const matches = (d, conds) => (conds || []).every(({field, op, val}) => {
    const v = d[field];
    if (op === 'array-contains') return (v || []).includes(val);
    if (val instanceof Timestamp && !(v && typeof v === 'object' && TS in v)) return false;   // andere Typen passen nie
    if (op === '>=') return v != null && cmp(v, val) >= 0;
    if (op === '>') return v != null && cmp(v, val) > 0;
    if (op === '==') return v === val;
    return false;
  });
  const meta = {fromCache: false, hasPendingWrites: false};
  const docSnap = (path) => ({id: path.split('/').pop(), exists: () => store.has(path), data: () => out(store.get(path)), metadata: meta});
  const qIds = q => childrenOf(q.path).filter(k => matches(store.get(k), q.conds));
  const qSnap = q => { const ids = qIds(q); return {empty: !ids.length, docs: ids.map(docSnap), metadata: {fromCache: false}}; };
  const notify = (path) => { if (window.FAKE && window.FAKE.mute) return; for (const l of listeners) { if (l.path === path || path.startsWith(l.path + '/') && l.type === 'col' && path.split('/').length === l.path.split('/').length + 1) setTimeout(() => l.fire(), 5); } };
  const resolve = (v) => {
    if (v && v[ST]) return {[TS]: clock.now()};
    return clone(v);
  };
  const applyFields = (cur, fields) => {
    const o = clone(cur);
    for (const [k, v] of Object.entries(fields)) {
      const parts = k.split('.'); let t = o; for (const p of parts.slice(0, -1)) t = t[p] = t[p] || {};
      const last = parts[parts.length - 1];
      if (v && v[AU]) { const arr = t[last] || []; for (const x of v[AU]) if (!arr.some(y => JSON.stringify(y) === JSON.stringify(x))) arr.push(x); t[last] = arr; }
      else t[last] = resolve(v);
    }
    return o;
  };
  const set = (r, d) => { const o = {}; for (const [k, v] of Object.entries(d)) o[k] = resolve(v); store.set(r.path, o); writes.push(['set', r.path]); persist(); notify(r.path); };
  const update = (r, f) => { if (!store.has(r.path)) { const e = new Error('not-found'); e.code = 'not-found'; throw e; } store.set(r.path, applyFields(store.get(r.path), f)); writes.push(['update', r.path, Object.keys(f)]); persist(); notify(r.path); };
  const del = (r) => { store.delete(r.path); writes.push(['delete', r.path]); persist(); notify(r.path); };
  const F = {
    db: {path: ''}, auth: {currentUser: null},
    signInAnonymously: async () => {}, signOut: async () => {},
    onAuthStateChanged: (a, cb) => { setTimeout(() => { F.auth.currentUser = {uid: window.FAKE_UID}; cb(F.auth.currentUser); }, 10); },
    doc, collection, Timestamp,
    serverTimestamp: () => ({[ST]: true}),
    getDoc: async r => { reads++; return docSnap(r.path); },
    getDocs: async q => { const s = qSnap(q); reads += Math.max(1, s.docs.length); return s; },
    setDoc: async (r, d) => set(r, d), updateDoc: async (r, f) => update(r, f), deleteDoc: async r => del(r),
    query: (col, ...conds) => ({...col, conds: [...(col.conds || []), ...conds]}),
    where: (field, op, val) => ({field, op, val}),
    arrayUnion: (...xs) => ({[AU]: xs}),
    writeBatch: () => { const ops = []; return {set: (r, d) => ops.push(() => set(r, d)), update: (r, f) => ops.push(() => update(r, f)), delete: r => ops.push(() => del(r)), commit: async () => ops.forEach(f => f())}; },
    onSnapshot: (r, cb, err) => {
      // Gemerkt wird der zuletzt gelieferte Stand, damit nur Änderungen als Lesezugriff zählen
      let last = null;
      const l = {path: r.path, type: r.type, fire: () => {
        if (r.type === 'doc') {
          const cur = JSON.stringify(store.get(r.path) || null);
          if (last === cur) return;
          reads++; last = cur; cb(docSnap(r.path)); return;
        }
        const ids = qIds(r), now = new Map(ids.map(k => [k, JSON.stringify(store.get(k))]));
        let changed = 0;
        for (const [k, v] of now) if (!last || last.get(k) !== v) changed++;
        const removed = last ? [...last.keys()].some(k => !now.has(k)) : false;
        if (last && !changed && !removed) return;
        reads += last ? changed : Math.max(1, changed);
        last = now; cb(qSnap(r));
      }};
      listeners.add(l); setTimeout(() => l.fire(), 5); return () => listeners.delete(l);
    }
  };
  window.HFB = F;
  window.FAKE = {store, writes, clock, reads: () => reads, resetReads: () => { reads = 0; writes.length = 0; },
    seed: (obj) => { for (const [k, v] of Object.entries(obj)) store.set(k, clone(v)); persist(); },
    remoteSet: (path, d) => set(ref(path), d), remoteUpdate: (path, f) => update(ref(path), f), remoteDelete: path => del(ref(path)),
    get: p => out(store.get(p)), ts: v => v && v[TS]};
  let restored = false;
  try { const raw = sessionStorage.getItem(PKEY); if (raw) { for (const [k, v] of JSON.parse(raw)) store.set(k, v); restored = true; } } catch(e) {}
  if (!restored && window.FAKE_SEED) window.FAKE.seed(window.FAKE_SEED);
})();

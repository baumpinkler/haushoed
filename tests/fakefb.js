(() => {
  const store = new Map(); const listeners = new Set(); let reads = 0; const writes = [];
  const clone = o => o === undefined ? undefined : JSON.parse(JSON.stringify(o));
  const AU = '__arrayUnion';
  const ref = (path) => ({path, id: path.split('/').pop(), type: path.split('/').length % 2 ? 'col' : 'doc'});
  const doc = (base, ...segs) => {
    let p = base && base.path ? base.path : '';
    if (base && base.path && base.type === 'col' && segs.length === 0) segs = [Math.random().toString(36).slice(2, 12)];
    p = [p, ...segs].filter(Boolean).join('/'); return ref(p);
  };
  const collection = (base, ...segs) => ref([base && base.path ? base.path : '', ...segs].filter(Boolean).join('/'));
  const childrenOf = col => [...store.keys()].filter(k => k.startsWith(col + '/') && k.split('/').length === col.split('/').length + 1);
  const docSnap = (path) => ({id: path.split('/').pop(), exists: () => store.has(path), data: () => clone(store.get(path)), metadata: {fromCache: false}});
  const qSnap = (col, filter) => { const ids = childrenOf(col).filter(k => !filter || filter(store.get(k))); return {empty: !ids.length, docs: ids.map(docSnap), metadata: {fromCache: false}}; };
  const notify = (path) => { for (const l of listeners) { if (l.path === path || path.startsWith(l.path + '/') && l.type === 'col' && path.split('/').length === l.path.split('/').length + 1) setTimeout(() => l.fire(), 5); } };
  const applyFields = (cur, fields) => {
    const o = clone(cur);
    for (const [k, v] of Object.entries(fields)) {
      const parts = k.split('.'); let t = o; for (const p of parts.slice(0, -1)) t = t[p] = t[p] || {};
      const last = parts[parts.length - 1];
      if (v && v[AU]) { const arr = t[last] || []; for (const x of v[AU]) if (!arr.some(y => JSON.stringify(y) === JSON.stringify(x))) arr.push(x); t[last] = arr; }
      else t[last] = clone(v);
    }
    return o;
  };
  const set = (r, d) => { store.set(r.path, clone(d)); writes.push(['set', r.path]); notify(r.path); };
  const update = (r, f) => { if (!store.has(r.path)) { const e = new Error('not-found'); e.code = 'not-found'; throw e; } store.set(r.path, applyFields(store.get(r.path), f)); writes.push(['update', r.path, Object.keys(f)]); notify(r.path); };
  const del = (r) => { store.delete(r.path); writes.push(['delete', r.path]); notify(r.path); };
  const F = {
    db: {path: ''}, auth: {currentUser: null},
    signInAnonymously: async () => {}, signOut: async () => {},
    onAuthStateChanged: (a, cb) => { setTimeout(() => { F.auth.currentUser = {uid: window.FAKE_UID}; cb(F.auth.currentUser); }, 10); },
    doc, collection,
    getDoc: async r => { reads++; return docSnap(r.path); },
    getDocs: async q => { const s = qSnap(q.path, q.filter); reads += Math.max(1, s.docs.length); return s; },
    setDoc: async (r, d) => set(r, d), updateDoc: async (r, f) => update(r, f), deleteDoc: async r => del(r),
    query: (col, w) => ({...col, filter: w}), where: (field, op, val) => d => (d[field] || []).includes(val),
    arrayUnion: (...xs) => ({[AU]: xs}),
    writeBatch: () => { const ops = []; return {set: (r, d) => ops.push(() => set(r, d)), update: (r, f) => ops.push(() => update(r, f)), delete: r => ops.push(() => del(r)), commit: async () => ops.forEach(f => f())}; },
    onSnapshot: (r, cb, err) => {
      const l = {path: r.path, type: r.type, first: true, fire: () => {
        if (r.type === 'doc') { if (l.first) reads++; cb(docSnap(r.path)); }
        else { const s = qSnap(r.path); if (l.first) reads += Math.max(1, s.docs.length); cb(s); }
        l.first = false;
      }};
      listeners.add(l); setTimeout(() => l.fire(), 5); return () => listeners.delete(l);
    }
  };
  window.HFB = F;
  window.FAKE = {store, writes, reads: () => reads, seed: (obj) => { for (const [k, v] of Object.entries(obj)) store.set(k, clone(v)); }, remoteUpdate: (path, f) => update(ref(path), f), get: p => clone(store.get(p))};
  if (window.FAKE_SEED) window.FAKE.seed(window.FAKE_SEED);
})();

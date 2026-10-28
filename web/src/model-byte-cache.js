// Keep one verified public campus model. A release change replaces the record;
// unavailable/private/full browser storage always falls back to the network.
const DATABASE = 'lsemap-model-bytes';
const STORE = 'current-model';
const SLOT = 'campus';

async function withStore(mode, operation) {
  if (typeof indexedDB === 'undefined') return null;
  return new Promise(resolve => {
    let finished = false, database;
    const finish = value => {
      if (finished) return;
      finished = true; clearTimeout(timer); database?.close(); resolve(value);
    };
    const timer = setTimeout(() => finish(null), 800);
    let request;
    try { request = indexedDB.open(DATABASE, 1); }
    catch { finish(null); return; }
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onerror = request.onblocked = () => finish(null);
    request.onsuccess = () => {
      database = request.result;
      if (finished) { database.close(); return; }
      try {
        const transaction = database.transaction(STORE, mode);
        const result = operation(transaction.objectStore(STORE));
        let value = null;
        result.onsuccess = () => { value = result.result ?? true; };
        transaction.oncomplete = () => finish(value);
        transaction.onerror = transaction.onabort = () => finish(null);
      } catch { finish(null); }
    };
  });
}

export const campusByteCache = {
  async read(sha256) {
    const record = await withStore('readonly', store => store.get(SLOT));
    if (record?.sha256 !== sha256) return null;
    if (record.buffer instanceof ArrayBuffer) return record.buffer;
    if (!(record.blob instanceof Blob)) return null;
    // IndexedDB clones only the Blob handle. Read binary bytes outside its
    // transaction, avoiding a second 50MB structured clone on the main thread.
    return record.blob.arrayBuffer();
  },
  async write(sha256, bytes) {
    // Small overviews use binary records on WebKit, which can reject Blob writes.
    // Keep large desktop models file-backed to avoid a50MB structured clone.
    const record = bytes.byteLength <= 16*1024*1024
      ? {sha256,buffer:bytes}
      : {sha256,blob:new Blob([bytes], {type:'model/gltf-binary'})};
    await withStore('readwrite', store => store.put(record, SLOT));
  },
};

export function persistCampusBytes(cache, sha256, bytes, signal) {
  // Deferred storage serialization never blocks the download promise.
  const persist = () => {
    if (!signal?.aborted) Promise.resolve(cache.write(sha256, bytes)).catch(() => {});
  };
  setTimeout(() => {
    if (signal?.aborted) return;
    if (typeof requestIdleCallback === 'function') requestIdleCallback(persist, {timeout:1500});
    else persist();
  }, 2500);
}

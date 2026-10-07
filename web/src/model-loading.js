/** A progressing download has no fixed deadline. Decoding has its own budget. */
export function loadModelInStages(download, decode, {
  signal,
  onProgress,
  cancelDownload = () => {},
  discardModel = () => {},
  idleTimeout = 45000,
  decodeTimeout = 90000,
} = {}) {
  return new Promise((resolve, reject) => {
    let timer;
    let settled = false;
    let loaded = 0;
    let phase = "download";
    const cleanup = () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      cleanup();
      cancelDownload();
      reject(error);
    };
    const abort = () => fail(signal.reason || new DOMException("Model load cancelled", "AbortError"));
    const arm = (milliseconds, message) => {
      clearTimeout(timer);
      timer = setTimeout(() => fail(new Error(message)), milliseconds);
    };
    if (signal?.aborted) { abort(); return; }
    signal?.addEventListener("abort", abort, { once: true });
    arm(idleTimeout, "Model download stalled");
    const progress = (event) => {
      if (settled || phase !== "download") return;
      if (event.loaded > loaded) {
        loaded = event.loaded;
        arm(idleTimeout, "Model download stalled");
      }
      onProgress?.(event);
    };
    Promise.resolve().then(() => settled ? undefined : download(progress)).then(async (bytes) => {
      if (settled) return;
      phase = "decode";
      arm(decodeTimeout, "Model decoding timed out");
      const model = await decode(bytes);
      if (settled) { discardModel(model); return; }
      settled = true;
      cleanup();
      resolve(model);
    }).catch(fail);
  });
}

/** Validate complete GLB bytes before decoding; retry transport failures once. */
export async function downloadVerifiedModel(url, {
  signal, onProgress, expectedSha256, fetchModel = fetch,
} = {}) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      signal?.throwIfAborted();
      const response = await fetchModel(url, {signal, cache: attempt ? 'reload' : 'default'});
      if (!response.ok) throw new Error(`Model request failed: HTTP${response.status}`);
      const chunks = [];
      let loaded = 0;
      const total = Number(response.headers.get('Content-Length')) || 0;
      const reader = response.body?.getReader();
      if (reader) {
        try {
          for (;;) {
            const {done, value} = await reader.read();
            if (done) break;
            chunks.push(value); loaded += value.byteLength;
            onProgress?.({loaded, total, lengthComputable: total > 0});
          }
        } catch (error) {
          await reader.cancel(error).catch(() => {});
          throw error;
        } finally { reader.releaseLock(); }
      } else {
        const bytes = new Uint8Array(await response.arrayBuffer());
        chunks.push(bytes); loaded = bytes.byteLength;
        onProgress?.({loaded, total, lengthComputable: total > 0});
      }
      signal?.throwIfAborted();
      const bytes = new Uint8Array(loaded);
      let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
      const header = new DataView(bytes.buffer);
      const valid = loaded >= 20 && header.getUint32(0, true) === 0x46546c67
        && header.getUint32(4, true) === 2 && header.getUint32(8, true) === loaded;
      const etag = response.headers.get('ETag')?.replace(/^W\//, '').replaceAll('"', '');
      const expected = expectedSha256 || (/^[a-f0-9]{64}$/i.test(etag || '') ? etag : null);
      let matches = true;
      if (expected) {
        const digest = await crypto.subtle.digest('SHA-256', bytes);
        const actual = [...new Uint8Array(digest)].map(n => n.toString(16).padStart(2, '0')).join('');
        matches = actual === expected.toLowerCase();
      }
      if (!valid || !matches) {
        const error = new Error('Model download failed integrity validation');
        error.name = 'ModelIntegrityError';
        throw error;
      }
      return bytes.buffer;
    } catch (error) {
      signal?.throwIfAborted();
      if (attempt || !['TypeError', 'ModelIntegrityError'].includes(error.name)) throw error;
    }
  }
}

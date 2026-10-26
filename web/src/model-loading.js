import {throwIfAborted} from "./abort-utils.js";
import {campusByteCache, persistCampusBytes} from "./model-byte-cache.js";

/** A progressing download has no fixed deadline. Decoding has its own budget. */
export function loadModelInStages(download, decode, {
  signal,
  onProgress,
  cancelDownload = () => {},
  beforeDecode,
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
    const abort = () => {
      try { throwIfAborted(signal); } catch (error) { fail(error); }
    };
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
      // Downloading may finish during a gesture. Give navigation priority before
      // GLTF parsing starts; waiting is neither a stalled transfer nor decoding.
      clearTimeout(timer);
      phase = "waiting";
      if (beforeDecode) await beforeDecode();
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
  signal, onProgress, expectedSha256, fetchModel = fetch, priority = "auto",
} = {}) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      throwIfAborted(signal);
      const response = await fetchModel(url, {signal, cache: attempt ? 'reload' : 'default', priority});
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
      throwIfAborted(signal);
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
      throwIfAborted(signal);
      if (attempt || !['TypeError', 'ModelIntegrityError'].includes(error.name)) throw error;
    }
  }
}

/** Download lossless compressed campus segments concurrently into the final GLB. */
export async function downloadCampusModel(url, options = {}) {
  const {signal, onProgress, fetchModel = fetch, priority = "high",
    supportsCompression = typeof DecompressionStream === 'function',
    byteCache = campusByteCache} = options;
  const query = url.includes('?') ? url.slice(url.indexOf('?')) : '';
  throwIfAborted(signal);
  const response = await fetchModel('/models/campus-parts.json' + query, {signal, cache:'no-cache', priority});
  // Development serves the original GLB without the release-only segment index.
  if (response.status === 404 || response.headers.get('Content-Type')?.includes('text/html'))
    return downloadVerifiedModel(url, options);
  if (!response.ok) throw new Error(`Campus index request failed: HTTP${response.status}`);
  const manifest = await response.json();
  const validHash = value => /^[a-f0-9]{64}$/.test(value || '');
  const validCompression = part => !part.compressed || (
    part.compressed.encoding === 'gzip' &&
    /^\/models\/campus-\d+-[a-f0-9]{12}\.bin\.gz$/.test(part.compressed.path) &&
    Number.isSafeInteger(part.compressed.bytes) && part.compressed.bytes > 0 &&
    part.compressed.bytes < 25 * 1024 * 1024 && validHash(part.compressed.sha256)
  );
  if (!Number.isSafeInteger(manifest.bytes) || manifest.bytes < 20 ||
      !validHash(manifest.sha256) || !Array.isArray(manifest.parts) || !manifest.parts.length ||
      manifest.parts.length > 4 || manifest.parts.some(part =>
        !/^\/models\/campus-\d+-[a-f0-9]{12}\.bin$/.test(part.path) ||
        !Number.isSafeInteger(part.bytes) || part.bytes <= 0 ||
        !validHash(part.sha256) || !validCompression(part)) ||
      manifest.parts.reduce((sum,part) => sum+part.bytes,0) !== manifest.bytes)
    throw new Error('Invalid campus segment index');

  const digest = async data => [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))]
    .map(value => value.toString(16).padStart(2, '0')).join('');
  const validHeader = buffer => {
    if (!(buffer instanceof ArrayBuffer) || buffer.byteLength !== manifest.bytes) return false;
    const header = new DataView(buffer);
    return header.getUint32(0, true) === 0x46546c67 && header.getUint32(4, true) === 2 &&
      header.getUint32(8, true) === manifest.bytes;
  };
  // The fresh index selects the cache by content hash, never by a mutable URL.
  let cached;
  try { cached = await byteCache?.read(manifest.sha256); } catch { /* Network fallback. */ }
  throwIfAborted(signal);
  if (validHeader(cached) && await digest(cached) === manifest.sha256) {
    throwIfAborted(signal);
    onProgress?.({loaded:manifest.bytes, total:manifest.bytes, lengthComputable:true});
    return cached;
  }
  const bytes = new Uint8Array(manifest.bytes);
  const controller = new AbortController();
  const abort = () => {
    try { throwIfAborted(signal); } catch (error) { controller.abort(error); }
  };
  throwIfAborted(signal);
  signal?.addEventListener('abort',abort,{once:true});
  const received = manifest.parts.map(() => 0);
  let offset = 0;
  const reportProgress = () => onProgress?.({
    loaded:received.reduce((sum,size)=>sum+size,0), total:manifest.bytes, lengthComputable:true,
  });

  async function readSegment(part, index, begin, compressed) {
    throwIfAborted(controller.signal);
    const result = await fetchModel(compressed ? part.compressed.path : part.path,
      {signal:controller.signal, priority});
    if (!result.ok) throw new Error(`Campus segment request failed: HTTP${result.status}`);
    let stream = result.body;
    if (!stream) stream = new Blob([await result.arrayBuffer()]).stream();
    // Some static hosts advertise HTTP gzip. Fetch already decodes that body;
    // decode manually only when the host serves the compressed file as raw bytes.
    const decodedByFetch = /\bgzip\b/i.test(result.headers.get('Content-Encoding') || '');
    if (compressed && !decodedByFetch)
      stream = stream.pipeThrough(new DecompressionStream('gzip'));
    const reader = stream.getReader();
    received[index] = 0;
    try {
      for (;;) {
        const {done,value} = await reader.read();
        if (done) break;
        throwIfAborted(controller.signal);
        if (received[index]+value.byteLength > part.bytes)
          throw new Error('Campus segment length mismatch');
        bytes.set(value,begin+received[index]);
        received[index] += value.byteLength;
        reportProgress();
      }
      if (received[index] !== part.bytes ||
          await digest(bytes.subarray(begin,begin+part.bytes)) !== part.sha256)
        throw new Error('Campus segment integrity mismatch');
    } catch (error) {
      await reader.cancel(error).catch(()=>{});
      throw error;
    } finally { reader.releaseLock(); }
  }

  try {
    await Promise.all(manifest.parts.map((part,index) => {
      const begin = offset;
      offset += part.bytes;
      return (async () => {
        if (!supportsCompression || !part.compressed)
          return readSegment(part,index,begin,false);
        try { await readSegment(part,index,begin,true); }
        catch (error) {
          // A failed compressed transport can retry the identical raw segment.
          // Cancellation still stops the complete load, including sibling streams.
          throwIfAborted(controller.signal);
          received[index] = 0;
          await readSegment(part,index,begin,false);
        }
      })();
    }));
    throwIfAborted(signal);
    const header = new DataView(bytes.buffer);
    if (header.getUint32(0,true) !== 0x46546c67 || header.getUint32(4,true) !== 2 ||
        header.getUint32(8,true) !== bytes.length || await digest(bytes) !== manifest.sha256)
      throw new Error('Campus model integrity mismatch');
    if (byteCache) persistCampusBytes(byteCache, manifest.sha256, bytes.buffer, signal);
    return bytes.buffer;
  } catch (error) { controller.abort(error); throw error; }
  finally { signal?.removeEventListener('abort',abort); }
}

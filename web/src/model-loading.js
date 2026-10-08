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

/** Fetch the published campus segments concurrently into one final buffer. */
export async function downloadCampusModel(url, options = {}) {
  const {signal, onProgress, fetchModel = fetch} = options;
  const query = url.includes('?') ? url.slice(url.indexOf('?')) : '';
  const response = await fetchModel('/models/campus-parts.json' + query, {signal, cache:'no-cache'});
  // Development serves the original GLB without the release-only segment index.
  if (response.status === 404 || response.headers.get('Content-Type')?.includes('text/html')) return downloadVerifiedModel(url, options);
  if (!response.ok) throw new Error(`Campus index request failed: HTTP${response.status}`);
  const manifest = await response.json();
  const validHash = value => /^[a-f0-9]{64}$/.test(value || '');
  if (!Number.isSafeInteger(manifest.bytes) || manifest.bytes < 20 ||
      !validHash(manifest.sha256) || !Array.isArray(manifest.parts) || !manifest.parts.length ||
      manifest.parts.length > 4 || manifest.parts.some(p => !/^\/models\/campus-\d+-[a-f0-9]{12}\.bin$/.test(p.path) || !Number.isSafeInteger(p.bytes) || p.bytes <= 0 || !validHash(p.sha256)) ||
      manifest.parts.reduce((n,p) => n+p.bytes,0) !== manifest.bytes) throw new Error('Invalid campus segment index');
  const bytes = new Uint8Array(manifest.bytes);
  const controller = new AbortController();
  const abort = () => controller.abort(signal.reason);
  signal?.throwIfAborted();signal?.addEventListener('abort',abort,{once:true});
  const digest = async data => [...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(n=>n.toString(16).padStart(2,'0')).join('');
  let offset=0,loaded=0;
  try {
    const tasks=manifest.parts.map(part=>{
      const begin=offset;offset+=part.bytes;
      return (async()=>{
        const result=await fetchModel(part.path,{signal:controller.signal});
        if (!result.ok) throw new Error(`Campus segment request failed: HTTP${result.status}`);
        let received=0;const reader=result.body?.getReader();
        const append=value=>{
          if(received+value.byteLength>part.bytes)throw new Error('Campus segment length mismatch');
          bytes.set(value,begin+received);received+=value.byteLength;loaded+=value.byteLength;
          onProgress?.({loaded,total:manifest.bytes,lengthComputable:true});
        };
        if(reader){
          try{for(;;){const {done,value}=await reader.read();if(done)break;append(value);}}
          catch(error){await reader.cancel(error).catch(()=>{});throw error;}
          finally{reader.releaseLock();}
        }else append(new Uint8Array(await result.arrayBuffer()));
        if(received!==part.bytes || await digest(bytes.subarray(begin,begin+received))!==part.sha256)throw new Error('Campus segment integrity mismatch');
      })();
    });
    await Promise.all(tasks);signal?.throwIfAborted();
    const header=new DataView(bytes.buffer);
    if(header.getUint32(0,true)!==0x46546c67 || header.getUint32(4,true)!==2 || header.getUint32(8,true)!==bytes.length || await digest(bytes)!==manifest.sha256)throw new Error('Campus model integrity mismatch');
    return bytes.buffer;
  }catch(error){controller.abort(error);throw error;}
  finally{signal?.removeEventListener('abort',abort);}
}

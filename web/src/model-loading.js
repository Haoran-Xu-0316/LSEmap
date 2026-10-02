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

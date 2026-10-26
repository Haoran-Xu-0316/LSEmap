/** Resource limits follow the device, not portrait or landscape viewport width. */
export function deviceBudget(environment = globalThis) {
  const navigator = environment.navigator ?? {};
  const coarsePointer = environment.matchMedia?.('(pointer: coarse)').matches ?? false;
  const userAgent = navigator.userAgent ?? '';
  const ios = /iPhone|iPad|iPod/.test(userAgent) ||
    (/Macintosh/.test(userAgent) && navigator.maxTouchPoints > 1);
  const mobile = ios || (coarsePointer && navigator.maxTouchPoints > 0);
  return Object.freeze({
    mobile,
    shadowSize: mobile ? 1024 : 4096,
    decoderWorkers: mobile ? 1 : Math.min(4, Math.max(2, navigator.hardwareConcurrency || 2)),
    exteriorLimit: mobile ? 2 : Infinity,
    pixelRatio: mobile ? 1.75 : 1.5,
  });
}

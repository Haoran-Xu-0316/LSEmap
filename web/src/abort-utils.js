// AbortController is available on older WebKit releases that lack the newer
// AbortSignal helpers. Keep cancellation and listener ownership explicit.
const combinedReasons = new WeakMap();

function abortReason(signal) {
  if (combinedReasons.has(signal)) return combinedReasons.get(signal);
  if (signal.reason !== undefined) return signal.reason;
  return new DOMException('The operation was aborted.', 'AbortError');
}

export function throwIfAborted(signal) {
  if (signal?.aborted) throw abortReason(signal);
}

/** Follow the first cancelled source until cancellation or explicit disposal. */
export function combineAbortSignals(signals) {
  const controller = new AbortController();
  const listeners = new Map();
  const dispose = () => {
    for (const [signal, listener] of listeners)
      signal.removeEventListener('abort', listener);
    listeners.clear();
  };
  const cancel = source => {
    if (controller.signal.aborted) return;
    const reason = abortReason(source);
    combinedReasons.set(controller.signal, reason);
    dispose();
    controller.abort(reason);
  };
  for (const source of new Set(signals.filter(Boolean))) {
    if (source.aborted) { cancel(source); break; }
    const listener = () => cancel(source);
    listeners.set(source, listener);
    source.addEventListener('abort', listener, {once:true});
    // A custom signal can cancel while its listener is being registered.
    if (source.aborted) cancel(source);
    if (controller.signal.aborted) break;
  }
  return {signal:controller.signal, dispose};
}

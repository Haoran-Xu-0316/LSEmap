import {combineAbortSignals, throwIfAborted} from './abort-utils.js';

/** Bound headers and JSON-body loading without requiring newer iOS abort APIs. */
export async function fetchStartupJson(url, {
  signal, timeout = 8000, attempts = 2, fetchResource = fetch,
} = {}) {
  for (let attempt = 0; attempt < attempts; attempt++) {
    throwIfAborted(signal);
    const deadline = new AbortController();
    const cancellation = combineAbortSignals([signal, deadline.signal]);
    const timer = setTimeout(() => deadline.abort(new Error('Startup request timed out')), timeout);
    try {
      const response = await fetchResource(url, {
        signal: cancellation.signal, cache: attempt ? 'reload' : 'no-cache',
      });
      if (!response.ok) {
        const error = new Error(`Startup request failed: HTTP${response.status}`);
        error.retryable = response.status === 408 || response.status === 429 || response.status >= 500;
        throw error;
      }
      const result = await response.json();
      throwIfAborted(cancellation.signal);
      return result;
    } catch (error) {
      throwIfAborted(signal);
      if (attempt + 1 === attempts || error.retryable === false) throw error;
    } finally {
      clearTimeout(timer);
      cancellation.dispose();
    }
  }
}

/** Gallery hashes are optional at startup; the catalogue is required for 3D. */
export async function loadStartupMetadata({signal} = {}) {
  const gallery = fetchStartupJson('/gallery-manifest.json', {
    signal, timeout: 2000, attempts: 1,
  }).catch(() => null);
  const catalogue = await fetchStartupJson('/models/catalogue.json', {signal});
  const manifest = await gallery;
  throwIfAborted(signal);
  return {catalogue, gallery: manifest};
}

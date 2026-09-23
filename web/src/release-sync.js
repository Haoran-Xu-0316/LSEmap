/** Refresh long-lived tabs when their entry bundle no longer matches the server. */
export function startReleaseSync() {
  const script = document.querySelector('script[type="module"][src]');
  if (!script) return;
  const current = new URL(script.src, location.href).pathname;
  // Vite development modules are live-reloaded by Vite itself.
  if (!current.startsWith('/assets/')) return;
  let stopped = false;
  let pending = false;
  let lastCheck = 0;
  async function check() {
    if (stopped || pending || document.visibilityState !== 'visible' || Date.now() - lastCheck < 5000) return;
    pending = true;
    lastCheck = Date.now();
    try {
      const response = await fetch('/release.json', { cache: 'no-store' });
      if (!response.ok) return;
      const release = await response.json();
      const next = release.entryScript;
      if (stopped || typeof next !== 'string' || !/^\/assets\/[\w.-]+\.js$/.test(next) || next === current) return;
      // A transient CDN mismatch must not trap the visitor in a reload loop.
      const key = 'lsemap-release-reload';
      const previous = JSON.parse(sessionStorage.getItem(key) || 'null');
      if (previous?.entry === next && Date.now() - previous.at < 60000) return;
      sessionStorage.setItem(key, JSON.stringify({ entry: next, at: Date.now() }));
      location.reload(); // Keep the current building hash and URL.
    } catch {
      // Offline and temporarily unavailable manifests leave exploration intact.
    } finally {
      pending = false;
    }
  }
  const timer = setInterval(check, 60000);
  window.addEventListener('focus', check);
  document.addEventListener('visibilitychange', check);
  window.addEventListener('pagehide', () => {
    stopped = true;
    clearInterval(timer);
    window.removeEventListener('focus', check);
    document.removeEventListener('visibilitychange', check);
  }, { once: true });
  check();
}

/** Cancel obsolete transfers, share current requests and retain a bounded cache. */
export class ModelCache {
  constructor(load, prepare, dispose, limit = 3) {
    Object.assign(this, {load, prepare, disposeModel: dispose, limit});
    this.models = new Map();
    this.pending = new Map();
    this.queue = [];
    this.activeKey = null;
    this.activeLoad = null;
    this.closed = false;
  }

  activate(key) {
    this.activeKey = key;
    for (const [pendingKey, request] of this.pending) {
      if (pendingKey === key) continue;
      const reason = new DOMException('Selection changed', 'AbortError');
      request.controller.abort(reason);
      request.reject(reason);
      this.pending.delete(pendingKey);
      if (this.activeLoad === request) this.activeLoad = null;
    }
    this.queue = this.queue.filter(queued => queued === key);
    this.trim();
  }

  request(key, url) {
    if (this.closed) return Promise.reject(new Error('Model cache disposed'));
    this.activate(key);
    if (this.models.has(key)) {
      const model = this.models.get(key);
      this.models.delete(key);
      this.models.set(key, model);
      return Promise.resolve(model);
    }
    if (this.pending.has(key)) return this.pending.get(key).promise;
    let resolve, reject;
    const promise = new Promise((done, fail) => { resolve = done; reject = fail; });
    this.pending.set(key, {key, url, promise, resolve, reject, controller: new AbortController()});
    this.queue.push(key);
    void this.drain();
    return promise;
  }

  async drain() {
    if (this.activeLoad || this.closed || !this.queue.length) return;
    const key = this.queue.shift();
    const request = this.pending.get(key);
    if (!request) { void this.drain(); return; }
    this.activeLoad = request;
    let model;
    try {
      model = await this.load(request.url, request.controller.signal);
      request.controller.signal.throwIfAborted();
      if (this.closed) throw new Error('Model cache disposed');
      this.prepare(model);
      this.models.set(key, model);
      this.trim();
      request.resolve(model);
    } catch (error) {
      if (model && this.models.get(key) !== model) this.disposeModel(model);
      request.reject(error);
    } finally {
      // A -> B -> A can start a new A while the first decoder finishes late.
      // Only the owning job may remove its pending record or release the slot.
      if (this.pending.get(key) === request) this.pending.delete(key);
      if (this.activeLoad === request) {
        this.activeLoad = null;
        void this.drain();
      }
    }
  }

  trim() {
    for (const [key, model] of this.models) {
      if (this.models.size <= this.limit) break;
      if (key === this.activeKey) continue;
      this.models.delete(key);
      this.disposeModel(model);
    }
  }

  hideAll() {
    for (const model of this.models.values()) model.visible = false;
  }

  dispose() {
    this.closed = true;
    this.activate(null);
    for (const model of this.models.values()) this.disposeModel(model);
    this.models.clear();
  }
}

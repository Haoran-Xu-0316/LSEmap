/** One download at a time, stale queued work cancelled, and a bounded model cache. */
export class ModelCache {
  constructor(load, prepare, dispose, limit = 3) {
    Object.assign(this, { load, prepare, disposeModel: dispose, limit });
    this.models = new Map();
    this.pending = new Map();
    this.queue = [];
    this.activeKey = null;
    this.loading = false;
    this.closed = false;
  }

  activate(key) {
    this.activeKey = key;
    for (const queued of this.queue) {
      if (queued === key) continue;
      this.pending.get(queued)?.reject(new DOMException("Selection changed", "AbortError"));
      this.pending.delete(queued);
    }
    this.queue = this.queue.filter((queued) => queued === key);
    this.trim();
  }

  request(key, url) {
    if (this.closed) return Promise.reject(new Error("Model cache disposed"));
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
    this.pending.set(key, { promise, resolve, reject, url });
    this.queue.push(key);
    this.drain();
    return promise;
  }

  async drain() {
    if (this.loading || this.closed || !this.queue.length) return;
    const key = this.queue.shift();
    const request = this.pending.get(key);
    this.loading = true;
    let model;
    try {
      model = await this.load(request.url);
      if (this.closed) throw new Error("Model cache disposed");
      this.prepare(model);
      this.models.set(key, model);
      this.trim();
      request.resolve(model);
    } catch (error) {
      if (model && !this.models.has(key)) this.disposeModel(model);
      request.reject(error);
    } finally {
      this.pending.delete(key);
      this.loading = false;
      this.drain();
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

import test from 'node:test';
import assert from 'node:assert/strict';
import {ModelCache} from '../src/model-cache.js';

const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise,resolve};
};
const tick = () => new Promise(resolve => setImmediate(resolve));

function fixture(limit = 2) {
  const jobs = [], prepared = [], disposed = [];
  const cache = new ModelCache((url, signal) => {
    const gate = deferred();
    jobs.push({url,signal,...gate});
    // Deliberately ignore cancellation to model a decoder already running.
    return gate.promise;
  },model=>prepared.push(model),model=>disposed.push(model),limit);
  return {cache,jobs,prepared,disposed};
}

test('a new selection starts immediately and late obsolete geometry is released', async () => {
  const {cache,jobs,prepared,disposed} = fixture();
  const first = cache.request('A','/a.glb');
  const rejected = assert.rejects(first,{name:'AbortError'});
  const second = cache.request('B','/b.glb');
  assert.equal(jobs.length,2);
  assert.equal(jobs[0].signal.aborted,true);
  const b = {name:'B'}; jobs[1].resolve(b);
  assert.equal(await second,b);
  const a = {name:'A'}; jobs[0].resolve(a);
  await rejected; await tick();
  assert.deepEqual(prepared,[b]); assert.deepEqual(disposed,[a]);
  assert.equal(cache.models.has('A'),false);
  cache.dispose();
});

test('A to B to A cannot let the first A delete or replace the current request', async () => {
  const {cache,jobs,prepared,disposed} = fixture();
  const first = cache.request('A','/a.glb');
  const rejectedA = assert.rejects(first,{name:'AbortError'});
  const middle = cache.request('B','/b.glb');
  const rejectedB = assert.rejects(middle,{name:'AbortError'});
  const latest = cache.request('A','/a.glb');
  const oldA = {name:'old A'}; jobs[0].resolve(oldA);
  await tick();
  assert.equal(cache.pending.get('A').promise,latest);
  const currentA = {name:'current A'}; jobs[2].resolve(currentA);
  assert.equal(await latest,currentA);
  const oldB = {name:'old B'}; jobs[1].resolve(oldB);
  await rejectedA; await rejectedB; await tick();
  assert.deepEqual(prepared,[currentA]); assert.deepEqual(disposed,[oldA,oldB]);
  assert.equal(cache.models.get('A'),currentA);
  assert.equal(cache.pending.size,0); cache.dispose();
});

test('the same pending asset and cached scene are shared without duplicate work', async () => {
  const {cache,jobs,prepared} = fixture();
  const first = cache.request('A','/a.glb');
  assert.equal(cache.request('A','/a.glb'),first);
  const model = {}; jobs[0].resolve(model); await first;
  assert.equal(await cache.request('A','/a.glb'),model);
  assert.equal(jobs.length,1); assert.deepEqual(prepared,[model]); cache.dispose();
});

test('closing the cache aborts transfer and discards a late result', async () => {
  const {cache,jobs,prepared,disposed} = fixture();
  const pending = cache.request('A','/a.glb');
  const rejected = assert.rejects(pending,{name:'AbortError'});
  cache.dispose(); assert.equal(jobs[0].signal.aborted,true);
  const model = {}; jobs[0].resolve(model);
  await rejected; await tick();
  assert.deepEqual(prepared,[]); assert.deepEqual(disposed,[model]);
  assert.equal(cache.models.size,0); assert.equal(cache.pending.size,0);
  await assert.rejects(cache.request('B','/b.glb'),/disposed/);
});

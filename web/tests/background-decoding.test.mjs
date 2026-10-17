import {test} from 'node:test';
import assert from 'node:assert/strict';
import {loadModelInStages} from '../src/model-loading.js';

const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
};

test('download completes during navigation but decoding waits for permission', async () => {
  const gate = deferred(), bytes = new ArrayBuffer(20);
  let downloaded = false, decoded = false;
  const loaded = loadModelInStages(() => { downloaded = true; return bytes; }, buffer => {
    assert.equal(buffer, bytes); decoded = true; return {scene:'ready'};
  }, {beforeDecode:() => gate.promise});
  await flush();
  assert.equal(downloaded, true); assert.equal(decoded, false);
  gate.resolve(); assert.deepEqual(await loaded, {scene:'ready'});
});

test('waiting for navigation does not consume the download or decode timeout', async t => {
  t.mock.timers.enable({apis:['setTimeout']});
  const gate = deferred(), finishDecode = deferred();
  let decodeStarted = false;
  const loaded = loadModelInStages(() => new ArrayBuffer(20), () => {
    decodeStarted = true; return finishDecode.promise;
  }, {beforeDecode:() => gate.promise, idleTimeout:45, decodeTimeout:90});
  await flush(); t.mock.timers.tick(1000); await flush();
  assert.equal(decodeStarted, false);
  gate.resolve(); await flush(); assert.equal(decodeStarted, true);
  t.mock.timers.tick(89); await flush();
  finishDecode.resolve({scene:'ready'}); assert.deepEqual(await loaded, {scene:'ready'});
});

test('a viewer disposed while waiting never starts decoding', async () => {
  const gate = deferred(), controller = new AbortController();
  let decodeCount = 0;
  const loaded = loadModelInStages(() => new ArrayBuffer(20), () => { decodeCount++; },
    {signal:controller.signal, beforeDecode:() => gate.promise});
  const rejected = assert.rejects(loaded, {name:'AbortError'});
  await flush(); controller.abort(); await rejected;
  gate.resolve(); await flush(); assert.equal(decodeCount, 0);
});

test('a failed scheduling gate rejects the load and cancels its transfer', async () => {
  let cancelled = 0, decoded = false;
  await assert.rejects(loadModelInStages(() => new ArrayBuffer(20), () => { decoded = true; }, {
    beforeDecode:() => { throw new Error('Scheduler stopped'); }, cancelDownload:() => { cancelled++; },
  }), /Scheduler stopped/);
  assert.equal(decoded, false); assert.equal(cancelled, 1);
});

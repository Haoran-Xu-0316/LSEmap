import test from 'node:test';
import assert from 'node:assert/strict';
import {downloadVerifiedModel, downloadCampusModel} from '../src/model-loading.js';

function minimalGlb() {
  const text = new TextEncoder().encode(JSON.stringify({asset:{version:'2.0'}}));
  const length = Math.ceil(text.length/4)*4;
  const buffer = new ArrayBuffer(20+length), header = new DataView(buffer);
  header.setUint32(0,0x46546c67,true); header.setUint32(4,2,true);
  header.setUint32(8,buffer.byteLength,true); header.setUint32(12,length,true);
  header.setUint32(16,0x4e4f534a,true);
  new Uint8Array(buffer,20).fill(32); new Uint8Array(buffer,20,text.length).set(text);
  return buffer;
}

test('background priority survives a retry without weakening validation', async () => {
  const calls = [], bytes = minimalGlb();
  const result = await downloadVerifiedModel('/models/details/example.glb', {
    priority:'low',
    fetchModel:async (url,options) => {
      calls.push({url,...options});
      if (calls.length === 1) throw new TypeError('Transient transfer failure');
      return new Response(bytes);
    },
  });
  assert.deepEqual(result,bytes);
  assert.deepEqual(calls.map(call=>call.priority),['low','low']);
  assert.deepEqual(calls.map(call=>call.cache),['default','reload']);
});

test('first campus transfer and original-GLB fallback retain foreground priority', async () => {
  const calls = [], bytes = minimalGlb();
  const result = await downloadCampusModel('/models/campus.glb?v=current', {
    priority:'high', byteCache:null,
    fetchModel:async (url,options) => {
      calls.push({url,...options});
      return url.startsWith('/models/campus-parts.json')
        ? new Response(null,{status:404}) : new Response(bytes);
    },
  });
  assert.deepEqual(result,bytes);
  assert.deepEqual(calls.map(call=>call.priority),['high','high']);
  assert.equal(calls[0].url,'/models/campus-parts.json?v=current');
});

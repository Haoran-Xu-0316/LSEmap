import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {downloadCampusModel} from '../src/model-loading.js';

const hash = data => createHash('sha256').update(new Uint8Array(data)).digest('hex');
function fixture() {
  const buffer = new ArrayBuffer(96), bytes = new Uint8Array(buffer);
  const header = new DataView(buffer);
  header.setUint32(0, 0x46546c67, true); header.setUint32(4, 2, true); header.setUint32(8, 96, true);
  for (let i = 20; i < bytes.length; i++) bytes[i] = i;
  const sha256 = hash(buffer);
  const parts = [0, 32, 64].map((offset, i) => {
    const data = bytes.slice(offset, offset + 32), digest = hash(data.buffer);
    return {path:`/models/campus-${i}-${digest.slice(0,12)}.bin`, bytes:32, sha256:digest, data};
  });
  const manifest = {bytes:96, sha256, parts:parts.map(({data,...part}) => part)};
  return {buffer, sha256, parts, manifest};
}
async function load(f, cached) {
  const requests = [];
  const output = await downloadCampusModel('/models/campus.glb', {
    supportsCompression:false,
    byteCache:{read:async key => {assert.equal(key, f.sha256); return cached;}, write:async()=>{}},
    fetchModel:async url => {
      requests.push(url);
      return url.includes('parts.json') ? Response.json(f.manifest) : new Response(f.parts.find(p=>p.path===url).data);
    },
  });
  return {output, requests};
}

test('verified cached bytes need only the fresh release index, with no segment downloads', async()=>{
  const f=fixture(), {output,requests}=await load(f,f.buffer);
  assert.equal(output,f.buffer); assert.equal(requests.length,1);
});
test('corrupt cached bytes are rejected before model decoding and replaced from the network',async()=>{
  const f=fixture(), corrupt=f.buffer.slice(0); new Uint8Array(corrupt)[28]^=8;
  const {output,requests}=await load(f,corrupt);
  assert.deepEqual(new Uint8Array(output),new Uint8Array(f.buffer)); assert.equal(requests.length,4);
});
test('a cached different release length cannot replace the selected model',async()=>{
  const f=fixture(), {output,requests}=await load(f,new ArrayBuffer(32));
  assert.deepEqual(new Uint8Array(output),new Uint8Array(f.buffer));assert.equal(requests.length,4);
});
test('denied browser storage retains the normal verified network path',async()=>{
  const f=fixture();let segments=0;
  const bytes=await downloadCampusModel('/models/campus.glb', {
    supportsCompression:false, byteCache:{read:async()=>{throw Error('Quota');},write:async()=>{throw Error('Quota');}},
    fetchModel:async url=>url.includes('parts.json') ? Response.json(f.manifest) : (segments++,new Response(f.parts.find(p=>p.path===url).data)),
  });
  assert.equal(segments,3);assert.deepEqual(new Uint8Array(bytes),new Uint8Array(f.buffer));
});
test('cancellation during cache lookup cannot return a stale success',async()=>{
  const f=fixture(), controller=new AbortController();
  await assert.rejects(downloadCampusModel('/models/campus.glb', {
    signal:controller.signal, byteCache:{read:async()=>{controller.abort();return f.buffer;}},
    fetchModel:async()=>Response.json(f.manifest),
  }),{name:'AbortError'});
});

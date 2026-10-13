import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {downloadCampusModel} from '../src/model-loading.js';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
function fixture() {
  const bytes = new Uint8Array(120);
  const header = new DataView(bytes.buffer);
  header.setUint32(0,0x46546c67,true);header.setUint32(4,2,true);header.setUint32(8,bytes.length,true);
  for(let index=20;index<bytes.length;index++)bytes[index]=index;
  const parts = [0,40,80].map((begin,index)=>{
    const raw=bytes.slice(begin,begin+40),gzip=gzipSync(raw),sha256=hash(raw),compressedHash=hash(gzip);
    return {path:`/models/campus-${index}-${sha256.slice(0,12)}.bin`,bytes:raw.length,sha256,
      compressed:{path:`/models/campus-${index}-${compressedHash.slice(0,12)}.bin.gz`,bytes:gzip.length,sha256:compressedHash,encoding:'gzip'},raw,gzip};
  });
  const manifest={bytes:bytes.length,sha256:hash(bytes),parts:parts.map(({raw,gzip,...part})=>part)};
  return {bytes,parts,manifest};
}
function transport(f, requests, override=()=>undefined) {
  return async (url,{signal}={})=>{
    signal?.throwIfAborted();requests.push(url);
    if(url.includes('parts.json'))return Response.json(f.manifest);
    const part=f.parts.find(part=>part.path===url||part.compressed.path===url);
    return override(url,part) ?? new Response(url.endsWith('.gz')?part.gzip:part.raw);
  };
}
test('gzip streams reconstruct every original byte and use no raw segment requests',async()=>{
  const f=fixture(),requests=[],progress=[];
  const actual=await downloadCampusModel('/models/campus.glb',{fetchModel:transport(f,requests),onProgress:e=>progress.push(e.loaded)});
  assert.deepEqual(new Uint8Array(actual),f.bytes);
  assert.equal(requests.filter(url=>url.endsWith('.gz')).length,3);
  assert.equal(requests.filter(url=>url.endsWith('.bin')).length,0);
  assert.equal(progress.at(-1),f.bytes.length);
});
test('clients without stream decompression load the exact raw model',async()=>{
  const f=fixture(),requests=[];
  const actual=await downloadCampusModel('/models/campus.glb',{supportsCompression:false,fetchModel:transport(f,requests)});
  assert.deepEqual(new Uint8Array(actual),f.bytes);
  assert.equal(requests.filter(url=>url.endsWith('.gz')).length,0);
  assert.equal(requests.filter(url=>url.endsWith('.bin')).length,3);
});
test('a corrupt gzip stream retries only its raw segment',async()=>{
  const f=fixture(),requests=[];
  const actual=await downloadCampusModel('/models/campus.glb',{fetchModel:transport(f,requests,
    (url,part)=>url===f.parts[1].compressed.path?new Response(new Uint8Array(10)):undefined)});
  assert.deepEqual(new Uint8Array(actual),f.bytes);
  assert.deepEqual(requests.filter(url=>url.endsWith('.bin')),[f.parts[1].path]);
});
test('corruption in both forms fails integrity validation and cancels siblings',async()=>{
  const f=fixture(),requests=[];let activeSignal;
  const fetchModel=transport(f,requests,(url,part)=>new Response(new Uint8Array(part.bytes)));
  await assert.rejects(downloadCampusModel('/models/campus.glb',{fetchModel:(url,options)=>{
    if(!url.includes('parts.json'))activeSignal=options.signal;
    return fetchModel(url,options);
  }}),/integrity/);
  assert.equal(activeSignal.aborted,true);
});
test('compressed segment paths cannot escape the published model directory',async()=>{
  const f=fixture(),requests=[];f.manifest.parts[0].compressed.path='https://untrusted.invalid/model.gz';
  await assert.rejects(downloadCampusModel('/models/campus.glb',{fetchModel:transport(f,requests)}),/Invalid campus segment index/);
  assert.equal(requests.length,1);
});

test('HTTP gzip bodies already decoded by fetch are never decompressed twice',async()=>{
  const f=fixture(),requests=[];
  const actual=await downloadCampusModel('/models/campus.glb',{fetchModel:transport(f,requests,
    (url,part)=>url.endsWith('.gz')?new Response(part.raw,{headers:{'Content-Encoding':'gzip'}}):undefined)});
  assert.deepEqual(new Uint8Array(actual),f.bytes);
  assert.equal(requests.filter(url=>url.endsWith('.bin')).length,0);
});

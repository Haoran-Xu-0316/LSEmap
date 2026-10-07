import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {downloadVerifiedModel} from '../src/model-loading.js';
const glb=()=>{const b=new Uint8Array(20);const v=new DataView(b.buffer);v.setUint32(0,0x46546c67,true);v.setUint32(4,2,true);v.setUint32(8,20,true);return b;};
const sha=b=>createHash('sha256').update(b).digest('hex');
test('corrupted complete transfer is retried before it can reach decoding',async()=>{
 const good=glb(),bad=good.slice();bad[19]=1;let count=0;const caches=[];
 const bytes=await downloadVerifiedModel('/model',{expectedSha256:sha(good),fetchModel:async(_,options)=>{caches.push(options.cache);return new Response(++count===1?bad:good);}});
 assert.deepEqual(new Uint8Array(bytes),good);assert.deepEqual(caches,['default','reload']);
});
test('repeated truncated GLB is rejected after two attempts',async()=>{
 const bad=glb().slice(0,19);let count=0;
 await assert.rejects(downloadVerifiedModel('/model',{fetchModel:async()=>{count++;return new Response(bad);}}),{name:'ModelIntegrityError'});
 assert.equal(count,2);
});
test('network change retries once; a valid model uses its response ETag',async()=>{
 const good=glb();let count=0;
 const bytes=await downloadVerifiedModel('/model',{fetchModel:async()=>{if(++count===1)throw new TypeError('network changed');return new Response(good,{headers:{ETag:'"'+sha(good)+'"'}});}});
 assert.equal(bytes.byteLength,20);assert.equal(count,2);
});
test('aborted transfer never retries and failed HTTP is not retried',async()=>{
 const c=new AbortController();let count=0;c.abort();
 await assert.rejects(downloadVerifiedModel('/model',{signal:c.signal,fetchModel:async()=>{count++;}}),{name:'AbortError'});assert.equal(count,0);
 await assert.rejects(downloadVerifiedModel('/model',{fetchModel:async()=>{count++;return new Response('',{status:404});}}),/HTTP404/);assert.equal(count,1);
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {downloadVerifiedModel} from '../src/model-loading.js';
const good=new Uint8Array(80);const header=new DataView(good.buffer);
header.setUint32(0,0x46546c67,true);header.setUint32(4,2,true);header.setUint32(8,good.length,true);good.fill(19,20);
const sha=createHash('sha256').update(good).digest('hex');
const options={expectedSha256:sha,expectedBytes:good.length};
const url='/models/details/campus-mobile-'+sha.slice(0,12)+'.glb.gz';

test('verified mobile bytes reopen without another model transfer',async()=>{
 let transfers=0;
 const result=await downloadVerifiedModel(url,{...options,byteCache:{read:async()=>good.buffer},fetchModel:async()=>{transfers++;return new Response(good);}});
 assert.deepEqual(new Uint8Array(result),good);assert.equal(transfers,0);
});
test('corrupt cached bytes fall back to the unchanged verified network payload',async()=>{
 const bad=good.slice();bad[40]^=1;let transfers=0;
 const result=await downloadVerifiedModel(url,{...options,byteCache:{read:async()=>bad.buffer,write:async()=>{}},fetchModel:async()=>{transfers++;return new Response(good);}});
 assert.deepEqual(new Uint8Array(result),good);assert.equal(transfers,1);
});
test('missing compressed asset retries the original file with identical checksum and priority',async()=>{
 const calls=[],fallbackUrl=url.slice(0,-3);
 const result=await downloadVerifiedModel(url,{...options,fallbackUrl,byteCache:null,priority:'high',fetchModel:async(path,init)=>{
  calls.push({path,priority:init.priority});return path===url?new Response(null,{status:404}):new Response(good);
 }});
 assert.deepEqual(new Uint8Array(result),good);assert.deepEqual(calls,[{path:url,priority:'high'},{path:fallbackUrl,priority:'high'}]);
});
test('known-size transfer rejects truncation before decoding',async()=>{
 await assert.rejects(downloadVerifiedModel('/models/example.glb',{...options,byteCache:null,fetchModel:async()=>new Response(good.slice(0,-1))}),{name:'ModelIntegrityError'});
});
test('cancellation during the mobile cache lookup starts no transfer',async()=>{
 const controller=new AbortController();let transfers=0;
 await assert.rejects(downloadVerifiedModel(url,{...options,signal:controller.signal,byteCache:{read:async()=>{controller.abort();return good.buffer;}},fetchModel:async()=>{transfers++;}}),{name:'AbortError'});
 assert.equal(transfers,0);
});

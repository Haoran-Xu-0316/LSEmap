import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {downloadCampusModel} from '../src/model-loading.js';
const hash=b=>createHash('sha256').update(b).digest('hex');
function fixture(){
 const bytes=new Uint8Array(60);const view=new DataView(bytes.buffer);view.setUint32(0,0x46546c67,true);view.setUint32(4,2,true);view.setUint32(8,60,true);
 for(let i=20;i<60;i++)bytes[i]=i;
 const parts=[0,20,40].map((offset,i)=>{const data=bytes.slice(offset,offset+20),sha256=hash(data);return {path:`/models/campus-${i}-${sha256.slice(0,12)}.bin`,bytes:20,sha256,data};});
 return {bytes,parts,manifest:{bytes:60,sha256:hash(bytes),parts:parts.map(({data,...part})=>part)}};
}
test('all segments start before any finishes; reordered responses reconstruct exact source',async()=>{
 const f=fixture(),started=[],done=new Map(),progress=[];
 const promise=downloadCampusModel('/models/campus.glb?v=current',{onProgress:e=>progress.push(e.loaded),fetchModel:async url=>{
  if(url.startsWith('/models/campus-parts.json')){assert.equal(url,'/models/campus-parts.json?v=current');return Response.json(f.manifest);}
  started.push(url);return new Promise(resolve=>done.set(url,resolve));
 }});
 while(started.length<3)await new Promise(resolve=>setTimeout(resolve,0));
 assert.equal(done.size,3);
 for(const part of [...f.parts].reverse())done.get(part.path)(new Response(part.data));
 assert.deepEqual(new Uint8Array(await promise),f.bytes);assert.equal(progress.at(-1),60);assert.deepEqual(progress,[20,40,60]);
});
test('corrupt segment is rejected and sibling fetches are cancelled',async()=>{
 const f=fixture();let signal;
 await assert.rejects(downloadCampusModel('/models/campus.glb',{fetchModel:async(url,options)=>{
  if(url.includes('parts.json'))return Response.json(f.manifest);signal=options.signal;
  const part=f.parts.find(p=>p.path===url);return new Response(new Uint8Array(part.bytes));
 }}),/integrity/);assert.equal(signal.aborted,true);
});
test('development without a segment index retains GLB validation and progress',async()=>{
 const f=fixture();let count=0;
 const data=await downloadCampusModel('/models/campus.glb',{fetchModel:async url=>{count++;return url.includes('parts.json')?new Response(null,{status:404}):new Response(f.bytes);}});
 assert.deepEqual(new Uint8Array(data),f.bytes);assert.equal(count,2);
});
test('an already cancelled campus request does not download segments',async()=>{
 const c=new AbortController();c.abort();let segments=0;
 await assert.rejects(downloadCampusModel('/models/campus.glb',{signal:c.signal,fetchModel:async url=>{if(url.includes('parts.json'))return Response.json(fixture().manifest);segments++;}}),{name:'AbortError'});assert.equal(segments,0);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';
import {outdoorSkyVisible,loadOutdoorEnvironment,SKY_URL} from '../src/outdoor-environment.js';

test('map and STC elevation stay neutral while street pitch reveals the sky',()=>{
 assert.equal(outdoorSkyVisible('campus',-.65),false);
 assert.equal(outdoorSkyVisible('campus',-.387),false);
 assert.equal(outdoorSkyVisible('detail',-.10),true);
 assert.equal(outdoorSkyVisible('interior',.4,true),false);
 assert.equal(outdoorSkyVisible('campus',-.22,false),false);
 assert.equal(outdoorSkyVisible('campus',-.22,true),true);
 assert.equal(outdoorSkyVisible('campus',-.27,true),false);
});

test('fixed CC0 panorama is an intact 1k HDR below the optional delivery budget',async()=>{
 const bytes=await readFile(new URL('../public'+SKY_URL,import.meta.url));
 assert.equal(bytes.length,1086297);assert.ok(bytes.length<2_000_000);
 assert.equal(createHash('sha256').update(bytes).digest('hex'),'9da5a7f9c799fa6e41cac8fbc4fb7aa2d4556e2f00ce9943abe0fd83b6d4caf5');
 const image=new HDRLoader().parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));
 assert.equal(image.width,1024);assert.equal(image.height,512);
});

test('failed optional sky keeps the startup environment and disposed viewers never start a request',async()=>{
 const previousFetch=globalThis.fetch;let requests=0;
 globalThis.fetch=async()=>{requests++;throw Error('Offline');};
 try{
  const sentinel={texture:{startup:true}},scene={environment:sentinel.texture};
  const viewer={disposed:false,environmentTarget:sentinel,scene,loadController:new AbortController(),canvas:{dataset:{}}};
  assert.equal(await loadOutdoorEnvironment(viewer),false);
  assert.equal(viewer.canvas.dataset.skyReady,'fallback');assert.equal(scene.environment,sentinel.texture);assert.equal(requests,1);
  viewer.disposed=true;assert.equal(await loadOutdoorEnvironment(viewer),false);assert.equal(requests,1);
 }finally{globalThis.fetch=previousFetch;}
});

test('an abort during response decoding cannot replace the startup environment',async()=>{
 const previousFetch=globalThis.fetch,controller=new AbortController();
 const sentinel={texture:{startup:true}},scene={environment:sentinel.texture};
 globalThis.fetch=async(_url,options)=>{
  assert.equal(options.signal,controller.signal);
  return {ok:true,arrayBuffer:async()=>{controller.abort();return new ArrayBuffer(0);}};
 };
 try{
  const viewer={disposed:false,environmentTarget:sentinel,scene,loadController:controller,canvas:{dataset:{}}};
  assert.equal(await loadOutdoorEnvironment(viewer),false);
  assert.equal(scene.environment,sentinel.texture);assert.equal(viewer.environmentTarget,sentinel);assert.equal(viewer.skyTexture,undefined);
 }finally{globalThis.fetch=previousFetch;}
});

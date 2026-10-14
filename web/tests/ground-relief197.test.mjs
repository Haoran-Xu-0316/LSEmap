import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import * as THREE from 'three';
import {GROUND_FINISHES,createGroundTextureState,loadGroundTextures,disposeGroundTextures} from '../src/ground-textures.js';

function viewer() {
 return {loadController:new AbortController(),groundTextures:createGroundTextureState(),canvas:{dataset:{}},
  renderer:{capabilities:{getMaxAnisotropy:()=>16}},renderPipeline:{resetHistory(){}},disposed:false};
}

test('captured road relief is self-hosted, lossless data with source hashes and a bounded download',async()=>{
 const manifest=JSON.parse(await readFile('web/public/environment/sources.json','utf8'));
 let total=0;
 for(const asset of GROUND_FINISHES){
  const record=manifest.assets.find(item=>item.path===asset.reliefUrl);
  const bytes=await readFile('web/public'+asset.reliefUrl);total+=bytes.length;
  assert.equal(record.license,'CC0-1.0');assert.equal(record.colorSpace,'linear-data');
  assert.equal(createHash('sha256').update(bytes).digest('hex'),record.sha256);
  assert.equal(bytes.length,record.bytes);assert.equal(record.repeatMetres,asset.metres);
  assert.deepEqual(record.channels,{red:'height',green:'roughness',blue:'unused'});
  assert.deepEqual(record.originals.map(x=>x.semantic),['Displacement','Rough']);
  assert(record.originals.every(x=>/^[0-9a-f]{64}$/.test(x.originalSha256)));
 }
 assert(total<500000);
});

test('optional relief failure retains both usable road colours and frees only its partial download',async()=>{
 const oldFetch=globalThis.fetch,oldBitmap=globalThis.createImageBitmap;let requests=0,closed=0;
 globalThis.fetch=async()=>({ok:++requests<4,blob:async()=>new Blob()});
 globalThis.createImageBitmap=async()=>({width:512,height:512,close:()=>closed++});
 const v=viewer();
 try {
  assert.equal(await loadGroundTextures(v),true);assert.equal(v.groundTextures.ready.value,1);
  assert.equal(v.groundTextures.reliefReady.value,0);assert.equal(v.canvas.dataset.groundReliefReady,'fallback');
  assert.equal(closed,1);assert(v.groundTextures.stone.value);assert(v.groundTextures.asphalt.value);
  disposeGroundTextures(v.groundTextures);assert.equal(closed,3);
 }finally{globalThis.fetch=oldFetch;globalThis.createImageBitmap=oldBitmap;}
});

test('shared relief slots preserve linear channels, filtered sampling and release all decoded pixels',async()=>{
 const oldFetch=globalThis.fetch,oldBitmap=globalThis.createImageBitmap;let closed=0;
 globalThis.fetch=async()=>({ok:true,blob:async()=>new Blob()});
 globalThis.createImageBitmap=async()=>({width:512,height:512,close:()=>closed++});
 const v=viewer();
 try {
  assert.equal(await loadGroundTextures(v),true);assert.equal(v.groundTextures.reliefReady.value,1);
  for(const name of ['asphaltRelief','stoneRelief']) {
   const texture=v.groundTextures[name].value;
   assert.equal(texture.colorSpace,THREE.NoColorSpace);assert.equal(texture.minFilter,THREE.LinearMipmapLinearFilter);
   assert.equal(texture.anisotropy,4);
  }
  disposeGroundTextures(v.groundTextures);assert.equal(closed,4);assert.equal(v.groundTextures.reliefReady.value,0);
 }finally{globalThis.fetch=oldFetch;globalThis.createImageBitmap=oldBitmap;}
});

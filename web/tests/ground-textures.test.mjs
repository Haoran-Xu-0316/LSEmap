import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import * as THREE from 'three';
import {GROUND_FINISHES,createGroundTextureState,loadGroundTextures,disposeGroundTextures} from '../src/ground-textures.js';
import {applySurfaceDetail} from '../src/surface-materials.js';

test('small self-hosted CC0 finishes have verified provenance and normalized linear tone',async()=>{
 const manifest=JSON.parse(await readFile('web/public/environment/sources.json','utf8'));
 let bytes=0;
 for(const asset of GROUND_FINISHES){
  const record=manifest.assets.find(item=>item.path===asset.url);assert(record);assert.equal(record.license,'CC0-1.0');
  const data=await readFile('web/public'+asset.url);bytes+=data.length;
  assert.equal(data.length,record.bytes);assert.equal(createHash('sha256').update(data).digest('hex'),record.sha256);
  assert.equal(asset.mean,record.linearLuminanceMean);assert.equal(asset.metres,record.repeatMetres);
  assert.deepEqual(record.dimensions,[512,512]);assert(record.scope.includes('Not an LSE survey'));
 }
 assert(bytes<150000);
});

test('world-coordinate road finish shares slots without changing authored maps or adding grout',()=>{
 const state=createGroundTextureState();
 for(const name of ['WEB_Road asphalt','WEB_SITE172_SITE_V47_slab_2_Houghton']){
  const material=new THREE.MeshStandardMaterial({name});
  applySurfaceDetail(material,state);
  const shader={uniforms:{},vertexShader:'#include <project_vertex>',fragmentShader:'#include <color_fragment>\n#include <roughnessmap_fragment>\n#include <normal_fragment_maps>'};
  material.onBeforeCompile(shader);
  assert.equal(shader.uniforms.groundReady,state.ready);assert.equal(shader.uniforms.groundFinish,state[name.includes('asphalt')?'asphalt':'stone']);
  assert.equal(material.map,null);assert(shader.fragmentShader.includes('vSurfacePosition.xz / groundMetres'));assert(!shader.fragmentShader.includes('slabVisibility'));
  assert(shader.fragmentShader.includes('groundFace'));assert(shader.fragmentShader.includes('fwidth(surfacePoint)'));
 }
});

test('an unavailable second finish releases decoded pixels and keeps both fallback slots intact',async()=>{
 const oldFetch=globalThis.fetch,oldBitmap=globalThis.createImageBitmap;let closed=0,calls=0;
 globalThis.fetch=async()=>({ok:++calls===1,blob:async()=>new Blob()});
 globalThis.createImageBitmap=async()=>({width:512,height:512,close:()=>closed++});
 const viewer={loadController:new AbortController(),groundTextures:createGroundTextureState(),canvas:{dataset:{}},renderer:{capabilities:{getMaxAnisotropy:()=>16}},disposed:false};
 try{assert.equal(await loadGroundTextures(viewer),false);assert.equal(viewer.canvas.dataset.groundReady,'fallback');assert.equal(viewer.groundTextures.ready.value,0);assert.equal(closed,1);disposeGroundTextures(viewer.groundTextures);}
 finally{globalThis.fetch=oldFetch;globalThis.createImageBitmap=oldBitmap;}
});

test('approved authored stone and globe maps remain visible rather than being overwritten by noise',()=>{
 const material=new THREE.MeshStandardMaterial({name:'WEB_OLD_portland_stone',map:new THREE.Texture()});
 const compile=material.onBeforeCompile;applySurfaceDetail(material,createGroundTextureState());
 assert.equal(material.onBeforeCompile,compile);
});

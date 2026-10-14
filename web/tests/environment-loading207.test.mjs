import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {createGroundTextureState,loadGroundTextures,disposeGroundTextures} from '../src/ground-textures.js';
import {outdoorSurfaceKind,applySurfaceDetail} from '../src/surface-materials.js';

const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve};};
function makeViewer(){
 const viewer={loadController:new AbortController(),disposed:false,groundTextures:createGroundTextureState(),canvas:{dataset:{}},renderer:{capabilities:{getMaxAnisotropy:()=>4}},refreshes:0};
 viewer.renderPipeline={resetHistory(){viewer.refreshes++;}};return viewer;
}

test('road colours render while larger relief requests remain pending',async()=>{
 const saved={fetch:globalThis.fetch,bitmap:globalThis.createImageBitmap},gate=deferred(),requests=[];let closed=0;
 const v=makeViewer();
 globalThis.fetch=async url=>{requests.push(url);if(url.includes('relief'))await gate.promise;return{ok:true,blob:async()=>new Blob()};};
 globalThis.createImageBitmap=async()=>({close(){closed++;}});
 try{
  const pending=loadGroundTextures(v);await tick();
  assert.equal(requests.length,4);assert.equal(v.groundTextures.ready.value,1);assert.equal(v.groundTextures.reliefReady.value,0);assert.equal(v.refreshes,1);assert.equal(v.needsRender,true);
  gate.resolve();assert.equal(await pending,true);assert.equal(v.refreshes,2);assert.equal(v.groundTextures.reliefReady.value,1);
  disposeGroundTextures(v.groundTextures);assert.equal(closed,4);
 }finally{globalThis.fetch=saved.fetch;globalThis.createImageBitmap=saved.bitmap;}
});

test('failed parallel pair waits for and releases a late successful bitmap',async()=>{
 const saved={fetch:globalThis.fetch,bitmap:globalThis.createImageBitmap},gate=deferred();let closed=0,settled=false;
 const v=makeViewer();globalThis.fetch=async url=>({ok:!url.includes('asphalt'),blob:async()=>new Blob()});
 globalThis.createImageBitmap=async()=>{await gate.promise;return{close(){closed++;}};};
 try{
  const pending=loadGroundTextures(v).then(result=>{settled=true;return result;});await tick();assert.equal(settled,false);
  gate.resolve();assert.equal(await pending,false);assert.equal(closed,1);assert.equal(v.groundTextures.ready.value,0);assert.equal(v.refreshes,0);
 }finally{globalThis.fetch=saved.fetch;globalThis.createImageBitmap=saved.bitmap;}
});

test('disposal during relief decoding cannot resurrect disposed ground textures',async()=>{
 const saved={fetch:globalThis.fetch,bitmap:globalThis.createImageBitmap},gate=deferred();let closed=0,decoded=0;
 const v=makeViewer();globalThis.fetch=async()=>({ok:true,blob:async()=>new Blob()});
 globalThis.createImageBitmap=async()=>{if(++decoded>2)await gate.promise;return{close(){closed++;}};};
 try{
  const pending=loadGroundTextures(v);await tick();assert.equal(decoded,4);assert.equal(v.refreshes,1);
  v.disposed=true;v.loadController.abort();disposeGroundTextures(v.groundTextures);gate.resolve();await pending;
  assert.equal(closed,4);assert.equal(v.groundTextures.ready.value,0);assert.equal(v.groundTextures.reliefReady.value,0);assert.equal(v.refreshes,1);
 }finally{globalThis.fetch=saved.fetch;globalThis.createImageBitmap=saved.bitmap;}
});

test('terrace and plaza stone reuse captured finish without inventing tile joints',()=>{
 for(const name of ['WEB_CBG203_ROOF_paving','WEB_CBG205_PODIUM_paving','WEB_LRB_NEXT_LRB_NEXT_PLAZA155_stone']){
  assert.equal(outdoorSurfaceKind(name),'stone');const m=new THREE.MeshStandardMaterial({name});applySurfaceDetail(m,createGroundTextureState());
  assert(m.customProgramCacheKey().includes('captured'));const shader={uniforms:{},vertexShader:'#include <project_vertex>',fragmentShader:'#include <color_fragment>'};m.onBeforeCompile(shader);assert(!shader.fragmentShader.includes('slabVisibility'));
 }
 assert.equal(outdoorSurfaceKind('WEB_OLD196_FOYER_neutral_limestone_slabs'),null);
});

test('source HDR sun agrees with the shared presentation light while retaining an upright horizon',async()=>{
 const {readFile}=await import('node:fs/promises');const {HDRLoader}=await import('three/addons/loaders/HDRLoader.js');
 const {SKY_URL,DAYLIGHT_DIRECTION}=await import('../src/outdoor-environment.js');
 const bytes=await readFile('web/public'+SKY_URL),image=new HDRLoader().parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));
 let maximum=0,hotspot=0;
 for(let i=0;i<image.width*image.height;i++){const luminance=THREE.DataUtils.fromHalfFloat(image.data[i*4]);if(luminance>maximum){maximum=luminance;hotspot=i;}}
 const longitude=((hotspot%image.width+.5)/image.width-.5)*Math.PI*2;
 const latitude=Math.PI/2-(Math.floor(hotspot/image.width)+.5)/image.height*Math.PI;
 const direction=new THREE.Vector3(Math.cos(latitude)*Math.cos(longitude),Math.sin(latitude),Math.cos(latitude)*Math.sin(longitude));
 direction.applyEuler(new THREE.Euler(0,-.297803,0));
 assert(direction.dot(DAYLIGHT_DIRECTION)>.99999);
 assert(Math.abs(THREE.MathUtils.radToDeg(Math.asin(DAYLIGHT_DIRECTION.y))-48)<.001);
});

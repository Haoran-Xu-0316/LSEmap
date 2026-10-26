import {test} from 'node:test';
import assert from 'node:assert/strict';
import {throwIfAborted,combineAbortSignals} from '../src/abort-utils.js';
import {deviceBudget} from '../src/device-budget.js';
import {downloadCampusModel} from '../src/model-loading.js';
import {ModelCache} from '../src/model-cache.js';

test('older cancellation APIs are not required and every source listener is released',()=>{
 const originalAny=AbortSignal.any,originalThrow=AbortSignal.prototype.throwIfAborted;
 try{
  AbortSignal.any=undefined;AbortSignal.prototype.throwIfAborted=undefined;
  const a=new AbortController(),b=new AbortController();let active=0;
  for(const signal of [a.signal,b.signal]){
   const add=signal.addEventListener.bind(signal),remove=signal.removeEventListener.bind(signal);
   signal.addEventListener=(...args)=>{active++;add(...args);};signal.removeEventListener=(...args)=>{active--;remove(...args);};
  }
  const request=combineAbortSignals([a.signal,b.signal]);assert.equal(active,2);
  b.abort(new Error('User selected another room'));
  assert.throws(()=>throwIfAborted(request.signal),/another room/);assert.equal(active,0);
  request.dispose();assert.equal(active,0);
  const completed=combineAbortSignals([a.signal]);assert.equal(active,1);completed.dispose();assert.equal(active,0);
 }finally{AbortSignal.any=originalAny;AbortSignal.prototype.throwIfAborted=originalThrow;}
});

test('an old signal lacking reason still cancels with AbortError',()=>{
 const signal={aborted:true,addEventListener(){},removeEventListener(){}};
 const combined=combineAbortSignals([signal]);assert.throws(()=>throwIfAborted(combined.signal),{name:'AbortError'});
});

test('a cancelled campus request stops before network work without throwIfAborted',async()=>{
 const original=AbortSignal.prototype.throwIfAborted;AbortSignal.prototype.throwIfAborted=undefined;
 try{let fetched=0;const c=new AbortController();c.abort();
 await assert.rejects(downloadCampusModel('/models/campus.glb',{signal:c.signal,fetchModel:async()=>{fetched++;}}),{name:'AbortError'});assert.equal(fetched,0);
 }finally{AbortSignal.prototype.throwIfAborted=original;}
});

test('resource budget follows iOS and touch capability rather than viewport width',()=>{
 const phone=deviceBudget({navigator:{userAgent:'iPhone EdgiOS',maxTouchPoints:5},matchMedia:()=>({matches:true})});
 const ipad=deviceBudget({navigator:{userAgent:'Macintosh',maxTouchPoints:5},matchMedia:()=>({matches:false})});
 const desktop=deviceBudget({navigator:{userAgent:'Chrome',maxTouchPoints:0,hardwareConcurrency:16},matchMedia:()=>({matches:false})});
 assert(phone.mobile&&ipad.mobile);assert.equal(phone.decoderWorkers,1);assert.equal(phone.shadowSize,1024);assert.equal(phone.exteriorLimit,2);assert.equal(desktop.mobile,false);assert.equal(desktop.shadowSize,4096);
});

test('cancelled room decode never attaches its late geometry on older signals',async()=>{
 const original=AbortSignal.prototype.throwIfAborted;AbortSignal.prototype.throwIfAborted=undefined;
 try{let finish,prepared=0,disposed=0;const cache=new ModelCache(()=>new Promise(resolve=>{finish=resolve;}),()=>prepared++,()=>disposed++);
 const pending=cache.request('A','/a.glb');cache.activate('B');await assert.rejects(pending,{name:'AbortError'});finish({});await new Promise(resolve=>setTimeout(resolve,0));
 assert.equal(prepared,0);assert.equal(disposed,1);cache.dispose();
 }finally{AbortSignal.prototype.throwIfAborted=original;}
});


test('mobile eviction releases owned bitmap maps but keeps the shared environment',async()=>{
 const THREE=await import('three');const {disposeModel}=await import('../src/surface-materials.js');
 let closed=0,disposed=0,environmentDisposed=0;const image={close:()=>closed++};
 const map=new THREE.Texture(image),normal=new THREE.Texture(image),environment=new THREE.Texture();
 map.addEventListener('dispose',()=>disposed++);normal.addEventListener('dispose',()=>disposed++);environment.addEventListener('dispose',()=>environmentDisposed++);
 const group=new THREE.Group();group.add(new THREE.Mesh(new THREE.BoxGeometry(),new THREE.MeshStandardMaterial({map,normalMap:normal,envMap:environment})));
 disposeModel(group,true);assert.equal(closed,1);assert.equal(disposed,2);assert.equal(environmentDisposed,0);
});

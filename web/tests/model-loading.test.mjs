import {test} from 'node:test';
import assert from 'node:assert/strict';
import {loadModelInStages} from '../src/model-loading.js';

const flush = async () => { for (let i=0;i<12;i++) await Promise.resolve(); };
function harness(t, overrides={}) {
 t.mock.timers.enable({apis:['setTimeout']});
 let progress, finishDownload, finishDecode;
 const record={cancelled:0,discarded:[]};
 const promise=loadModelInStages(
  callback=>{progress=callback;return new Promise(resolve=>finishDownload=resolve);},
  ()=>new Promise(resolve=>finishDecode=resolve),
  {idleTimeout:45,decodeTimeout:90,cancelDownload:()=>record.cancelled++,
   discardModel:model=>record.discarded.push(model),...overrides});
 return {promise,record,progress:event=>progress(event),download:()=>finishDownload(new ArrayBuffer(1)),
  decode:model=>finishDecode(model),tick:async ms=>{t.mock.timers.tick(ms);await flush();}};
}

test('continuous byte progress can exceed the old fixed loading deadline',async t=>{
 const h=harness(t);await flush();
 for(let i=1;i<=8;i++){await h.tick(30);h.progress({loaded:i,total:8});}
 h.download();await flush();await h.tick(60);h.decode({scene:'ready'});
 assert.deepEqual(await h.promise,{scene:'ready'});assert.equal(h.record.cancelled,0);
 await h.tick(500);assert.equal(h.record.cancelled,0);
});

test('repeated unchanged progress cannot hide a stalled transfer',async t=>{
 const h=harness(t);const rejection=assert.rejects(h.promise,/download stalled/);await flush();
 h.progress({loaded:1});await h.tick(30);h.progress({loaded:1});await h.tick(15);
 await rejection;assert.equal(h.record.cancelled,1);
});

test('download completion gives decoding its separate time budget',async t=>{
 const h=harness(t);await flush();await h.tick(40);h.download();await flush();
 await h.tick(80);h.decode({scene:'decoded'});assert.deepEqual(await h.promise,{scene:'decoded'});
});

test('late decoded models are released after a decoding timeout',async t=>{
 const h=harness(t);const rejection=assert.rejects(h.promise,/decoding timed out/);await flush();
 h.download();await flush();await h.tick(90);await rejection;
 h.decode({scene:'late'});await flush();assert.deepEqual(h.record.discarded,[{scene:'late'}]);
});

test('disposing a viewer cancels download and suppresses subsequent decoding',async t=>{
 const controller=new AbortController();const h=harness(t,{signal:controller.signal});
 const rejection=assert.rejects(h.promise,{name:'AbortError'});await flush();
 controller.abort();await rejection;h.download();await flush();assert.equal(h.record.cancelled,1);
});

test('an already disposed viewer starts no network transfer',async()=>{
 const controller=new AbortController();controller.abort();let started=false;
 await assert.rejects(loadModelInStages(()=>{started=true;},()=>{}, {signal:controller.signal}),{name:'AbortError'});
 assert.equal(started,false);
});

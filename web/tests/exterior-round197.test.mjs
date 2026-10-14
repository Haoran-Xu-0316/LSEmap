import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const previous=JSON.parse(execFileSync('git',['show','a66c8a498c76a4ca942785bc7e19afdec9106e32:web/public/models/catalogue.json'],{encoding:'utf8'}));

test('edition197 reopens all original geometry and isolates the two new room collections',async()=>{
 const audit=await json('result/blender/stage197/building-refinement.json');
 const proof=await json('result/blender/stage197/reopened-verification.json');
 assert.equal(audit.version,197);assert.equal(audit.addedObjects.length,94);assert.equal(audit.archivedObjects.length,26);
 assert.equal(audit.independentRooms.length,2);
 assert.equal(proof.originalsVerified,6734);assert.equal(proof.originalGeometryUVsAndBindingsPreserved,true);
 assert.equal(proof.completeModelReopened,true);
 assert.equal(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v197.blend')).digest('hex'),proof.sourceModelSha256);
});

test('new rooms supplement the existing interior studies without replacing their geometry or approved maps',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');
 assert.equal(catalogue.version,'197');assert.equal(catalogue.buildings.length,31);
 assert.equal(catalogue.buildings.flatMap(b=>b.interiorSpaces??[]).length,15);
 for(const old of previous.buildings){
  const next=catalogue.buildings.find(b=>b.code===old.code);
  assert.equal(next.detailedInterior?.sha256,old.detailedInterior?.sha256,old.code);
  for(const room of old.interiorSpaces??[])assert.deepEqual(next.interiorSpaces.find(s=>s.id===room.id),room,room.id);
 }
 assert.deepEqual(catalogue.generatedTextures.map(t=>t.sha256).sort(),previous.generatedTextures.map(t=>t.sha256).sort());
});

test('paired historical room records retain their supported seat counts and independent browser assets',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');
 for(const [code,id,folder,seats]of [['FAW','faw-401','faw-room197',30],['CLM','clm-502','clm-room197',120]]){
  const report=await json('result/blender/'+folder+'/audit.json');assert.equal(report.studentSeatCount,seats);
  const room=catalogue.buildings.find(b=>b.code===code).interiorSpaces.find(s=>s.id===id);assert(room);
  assert(room.scope.includes('2026'));assert.equal(room.interiorStudy.kind,'room-sample');
  const buffer=await readFile('web/public'+room.detailedInterior.url);
  assert.equal(createHash('sha256').update(buffer).digest('hex'),room.detailedInterior.sha256);
  assert(buffer.length<500000);
  const model=JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)));
  assert(model.meshes.length);assert(model.meshes.flatMap(m=>m.primitives).every(p=>p.attributes.TEXCOORD_0!==undefined));
 }
});

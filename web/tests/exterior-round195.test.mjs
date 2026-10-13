import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const previous=JSON.parse(execFileSync('git',['show','0d82ea5fcc6d5816eb3a86d034ef01770c55f40f:web/public/models/catalogue.json'],{encoding:'utf8'}));

test('reopened complete source integrates only accepted KSW and COL objects',async()=>{
 const report=await json('result/blender/stage195/building-refinement.json');
 const verification=await json('result/blender/stage195/reopened-verification.json');
 assert.equal(report.version,195);assert.deepEqual(report.changes.map(change=>change.code),['KSW','COL']);
 assert.equal(report.addedObjects.length,80);assert.equal(report.archivedObjects.length,79);
 assert.equal(verification.originalGeometryUVsAndBindingsPreserved,true);assert.equal(verification.completeModelReopened,true);
 const native=await readFile('result/blender/LSE_campus_detailed_v195.blend');assert.equal(createHash('sha256').update(native).digest('hex'),verification.sourceModelSha256);
});

test('published assets use the accepted native source and retain every interior study',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');
 const verification=await json('result/blender/stage195/reopened-verification.json');
 assert.equal(catalogue.version,'195');assert.equal(catalogue.sourceModelSha256,verification.sourceModelSha256);
 assert.equal(catalogue.buildings.length,31);
 for(const original of previous.buildings){
  const current=catalogue.buildings.find(building=>building.code===original.code);
  assert.equal(current.detailedInterior?.sha256,original.detailedInterior?.sha256,original.code);
  assert.deepEqual(current.interiorSpaces,original.interiorSpaces,original.code);
 }
});

test('both building views carry COL approved finish maps and KSW window corrections',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');
 const model=async path=>{const buffer=await readFile(path);return JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)));};
 const campus=await model('web/public/models/campus.glb');
 for(const code of ['COL','KSW']){
  const building=catalogue.buildings.find(item=>item.code===code);
  const detail=await model('web/public'+building.detailedExterior.url);
  for(const doc of [campus,detail])assert(doc.materials.some(material=>material.name.includes(code==='COL'?'COL195':'KSW_NEXT_EXTERIOR195')));
  if(code==='COL')assert(detail.images?.length>0);
 }
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const previous=JSON.parse(execFileSync('git',['show','5ffa93541da3e3408db20061882ebb82df5916eb:web/public/models/catalogue.json'],{encoding:'utf8'}));

test('continuous road source reopens with every pre-existing object preserved',async()=>{
 const audit=await json('result/blender/stage198/building-refinement.json');
 const proof=await json('result/blender/stage198/reopened-verification.json');
 assert.equal(audit.version,198);assert.equal(audit.addedObjects.length,1);assert.equal(audit.archivedObjects.length,138);
 assert.equal(proof.originalsVerified,6828);assert.equal(proof.originalGeometryUVsAndBindingsPreserved,true);assert.equal(proof.completeModelReopened,true);
 assert.equal(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v198.blend')).digest('hex'),proof.sourceModelSha256);
});

test('road consolidation retains all building exterior and interior assets byte for byte',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');
 assert.equal(catalogue.version,'198');assert.equal(catalogue.buildings.length,31);
 for(const original of previous.buildings){
  const current=catalogue.buildings.find(b=>b.code===original.code);
  assert.equal(current.detailedExterior?.sha256,original.detailedExterior?.sha256,original.code);
  assert.equal(current.detailedInterior?.sha256,original.detailedInterior?.sha256,original.code);
  assert.deepEqual(current.interiorSpaces,original.interiorSpaces,original.code);
 }
 assert.deepEqual(catalogue.generatedTextures.map(t=>t.sha256).sort(),previous.generatedTextures.map(t=>t.sha256).sort());
});

test('full-network coverage proof retains holes and removes redundant coplanar area',async()=>{
 const proof=await json('result/blender/street-network198/coverage-verification.json');
 assert(proof.verified);assert.equal(proof.sourceObjects,138);assert.equal(proof.retainedHoles,23);
 assert(proof.duplicateAreaBeforeM2>6500);assert(Math.abs(proof.duplicateAreaAfterM2)<1e-5);
 assert(proof.boundaryMaximumDeviationMetres<.0001);
});

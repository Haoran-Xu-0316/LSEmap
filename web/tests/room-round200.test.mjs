import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const json=async p=>JSON.parse(await readFile(p,'utf8'));
const previous=JSON.parse(execFileSync('git',['show','eb6e8d6a33bcf491d95d422f7af324792e9957e1:web/public/models/catalogue.json'],{encoding:'utf8'}));

test('complete source reopens and isolates new rooms from all original campus objects',async()=>{
 const proof=await json('result/blender/stage200/reopened-verification.json');
 assert(proof.completeModelReopened&&proof.originalGeometryUVsAndBindingsPreserved);assert.equal(proof.originalsVerified,6963);assert.equal(proof.addedObjectsVerified,75);
 const report=await json('result/blender/stage200/building-refinement.json');assert.equal(report.independentRooms.length,2);assert.equal(report.archivedObjects.length,0);
 assert.equal(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v200.blend')).digest('hex'),proof.sourceModelSha256);
});

test('new room downloads preserve every previous exterior, room and shared campus asset',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');assert.equal(catalogue.version,'200');
 assert.equal(catalogue.sourceModelSha256,(await json('result/blender/stage200/reopened-verification.json')).sourceModelSha256);
 for(const old of previous.buildings){const now=catalogue.buildings.find(b=>b.code===old.code);assert.equal(now.detailedExterior?.sha256,old.detailedExterior?.sha256,old.code);assert.equal(now.detailedInterior?.sha256,old.detailedInterior?.sha256,old.code);for(const room of old.interiorSpaces??[])assert.deepEqual(now.interiorSpaces.find(r=>r.id===room.id),room);}
 const oldHash=execFileSync('git',['show','eb6e8d6a33bcf491d95d422f7af324792e9957e1:web/public/models/campus.glb'],{maxBuffer:70*1024*1024});assert.equal(createHash('sha256').update(await readFile('web/public/models/campus.glb')).digest('hex'),createHash('sha256').update(oldHash).digest('hex'));
 assert.deepEqual(catalogue.generatedTextures.map(x=>x.sha256),previous.generatedTextures.map(x=>x.sha256));
 for(const[code,id]of[['OLD','old-321'],['MAR','mar-107']]){const room=catalogue.buildings.find(b=>b.code===code).interiorSpaces.find(r=>r.id===id);assert(room?.detailedInterior?.sha256);assert(room.detailedInterior.bytes<1000000);}
});

test('both room sources remain archived historical evidence with reopened bounded geometry',async()=>{
 for(const[code,count]of[['old',32],['mar',20]]){const report=await json(`result/blender/${code}-room200/audit.json`);assert.equal(report.studentSeatCount,count);assert(report.triangleCount<40000);assert.equal(report.archivedObjects.length,0);assert.equal(report.collectionSpec.kind,'independent-room');assert(/估计/.test(report.space.scope)&&/不代表2026/.test(report.space.scope));for(const source of report.sources??report.references){assert.equal(createHash('sha256').update(await readFile(source.path)).digest('hex'),source.sha256);}}
});

test('CBG decision follows independent drawing scale rather than circular footprint registration',async()=>{
 const audit=await json('result/blender/cbg-grid200/audit.json');assert(audit.nativeFileUnchanged);assert.equal(audit.drawing.gridSpanCount,7);assert(audit.drawing.gridSpansMetres.every(x=>x>5.8&&x<6.3));assert.equal(audit.native.gridSpansMetres.length,6);assert(audit.native.gridSpansMetres.every(x=>x>8.1&&x<8.2));assert(/Do not merge/.test(audit.decision));
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const previous=JSON.parse(execFileSync('git',['show','fd02f635c7d7b49a44ad799ecc698ede344b7408:web/public/models/catalogue.json'],{encoding:'utf8'}));

test('edition199 reopens original geometry and integrates the three owned outdoor systems',async()=>{
 const audit=await json('result/blender/stage199/building-refinement.json');
 const proof=await json('result/blender/stage199/reopened-verification.json');
 assert.equal(audit.version,199);assert.equal(audit.addedObjects.length,134);assert.equal(audit.archivedObjects.length,574);
 assert.equal(proof.originalsVerified,6829);assert(proof.originalGeometryUVsAndBindingsPreserved);assert(proof.completeModelReopened);
 assert.equal(createHash('sha256').update(await readFile('result/blender/LSE_campus_detailed_v199.blend')).digest('hex'),proof.sourceModelSha256);
});

test('landscape refinements preserve every building exterior, interior and approved image map',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');assert.equal(catalogue.version,'199');
 const proof=await json('result/blender/stage199/reopened-verification.json');assert.equal(catalogue.sourceModelSha256,proof.sourceModelSha256);
 for(const original of previous.buildings){
  const current=catalogue.buildings.find(b=>b.code===original.code);
  assert.equal(current.detailedExterior?.sha256,original.detailedExterior?.sha256,original.code);
  assert.equal(current.detailedInterior?.sha256,original.detailedInterior?.sha256,original.code);
  assert.deepEqual(current.interiorSpaces,original.interiorSpaces,original.code);
 }
 assert.deepEqual(catalogue.generatedTextures.map(t=>t.sha256).sort(),previous.generatedTextures.map(t=>t.sha256).sort());
});

test('canopy detail stays inside retained envelopes and the bounded opaque geometry budget',async()=>{
 const report=await json('result/blender/landscape199/audit.json');
 assert.equal(report.crownEnvelopeChecks.length,522);assert.equal(report.crownEnvelopeChecks.filter(r=>r.modified).length,510);
 assert.equal(report.performance.addedTriangles,122400);assert(report.performance.addedTriangles<200000);
 assert.equal(report.performance.objectsAfter,1);assert.equal(report.performance.newTextures,0);assert.equal(report.performance.alphaCards,0);
 assert(report.verification.all12WatkinsMassesUnmodified);assert(report.verification.houghtonUnmodified);assert(report.verification.all522EnvelopeAndCentreChecksPassed);
 assert(report.crownEnvelopeChecks.every(r=>r.maxEnvelopeError<.00002));
});

test('context finishes have singular mapped evidence and remain outside the LSE building records',async()=>{
 const report=await json('result/blender/context-palette199/audit.json');
 const site=await json('result/blender/site_geometry.json');const records=new Map(site.buildings.map(b=>[b.id,b]));
 assert.equal(report.buildings,24);assert.equal(report.profiles,13);assert.equal(report.bindings.length,453);
 assert(report.verification.sourceWorldFacesPreserved);assert(report.verification.componentReopened);
 for(const binding of report.bindings){
  const record=records.get(binding.sourceId);assert.equal(record.code,null);
  const roof=binding.profile.startsWith('roof_'),attributes=record.properties;
  const colour=attributes[roof?'roof:colour':'building:colour'],material=attributes[roof?'roof:material':'building:material'];
  assert(!colour?.includes(';'));assert(colour||['brick','stone','sandstone','concrete'].includes(material));
 }
 const bytes=await readFile('web/public/models/campus.glb');const model=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 const materials=model.materials.filter(m=>m.name.includes('CONTEXT199_'));assert.equal(materials.length,13);
 const brick=new Set(materials.filter(m=>m.extras?.surfaceDetail?.kind==='brick').map(m=>model.materials.indexOf(m)));assert(brick.size>0);
 for(const primitive of model.meshes.flatMap(m=>m.primitives).filter(p=>brick.has(p.material)))assert.notEqual(primitive.attributes.TEXCOORD_0,undefined);
});


test('native ground repair changes orientation only and includes the diagnosed park sheet',async()=>{
 const report=await json('result/blender/ground-orientation199/audit.json');
 assert.equal(report.addedObjects.length,120);assert.equal(report.records.reduce((n,r)=>n+r.facesReoriented,0),5241);
 assert(report.records.some(r=>r.source==='GIS_green_way/30613392'&&r.flatGreenSheet));
 assert(report.verification.positionsCoverageCornerUVAndBindingsPreserved);assert(report.verification.allOwnedShellsOutward);
 const park=await json('result/blender/ground-orientation199/park-verification.json');assert(park.nativeParkFacesUpward);assert(park.baselineUnchanged);
});


test('published canopy and context remain opaque without material textures or a large campus download increase',async()=>{
 const current=await readFile('web/public/models/campus.glb');
 const previous=execFileSync('git',['cat-file','-s','fd02f635c7d7b49a44ad799ecc698ede344b7408:web/public/models/campus.glb'],{encoding:'utf8'});
 assert(current.length-Number(previous)<1000000);
 const model=JSON.parse(current.subarray(20,20+current.readUInt32LE(12)));
 const refinements=model.materials.filter(m=>/CONTEXT199_|LANDSCAPE199_/.test(m.name));assert(refinements.length>=15);
 for(const material of refinements){assert.equal(material.alphaMode??'OPAQUE','OPAQUE');assert.equal(material.pbrMetallicRoughness?.baseColorTexture,undefined);}
});

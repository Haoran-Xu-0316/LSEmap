import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const previous=JSON.parse(execFileSync('git',['show','f9d2eed378029612ce8854b0d109f80be27b5b85:web/public/models/catalogue.json'],{encoding:'utf8'}));
const model=async path=>{const buffer=await readFile(path);return JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)));};

test('reopened edition196 retains source geometry and only integrates three owned components',async()=>{
 const audit=await json('result/blender/stage196/building-refinement.json');
 const verify=await json('result/blender/stage196/reopened-verification.json');
 assert.equal(audit.version,196);assert.deepEqual(audit.changes.map(change=>change.code),['LRB','CLM','OLD_FOYER']);
 assert.equal(audit.addedObjects.length,80);assert.equal(audit.archivedObjects.length,79);
 assert.equal(verify.originalGeometryUVsAndBindingsPreserved,true);assert.equal(verify.originalsVerified,6654);assert.equal(verify.completeModelReopened,true);
 const native=await readFile('result/blender/LSE_campus_detailed_v196.blend');assert.equal(createHash('sha256').update(native).digest('hex'),verify.sourceModelSha256);
});

test('only the existing OLD foyer room changes while other interior studies remain intact',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');const verify=await json('result/blender/stage196/reopened-verification.json');
 assert.equal(catalogue.version,'196');assert.equal(catalogue.sourceModelSha256,verify.sourceModelSha256);
 assert.equal(catalogue.buildings.length,previous.buildings.length);
 for(const original of previous.buildings){
  const current=catalogue.buildings.find(building=>building.code===original.code);
  if(original.code!=='LRB')assert.equal(current.detailedInterior?.sha256,original.detailedInterior?.sha256,original.code);
  assert.equal(current.interiorSpaces?.length,original.interiorSpaces?.length,original.code);
  for(const room of original.interiorSpaces??[]){
   const next=current.interiorSpaces.find(item=>item.id===room.id);assert(next,room.id);
   if(room.id==='old-foyer')assert.notEqual(next.detailedInterior.sha256,room.detailedInterior.sha256);
   else assert.deepEqual(next,room,room.id);
  }
 }
 const maps=list=>list.map(item=>item.sha256).sort();assert.deepEqual(maps(catalogue.generatedTextures),maps(previous.generatedTextures));
});

test('OLD floor and mat carry metric filtered surfaces and the disc lights emit authored light',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');
 const old=catalogue.buildings.find(building=>building.code==='OLD');
 const room=old.interiorSpaces.find(item=>item.id==='old-foyer');
 const document=await model('web/public'+room.detailedInterior.url);
 for(const part of ['neutral_limestone_slabs','dark_ribbed_entrance_mat']){
  const index=document.materials.findIndex(material=>material.name.includes('OLD196_FOYER_'+part));assert(index>=0);
  assert.equal(document.materials[index].extras.surfaceDetail.kind,'brick');
  const primitives=document.meshes.flatMap(mesh=>mesh.primitives).filter(primitive=>primitive.material===index);assert(primitives.length);
  for(const primitive of primitives)assert.notEqual(primitive.attributes.TEXCOORD_0,undefined);
 }
 const light=document.materials.find(material=>material.name.includes('OLD196_FOYER_warm_disc_diffusers'));
 assert(light.emissiveFactor.some(value=>value>0));
 const coverage=await json('result/blender/old-foyer196/verification.json');assert.equal(coverage.floorCoverageSamples,9);assert.equal(coverage.componentReopened,true);
});

test('shared LRB roof finishes reach the public interior without changing compressed geometry',async()=>{
 const catalogue=await json('web/public/models/catalogue.json');
 const before=previous.buildings.find(building=>building.code==='LRB');
 const after=catalogue.buildings.find(building=>building.code==='LRB');
 const primitiveSignatures=buffer=>{
  const document=JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12))),start=28+buffer.readUInt32LE(12);
  return document.meshes.flatMap(mesh=>mesh.primitives.map(primitive=>{
   const view=document.bufferViews[primitive.extensions.KHR_draco_mesh_compression.bufferView];
   return createHash('sha256').update(buffer.subarray(start+(view.byteOffset??0),start+(view.byteOffset??0)+view.byteLength)).digest('hex');
  })).sort();
 };
 for(const [oldPath,newPath]of [['web/public/models/lrb-interior.glb','web/public/models/lrb-interior.glb'],['web/public'+before.detailedInterior.url,'web/public'+after.detailedInterior.url]]){
  const old=execFileSync('git',['show','f9d2eed378029612ce8854b0d109f80be27b5b85:'+oldPath],{maxBuffer:20e6});
  const current=await readFile(newPath);assert.deepEqual(primitiveSignatures(current),primitiveSignatures(old));
 }
});

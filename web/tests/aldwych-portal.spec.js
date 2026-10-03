import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
function geometryDigest(glb,bytes,primitive){
 const extension=primitive.extensions?.KHR_draco_mesh_compression;
 if(!extension)throw Error('Expected production Draco geometry');
 const view=glb.bufferViews[extension.bufferView],start=28+bytes.readUInt32LE(12)+(view.byteOffset??0);
 const meta=index=>{const a=glb.accessors[index];return {count:a.count,type:a.type,componentType:a.componentType,min:a.min,max:a.max};};
 return {sha256:createHash('sha256').update(bytes.subarray(start,start+view.byteLength)).digest('hex'),decoderAttributes:extension.attributes,indices:meta(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([k,v])=>[k,meta(v)]))};
}
test('61A portal recovers from the latest campus without changing source objects or glass',async()=>{
 const audit=await read('result/blender/aldwych_facade_next/audit.json');
 const original=await read('result/blender/aldwych_facade_next/verification.json');
 const recovery=await read('result/blender/stage137/aldwych-recovery/verification.json');
 const rebuiltAudit=await read('result/blender/stage137/aldwych-recovery/audit.json');
 expect(audit.changes).toHaveLength(26);expect(audit.archivedObjects).toHaveLength(19);expect(audit.ownedObjects).toHaveLength(26);
 expect(audit.changes.filter(c=>c.source===null)).toHaveLength(7);
 expect(audit.changes.filter(c=>c.source!==null).map(c=>c.source)).toEqual(audit.archivedObjects);
 expect(audit.changes.map(c=>c.owned)).toEqual(audit.ownedObjects);
 expect(createHash('sha256').update(await readFile('result/blender/aldwych_facade_next/aldwych-facade-component.blend')).digest('hex')).toBe(original.componentSha256);
 expect(recovery.latestBaseline).toMatch(/LSE_campus_detailed_v137\.blend$/);
 expect(recovery.savedComponentReopened).toBe(true);expect(recovery.originalGeometryPreserved).toBe(true);
 expect(recovery.otherComponentsPreserved).toBe(true);expect(recovery.fullModelSaved).toBe(false);expect(recovery.renderPerformed).toBe(false);
 expect(recovery.originalObjectCount).toBe(5571);expect(recovery.firstSurfaceChecks).toHaveLength(20);
 expect(recovery.firstSurfaceChecks.map(p=>p.firstSurface)).toEqual(original.firstSurfaceChecks.map(p=>p.firstSurface));
 expect(rebuiltAudit.ownedObjects).toEqual(audit.ownedObjects);expect(rebuiltAudit.archivedObjects).toEqual(audit.archivedObjects);
 expect(recovery.glassStatePreserved).toBe(true);expect(recovery.reloadedGlassState).toEqual(recovery.originalGlassState);
 for(const state of Object.values(recovery.originalGlassState)){
  expect(state.slots.Alpha).toBe(1);expect(state.slots['Transmission Weight']).toBe(0);
 }
});
test('61A NEXT portal exports identical geometry UV and PBR in campus and detail',async()=>{
 const proof=await read('result/blender/stage137/saved-verification.json');
 const catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('137');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);
 const accepted=new Set(proof.ownedMaterialNames['61A']);expect(accepted.size).toBe(10);
 const building=catalogue.buildings.find(b=>b.code==='61A'),summaries=[];
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
  for(const mesh of glb.meshes)for(const p of mesh.primitives){
   const material=glb.materials[p.material],name=material.name.replace(/^WEB_(DETAIL_)?/,'');
   if(!accepted.has(name))continue;
   expect(p.attributes.TEXCOORD_0,name).toBeDefined();
   primitives.push({material:name,geometry:geometryDigest(glb,bytes,p),pbr:material.pbrMetallicRoughness,alphaMode:material.alphaMode??'OPAQUE',doubleSided:material.doubleSided??false,finish:material.extras?.surfaceDetail});
  }
  expect(new Set(primitives.map(p=>p.material))).toEqual(accepted);summaries.push(primitives);
 }
 expect(summaries[0]).toEqual(summaries[1]);
 const glass=summaries[0].filter(p=>p.material==='61A_NEXT_61A_glass');expect(glass.length).toBeGreaterThan(0);
 for(const primitive of glass){expect(primitive.alphaMode).toBe('OPAQUE');expect(primitive.pbr.baseColorFactor[3]).toBe(1);}
 const before=await read('result/blender/stage137/catalogue-before.json'),old=before.buildings.find(b=>b.code==='61A');
 expect(building.detailedInterior).toEqual(old.detailedInterior);expect(building.interiorSpaces).toEqual(old.interiorSpaces);
});

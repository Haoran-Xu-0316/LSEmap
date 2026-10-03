import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const componentDir='result/blender/clement_facade_next';
const recoveryDir='result/blender/stage137/clm-recovery';

// Compare the actual compressed geometry bytes and the accessor declarations,
// including UV attributes, rather than treating triangle counts as fidelity.
function geometryDigest(glb,bytes,primitive){
 const extension=primitive.extensions?.KHR_draco_mesh_compression;
 if(!extension)throw Error('Expected production Draco geometry');
 const view=glb.bufferViews[extension.bufferView];
 const start=28+bytes.readUInt32LE(12)+(view.byteOffset??0);
 const accessor=index=>{const a=glb.accessors[index];return {count:a.count,type:a.type,componentType:a.componentType,min:a.min,max:a.max};};
 return {sha256:sha256(bytes.subarray(start,start+view.byteLength)),decoderAttributes:extension.attributes,indices:accessor(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([name,index])=>[name,accessor(index)]))};
}

test('CLM accepted spandrels recover from the latest native scene',async()=>{
 const audit=await read(componentDir+'/audit.json');
 const accepted=await read(componentDir+'/verification.json');
 const recoveryAudit=await read(recoveryDir+'/audit.json');
 const recovery=await read(recoveryDir+'/verification.json');
 const merge=await read('result/blender/stage137/saved-verification.json');
 expect(audit.ownedObjects).toEqual(['CLM_NEXT_FACADE_split_tall_panes','CLM_NEXT_FACADE_spandrel_edge_rails','CLM_NEXT_FACADE_opaque_brown_spandrels']);
 expect(audit.archivedObjects).toEqual(['CLM_D5_tall114_glass_panes','CLM_D5_tall114_metal_bars']);
 expect(audit.panelRegistration.metreDimensionsEstimated).toBe(true);
 expect(audit.references.map(r=>r.captureDate)).toEqual(['2018-04-24','2023-11-15','unknown']);
 expect(audit.wholeStreetReview.stoneAndBrick).toContain('pale stone');
 expect(accepted.componentSha256).toBe(sha256(await readFile(componentDir+'/clement-tall-window-spandrel-component.blend')));
 expect(accepted.originalGeometryPreserved).toBe(true);
 expect(accepted.savedComponentReopened).toBe(true);
 expect(accepted.splitGlassCount).toBe(14);expect(accepted.opaqueBandCount).toBe(7);
 expect(accepted.retainedOtherBarVertices).toBe(336);
 expect(accepted.reloadedProbes).toEqual(audit.afterProbes);
 expect(audit.afterProbes).toHaveLength(44);
 expect(audit.afterProbes.slice(0,21).every(p=>p.firstObject===audit.ownedObjects[2])).toBe(true);
 expect(audit.afterProbes.slice(21,35).every(p=>p.firstObject===audit.ownedObjects[0])).toBe(true);
 expect(audit.afterProbes.slice(35)).toEqual(audit.beforeProbes.slice(35));
 expect(recoveryAudit.baselineSha256).toBe(merge.sourceModelSha256);
 expect(recovery.recoveryFromLatestVersion).toBe(137);
 expect(recovery.originalObjectCount).toBe(merge.retainedOriginalObjects+merge.ownedObjects.length-audit.ownedObjects.length);
 expect(recovery.originalGeometryPreserved).toBe(true);expect(recovery.baselineUnchanged).toBe(true);
 expect(recovery.savedComponentReopened).toBe(true);expect(recovery.nativeRender).toBeNull();
 expect(recovery.reloadedProbes).toEqual(accepted.reloadedProbes);
 expect(recovery.componentSha256).toBe(sha256(await readFile(recoveryDir+'/clement-tall-window-spandrel-component.blend')));
 // Recovery removes only CLM's three accepted additions; every other accepted
 // building component remains in the native scene with its original fingerprint.
 for(const name of merge.ownedObjects.filter(name=>!audit.ownedObjects.includes(name)))expect(recoveryAudit.originalFingerprints[name],name).toMatch(/^[a-f0-9]{64}$/);
 for(const name of merge.archivedObjects.filter(name=>!audit.archivedObjects.includes(name)))expect(recoveryAudit.originalVisibility[name][0],name).toBe(true);
 for(const [name,fingerprint] of Object.entries(audit.originalFingerprints))expect(recoveryAudit.originalFingerprints[name],name).toBe(fingerprint);
});

test('CLM spandrel geometry UV and PBR remain identical at campus and close scales',async()=>{
 const proof=await read('result/blender/stage137/saved-verification.json');
 const catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('137');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);
 const building=catalogue.buildings.find(b=>b.code==='CLM');
 const accepted=new Set(proof.ownedMaterialNames.CLM);const summaries=[];
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
  for(const mesh of glb.meshes)for(const p of mesh.primitives){
   const m=glb.materials[p.material];if(!accepted.has(m.name.replace(/^WEB_(DETAIL_)?/,'')))continue;
   primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,alphaMode:m.alphaMode??'OPAQUE',doubleSided:m.doubleSided??false,finish:m.extras?.surfaceDetail});
  }
  expect(primitives.length).toBeGreaterThan(0);expect(new Set(primitives.map(p=>p.material)).size).toBe(3);summaries.push(primitives);
 }
 expect(summaries[0]).toEqual(summaries[1]);
 expect(summaries[0].find(p=>p.material.includes('opaque_spandrel')).alphaMode).toBe('OPAQUE');
});

test('CLM release retains other accepted exteriors and every interior asset',async()=>{
 const before=await read('result/blender/stage137/catalogue-before.json');
 const catalogue=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage137/saved-verification.json');
 const changed=new Set(proof.components.map(c=>c.code));
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));
 expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const b of catalogue.buildings){
  const old=before.buildings.find(o=>o.code===b.code);
  for(const key of ['detailedInterior','interiorSpaces','interiorStudy','interiorBounds','interiorView'])expect(b[key],b.code+' '+key).toEqual(old[key]);
  if(!changed.has(b.code))expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
  const interiorAssets=[b.detailedInterior,...(b.interiorSpaces??[]).map(space=>space.detailedInterior??space.asset??space)];
  for(const asset of interiorAssets.filter(a=>a?.url&&a?.sha256))expect(sha256(await readFile('dist'+asset.url)),b.code+' '+asset.url).toBe(asset.sha256);
 }
});

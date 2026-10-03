import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
const componentDir='result/blender/mar_envelope_next';
const recoveryDir='result/blender/stage138/mar-recovery';

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

test('MAR three north window rows retain real openings and recover independently',async()=>{
 const audit=await read(componentDir+'/audit.json'),accepted=await read(componentDir+'/verification.json');
 expect(audit.ownedObjects).toEqual(['MAR_NEXT_ENVELOPE_north_three_row_walls','MAR_NEXT_ENVELOPE_north_three_row_glass','MAR_NEXT_ENVELOPE_north_three_row_frames']);
 expect(audit.archivedObjects).toEqual(['MAR_D5_north115_panel','MAR_D5_north115_glass','MAR_D5_north115_frame']);
 expect(audit.windowRegistration.newRows).toEqual([[24,26.2],[27,29.2],[30,32.2]]);
 expect(audit.windowRegistration.newWindowCount).toBe(45);expect(audit.windowRegistration.retainedReturnWindowCount).toBe(16);
 expect(audit.windowRegistration.absoluteDimensionsEstimated).toBe(true);
 expect(audit.retainedFaces.map(f=>f.faces)).toEqual([79,16,80]);expect(audit.removedFaceCounts).toEqual([130,30,150]);
 expect(audit.materials.every(m=>!m.changed&&JSON.stringify(m.original)===JSON.stringify(m.owned))).toBe(true);
 expect(accepted.originalGeometryPreserved).toBe(true);expect(accepted.unrelatedVisibilityPreserved).toBe(true);expect(accepted.savedComponentReopened).toBe(true);expect(accepted.fissureProbesUnchanged).toBe(true);
 expect(accepted.componentSha256).toBe(sha256(await readFile(componentDir+'/marshall-north-three-row-envelope-component.blend')));
 expect(accepted.reloadedProbes).toEqual(audit.afterProbes);expect(audit.afterProbes).toHaveLength(139);
 for(let i=0;i<90;i++)expect(audit.afterProbes[i].firstObject).toBe(audit.ownedObjects[i%2?0:1]);
 expect(audit.afterProbes.slice(90,135).every(p=>p.firstObject===audit.ownedObjects[1])).toBe(true);
 const aliases=new Map(audit.ownedObjects.map((n,i)=>[n,audit.archivedObjects[i]]));
 expect(audit.afterProbes.slice(135).map(p=>({...p,firstObject:aliases.get(p.firstObject)??p.firstObject}))).toEqual(audit.beforeProbes.slice(135));
 const recovered=await read(recoveryDir+'/verification.json'),recoveryAudit=await read(recoveryDir+'/audit.json');
 const merge=await read('result/blender/stage138/saved-verification.json');
 expect(recoveryAudit.baselineSha256).toBe(merge.sourceModelSha256);expect(recovered.baselineUnchanged).toBe(true);
 expect(recovered.savedComponentReopened).toBe(true);expect(recovered.originalGeometryPreserved).toBe(true);expect(recovered.unrelatedVisibilityPreserved).toBe(true);
 expect(recovered.reloadedProbes).toEqual(accepted.reloadedProbes);expect(recovered.nativeRender).toBeNull();
 for(const name of merge.ownedObjects.filter(n=>!audit.ownedObjects.includes(n)))expect(recoveryAudit.originalFingerprints[name],name).toMatch(/^[a-f0-9]{64}$/);
 for(const [name,fp]of Object.entries(audit.originalFingerprints))expect(recoveryAudit.originalFingerprints[name],name).toBe(fp);
});

test('MAR envelope geometry UV PBR and retained asset ranges match the release',async()=>{
 const proof=await read('result/blender/stage138/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('138');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(proof.savedSceneReopened).toBe(true);expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);
 const b=catalogue.buildings.find(b=>b.code==='MAR'),accepted=new Set(proof.ownedMaterialNames.MAR),summaries=[];
 for(const url of ['/models/campus.glb',b.detailedExterior.url]){
  const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
  for(const mesh of glb.meshes)for(const p of mesh.primitives){const m=glb.materials[p.material];if(!accepted.has(m.name.replace(/^WEB_(DETAIL_)?/,'')))continue;
   primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,alphaMode:m.alphaMode??'OPAQUE',doubleSided:m.doubleSided??false,finish:m.extras?.surfaceDetail});}
  expect(primitives.length).toBeGreaterThan(0);expect(new Set(primitives.map(p=>p.material)).size).toBe(3);summaries.push(primitives);
 }
 expect(summaries[0]).toEqual(summaries[1]);
 const before=await read('result/blender/stage138/catalogue-before.json'),changed=new Set(proof.components.map(c=>c.code));
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const building of catalogue.buildings){const old=before.buildings.find(o=>o.code===building.code);
  for(const key of ['detailedInterior','interiorSpaces','interiorStudy','interiorBounds','interiorView'])expect(building[key],building.code+' '+key).toEqual(old[key]);
  if(!changed.has(building.code))expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  const assets=[building.detailedInterior,...(building.interiorSpaces??[]).map(space=>space.detailedInterior??space.asset??space)];
  for(const asset of assets.filter(a=>a?.url&&a?.sha256))expect(sha256(await readFile('dist'+asset.url)),building.code+' '+asset.url).toBe(asset.sha256);
 }
});

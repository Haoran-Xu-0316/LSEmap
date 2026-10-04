import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const stage='result/blender/stage141';
const parts=[['61A','aldwych_envelope_next','aldwych-envelope-component.blend'],['LRB','lrb_envelope_next','library-envelope-component.blend'],['OLD','old_access_next','old-access-component.blend']];
function geometryDigest(glb,bytes,primitive){
 const extension=primitive.extensions?.KHR_draco_mesh_compression;
 if(!extension)throw Error('Missing compressed production geometry');
 const view=glb.bufferViews[extension.bufferView],start=28+bytes.readUInt32LE(12)+(view.byteOffset??0);
 const accessor=index=>{const a=glb.accessors[index];return {count:a.count,type:a.type,componentType:a.componentType,min:a.min,max:a.max};};
 return {sha256:sha(bytes.subarray(start,start+view.byteLength)),decoderAttributes:extension.attributes,indices:accessor(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([name,index])=>[name,accessor(index)]))};
}

test('OLD access 61A dormers and LRB artwork retain their source scene and verified surfaces',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.components.map(c=>c.code)).toEqual(parts.map(c=>c[0]));expect(proof.retainedOriginalObjects).toBe(5616);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.savedSceneReopened).toBe(true);
 for(const [code,folder,filename]of parts){
  const dir='result/blender/'+folder,audit=await read(dir+'/audit.json'),accepted=await read(dir+'/verification.json');
  expect(audit.baselineSha256,code).toBe(proof.baselineSha256);expect(accepted.componentSha256,code).toBe(sha(await readFile(dir+'/'+filename)));
  expect(accepted.savedComponentReopened,code).toBe(true);expect(accepted.originalGeometryPreserved,code).toBe(true);expect(accepted.unrelatedVisibilityPreserved,code).toBe(true);
  expect(audit.ownedObjects.every(n=>n.startsWith(code+'_NEXT_')),code).toBe(true);
  expect(audit.originalFingerprints&&Object.keys(audit.originalFingerprints),code).toHaveLength(5616);
 }
 const roof=await read('result/blender/aldwych_envelope_next/verification.json');
 expect(roof.dormers).toBe(24);expect(roof.cornerDormersRetained).toBe(2);expect(roof.reloadedProbes).toHaveLength(148);expect(roof.retainedFacadeProbesUnchanged).toBe(true);
 const access=await read('result/blender/old_access_next/verification.json'),registration=(await read('result/blender/old_access_next/audit.json')).registration;
 expect(access.externalSteps).toBe(4);expect(access.internalSteps).toBe(4);expect(access.thresholdContinuous).toBe(true);expect(access.oldWallBelowDoorRemoved).toBe(true);expect(access.reloadedProbes).toHaveLength(34);
 expect(registration.nativePavedStreetZ).toBe(.05);expect(registration.nativeGFZ).toBe(1.245);expect(registration.thresholdZ).toBeCloseTo(.69,6);expect(registration.absoluteDimensionsEstimated).toBe(true);
 const lamp=await read('result/blender/lrb_envelope_next/verification.json'),art=(await read('result/blender/lrb_envelope_next/audit.json')).artworkIdentity;
 expect(lamp.fourOriginalAperturesFilled).toBe(true);expect(lamp.singleDisplayMesh).toBe(true);expect(lamp.webEmissionRetained).toBe(true);expect(lamp.retainedWindowPolygonUVMaterialsPreserved).toBe(true);
 const dense=await read('result/blender/lrb_envelope_next/dense-probes.json');expect(dense).toHaveLength(55);const hits=dense.map(p=>p.first[0][1]);expect(hits.filter(n=>n==='LRB_NEXT_ENVELOPE_continuous_artwork_corner_wall')).toHaveLength(49);expect(hits.filter(n=>n==='LRB_NEXT_ENVELOPE_Blue_Rain_static_photo_display')).toHaveLength(1);expect(hits.filter(n=>n.includes('Cornice_stringcourse'))).toHaveLength(5);
 expect(lamp.surfaceProbes).toHaveLength(lamp.staticPhotoSampleCount);expect(lamp.allFirstHitsAreDisplayOrExistingCornice).toBe(true);expect(lamp.physicalLEDCountIsNotSampleCount).toBe(true);expect(art.physicalLEDCount).toBe(23520);expect(art.nativeRepresentation).toContain('Static');
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.savedSceneReopened).toBe(true);expect(rebuilt.objects).toBe(5616+proof.ownedObjects.length);
});

test('three corrected buildings share compressed geometry UV PBR and emission at both viewing scales',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.version).toBe('141');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 for(const [code]of parts){
  const building=catalogue.buildings.find(b=>b.code===code),accepted=new Set(proof.ownedMaterialNames[code]),summaries=[];
  for(const url of ['/models/campus.glb',building.detailedExterior.url]){
   const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
   for(const mesh of glb.meshes)for(const p of mesh.primitives){const m=glb.materials[p.material];if(!accepted.has(m.name.replace(/^WEB_(DETAIL_)?/,'')))continue;
    primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,alphaMode:m.alphaMode??'OPAQUE',doubleSided:m.doubleSided??false,finish:m.extras?.surfaceDetail,emissive:m.emissiveFactor,emissionStrength:m.extensions?.KHR_materials_emissive_strength,authoredEmission:m.extras?.webEmission});}
   expect(primitives.length,code+' '+url).toBeGreaterThan(0);for(const p of primitives)expect(p.geometry.attributes.TEXCOORD_0,code).toBeTruthy();summaries.push(primitives);
  }
  expect(summaries[0],code).toEqual(summaries[1]);
  if(code==='61A'){const slate=summaries[0].filter(p=>p.material.endsWith('61A_slate'));expect(slate.length).toBeGreaterThan(0);for(const p of slate){expect(p.pbr.baseColorFactor[0]).toBeCloseTo(.12,5);expect(p.pbr.baseColorFactor[1]).toBeCloseTo(.15,5);expect(p.pbr.baseColorFactor[2]).toBeCloseTo(.16,5);}}
 }
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const building of catalogue.buildings){const old=before.buildings.find(o=>o.code===building.code);
  for(const key of ['detailedInterior','interiorSpaces','interiorStudy','interiorBounds','interiorView'])expect(building[key],building.code+' '+key).toEqual(old[key]);
  if(!parts.some(([code])=>code===building.code))expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  const assets=[building.detailedInterior,...(building.interiorSpaces??[]).map(space=>space.detailedInterior)];
  for(const asset of assets.filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url)),building.code+' '+asset.url).toBe(asset.sha256);
 }
});

test('OLD 61A and LRB corrected exteriors and existing interiors load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const [code]of parts)for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});

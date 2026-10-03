import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const stage='result/blender/stage140';
const parts=[['KSW','ksw_envelope_next','kingsway-envelope-component.blend']];
function geometryDigest(glb,bytes,primitive){
 const extension=primitive.extensions?.KHR_draco_mesh_compression;
 if(!extension)throw Error('Missing compressed production geometry');
 const view=glb.bufferViews[extension.bufferView],start=28+bytes.readUInt32LE(12)+(view.byteOffset??0);
 const accessor=index=>{const a=glb.accessors[index];return {count:a.count,type:a.type,componentType:a.componentType,min:a.min,max:a.max};};
 return {sha256:sha(bytes.subarray(start,start+view.byteLength)),decoderAttributes:extension.attributes,indices:accessor(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([name,index])=>[name,accessor(index)]))};
}

test('KSW saved storefront component retain their source scene and real opening checks',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.components.map(c=>c.code)).toEqual(parts.map(c=>c[0]));expect(proof.retainedOriginalObjects).toBe(5611);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.savedSceneReopened).toBe(true);
 for(const [code,folder,filename]of parts){
  const dir='result/blender/'+folder,audit=await read(dir+'/audit.json'),accepted=await read(dir+'/verification.json');
  expect(audit.baselineSha256,code).toBe(proof.baselineSha256);expect(accepted.componentSha256,code).toBe(sha(await readFile(dir+'/'+filename)));
  expect(accepted.savedComponentReopened,code).toBe(true);expect(accepted.originalGeometryPreserved,code).toBe(true);expect(accepted.unrelatedVisibilityPreserved,code).toBe(true);
  expect(audit.ownedObjects.every(n=>n.startsWith(code+'_NEXT_ENVELOPE_')),code).toBe(true);
  expect(audit.originalFingerprints&&Object.keys(audit.originalFingerprints),code).toHaveLength(5611);
 }
 const audit=await read('result/blender/ksw_envelope_next/audit.json'),accepted=await read('result/blender/ksw_envelope_next/verification.json');
 expect(audit.ownedObjects).toHaveLength(5);expect(audit.archivedObjects).toHaveLength(4);
 expect(audit.storefrontRegistration.absoluteDimensionsEstimated).toBe(true);
 expect(accepted.reloadedProbes).toHaveLength(29);expect(accepted.upperGeometryProbesUnchanged).toBe(true);
 expect(accepted.reloadedProbes.filter(p=>p.kind==='opaqueBand').every(p=>p.firstObject==='KSW_NEXT_ENVELOPE_opaque_storefront_bands')).toBe(true);
 expect(accepted.reloadedProbes.filter(p=>p.kind==='upperLowerGlass').every(p=>p.firstObject==='KSW_NEXT_ENVELOPE_window_glass')).toBe(true);
 expect(accepted.opaqueBands).toBe(2);expect(accepted.storefrontWindows).toBe(2);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.savedSceneReopened).toBe(true);expect(rebuilt.objects).toBe(5611+proof.ownedObjects.length);
});

test('KSW compressed geometry UV and PBR match both viewing scales and retain every other asset',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.version).toBe('140');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 for(const [code]of parts){
  const building=catalogue.buildings.find(b=>b.code===code),accepted=new Set(proof.ownedMaterialNames[code]),summaries=[];
  for(const url of ['/models/campus.glb',building.detailedExterior.url]){
   const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
   for(const mesh of glb.meshes)for(const p of mesh.primitives){const m=glb.materials[p.material];if(!accepted.has(m.name.replace(/^WEB_(DETAIL_)?/,'')))continue;
    primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,alphaMode:m.alphaMode??'OPAQUE',doubleSided:m.doubleSided??false,finish:m.extras?.surfaceDetail});}
   expect(primitives.length,code+' '+url).toBeGreaterThan(0);for(const p of primitives)expect(p.geometry.attributes.TEXCOORD_0,code).toBeTruthy();summaries.push(primitives);
  }
  expect(summaries[0],code).toEqual(summaries[1]);
 }
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const building of catalogue.buildings){const old=before.buildings.find(o=>o.code===building.code);
  for(const key of ['detailedInterior','interiorSpaces','interiorStudy','interiorBounds','interiorView'])expect(building[key],building.code+' '+key).toEqual(old[key]);
  if(!parts.some(([code])=>code===building.code))expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  const assets=[building.detailedInterior,...(building.interiorSpaces??[]).map(space=>space.detailedInterior)];
  for(const asset of assets.filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url)),building.code+' '+asset.url).toBe(asset.sha256);
 }
});

test('KSW corrected exterior and their existing interiors load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const [code]of parts)for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});

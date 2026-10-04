import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const stage='result/blender/stage143';
const parts=[['OLD','old_side_approach_next','old-side-approach-component.blend'],['MAR','mar_panel_joints_next','marshall-blank-wall-component.blend'],['STC','stc_artwork_next','stc-artwork-component.blend']];
function geometryDigest(glb,bytes,primitive){
 const extension=primitive.extensions?.KHR_draco_mesh_compression;
 if(!extension)throw Error('Missing compressed production geometry');
 const view=glb.bufferViews[extension.bufferView],start=28+bytes.readUInt32LE(12)+(view.byteOffset??0);
 const accessor=index=>{const a=glb.accessors[index];return {count:a.count,type:a.type,componentType:a.componentType,min:a.min,max:a.max};};
 return {sha256:sha(bytes.subarray(start,start+view.byteLength)),decoderAttributes:extension.attributes,indices:accessor(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([name,index])=>[name,accessor(index)]))};
}

test('OLD approach MAR blank wall and STC artwork retain verified source geometry',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.components.map(c=>c.code)).toEqual(parts.map(c=>c[0]));expect(proof.retainedOriginalObjects).toBe(5662);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.savedSceneReopened).toBe(true);expect(proof.ownedObjects).toHaveLength(32);
 for(const [code,folder,filename]of parts){const dir='result/blender/'+folder,audit=await read(dir+'/audit.json'),accepted=await read(dir+'/verification.json');
  expect(audit.baselineSha256,code).toBe(proof.baselineSha256);expect(accepted.componentSha256,code).toBe(sha(await readFile(dir+'/'+filename)));
  expect(accepted.savedComponentReopened,code).toBe(true);expect(accepted.originalGeometryPreserved,code).toBe(true);expect(accepted.unrelatedVisibilityPreserved,code).toBe(true);expect(accepted.originalObjectCount).toBe(5662);
 }
 const old=await read('result/blender/old_side_approach_next/verification.json');expect(old.reloadedProbes).toHaveLength(112);
 for(const key of ['startSeamConnected','endSeamFlushToStreet','retainedFourStepFlightsUnchanged','clearTravelLine','clearHeadTravelLine','junctionClosed','retainedFacadeContactsUnchanged'])expect(old[key],key).toBe(true);
 expect(old.junctionMissingBeforeNowClosed).toBe(28);expect(old.retainedCorniceJunctionContacts).toBe(2);
 const mar=await read('result/blender/mar_panel_joints_next/verification.json');expect(mar.falseWindowCountRemoved).toBe(35);expect(mar.blankWallFirstHitProbes).toHaveLength(35);expect(mar.physicalJointRecessProbes).toHaveLength(4);expect(mar.realAdjacentEndWindowCount).toBe(40);expect(mar.allRealAdjacentEndWindowFirstHitsPreserved).toBe(true);expect(mar.retainedFaceGeometryUVMaterialSlotsPreserved).toBe(true);
 const stc=await read('result/blender/stc_artwork_next/verification.json');expect(stc.motifCount).toBe(6);expect(stc.firstSurfaceChecks).toHaveLength(12);expect(stc.originalBorderPreserved).toBe(true);expect(stc.textPlaqueChanged).toBe(false);expect(stc.embeddedImageTextures).toBe(0);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.savedSceneReopened).toBe(true);expect(rebuilt.objects).toBe(5694);
});

test('OLD MAR STC share compressed geometry UV PBR and emission at both viewing scales',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.version).toBe('143');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 for(const [code]of parts){
  const building=catalogue.buildings.find(b=>b.code===code),accepted=new Set(proof.ownedMaterialNames[code]),summaries=[];
  for(const url of ['/models/campus.glb',building.detailedExterior.url]){
   const bytes=await readFile('dist'+url),glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))),primitives=[];
   for(const mesh of glb.meshes)for(const p of mesh.primitives){const m=glb.materials[p.material];if(!accepted.has(m.name.replace(/^WEB_(DETAIL_)?/,'')))continue;
    primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),geometry:geometryDigest(glb,bytes,p),pbr:m.pbrMetallicRoughness,alphaMode:m.alphaMode??'OPAQUE',doubleSided:m.doubleSided??false,finish:m.extras?.surfaceDetail,emissive:m.emissiveFactor,emissionStrength:m.extensions?.KHR_materials_emissive_strength,authoredEmission:m.extras?.webEmission});}
   expect(primitives.length,code+' '+url).toBeGreaterThan(0);for(const p of primitives)expect(p.geometry.attributes.TEXCOORD_0,code).toBeTruthy();summaries.push(primitives);
  }
  expect(summaries[0],code).toEqual(summaries[1]);
 }
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const building of catalogue.buildings){const old=before.buildings.find(o=>o.code===building.code);
  for(const key of ['detailedInterior','interiorSpaces','interiorStudy','interiorBounds','interiorView'])expect(building[key],building.code+' '+key).toEqual(old[key]);
  if(!parts.some(([code])=>code===building.code))for(const key of ['url','sha256','bytes'])expect(building.detailedExterior?.[key],building.code+' '+key).toEqual(old.detailedExterior?.[key]);
  const assets=[building.detailedInterior,...(building.interiorSpaces??[]).map(space=>space.detailedInterior)];
  for(const asset of assets.filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url)),building.code+' '+asset.url).toBe(asset.sha256);
 }
});

test('OLD MAR STC corrected exteriors and existing interiors load on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const [code]of parts)for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#'+code);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
 }
 expect(errors).toEqual([]);
});

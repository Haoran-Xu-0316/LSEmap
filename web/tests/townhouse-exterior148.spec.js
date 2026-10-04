import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const stage='result/blender/stage148';
const baselineSha='02607a215a50db6fb0807091000c271e93a1686d035e9512fe565acd1de30e6a';
const changedCodes=['LCH','SHF','POR','51L'];
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const materialName=material=>material.name.replace(/^WEB_(DETAIL_)?/,'');
function geometryDigest(glb,bytes,primitive){
 const extension=primitive.extensions?.KHR_draco_mesh_compression;
 if(!extension)throw Error('Missing compressed production geometry');
 const view=glb.bufferViews[extension.bufferView];
 const start=28+bytes.readUInt32LE(12)+(view.byteOffset??0);
 const accessor=index=>{const a=glb.accessors[index];return {count:a.count,type:a.type,componentType:a.componentType,min:a.min,max:a.max};};
 return {sha256:sha(bytes.subarray(start,start+view.byteLength)),decoderAttributes:extension.attributes,indices:accessor(primitive.indices),attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([name,index])=>[name,accessor(index)]))};
}
async function assetDocument(url){
 const bytes=await readFile('dist'+url);
 return {bytes,glb:JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)))};
}
function matchingPrimitives({bytes,glb},accepted){
 const results=[];
 for(const mesh of glb.meshes)for(const primitive of mesh.primitives){
  const material=glb.materials[primitive.material];
  if(!accepted.has(materialName(material)))continue;
  results.push({material:materialName(material),geometry:geometryDigest(glb,bytes,primitive),pbr:material.pbrMetallicRoughness,alphaMode:material.alphaMode??'OPAQUE',doubleSided:material.doubleSided??false,finish:material.extras?.surfaceDetail,emissive:material.emissiveFactor,emissionStrength:material.extensions?.KHR_materials_emissive_strength,authoredEmission:material.extras?.webEmission});
 }
 return results;
}



test('stage148 independent facade components preserve the verified native baseline',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.baselineSha256).toBe(baselineSha);expect(proof.retainedOriginalObjects).toBe(5829);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.savedSceneReopened).toBe(true);
 const names=[],archives=[];
 for(const component of proof.components){
  const a=await read(component.audit),v=await read(component.verification);
  expect(a.baselineSha256).toBe(baselineSha);expect(v.componentSha256).toBe(sha(await readFile(component.source)));
  expect(v.savedComponentReopened).toBe(true);expect(v.originalGeometryPreserved).toBe(true);expect(v.unrelatedVisibilityPreserved).toBe(true);expect(v.originalObjectCount).toBe(5829);
  names.push(...a.ownedObjects);archives.push(...a.archivedObjects);
 }
 expect(proof.ownedObjects).toEqual(names);expect(proof.archivedObjects).toEqual(archives);
 expect(new Set(names).size).toBe(names.length);expect(new Set(archives).size).toBe(archives.length);
 const lch=await read('result/blender/lch_exterior148/verification.json');
 expect(lch.reloadedProbes).toHaveLength(45);expect(lch.nativePreviewInspected).toBe(true);
 for(const p of lch.reloadedProbes)expect(p.firstObject).toBe(p.expected);
 for(const [name,count] of [['verification.json',23],['lincoln51-verification.json',2]]){
  const v=await read('result/blender/por_exterior148/'+name);
  expect(v.glassFirstHits).toBe(count);expect(v.nearFieldAtLeast2mClear).toBe(count);expect(v.reloadedBrowserOpacityVerified).toBe(true);expect(v.webOpacity).toBe(.82);
  expect(v.reloadedFrontProbes).toHaveLength(count);expect(v.reloadedBehindProbes).toHaveLength(count);
  for(const p of v.reloadedBehindProbes)if(p.firstObject)expect(p.distance).toBeGreaterThanOrEqual(2);
  if(count===2){expect(v.realDoorApertureProbes).toHaveLength(8);for(const p of v.realDoorApertureProbes)expect(p.opaqueLeafBlocked).toBe(false);expect(v.retainedLowerSolidDoorProbes).toHaveLength(2);}
 }
 const shf=await read('result/blender/shf_exterior148/verification.json');
 expect(shf.firstSurfaceChecks).toHaveLength(72);expect(shf.glassGeometryUVMaterialAndOpticsPreserved).toBe(true);expect(shf.unknownLeftDormerRetained).toBe(true);
 for(const p of shf.firstSurfaceChecks)expect(p.firstObject).toBe(p.expected);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.objects).toBe(5829+names.length);
});

test('stage148 four facades retain identical overview and closeup compressed geometry UV and PBR',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('148');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 const campus=await assetDocument('/models/campus.glb');
 for(const code of changedCodes){
  const detail=await assetDocument(catalogue.buildings.find(b=>b.code===code).detailedExterior.url),accepted=new Set(proof.ownedMaterialNames[code]);
  const overview=matchingPrimitives(campus,accepted),closeup=matchingPrimitives(detail,accepted);
  expect(closeup.length,code).toBeGreaterThan(0);expect(overview,code).toEqual(closeup);
  expect(new Set(closeup.map(p=>p.material)),code).toEqual(accepted);
  if(['POR','51L'].includes(code)){
   const glass=closeup.filter(p=>p.alphaMode==='BLEND');expect(glass.length).toBeGreaterThan(0);
   for(const p of glass)expect(p.pbr.baseColorFactor[3]).toBeCloseTo(.82,5);
  }
 }
});

test('stage148 retains every existing interior and all unrelated exterior assets byte for byte',async()=>{
 const catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const b of catalogue.buildings){
  const p=before.buildings.find(o=>o.code===b.code);
  for(const key of ['detailedInterior','interiorStudy','interiorBounds','interiorView','interiorSpaces'])expect(b[key],b.code+' '+key).toEqual(p[key]);
  if(!changedCodes.includes(b.code))for(const key of ['url','sha256','bytes'])expect(b.detailedExterior?.[key],b.code+' '+key).toEqual(p.detailedExterior?.[key]);
  for(const asset of [b.detailedInterior,...(b.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url))).toBe(asset.sha256);
 }
});

for(const width of [1440,390])test(`stage148 four reviewed facades load at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of changedCodes){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  await expect(page.locator('#interior-view')).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),code).toBe(true);
 }
 expect(errors).toEqual([]);
});

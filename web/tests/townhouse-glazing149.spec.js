import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const stage='result/blender/stage149';
const baselineSha='536b63660f8542ecae569523ef8beb2c45013068487f2aaa160820225e7076f2';
const changedCodes=['LCH','SHF','SAL'];
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



test('stage149 source components preserve the exact native baseline and verified apertures',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.baselineSha256).toBe(baselineSha);expect(proof.retainedOriginalObjects).toBe(5843);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.savedSceneReopened).toBe(true);
 const names=[],archives=[];
 for(const component of proof.components){
  const a=await read(component.audit),v=await read(component.verification);
  expect(a.baselineSha256).toBe(baselineSha);expect(v.componentSha256).toBe(sha(await readFile(component.source)));
  expect(v.savedComponentReopened).toBe(true);expect(v.originalGeometryPreserved).toBe(true);expect(v.unrelatedVisibilityPreserved).toBe(true);expect(v.originalObjectCount).toBe(5843);
  names.push(...a.ownedObjects);archives.push(...a.archivedObjects);
 }
 expect(proof.ownedObjects).toEqual(names);expect(proof.archivedObjects).toEqual(archives);
 expect(new Set(names).size).toBe(names.length);expect(new Set(archives).size).toBe(archives.length);
 const lch=await read('result/blender/lch_glazing149/verification.json');
 expect(lch.reloadedProbes).toHaveLength(179);expect(lch.nativePreviewInspected).toBe(true);expect(lch.webOpacityVerified).toBe(.78);
 expect(lch.reloadedProbes.filter(p=>p.behindObject)).toHaveLength(8);
 for(const p of lch.reloadedProbes){expect(p.firstObject).toMatch(/^LCH_NEXT_GLAZING149_/);if(p.behindObject){expect(p.behindObject).toContain('stone');expect(p.behindDistance).toBeGreaterThan(.15);expect(p.behindDistance).toBeLessThan(.20);}}
 const shf=await read('result/blender/shf_glazing149/verification.json');
 expect(shf.firstSurfaceChecks).toHaveLength(91);expect(shf.glazingGeometryUVAndSourceColorsPreserved).toBe(true);expect(shf.opaqueLeftDormerRetained).toBe(true);
 for(const p of shf.firstSurfaceChecks)expect(p.firstObject).toBe(p.expected);
 const unknown=shf.firstSurfaceChecks.filter(p=>p.kind==='unknown-left-dormer-retained');expect(unknown).toHaveLength(2);
 const registered=shf.firstSurfaceChecks.filter(p=>p.kind==='registered-dormer-light');expect(registered).toHaveLength(36);
 for(const p of registered){expect(p.noOpaqueNearfieldCap).toBe(true);if(p.behind)expect(p.behind[0]).toBeGreaterThan(1.08);}
 const sal=await read('result/blender/sal_glazing149/verification.json');
 expect(sal.glassFirstHits).toBe(30);expect(sal.nearFieldAtLeast2mClear).toBe(24);expect(sal.gableApertureCount).toBe(6);
 expect(sal.untargetedGlassMaterialPreserved).toBe(true);expect(sal.existingFourLightFramesAndOrielPreserved).toBe(true);
 expect(sal.trueGableThroughProbes).toHaveLength(24);for(const p of sal.trueGableThroughProbes)expect(p.masonryBlocked).toBe(false);
 expect(sal.gableBehindExistingRoofProbes).toHaveLength(6);for(const p of sal.gableBehindExistingRoofProbes){expect(p.firstObject).toBe('SAL_Roof_slates');expect(p.distance).toBeGreaterThan(1.4);}
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.objects).toBe(5843+names.length);
});

test('stage149 glazing and real apertures match in overview and closeup including compressed geometry UV and PBR',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('149');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 const campus=await assetDocument('/models/campus.glb'),opacity={LCH:.78,SHF:.84,SAL:.82};
 for(const code of changedCodes){
  const detail=await assetDocument(catalogue.buildings.find(b=>b.code===code).detailedExterior.url),accepted=new Set(proof.ownedMaterialNames[code]);
  const overview=matchingPrimitives(campus,accepted),closeup=matchingPrimitives(detail,accepted);
  expect(closeup.length,code).toBeGreaterThan(0);expect(overview,code).toEqual(closeup);
  expect(new Set(closeup.map(p=>p.material)),code).toEqual(accepted);
  const glass=closeup.filter(p=>p.alphaMode==='BLEND');expect(glass.length,code).toBeGreaterThan(0);
  for(const p of glass)expect(p.pbr.baseColorFactor[3],code).toBeCloseTo(opacity[code],5);
 }
});

test('stage149 retains every existing interior and all unrelated exterior assets byte for byte',async()=>{
 const catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const b of catalogue.buildings){
  const p=before.buildings.find(o=>o.code===b.code);
  for(const key of ['detailedInterior','interiorStudy','interiorBounds','interiorView','interiorSpaces'])expect(b[key],b.code+' '+key).toEqual(p[key]);
  if(!changedCodes.includes(b.code))for(const key of ['url','sha256','bytes'])expect(b.detailedExterior?.[key],b.code+' '+key).toEqual(p.detailedExterior?.[key]);
  for(const asset of [b.detailedInterior,...(b.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url))).toBe(asset.sha256);
 }
});

for(const width of [1440,390])test(`stage149 three reviewed facades load at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of changedCodes){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  if(code!=='SAL')await expect(page.locator('#interior-view')).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),code).toBe(true);
 }
 expect(errors).toEqual([]);
});

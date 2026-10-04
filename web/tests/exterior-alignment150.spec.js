import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const stage='result/blender/stage150';
const baselineSha='9057f87e47163c1d900d1365ce08315e24193f7443fbe915b9e43833eb05704e';
const changedCodes=['LCH','SHF','SAL','51L'];
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



test('stage150 keeps the verified native and clears seven real arch-frame boundaries',async()=>{
 const proof=await read(stage+'/saved-verification.json'),v=await read('result/blender/lincoln51_arch_next/verification.json'),a=await read('result/blender/lincoln51_arch_next/audit.json');
 expect(proof.baselineSha256).toBe(baselineSha);expect(proof.retainedOriginalObjects).toBe(5857);
 for(const k of ['originalGeometryRetained','unrelatedVisibilityPreserved','savedSceneReopened'])expect(proof[k]).toBe(true);
 expect(a.baselineSha256).toBe(baselineSha);expect(v.componentSha256).toBe(sha(await readFile(proof.components[0].source)));
 expect(v.originalObjectCount).toBe(5857);expect(v.originalGeometryPreserved).toBe(true);expect(v.unrelatedVisibilityPreserved).toBe(true);expect(v.nativePreviewInspected).toBe(true);expect(v.savedComponentReopened).toBe(true);
 expect(proof.ownedObjects).toEqual(a.ownedObjects);expect(proof.archivedObjects).toEqual(a.archivedObjects);expect(a.ownedObjects).toHaveLength(1);expect(a.archivedObjects).toHaveLength(1);expect(a.windows).toHaveLength(7);
 for(const k of ['reloadedProbes','reloadedEvaluatedProbes']){expect(v[k]).toHaveLength(308);for(const p of v[k]){if(p.kind==='retainedOuterStone')expect(p.firstObject).toBe(a.ownedObjects[0]);else{expect(p.expected).toBeTruthy();expect(Array.isArray(p.expected)?p.expected:[p.expected]).toContain(p.firstObject);}}expect(v[k].filter(p=>p.kind==='frameClearance')).toHaveLength(273);expect(v[k].filter(p=>p.kind==='retainedArchGlass')).toHaveLength(28);expect(v[k].filter(p=>p.kind==='retainedOuterStone')).toHaveLength(7);}
 expect(v.innerClearanceMoveRangeM[0]).toBeGreaterThan(.029);expect(v.innerClearanceMoveRangeM[1]).toBeLessThan(.031);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.objects).toBe(5858);
});

test('stage150 glazing and real apertures match in overview and closeup including compressed geometry UV and PBR',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('150');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 const earlier=await read('result/blender/stage149/saved-verification.json');
 const campus=await assetDocument('/models/campus.glb'),opacity={LCH:.78,SHF:.84,SAL:.82};
 for(const code of changedCodes){
  const detail=await assetDocument(catalogue.buildings.find(b=>b.code===code).detailedExterior.url),accepted=new Set((code==='51L'?proof:earlier).ownedMaterialNames[code]);
  const overview=matchingPrimitives(campus,accepted),closeup=matchingPrimitives(detail,accepted);
  expect(closeup.length,code).toBeGreaterThan(0);expect(overview,code).toEqual(closeup);
  expect(new Set(closeup.map(p=>p.material)),code).toEqual(accepted);
  if(code==='51L')continue;
  const glass=closeup.filter(p=>p.alphaMode==='BLEND');expect(glass.length,code).toBeGreaterThan(0);
  for(const p of glass)expect(p.pbr.baseColorFactor[3],code).toBeCloseTo(opacity[code],5);
 }
});

test('stage150 retains every existing interior and all unrelated exterior assets byte for byte',async()=>{
 const catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const b of catalogue.buildings){
  const p=before.buildings.find(o=>o.code===b.code);
  for(const key of ['detailedInterior','interiorStudy','interiorBounds','interiorView','interiorSpaces'])expect(b[key],b.code+' '+key).toEqual(p[key]);
  if(b.code!=='51L')for(const key of ['url','sha256','bytes'])expect(b.detailedExterior?.[key],b.code+' '+key).toEqual(p.detailedExterior?.[key]);
  for(const asset of [b.detailedInterior,...(b.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url))).toBe(asset.sha256);
 }
});

for(const width of [1440,390])test(`stage150 four reviewed facades load at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of changedCodes){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  if(code!=='SAL')await expect(page.locator('#interior-view')).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),code).toBe(true);
 }
 expect(errors).toEqual([]);
});

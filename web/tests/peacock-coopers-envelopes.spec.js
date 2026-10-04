import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const stage='result/blender/stage146';
const baselineSha='84e45149527c586960d8c8a9f3cf94d0a29a68e92fe5d17e251f45158fad00b3';
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


test('stage146 PEA real openings and49L registered fire exit retain native evidence',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.baselineSha256).toBe(baselineSha);expect(proof.retainedOriginalObjects).toBe(5754);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.savedSceneReopened).toBe(true);
 expect(proof.ownedObjects).toHaveLength(30);expect(proof.archivedObjects).toHaveLength(22);
 for(const [folder,filename]of [['peacock_envelope_next','peacock-envelope-component.blend'],['coopers_envelope_next','coopers-envelope-component.blend']]){
  const dir='result/blender/'+folder,a=await read(dir+'/audit.json'),v=await read(dir+'/verification.json');
  expect(a.baselineSha256).toBe(baselineSha);expect(v.componentSha256).toBe(sha(await readFile(dir+'/'+filename)));
  expect(v.savedComponentReopened).toBe(true);expect(v.originalGeometryPreserved).toBe(true);expect(v.unrelatedVisibilityPreserved).toBe(true);expect(v.originalObjectCount).toBe(5754);
  for(const name of a.ownedObjects)expect(proof.ownedObjects).toContain(name);
 }
 const pea=await read('result/blender/peacock_envelope_next/verification.json');
 expect(pea.registeredGlassFirstHits).toBe(11);expect(pea.nearFieldRealApertureClearanceProbes).toBe(11);
 expect(pea.wallApertureThroughProbes).toBe(18);expect(pea.reloadedWallApertureGrid.every(p=>!p.blocked)).toBe(true);
 expect(pea.glassGeometryAndUvPreserved).toBe(true);expect(pea.reloadedBrowserOpacityVerified).toBe(true);
 for(const hit of pea.reloadedBehindProbes)expect(hit.distance).toBeGreaterThan(2);
 const coop=await read('result/blender/coopers_envelope_next/verification.json');
 expect(coop.firstSurfaceChecks).toHaveLength(20);expect(coop.neighbour50GeometryAndVisibilityPreserved).toBe(true);expect(coop.originalCornerOculusPreserved).toBe(true);
 const five=await read('result/blender/five_lincolns_envelope_next/verification.json');
 expect(five.originalGeometryPreserved).toBe(true);expect(five.frontGlassProbeCount).toBe(44);expect(five.behindGlassProbeCount).toBe(44);expect(five.behindGlassHits).toEqual([]);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.objects).toBe(5784);
});

test('stage146 PEA49L overview and detail use identical compressed geometry UV PBR',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('146');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 const campus=await assetDocument('/models/campus.glb');
 for(const code of ['PEA','49L']){
  const detail=await assetDocument(catalogue.buildings.find(b=>b.code===code).detailedExterior.url),accepted=new Set(proof.ownedMaterialNames[code]);
  const overview=matchingPrimitives(campus,accepted),closeup=matchingPrimitives(detail,accepted);
  expect(closeup.length,code).toBeGreaterThan(0);expect(overview,code).toEqual(closeup);
  expect(new Set(closeup.map(p=>p.material)),code).toEqual(accepted);
  for(const p of closeup)expect(p.geometry.attributes.TEXCOORD_0,code+' '+p.material).toBeTruthy();
  if(code==='PEA'){
   const glass=closeup.filter(p=>p.material.includes('bounded_reflective_glass'));expect(glass.length).toBeGreaterThan(0);
   for(const p of glass){expect(p.alphaMode).toBe('BLEND');expect(p.pbr.baseColorFactor[3]).toBeCloseTo(.82,5);}
  }
 }
});

test('stage146 retains all other exteriors and every existing interior byte for byte',async()=>{
 const catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const b of catalogue.buildings){
  const p=before.buildings.find(o=>o.code===b.code);
  for(const key of ['detailedInterior','interiorStudy','interiorBounds','interiorView','interiorSpaces'])expect(b[key],b.code+' '+key).toEqual(p[key]);
  if(!['PEA','49L'].includes(b.code))for(const key of ['url','sha256','bytes'])expect(b.detailedExterior?.[key],b.code+' '+key).toEqual(p.detailedExterior?.[key]);
  for(const asset of [b.detailedInterior,...(b.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url))).toBe(asset.sha256);
 }
});

for(const width of [1440,390])test(`stage146 three reviewed buildings load their exterior and retained interior at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of ['PEA','49L','5LF']){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  await expect(page.locator('#interior-view')).toBeEnabled();await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
  await page.locator('#exterior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),code).toBe(true);
 }
 expect(errors).toEqual([]);
});

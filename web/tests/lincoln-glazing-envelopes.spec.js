import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const stage='result/blender/stage147';
const baselineSha='835b179c5bb32ecf3959ca6d9bf996ac92095fe42821fc42e7c2ddbf599b048a';
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


test('stage147 three townhouse envelopes retain independent native evidence',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.baselineSha256).toBe(baselineSha);expect(proof.retainedOriginalObjects).toBe(5784);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.unrelatedVisibilityPreserved).toBe(true);expect(proof.savedSceneReopened).toBe(true);
 const names=[],archives=[];
 for(const component of proof.components){
  const a=await read(component.audit),v=await read(component.verification);
  expect(a.baselineSha256).toBe(baselineSha);expect(v.componentSha256).toBe(sha(await readFile(component.source)));
  expect(v.savedComponentReopened).toBe(true);expect(v.originalGeometryPreserved).toBe(true);expect(v.unrelatedVisibilityPreserved).toBe(true);expect(v.originalObjectCount).toBe(5784);
  names.push(...a.ownedObjects);archives.push(...a.archivedObjects);
 }
 expect(proof.ownedObjects).toEqual(names);expect(proof.archivedObjects).toEqual(archives);
 const five=await read('result/blender/five_lincolns_glazing_next/verification.json');
 expect(five.reloadedFrontProbes).toHaveLength(44);expect(five.reloadedBehindProbes).toHaveLength(44);expect(five.rightPotProbes).toHaveLength(2);
 for(const p of five.reloadedBehindProbes)expect(p.firstHit.object).toBeNull();expect(five.webOpacityVerified).toBe(.78);
 const coop=await read('result/blender/coopers_glazing_next/verification.json');
 expect(coop.firstSurfaceChecks).toHaveLength(37);expect(coop.firstSurfaceChecks.filter(p=>p.noOpaqueNearfieldCap===true)).toHaveLength(31);
 expect(coop.fireexitLouvreOpaque).toBe(true);expect(coop.louvreFirstHits).toHaveLength(3);
 for(const p of coop.louvreFirstHits)expect(p.firstObject).toBe(p.expected);
 expect(coop.fireExitRoundLouvre.webOpacity).toBe(1);expect(coop.fireExitRoundLouvre.transmission).toBe(0);
 expect(coop.allGlazingGeometryAndUVRetained).toBe(true);expect(coop.sourceColorsPreserved).toBe(true);expect(coop.neighbour50GeometryAndVisibilityPreserved).toBe(true);
 const fifty=await read('result/blender/fifty_lincoln_glazing_next/verification.json');
 expect(fifty.glassFirstHits).toBe(14);expect(fifty.nearFieldGlassClearance).toBe(14);expect(fifty['50AupperGlassFirstHit']).toBe(true);expect(fifty['50AWallThroughProbes']).toBe(9);expect(fifty.reloadedBrowserOpacityVerified).toBe(true);expect(fifty.No50WindowBehindAtLeast2mClear).toBe(true);expect(fifty.No50WallThroughProbes).toHaveLength(6);
 for(const p of fifty.No50WallThroughProbes){expect(p.wallBlocked).toBe(false);expect(p.innerDepthReached).toBe(-2);}
 expect(fifty.nextStoreySillGap).toBeGreaterThan(.7);
 for(const p of fifty.reloadedBehindProbes)if(p.firstObject)expect(p.distance,p.label).toBeGreaterThan(2);
 for(const p of fifty['50ASolidLowerPanelAndSurroundAndNo50DoorChecks'])expect(p.firstObject,p.label).toBe(p.expected);
 const shared=await read('result/blender/fifty_lincoln_glazing_next/shared-upper-verification.json');
 expect(shared.parallelFourSourcesUntouched).toBe(true);expect(shared.No50TripleGlassFirstHits).toHaveLength(3);
 for(const p of shared.No50BehindClearance)if(p.firstObject)expect(p.distance,p.label).toBeGreaterThan(2);
 const fiftyAudit=await read('result/blender/fifty_lincoln_glazing_next/audit.json');
 expect(fiftyAudit.No50UpperWindowCorrection.photoTopCropped).toBe(true);expect(fiftyAudit.No50UpperWindowCorrection.bounds).toEqual([-1.91,1.91,4.3,6.32]);
 const registration=await read(stage+'/mar-plan-registration.json');expect(registration.fitMaxResidualMetres).toBeLessThan(.3);expect(registration.independentDiagonalMaxResidualMetres).toBeGreaterThan(2);expect(registration.highWingRegistrationAccepted).toBe(false);expect(registration.nativeGeometryChanged).toBe(false);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.objects).toBe(5784+names.length);
});

test('stage147 three townhouse envelopes overview and detail use identical compressed geometry UV PBR',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('147');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 const campus=await assetDocument('/models/campus.glb');
 for(const code of ['5LF','49L','50L']){
  const detail=await assetDocument(catalogue.buildings.find(b=>b.code===code).detailedExterior.url),accepted=new Set(proof.ownedMaterialNames[code]);
  const overview=matchingPrimitives(campus,accepted),closeup=matchingPrimitives(detail,accepted);
  expect(closeup.length,code).toBeGreaterThan(0);expect(overview,code).toEqual(closeup);
  expect(new Set(closeup.map(p=>p.material)),code).toEqual(accepted);
  for(const p of closeup)expect(p.geometry.attributes.TEXCOORD_0,code+' '+p.material).toBeTruthy();
  const glass=closeup.filter(p=>p.alphaMode==='BLEND');expect(glass.length).toBeGreaterThan(0);
  const opacity={'5LF':.78,'49L':.84,'50L':.82}[code];
  for(const p of glass)expect(p.pbr.baseColorFactor[3]).toBeCloseTo(opacity,5);
 }
});

test('stage147 retains all other exteriors and every existing interior byte for byte',async()=>{
 const catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const b of catalogue.buildings){
  const p=before.buildings.find(o=>o.code===b.code);
  for(const key of ['detailedInterior','interiorStudy','interiorBounds','interiorView','interiorSpaces'])expect(b[key],b.code+' '+key).toEqual(p[key]);
  if(!['5LF','49L','50L'].includes(b.code))for(const key of ['url','sha256','bytes'])expect(b.detailedExterior?.[key],b.code+' '+key).toEqual(p.detailedExterior?.[key]);
  for(const asset of [b.detailedInterior,...(b.interiorSpaces??[]).map(s=>s.detailedInterior)].filter(a=>a?.url&&a?.sha256))expect(sha(await readFile('dist'+asset.url))).toBe(asset.sha256);
 }
});

for(const width of [1440,390])test(`stage147 three reviewed buildings load their exterior and retained interior at ${width}px`,async({page})=>{
 const catalogue=await read('dist/models/catalogue.json');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of ['5LF','49L','50L']){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  if(catalogue.buildings.find(b=>b.code===code).detailedInterior){
   await expect(page.locator('#interior-view')).toBeEnabled();await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
   await page.locator('#exterior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  }else await expect(page.locator('#interior-view')).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),code).toBe(true);
 }
 expect(errors).toEqual([]);
});

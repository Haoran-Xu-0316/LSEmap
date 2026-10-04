import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const stage='result/blender/stage152';
const baselineSha='39376c7060856dd05b42596414e74a47d18a60828aba92a45f78c3d6fd842e19';
const changedCodes=['CLM','OLD'];
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



test('stage152 preserves originals and integrates independently verified exterior candidates',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.baselineSha256).toBe(baselineSha);expect(proof.retainedOriginalObjects).toBe(5868);
 for(const key of ['originalGeometryRetained','unrelatedVisibilityPreserved','savedSceneReopened'])expect(proof[key]).toBe(true);
 for(const component of proof.components){
  const audit=await read(component.audit),verified=await read(component.verification);
  expect(audit.baselineSha256).toBe(baselineSha);expect(verified.componentSha256).toBe(sha(await readFile(component.source)));
  expect(verified.originalObjectCount).toBe(5868);
  for(const key of ['savedComponentReopened','originalGeometryPreserved','unrelatedVisibilityPreserved'])expect(verified[key]).toBe(true);
  expect(component.objects).toBe(audit.ownedObjects.length);
  expect(audit.ownedObjects.every(name=>proof.ownedObjects.includes(name))).toBe(true);
  expect(audit.archivedObjects.every(name=>proof.archivedObjects.includes(name))).toBe(true);
 }
 const old=await read('result/blender/old_glazing152/verification.json');
 expect(old.glassPrincipalFaces).toBe(10);expect(old.glassFirstHitPassCount).toBe(40);expect(old.behind02To2mClearCount).toBe(40);
 expect(old.originalAndOwnedSurfaceEqual).toBe(true);expect(old.originalRGBRoughnessMetallicRetained).toBe(true);expect(old.explicitWebOpacity).toBe(.82);expect(old.previewViewed).toBe(true);
 const clm=await read('result/blender/clm_curved_dormer152/verification.json');
 expect(clm.checkCount).toBe(50);expect(clm.glazingGeometryUVAndMaterialsPreserved).toBe(true);expect(clm.priorFourAperturesPreserved).toBe(true);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');expect(rebuilt.exactFingerprintMatch).toBe(true);expect(rebuilt.objects).toBe(5868+proof.ownedObjects.length);
});

test('stage152 all accepted exterior geometry UV and materials match in overview and detail',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('152');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 const campus=await assetDocument('/models/campus.glb');
 for(const code of changedCodes){
  const detail=await assetDocument(catalogue.buildings.find(b=>b.code===code).detailedExterior.url),accepted=new Set(proof.ownedUsedMaterialNames[code]);
  const overview=matchingPrimitives(campus,accepted),closeup=matchingPrimitives(detail,accepted);
  expect(closeup.length,code).toBeGreaterThan(0);expect(overview,code).toEqual(closeup);
  expect(new Set(closeup.map(p=>p.material)),code).toEqual(accepted);
  const glass=closeup.filter(p=>p.alphaMode==='BLEND');expect(glass.length,code).toBeGreaterThan(0);
  for(const p of glass){expect(p.pbr.baseColorFactor[3],code).toBeGreaterThan(.5);expect(p.pbr.baseColorFactor[3],code).toBeLessThan(1);}
 }
});

test('stage152 retains existing interior and unrelated exterior assets exactly',async()=>{
 const before=await read(stage+'/catalogue-before.json'),current=await read('dist/models/catalogue.json');
 const previous=await read(stage+'/release-before.json');
 const priorCampusParts=new Set((previous.campusTransport?.parts??[]).map(part=>part.path));
 for(const b of current.buildings){
  const old=before.buildings.find(item=>item.code===b.code);
  for(const key of ['detailedInterior','interiorSpaces','interiorBounds'])expect(b[key],b.code+' '+key).toEqual(old[key]);
  if(!changedCodes.includes(b.code))expect(b.detailedExterior,b.code).toEqual(old.detailedExterior);
 }
 for(const [url,asset]of Object.entries(previous.assets)){
  if(!url.startsWith('/models/')||priorCampusParts.has(url)||url==='/models/campus.glb'||url==='/models/campus-parts.json'||url==='/models/catalogue.json'||changedCodes.some(code=>url.startsWith('/models/details/'+code.toLowerCase()+'-exterior-')))continue;
  expect(sha(await readFile('dist'+url)),url).toBe(asset.sha256);
 }
});

for(const width of [1440,390])test(`stage152 revised facades load at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of changedCodes){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),code).toBe(true);
 }
 expect(errors).toEqual([]);
});

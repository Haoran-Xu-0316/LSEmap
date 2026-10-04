import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const stage='result/blender/stage144';
const baselineSha='7cf90954936581f8b9416018f34ce06984464d8451fe8778a65d3c025181367d';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const parts=[
 ['OLD','old_student_services_next','old-student-services-component.blend',3],
 ['CBG','cbg_facade_registration_next','cbg-facade-registration-component.blend',9],
 ['OLD','old_ssc_room_next','old-ssc-room-component.blend',39],
];
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

test('stage144 OLD planting CBG facade and SSC retain verified native sources',async()=>{
 const proof=await read(stage+'/saved-verification.json');
 expect(proof.baselineSha256).toBe(baselineSha);
 expect(proof.retainedOriginalObjects).toBe(5694);
 expect(proof.originalGeometryRetained).toBe(true);
 expect(proof.unrelatedVisibilityPreserved).toBe(true);
 expect(proof.savedSceneReopened).toBe(true);
 for(const [code,folder,filename,count]of parts){
  const dir='result/blender/'+folder,audit=await read(dir+'/audit.json'),verified=await read(dir+'/verification.json');
  const source=dir+'/'+filename,component=proof.components.find(item=>item.source===source);
  expect(component,source).toBeTruthy();expect(component.code).toBe(code);expect(component.objects).toBe(count);
  expect(audit.baselineSha256,folder).toBe(baselineSha);
  expect(audit.ownedObjects,folder).toHaveLength(count);
  expect(verified.originalObjectCount,folder).toBe(5694);
  expect(verified.savedComponentReopened,folder).toBe(true);
  expect(verified.originalGeometryPreserved,folder).toBe(true);
  expect(verified.unrelatedVisibilityPreserved,folder).toBe(true);
  const digest=sha(await readFile(source));
  expect(verified.componentSha256,folder).toBe(digest);expect(component.sha256,folder).toBe(digest);
  for(const name of audit.ownedObjects)expect(proof.ownedObjects,folder).toContain(name);
  for(const name of audit.archivedObjects)expect(proof.archivedObjects,folder).toContain(name);
 }
 const old=await read('result/blender/old_student_services_next/verification.json');
 expect(old.reloadedProbes).toHaveLength(54);expect(old.retainedGlazingDoorStepsFirstContacts).toBe(true);expect(old.entranceApproachAndFrontWalkClear).toBe(true);
 const cbg=await read('result/blender/cbg_facade_registration_next/verification.json');
 expect(cbg.firstSurfaceChecks).toHaveLength(85);expect(cbg.windingCorrected).toBe(true);expect(cbg.glassMaterialsPreserved).toBe(true);expect(cbg.towerAndEndFacesPreserved).toBe(true);expect(cbg.fullModelSaved).toBe(false);
 const ssc=await read('result/blender/old_ssc_room_next/verification.json');
 expect(ssc.firstSurfaceChecks).toHaveLength(39);expect(ssc.ownedObjects).toBe(39);expect(ssc.embeddedImageTextures).toBe(0);expect(ssc.fullModelSaved).toBe(false);expect(ssc.roomDimensionsMeasured).toBe(false);
});

test('stage144 campus and detail share OLD planting and CBG compressed geometry UV PBR',async()=>{
 const proof=await read(stage+'/saved-verification.json'),catalogue=await read('dist/models/catalogue.json');
 expect(catalogue.version).toBe('144');expect(catalogue.sourceModelSha256).toBe(proof.sourceModelSha256);
 const campus=await assetDocument('/models/campus.glb');
 for(const code of ['OLD','CBG']){
  const building=catalogue.buildings.find(b=>b.code===code),detail=await assetDocument(building.detailedExterior.url);
  const allOwned=new Set(proof.ownedMaterialNames[code]);
  // OLD also owns SSC-room materials. Only materials actually exported in the
  // exterior participate in campus/detail parity; room materials stay separate.
  const accepted=new Set(detail.glb.materials.map(materialName).filter(name=>allOwned.has(name)));
  expect(accepted.size,code+' exterior owned materials').toBeGreaterThan(0);
  const overview=matchingPrimitives(campus,accepted),closeup=matchingPrimitives(detail,accepted);
  expect(closeup.length,code).toBeGreaterThan(0);expect(overview,code).toEqual(closeup);
  expect(new Set(closeup.map(p=>p.material)),code).toEqual(accepted);
  for(const primitive of closeup)expect(primitive.geometry.attributes.TEXCOORD_0,code+' '+primitive.material).toBeTruthy();
 }
});

test('stage144 preserves other exteriors and every existing interior while adding only OLD SSC',async()=>{
 const catalogue=await read('dist/models/catalogue.json'),before=await read(stage+'/catalogue-before.json');
 expect(catalogue.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));expect(catalogue.generatedTextures).toEqual(before.generatedTextures);
 for(const building of catalogue.buildings){
  const previous=before.buildings.find(b=>b.code===building.code);
  for(const key of ['detailedInterior','interiorStudy','interiorBounds','interiorView'])expect(building[key],building.code+' '+key).toEqual(previous[key]);
  const priorSpaces=previous.interiorSpaces??[],spaces=building.interiorSpaces??[];
  if(building.code==='OLD'){
   expect(spaces.filter(space=>space.id!=='old-ssc')).toEqual(priorSpaces);
   const added=spaces.filter(space=>space.id==='old-ssc');expect(added).toHaveLength(1);
   expect(priorSpaces.some(space=>space.id==='old-ssc')).toBe(false);
   expect(added[0].detailedInterior?.url).toBeTruthy();expect(added[0].detailedInterior?.sha256).toMatch(/^[a-f0-9]{64}$/);
  }else expect(building.interiorSpaces,building.code).toEqual(previous.interiorSpaces);
  if(!['OLD','CBG'].includes(building.code))for(const key of ['url','sha256','bytes'])expect(building.detailedExterior?.[key],building.code+' '+key).toEqual(previous.detailedExterior?.[key]);
  const assets=[building.detailedInterior,...spaces.map(space=>space.detailedInterior)];
  for(const asset of assets.filter(asset=>asset?.url&&asset?.sha256))expect(sha(await readFile('dist'+asset.url)),building.code+' '+asset.url).toBe(asset.sha256);
 }
});

for(const width of [1440,390])test(`stage144 OLD SSC production space loads and returns to existing views at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width,height:width===390?844:1000});await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
 await expect(page.locator('.detail-gallery img[src*="old-ssc-interior"]')).toHaveCount(1);
 await expect(page.locator('#interior-view')).toBeEnabled();await page.locator('#interior-view').click();
 await expect(page.locator('#interior-space option[value="old-ssc"]')).toHaveCount(1);
 await page.locator('#interior-space').selectOption('old-ssc');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD:old-ssc',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('#interior-space').selectOption('default');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD',{timeout:60000});
 await page.locator('#exterior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await page.goto('/#CBG');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CBG',{timeout:60000});await expect(page.locator('#fallback')).toBeHidden();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});


test('stage144 Portsmouth seven-tree component preserves original geometry and clear route',async()=>{
 const directory='result/blender/portsmouth_public_realm_next';
 const audit=await read(directory+'/audit.json'),verified=await read(directory+'/verification.json');
 const proof=await read(stage+'/saved-verification.json');
 const component=proof.components.find(part=>part.code==='SITE');
 expect(component.objects).toBe(3);
 const digest=sha(await readFile(directory+'/portsmouth-public-realm-component.blend'));
 expect(component.sha256).toBe(digest);expect(verified.componentSha256).toBe(digest);
 expect(verified.savedComponentReopened).toBe(true);
 expect(verified.originalGeometryUVMaterialSlotsPreserved).toBe(true);
 expect(verified.unrelatedVisibilityPreserved).toBe(true);
 expect(verified.allProtectedBuildingsGlobeRoadsPreserved).toBe(true);
 expect(verified.originalObjectCount).toBe(5694);
 expect(verified.registeredPoolFirstHits).toHaveLength(7);
 expect(verified.corridorFirstHits).toHaveLength(48);
 expect(audit.registration.anchors).toHaveLength(4);
 expect(audit.registration.treeCentres).toHaveLength(7);
 expect(audit.registration.maxResidualMetres).toBeLessThan(.57);
 expect(audit.buildingPoolClearanceMinimumMetres).toBeGreaterThan(2.1);
 expect(audit.archivedObjects).toEqual([]);
 expect(audit.dimensionsEstimated.poolOuterDiameter).toBe(1.44);
 const campus=await assetDocument('/models/campus.glb');
 const materials=new Set(proof.ownedMaterialNames.SITE);
 const primitives=matchingPrimitives(campus,materials);
 expect(primitives.length).toBeGreaterThan(0);
 expect(new Set(primitives.map(p=>p.material))).toEqual(materials);
 const rebuilt=await read(stage+'/rebuild/rebuild-verification.json');
 expect(rebuilt.savedSceneReopened).toBe(true);expect(rebuilt.exactFingerprintMatch).toBe(true);
 expect(rebuilt.objects).toBe(5748);
});

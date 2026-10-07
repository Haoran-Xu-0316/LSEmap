import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
async function model(url){const b=await readFile('dist'+url);return JSON.parse(b.subarray(20,20+b.readUInt32LE(12)));}

test('facade and street release preserves glass and independent rooms',async()=>{
 const before=await read('result/blender/stage165/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage165/building-refinement.json');
 const glass=await read('result/blender/stage164/building-refinement.json');
 const native=await read('result/blender/stage165/reopened-verification.json');
 expect(current.version).toBe('165');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.allMeshSignaturesVerified).toBe(true);expect(native.idempotent).toBe(true);
 expect(native.originalSharedMaterialsPreserved).toBe(true);
 expect(native.glassBindingsVerified).toBe(8);expect(native.externalDependencies).toBe(false);
 expect(proof.objects).toBe(5985);expect(proof.allUnrelatedMeshesPreserved).toBe(true);
 expect(proof.changes).toHaveLength(3);expect(proof.archivedObjects).toHaveLength(15);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['MAR','OLD'].includes(building.code))expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 const campus=await model('/models/campus.glb');
 // The exporter joins components into semantic building meshes.
 expect(campus.materials.some(m=>m.name.endsWith('SITE165_Houghton_black_cast_iron'))).toBe(true);
 const mar=await model(current.buildings.find(b=>b.code==='MAR').detailedExterior.url);
 for(const doc of [campus,mar])expect(doc.materials.some(m=>m.name.endsWith('MAR_LETTER165_dark_bronze'))).toBe(true);
 expect(native.archivedObjects).toEqual(proof.archivedObjects);
 for(const code of ['CKK','LRB']){
  const building=current.buildings.find(b=>b.code===code);
  const detail=await model(building.detailedExterior.url);
  const name=code+'_GLASS164_legacy_dielectric';
  const source=glass.changes[0].originalSourceMaterials[glass.changes[0].bindings.find(b=>b.material===name).sourceMaterial];
  for(const doc of [detail,campus]){
   const material=doc.materials.find(m=>m.name.endsWith(name));expect(material).toBeTruthy();
   expect(material.pbrMetallicRoughness.metallicFactor??0).toBe(0);
   expect(material.pbrMetallicRoughness.baseColorFactor).toEqual(source.color);
   expect(material.pbrMetallicRoughness.roughnessFactor).toBeCloseTo(source.roughness,5);
   expect(material.alphaMode??'OPAQUE').toBe('OPAQUE');
  }
 }
 const ckk=current.buildings.find(b=>b.code==='CKK');
 for(const asset of [ckk.detailedExterior,ckk.detailedInterior]){
  const doc=await model(asset.url);const material=doc.materials.find(m=>m.name.endsWith('CKK_GLASS164_clear_atrium'));
  expect(material).toBeTruthy();expect(material.alphaMode).toBe('BLEND');
  expect(material.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.16,4);
  expect(material.pbrMetallicRoughness.metallicFactor??0).toBe(0);
  expect(material.extensions?.KHR_materials_transmission).toBeUndefined();
 }
});

for(const width of [1440,390])test(`MAR and OLD navigation remains usable at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of ['MAR','OLD']){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await page.locator('.detail-gallery img[src*="'+code.toLowerCase()+'-exterior"]').click();
  await page.waitForFunction(()=>{const i=document.querySelector('#gallery-image');return i?.complete&&i.naturalWidth>0});
  await page.locator('#gallery-dialog [data-close]').click();await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});

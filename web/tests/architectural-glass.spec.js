import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
async function model(url){const b=await readFile('dist'+url);return JSON.parse(b.subarray(20,20+b.readUInt32LE(12)));}

test('architectural glass preserves shapes, shared materials and independent rooms',async()=>{
 const before=await read('result/blender/stage164/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage164/building-refinement.json');
 const native=await read('result/blender/stage164/reopened-verification.json');
 expect(current.version).toBe('164');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.allShapesAndUVsPreserved).toBe(true);
 expect(native.originalSharedMaterialsPreserved).toBe(true);
 expect(native.bindingsVerified).toBe(8);expect(native.externalDependencies).toBe(false);
 expect(proof.objects).toBe(5966);expect(proof.allUnrelatedMeshesPreserved).toBe(true);
 expect(proof.changes[0].changedObjects).toHaveLength(8);expect(proof.changes[0].addedObjects).toEqual([]);
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(['CKK','LRB'].includes(building.code))expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  if(building.code==='CKK')expect(building.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
  else expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
 }
 const campus=await model('/models/campus.glb');
 for(const code of ['CKK','LRB']){
  const building=current.buildings.find(b=>b.code===code);
  const detail=await model(building.detailedExterior.url);
  const name=code+'_GLASS164_legacy_dielectric';
  const source=proof.changes[0].originalSourceMaterials[proof.changes[0].bindings.find(b=>b.material===name).sourceMaterial];
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

for(const width of [1440,390])test(`CKK and LRB navigation remains usable at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.setViewportSize({width,height:1000});
 for(const code of ['CKK','LRB']){
  await page.goto('/#'+code);await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
  await page.locator('.detail-gallery img[src*="'+code.toLowerCase()+'-exterior"]').click();
  await page.waitForFunction(()=>{const i=document.querySelector('#gallery-image');return i?.complete&&i.naturalWidth>0});
  await page.locator('#gallery-dialog [data-close]').click();await page.locator('#interior-view').click();
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-'+code,{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});

import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async p=>JSON.parse(await readFile(p,'utf8'));

test('OLD wall lantern preserves every existing mesh and room export',async()=>{
 const before=await read('result/blender/stage163/catalogue-before.json');
 const current=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage163/building-refinement.json');
 const native=await read('result/blender/stage163/reopened-verification.json');
 expect(current.version).toBe('163');expect(current.buildings).toHaveLength(31);
 expect(current.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.sourceModelSha256).toBe(proof.sourceModelSha256);
 expect(native.allMeshSignaturesVerified).toBe(true);
 expect(native.lampBackFaceMeetsRegisteredWall).toBe(true);
 expect(native.externalDependencies).toBe(false);
 expect(proof.objects).toBe(5966);expect(proof.allUnrelatedMeshesPreserved).toBe(true);
 expect(proof.changes[0].changedObjects).toEqual([]);
 expect(proof.changes[0].addedObjects).toEqual(['OLD_LANTERN163_blue_frame','OLD_LANTERN163_opal_shade']);
 expect(proof.changes[0].lampCount).toBe(1);
 expect((await read('dist/release.json')).campusTransport.sha256).not.toBe((await read('result/blender/stage163/release-before.json')).campusTransport.sha256);
 let extraRooms=0;
 for(const building of current.buildings){
  const old=before.buildings.find(b=>b.code===building.code);
  if(building.code==='OLD')expect(building.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
  else expect(building.detailedExterior,building.code).toEqual(old.detailedExterior);
  expect(building.detailedInterior,building.code).toEqual(old.detailedInterior);
  expect(building.interiorSpaces,building.code).toEqual(old.interiorSpaces);
  extraRooms+=(building.interiorSpaces??[]).length;
 }
 expect(extraRooms).toBe(9);
 const asset=current.buildings.find(b=>b.code==='OLD').detailedExterior;
 const bytes=await readFile('dist'+asset.url);
 const glb=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
 const lamp=glb.materials.filter(m=>m.name.includes('OLD_LANTERN163_'));
 expect(lamp).toHaveLength(2);
 for(const m of lamp){
  expect(m.pbrMetallicRoughness.metallicFactor??0).toBe(0);
  expect(m.extensions?.KHR_materials_transmission).toBeUndefined();
  expect(m.emissiveFactor??[0,0,0]).toEqual([0,0,0]);
 }
 const shade=lamp.find(m=>m.name.includes('opal'));
 expect(shade.alphaMode).toBe('BLEND');
 expect(shade.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(.68,4);
});

for(const width of [1440,390])test(`OLD entrance and room navigation remain usable at ${width}px`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width,height:1000});await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 await page.waitForFunction(()=>{const i=document.querySelector('#gallery-image');return i?.complete&&i.naturalWidth>0});
 await page.locator('#gallery-dialog [data-close]').click();
 await page.locator('#interior-view').click();
 for(const id of ['old-ssc','default']){
  await page.locator('#interior-space').selectOption(id);
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-OLD'+(id==='default'?'':':'+id),{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});

import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved OLD Final Sale retain geometry and all other building assets',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage84/old-final-sale-audit.json'));
 expect(a.savedMeasurements.originalGeometryAndMaterialsUnchanged).toBeTruthy();
 expect(a.savedMeasurements.figures).toBe(6);
 expect(a.savedMeasurements.shoppingContainers).toBe(3);
 expect(a.savedMeasurements.latticeHasGeometricOpenings).toBeTruthy();
 const before=JSON.parse(await readFile('result/blender/stage84/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='OLD')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});
test('OLD overview and detail share plastic mesh materials',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const url of ['/models/campus.glb',c.buildings.find(b=>b.code==='OLD').detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  for(const key of ['figures','products','containers','glazing'])expect(materials.some(m=>m.name.endsWith('OLD_V84_FinalSale_'+key)),key).toBeTruthy();
 }
});
test('OLD Final Sale exterior and close gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-relief"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

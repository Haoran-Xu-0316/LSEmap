import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved SAW curtain walls retain geometry and all other building assets',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage82/saw-curtain-audit.json'));
 expect(a.savedMeasurements.originalGeometryAndMaterialsUnchanged).toBeTruthy();
 expect(a.savedMeasurements.facadeCount).toBe(4);
 expect(a.savedMeasurements.paneCount).toBe(125);
 const before=JSON.parse(await readFile('result/blender/stage82/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='SAW')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});
test('SAW overview and detail share the timber curtain wall materials',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const url of ['/models/campus.glb',c.buildings.find(b=>b.code==='SAW').detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='SAW')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  for(const key of ['jatoba','glass','seal'])expect(materials.some(m=>m.name.endsWith('SAW_V82_'+key)),key).toBeTruthy();
 }
});
test('SAW timber curtain exterior and close gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#SAW');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SAW',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="saw-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

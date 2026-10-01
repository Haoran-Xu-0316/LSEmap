import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved OLD casements retain geometry and all other building assets',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage85/old-casement-audit.json'));
 expect(a.savedMeasurements.originalGeometryAndMaterialsUnchanged).toBeTruthy();
 expect(a.savedMeasurements.fourColumnCasements).toBe(24);
 expect(a.savedMeasurements.verticalMembers).toBe(72);
 expect(a.savedMeasurements.horizontalMembers).toBe(77);
 expect(a.savedMeasurements.retainedOtherWindows).toBeTruthy();
 const before=JSON.parse(await readFile('result/blender/stage85/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const b of before.buildings){
  const current=after.buildings.find(c=>c.code===b.code);
  if(b.code!=='OLD')expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }
});
test('OLD overview and detail share casement and retained mesh materials',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const url of ['/models/campus.glb',c.buildings.find(b=>b.code==='OLD').detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const materials=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material]);
  expect(materials.some(m=>m.name.endsWith('OLD_V85_four_column_blue'))).toBeTruthy();
  expect(materials.some(m=>m.name.endsWith('OLD_V84_FinalSale_figures'))).toBeTruthy();
 }
});
test('OLD casement exterior and close gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-entablature"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

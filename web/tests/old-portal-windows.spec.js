import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved OLD portal relocates only two ground windows and preserves protected geometry',async()=>{
 const a=JSON.parse(await readFile('result/blender/stage78/old-portal-windows-audit.json'));
 expect(a.savedMeasurements.windows).toBe(2);
 expect(a.savedMeasurements.columns).toBe(2);
 expect(a.savedMeasurements.rows).toBe(4);
 expect(a.savedMeasurements.portalWindowAxes).toEqual([-3.55,3.55]);
 expect(a.savedMeasurements.protectedVerticesUnchanged).toBeTruthy();
 expect(a.savedMeasurements.otherBuildingsAndInteriorsUnchanged).toBeTruthy();
 const before=JSON.parse(await readFile('result/blender/stage78/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const old of before.buildings){
  const current=after.buildings.find(b=>b.code===old.code);
  if(old.code!=='OLD')expect(current.detailedExterior?.url).toBe(old.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(old.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(old.interiorSpaces);
 }
});
test('overview and OLD detail both include recessed portal window materials',async()=>{
 const c=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=c.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','blue','glass'])expect(names.some(n=>n.endsWith('OLD_V78_'+key))).toBeTruthy();
 }
});
test('OLD portal exterior and refreshed gallery load without errors',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-houghton-entrance"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

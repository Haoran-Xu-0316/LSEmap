import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
test('saved heraldry preserves original geometry and stays inside reserved shield',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage74/old-heraldic-device-audit.json'));
 expect(audit.changedExistingGeometry).toEqual([]);
 expect(audit.savedMeasurements.withinReservedShield).toBeTruthy();
 expect(audit.savedMeasurements.bookCount).toBe(2);
 expect(audit.savedMeasurements.beaverCount).toBe(1);
 expect(audit.savedMeasurements.mottoRetained).toBeTruthy();
});
test('campus and OLD close model share corrected stone heraldic materials',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=catalogue.buildings.find(b=>b.code==='OLD');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='OLD')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','incision','field'])expect(names.some(n=>n.endsWith('OLD_V74_'+key))).toBeTruthy();

 }
});

test('OLD exterior and refreshed gallery load in the browser',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#OLD');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="old-heraldry"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

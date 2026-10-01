import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved No.50 portal removes neighboring round windows and preserves existing geometry',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage72/fifty-lincoln-portal-audit.json'));
 expect(audit.savedMeasurements.changedOriginalObjects).toEqual([]);
 expect(audit.savedMeasurements.obsoleteRoundelsAndRadialBarsHidden).toBeTruthy();
 expect(audit.savedMeasurements.panelCenters).toHaveLength(6);
 expect(audit.savedMeasurements.topStepHeight).toBe(.26);
});

test('campus and No.50 close model share corrected sandstone, timber and hardware',async()=>{
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json'));
 const building=catalogue.buildings.find(b=>b.code==='50L');
 for(const url of ['/models/campus.glb',building.detailedExterior.url]){
  const bytes=await readFile('dist'+url);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  const node=doc.nodes.find(n=>n.extras?.buildingCode==='50L')??doc.nodes.find(n=>n.mesh!==undefined);
  const names=doc.meshes[node.mesh].primitives.map(p=>doc.materials[p.material].name);
  for(const key of ['stone','wood','glass','iron','brass','steel','step'])expect(names.some(n=>n.endsWith('50L_V72_'+key))).toBeTruthy();
  expect(names.some(n=>n.endsWith('EXT20_bronze'))).toBeFalsy();
 }
});

test('No.50 entry and refreshed gallery load in the browser',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#50L');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-50L',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="50l-entrance"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

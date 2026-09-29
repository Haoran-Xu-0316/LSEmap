import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('current edition preserves unrelated assets after LRB and CLM revisions',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition35-models.json','utf8'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(after.version).toBe('43');
 for(const building of after.buildings){
  expect(building.interiorSpaces??null,`${building.code}:rooms`).toEqual(before[building.code].interiorSpaces);
  for(const key of ['detailedInterior','detailedExterior']){
   if(building.code==='LRB')expect(building[key].sha256,key).not.toBe(before.LRB[key].sha256);
   else if(building.code==='CLM' && key==='detailedExterior')expect(building[key].sha256).not.toBe(before[building.code][key].sha256);
   else expect(building[key]??null,`${building.code}:${key}`).toEqual(before[building.code][key]);
  }
 }
});

test('LRB G-layer correction is available in the interactive interior and survives overview',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
 await page.locator('#interior-level').selectOption('G');
 await expect(page.locator('canvas')).toHaveAttribute('data-interior-section','G');
 await page.waitForTimeout(1000);
 await page.screenshot({path:'result/web/release36/lrb-ground.png'});
 await page.locator('#overview').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-campus-details',/LRB/);
 expect(errors).toEqual([]);
});

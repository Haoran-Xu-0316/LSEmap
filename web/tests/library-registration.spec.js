import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('registered LRB core and CLM tint preserve unrelated assets',async()=>{
 const baseline=JSON.parse(await readFile('web/tests/fixtures/edition37-models.json','utf8'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(catalogue.version).toBe('43');
 const lrb=catalogue.buildings.find(b=>b.code==='LRB');
 expect(lrb.interiorView.position[0]).toBeCloseTo(75.5933868,3);
 expect(lrb.interiorView.position[1]).toBeCloseTo(-2.5,3);
 expect(lrb.detailedExterior.bounds.min[1]).toBeGreaterThan(-.001);
 expect(lrb.detailedInterior.bounds.min[1]).toBeLessThan(-4);
 for(const b of catalogue.buildings){
  expect(b.interiorSpaces??null,`${b.code}:rooms`).toEqual(baseline[b.code].interiorSpaces);
  for(const key of ['detailedExterior','detailedInterior']){
   if(b.code==='LRB')expect(b[key].sha256).not.toBe(baseline[b.code][key].sha256);
   else if(b.code==='CLM' && key==='detailedExterior')expect(b[key].sha256).not.toBe(baseline[b.code][key].sha256);
   else expect(b[key]??null,`${b.code}:${key}`).toEqual(baseline[b.code][key]);
  }
 }
});

test('registered library opens from the campus and renders the G and fourth floor cuts',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
 for(const level of ['G','4']){
  await page.locator('#interior-level').selectOption(level);
  await expect(page.locator('canvas')).toHaveAttribute('data-interior-section',level);
  await page.waitForTimeout(1000);
  await page.screenshot({path:`result/web/release38/lrb-${level}.png`});
 }
 await page.locator('#overview').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-campus-details',/LRB/);
 expect(errors).toEqual([]);
});

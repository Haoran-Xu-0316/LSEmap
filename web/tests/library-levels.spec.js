import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('calibrated LRB levels retain basement only in interior and preserve unrelated assets',async()=>{
 const before=JSON.parse(await readFile('web/tests/fixtures/edition36-models.json','utf8'));
 const catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
 expect(catalogue.version).toBe('43');
 const lrb=catalogue.buildings.find(b=>b.code==='LRB');
 expect(lrb.detailedInterior.bounds.min[1]).toBeLessThan(-3.9);
 expect(lrb.detailedExterior.bounds.min[1]).toBeGreaterThanOrEqual(-.1);
 expect(lrb.interiorSections.find(s=>s.id==='LG').maxHeight).toBeCloseTo(-.08);
 expect(lrb.interiorSections.find(s=>s.id==='G').minHeight).toBeCloseTo(-.02);
 for(const b of catalogue.buildings){
  expect(b.interiorSpaces??null,`${b.code}:rooms`).toEqual(before[b.code].interiorSpaces);
  for(const key of ['detailedExterior','detailedInterior']){
   if(b.code==='LRB')expect(b[key].sha256).not.toBe(before[b.code][key].sha256);
   else if(b.code==='CLM' && key==='detailedExterior')expect(b[key].sha256).not.toBe(before[b.code][key].sha256);
   else expect(b[key]??null,`${b.code}:${key}`).toEqual(before[b.code][key]);
  }
 }
});

test('LRB underground and ground slices render with the corrected labels and heights',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#LRB');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
 await page.locator('#interior-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-LRB',{timeout:60000});
 for(const id of ['LG','G']){
  await page.locator('#interior-level').selectOption(id);
  await expect(page.locator('canvas')).toHaveAttribute('data-interior-section',id);
  await page.waitForTimeout(1000);
  await page.screenshot({path:`result/web/release37/lrb-${id}.png`});
 }
 await page.locator('#exterior-view').click();
 await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-section');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB');
 expect(errors).toEqual([]);
});

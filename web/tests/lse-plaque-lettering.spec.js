import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('vector plaque release preserves facade and interior references',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage100/plaque-lettering-audit.json'));
 for(const value of Object.values(audit.savedMeasurements))expect(value).toBeTruthy();
 expect(audit.plaques.map(p=>p.code).sort()).toEqual(['COL','OLD','OLD']);
 const before=JSON.parse(await readFile('result/blender/stage100/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('100');
 for(const b of before.buildings){
  const current=after.buildings.find(x=>x.code===b.code);
  if(['OLD','COL'].includes(b.code))expect(current.detailedExterior.url).not.toBe(b.detailedExterior.url);
  else expect(current.detailedExterior?.url).toBe(b.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(b.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(b.interiorSpaces);
 }

});
for(const code of ['OLD','COL'])test(code+' vector plaques and entrance gallery load',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#'+code);
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 const name=code==='OLD'?'old-houghton-entrance':'col-garrick-entrance';
 await page.locator('.detail-gallery img[src*="'+name+'"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

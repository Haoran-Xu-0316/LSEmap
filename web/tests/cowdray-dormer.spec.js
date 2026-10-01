import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('Cowdray attic rail correction preserves other exterior and interior references',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage98/cowdray-dormer-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.retainedSashVerticesUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.closedNewRails).toBeTruthy();
 expect(audit.savedMeasurements.dormerWindows).toHaveLength(11);
 expect(audit.savedMeasurements.railCount).toBe(44);
 const before=JSON.parse(await readFile('result/blender/stage98/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 expect(after.version).toBe('98');
 for(const building of before.buildings){
  const current=after.buildings.find(b=>b.code===building.code);
  if(building.code!=='COW')expect(current.detailedExterior?.url).toBe(building.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(building.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(building.interiorSpaces);
 }
 expect(after.buildings.find(b=>b.code==='COW').detailedExterior.url).not.toBe(before.buildings.find(b=>b.code==='COW').detailedExterior.url);
});

test('Cowdray revised exterior and gallery load without model fallback',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#COW');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-COW',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="cow-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});

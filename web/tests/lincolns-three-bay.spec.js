import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved 51L frontage has three openings on each floor and preserves other models',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage92/lincolns-three-bay-audit.json'));
 expect(audit.savedMeasurements.originalObjectsUnchanged).toBeTruthy();
 expect(audit.savedMeasurements.closedNewComponents).toBeTruthy();
 expect(audit.savedMeasurements.rightEntryVerified).toBeTruthy();
 expect(audit.savedMeasurements.fineVerticalBars).toBe(30);
 expect(audit.savedMeasurements.horizontalRails).toBe(72);
 expect(audit.savedMeasurements.retainedOtherComponents).toHaveLength(32);
 const openings=audit.savedMeasurements.openings;
 expect(openings).toHaveLength(18);
 for(let floor=0;floor<6;floor++)expect(openings.filter(o=>o.floor===floor)).toHaveLength(3);
 const before=JSON.parse(await readFile('result/blender/stage92/catalogue-before.json'));
 const after=JSON.parse(await readFile('dist/models/catalogue.json'));
 for(const building of before.buildings){
  const current=after.buildings.find(b=>b.code===building.code);
  if(building.code!=='51L')expect(current.detailedExterior?.url).toBe(building.detailedExterior?.url);
  expect(current.detailedInterior?.url).toBe(building.detailedInterior?.url);
  expect(current.interiorSpaces).toEqual(building.interiorSpaces);
 }
 expect(after.buildings.find(b=>b.code==='51L').detailedExterior.url).not.toBe(before.buildings.find(b=>b.code==='51L').detailedExterior.url);
});

test('51L reviewed frontage and gallery load without fallback',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/#51L');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-51L',{timeout:60000});
 await expect(page.locator('#fallback')).toBeHidden();
 await page.locator('.detail-gallery img[src*="51l-exterior"]').click();
 await expect(page.locator('#gallery-image')).toBeVisible();
 expect(await page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
 expect(errors).toEqual([]);
});
